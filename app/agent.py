"""Agent management utilities for QUANTUM MIND."""

import logging
import os
import re
import threading
import time
import unicodedata
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

try:
    import requests
except ImportError:
    requests = None

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GenerationConfig = None
    GENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


class QuantumMindAgent:
    """AI Agent with tool selection and search capabilities."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = 'gemini-2.5-flash-lite',
        temperature: float = 0.5,
    ) -> None:
        self.api_key = api_key or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        self.model = model
        self.temperature = temperature
        
        # Search configuration
        self.search_api_key = os.getenv('SERPAPI_KEY')
        self.search_engine = os.getenv('SEARCH_ENGINE', 'serpapi')
        self.hf_token = os.getenv('HF_TOKEN')
        
        # Tool settings
        self.max_arxiv_results = int(os.getenv('MAX_ARXIV_RESULTS', '3'))
        
        # Tool state tracking
        self._tool_cooldowns: Dict[str, float] = {}
        self._last_tool_used: str | None = None
        self._last_tool_assessments: Dict[str, Dict[str, Any]] = {}
        
        # MT-Bench cache
        self._mt_bench_cache: List[Dict[str, Any]] = []
        self._mt_bench_cache_timestamp: float = 0.0
        
        # Cache intelligent pour résultats (TTL: 1h)
        self._result_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl: int = 3600
        
        # arXiv stopwords
        self._arxiv_stopwords = {
            'les', 'des', 'aux', 'sur', 'pour', 'dans', 'avec', 'une', 'un', 'le', 'la',
            'derniers', 'dernieres', 'dernier', 'derniere', 'quels', 'quelles', 'quel', 'quelle',
            'donne', 'donnez', 'donner', 'montre', 'montrer', 'liste', 'lister', 'sont',
            'est', 'and', 'the', 'of', 'in', 'to', 'for', 'on', 'with', 'at', 'by', 'from',
        }
        
        # Curated MT-Bench baseline data
        self.CURATED_MT_BENCH: List[Dict[str, Any]] = [
            {'model': 'GPT-4 Turbo', 'size': '?', 'mt_bench': 9.32, 'mmlu': None, 'source': 'LMSYS', 'date': '2024-04', 'link': 'https://chat.lmsys.org/?leaderboard', 'aliases': {'gpt-4-turbo', 'gpt4-turbo'}},
            {'model': 'Claude 3.5 Sonnet', 'size': '?', 'mt_bench': 9.0, 'mmlu': 88.7, 'source': 'Anthropic', 'date': '2024-10', 'link': 'https://www.anthropic.com/news/claude-3-5-sonnet', 'aliases': {'claude-3.5-sonnet', 'claude-sonnet'}},
            {'model': 'Gemini 1.5 Pro', 'size': '?', 'mt_bench': 8.63, 'mmlu': 85.9, 'source': 'Google', 'date': '2024-05', 'link': 'https://deepmind.google/technologies/gemini/', 'aliases': {'gemini-1.5-pro', 'gemini-pro'}},
            {'model': 'Llama-3.1-405B-Instruct', 'size': '405B', 'mt_bench': 8.62, 'mmlu': 88.6, 'source': 'Meta', 'date': '2024-07', 'link': 'https://ai.meta.com/blog/meta-llama-3-1/', 'aliases': {'llama-3.1-405b', 'llama-405b'}},
            {'model': 'Mistral Large 2', 'size': '123B', 'mt_bench': 8.47, 'mmlu': 84.0, 'source': 'Mistral', 'date': '2024-07', 'link': 'https://mistral.ai/news/mistral-large-2407/', 'aliases': {'mistral-large-2', 'mistral-large'}},
            {'model': 'Qwen2.5-72B-Instruct', 'size': '72B', 'mt_bench': 8.41, 'mmlu': 85.3, 'source': 'Alibaba', 'date': '2024-09', 'link': 'https://qwenlm.github.io/blog/qwen2.5/', 'aliases': {'qwen2.5-72b', 'qwen-72b'}},
        ]
        
        # Configure Google AI if available
        if GENAI_AVAILABLE and self.api_key:
            genai.configure(api_key=self.api_key)
        
        # Build tool configurations
        self.tool_configs = self._build_tool_configs()
        
        # Enable all tools by default
        self.tools_enabled = {name: True for name in self.tool_configs.keys()}

    def _normalize_for_matching(self, text: str) -> str:
        """Normalize text for keyword matching."""
        normalized = unicodedata.normalize('NFKD', text)
        normalized = normalized.encode('ascii', 'ignore').decode('ascii')
        return normalized.lower()

    def _compute_tool_score(
        self,
        tool_name: str,
        normalized: str,
        tokens: set[str],
    ) -> Dict[str, Any]:
        config = self.tool_configs.get(tool_name, {})
        strong = config.get('strong_keywords', set()) or set()
        weak = config.get('weak_keywords', set()) or set()
        strong_hits = {kw for kw in strong if kw in normalized}
        weak_hits = {kw for kw in weak if kw in normalized and kw not in strong_hits}

        # Score de base
        score = len(strong_hits) * config.get('strong_weight', 2) + len(weak_hits) * config.get('weak_weight', 1)
        
        # Bonus contexte académique (favorise arXiv)
        academic_indicators = {'paper', 'article', 'publication', 'research', 'conference', 'preprint'}
        if tool_name == 'arxiv_lookup' and any(ind in normalized for ind in academic_indicators):
            score += 1
        
        # Bonus contexte industriel (favorise HuggingFace)
        industry_indicators = {'model', 'checkpoint', 'deployment', 'production', 'api'}
        if tool_name == 'huggingface_models' and any(ind in normalized for ind in industry_indicators):
            score += 1

        if score < config.get('min_score', 1) and config.get('token_overlaps'):
            overlaps = {token for token in tokens if token in config['token_overlaps']}
            if overlaps:
                weak_hits |= overlaps
                score += len(overlaps)

        if score < config.get('min_score', 1) and config.get('min_length_trigger'):
            if len(normalized) >= config['min_length_trigger']:
                score = config.get('min_score', 1)

        return {
            'score': score,
            'strong_hits': strong_hits,
            'weak_hits': weak_hits,
        }

    def _contains_refresh_keyword(self, normalized: str, config: Dict[str, Any]) -> bool:
        refresh = config.get('refresh_keywords') or set()
        return any(keyword in normalized for keyword in refresh)

    def _assess_tool_query(
        self,
        tool_name: str,
        query: str,
        normalized: str | None = None,
        tokens: set[str] | None = None,
        consider_cooldown: bool = True,
    ) -> Dict[str, Any]:
        config = self.tool_configs.get(tool_name, {})
        if not config:
            return {'should_run': False, 'score': 0, 'threshold': 0, 'reason': 'tool_not_configured'}

        normalized_text = normalized or self._normalize_for_matching(query)
        token_set = tokens or set(normalized_text.split())
        scores = self._compute_tool_score(tool_name, normalized_text, token_set)

        min_score = config.get('min_score', 1)
        should_run = scores['score'] >= min_score
        reason = 'score_threshold_met' if should_run else 'score_below_threshold'

        now = time.time()
        cooldown = config.get('cooldown', 0)
        if should_run and consider_cooldown and cooldown:
            last_used = self._tool_cooldowns.get(tool_name)
            if last_used and (now - last_used) < cooldown:
                if not self._contains_refresh_keyword(normalized_text, config):
                    should_run = False
                    reason = 'cooldown'
                else:
                    reason = 'cooldown_override'

        if should_run and consider_cooldown and self._last_tool_used == tool_name:
            # Avoid hammering the same tool if the request doesn't explicitly ask for updates
            if not self._contains_refresh_keyword(normalized_text, config):
                if scores['score'] > min_score:
                    reason = 'recent_repeat_allowed'
                else:
                    reason = 'recent_repeat'
                    should_run = False

        assessment = {
            'should_run': should_run,
            'score': scores['score'],
            'threshold': min_score,
            'reason': reason,
            'strong_hits': scores['strong_hits'],
            'weak_hits': scores['weak_hits'],
            'timestamp': now,
        }

        self._last_tool_assessments[tool_name] = assessment
        logger.debug(
            "Tool assessment for %s | score=%s threshold=%s reason=%s strong=%s weak=%s",
            tool_name,
            assessment['score'],
            min_score,
            reason,
            ','.join(sorted(assessment['strong_hits'])),
            ','.join(sorted(assessment['weak_hits'])),
        )
        return assessment

    def _register_tool_usage(self, tool_name: str) -> None:
        self._tool_cooldowns[tool_name] = time.time()
        self._last_tool_used = tool_name

    def _build_tool_configs(self) -> Dict[str, Dict[str, Any]]:
        """Return the keyword strategy for each tool."""
        refresh_terms = {'actualise', 'mise a jour', 'maj', 'update', 'refresh', 'nouveau', 'nouvelle', 'nouveaux', 'nouvelles'}

        return {
            'google_search': {
                'label': '🌐 Résultats web',
                'handler': self._perform_web_search,
                'formatter': self._format_search_results,
                'requires_requests': True,
                'requires_api_key': 'search_api_key',
                'predicate': lambda: isinstance(self.search_engine, str) and self.search_engine.lower() == 'serpapi',
                'strong_keywords': {
                    'derniere actualite', 'dernieres actualites', 'breaking news',
                    'annonce officielle', 'reglementation', 'regulation', 'legislation',
                    'loi ia', 'lois ia', 'urgence', 'alerte', 'openai announcement'
                },
                'weak_keywords': {
                    'quoi', 'quand', 'comment', 'pourquoi', 'combien', 'meteo',
                    'weather', 'prix', 'cout', 'couts', 'news', 'actualite',
                    'actualites', 'trend', 'tendance', 'update', 'nouveaute'
                },
                'min_score': 2,
                'min_length_trigger': 80,
                'cooldown': 45,
                'refresh_keywords': refresh_terms,
                'cooldown_message': 'ℹ️ Recherche web déjà effectuée récemment. Ajoutez "actualise" pour rafraîchir les résultats.',
            },
            'arxiv_lookup': {
                'label': '📚 Papers récents (arXiv)',
                'handler': self._perform_arxiv_search,
                'formatter': self._format_arxiv_results,
                'requires_requests': True,
                'strong_keywords': {
                    'arxiv', 'preprint', 'preprints', 'paper', 'articles scientifiques',
                    'publication scientifique', 'research article', 'scientific article',
                    'neurips', 'icml', 'iclr', 'cvpr', 'acl', 'emnlp'
                },
                'weak_keywords': {
                    'publication', 'article', 'etude', 'etudes', 'research', 'pfe',
                    'these', 'thesis', 'conference', 'latest paper', 'latest papers',
                    'nouveau papier', 'nouveaux papiers', 'nouvelle publication',
                    'rag', 'retrieval', 'llm', 'transformer', 'bert', 'gpt',
                    'neural', 'deep learning', 'machine learning', 'ai', 'ml', 'dl',
                    'diffusion', 'gan', 'vae', 'autoencoder', 'attention', 'multimodal'
                },
                'min_score': 2,
                'cooldown': 60,
                'refresh_keywords': refresh_terms,
                'cooldown_message': 'ℹ️ Résultats arXiv déjà fournis. Ajoutez "actualise" ou modifiez la requête pour récupérer de nouveaux papiers.',
            },
            'arxiv_digest': {
                'label': '📰 Preprints IA (arXiv)',
                'handler': self._perform_arxiv_digest,
                'formatter': self._format_arxiv_digest_results,
                'requires_requests': True,
                'strong_keywords': {
                    'tldr', 'tl dr', 'tl;dr', 'digest', 'resume rapide', 'resumer',
                    'synthese rapide', 'quick summary', 'short summary', 'brief summary'
                },
                'weak_keywords': {
                    'resume', 'resumes', 'synthese', 'syntheses', 'executive summary',
                    'condense', 'overview', 'recap', 'highlight'
                },
                'min_score': 2,
                'cooldown': 75,
                'refresh_keywords': refresh_terms,
                'cooldown_message': 'ℹ️ Un digest arXiv a déjà été fourni récemment. Ajoutez "actualise" pour forcer une nouvelle synthèse.',
            },
            'huggingface_models': {
                'label': '🤗 Modèles récents (Hugging Face)',
                'handler': self._perform_huggingface_search,
                'formatter': self._format_huggingface_results,
                'requires_requests': True,
                'strong_keywords': {
                    'huggingface', 'hugging face', 'hf model', 'hf models', 'checkpoint',
                    'model card', 'model hub', 'pretrained', 'pre trained'
                },
                'weak_keywords': {
                    'modele', 'modeles', 'model', 'models', 'open weight', 'openweights',
                    'fine tune', 'fine tuning', 'finetuning', 'weights', 'release', 'repo',
                    'llm', 'vision model', 'multimodal', 'embedding', 'encoder', 'decoder',
                    'seq2seq', 'causal lm', 'masked lm', 'text generation', 'image generation',
                    'francais', 'français', 'french', 'france', 'mistral', 'bloom', 'camembert',
                    'flaubert', 'vigogne', 'croissant', 'langue', 'language', 'multilingual'
                },
                'min_score': 2,
                'cooldown': 45,
                'refresh_keywords': refresh_terms,
                'cooldown_message': 'ℹ️ Résultats Hugging Face déjà fournis. Ajoutez "actualise" pour rafraîchir la liste.',
            },
            'ai_benchmarks': {
                'label': '📊 Benchmarks récents (datasets HF)',
                'handler': self._perform_ai_benchmark_search,
                'formatter': self._format_ai_benchmark_results,
                'requires_requests': True,
                'strong_keywords': {
                    'mt bench', 'mt-bench', 'mmlu', 'leaderboard', 'open llm leaderboard',
                    'lm evaluation', 'benchmarking', 'leaderboards', 'lmsys', 'chatbot arena'
                },
                'weak_keywords': {
                    'benchmark', 'benchmarks', 'score', 'scores', 'sota', 'state of the art',
                    'evaluation', 'eval', 'classement', 'ranking', 'gsm8k', 'hellaswag',
                    'truthfulqa', 'mmmu', 'mmbench', 'winogrande', 'human eval', 'humaneval',
                    'glue', 'superglue', 'squad', 'xsum', 'cnn dailymail', 'arc', 'bigbench',
                    'performance', 'accuracy', 'f1 score', 'perplexity', 'bleu', 'rouge'
                },
                'min_score': 2,
                'cooldown': 30,
                'refresh_keywords': refresh_terms,
                'cooldown_message': 'ℹ️ Benchmarks déjà fournis. Ajoutez "actualise" pour mettre à jour les scores.',
            },
            'ai_research_trends': {
                'label': '🧠 Tendances Recherche IA',
                'handler': self._perform_ai_trends_analysis,
                'formatter': self._format_ai_trends_results,
                'requires_requests': True,
                'strong_keywords': {
                    'tendance', 'tendances', 'trend', 'trends', 'trending', 'hot topic',
                    'emergent', 'emerging', 'popularity', 'popularite', 'en vogue',
                    'what is hot', 'whats new', 'cutting edge', 'breakthrough'
                },
                'weak_keywords': {
                    'nouveau', 'nouveaux', 'nouvelle', 'nouvelles', 'recent', 'recents',
                    'dernier', 'derniers', 'derniere', 'dernieres', 'actuel', 'actuelle',
                    'populaire', 'popular', 'top', 'best', 'meilleur', 'meilleurs',
                    'avancee', 'avancees', 'progress', 'innovation', 'decouverte'
                },
                'min_score': 2,
                'cooldown': 120,  # 2 minutes - analyse coûteuse
                'refresh_keywords': refresh_terms,
                'cooldown_message': '🧠 Analyse des tendances déjà effectuée. Ajoutez "actualise" pour rafraîchir (opération coûteuse).',
            },
        }

    def set_model(self, model: str) -> None:
        self.model = model

    def set_temperature(self, temperature: float) -> None:
        if 0.0 <= temperature <= 1.0:
            self.temperature = temperature
        else:
            raise ValueError('Temperature must be between 0.0 and 1.0')

    def toggle_tool(self, tool_name: str, enabled: bool) -> None:
        if tool_name in self.tools_enabled:
            self.tools_enabled[tool_name] = enabled

    def get_tools(self) -> Dict[str, bool]:
        return {name: enabled for name, enabled in self.tools_enabled.items() if enabled}

    def chat(self, messages: List[Dict[str, Any]], session_id: str | None = None) -> Dict[str, Any]:
        """Generate a response from the configured model given conversation history."""

        search_context = self._maybe_search(messages)

        # Provide a graceful fallback when GenAI SDK or API key is absent
        if not GENAI_AVAILABLE or not self.api_key:
            fallback = self._generate_offline_reply(messages)
            if search_context:
                fallback = f"{fallback}\n\n{self._strip_markdown_links(search_context)}"
            return {
                'content': fallback,
                'tokens_used': len(fallback.split()),
                'model': self.model,
            }

        try:
            model = genai.GenerativeModel(self.model)  # type: ignore[attr-defined]

            request_messages = []
            for message in messages:
                role = message.get('role', 'user')
                mapped_role = 'model' if role == 'assistant' else 'user'
                request_messages.append({
                    'role': mapped_role,
                    'parts': [message.get('content', '')],
                })

            if search_context:
                request_messages.insert(-1 if request_messages else 0, {
                    'role': 'user',
                    'parts': [f"Informations complémentaires :\n{search_context}"],
                })

            generation_config = GenerationConfig(  # type: ignore[call-arg]
                temperature=self.temperature,
            ) if GenerationConfig else None

            response = model.generate_content(  # type: ignore[attr-defined]
                request_messages,
                generation_config=generation_config,
            )

            text = (response.text or '').strip()
            if not text:
                if search_context:
                    text = self._strip_markdown_links(search_context)
                else:
                    text = "Je n'ai pas compris votre question, pouvez-vous reformuler ?"

            usage = getattr(response, 'usage_metadata', None)
            tokens_used = getattr(usage, 'total_token_count', None) if usage else None

            return {
                'content': text,
                'tokens_used': tokens_used or len(text.split()),
                'model': self.model,
            }
        except Exception as exc:  # pragma: no cover - network dependent
            fallback = self._generate_offline_reply(messages)
            if search_context:
                fallback = f"{fallback}\n\n{self._strip_markdown_links(search_context)}"
            return {
                'error': str(exc),
                'content': fallback,
                'tokens_used': len(fallback.split()),
            }

    def get_config(self) -> Dict[str, Any]:
        return {
            'model': self.model,
            'temperature': self.temperature,
            'tools': self.get_tools(),
        }

    def _generate_offline_reply(self, messages: List[Dict[str, Any]]) -> str:
        """Return a lightweight rule-based response when LLM is unavailable."""
        last_user_message = self._extract_last_user_message(messages)
        if not last_user_message:
            return "Bonjour ! Je suis votre assistant spécialisé en Intelligence Artificielle. Comment puis-je vous aider aujourd'hui ?"

        text = last_user_message.lower()

        # Détection questions sur l'IA elle-même
        if re.search(r"\b(c'est quoi|qu'est-ce que|what is|define)\b.*\b(ia|ai|intelligence artificielle|artificial intelligence)\b", text):
            return """L'**Intelligence Artificielle (IA)** est un domaine de l'informatique qui vise à créer des systèmes capables d'effectuer des tâches nécessitant normalement l'intelligence humaine.

🧠 **Domaines clés** :
• **Machine Learning (ML)** : Apprentissage à partir de données
• **Deep Learning** : Réseaux de neurones profonds
• **NLP** : Traitement du langage naturel (comme moi !)
• **Computer Vision** : Analyse d'images et vidéos
• **Robotique** : Machines autonomes

💡 **Applications** : ChatGPT, reconnaissance faciale, voitures autonomes, traduction automatique, diagnostics médicaux...

📚 Posez-moi des questions spécifiques : papers récents, modèles, benchmarks, tendances !"""

        greetings = ["salut", "bonjour", "bonsoir", "cc", "coucou", "hello"]
        if any(text.startswith(greet) or re.search(rf"\b{greet}\b", text) for greet in greetings):
            return "Bonjour ! Je suis spécialisé en IA/ML. Posez-moi des questions sur les papers, modèles, benchmarks ou architectures récentes !"

        if re.search(r"comment\s+ça\s+va|cv|ça\s+va\s?", text):
            return "Ça va très bien ! Prêt à discuter d'IA, de ML, de LLMs ou de recherche. Que puis-je faire pour vous ?"

        if "merci" in text:
            return "Avec plaisir ! N'hésitez pas pour d'autres questions sur l'IA/ML."

        # Détection de domaines IA spécifiques
        if any(term in text for term in ['rag', 'retrieval', 'augmented']):
            return "Je peux vous aider avec RAG (Retrieval-Augmented Generation). Voulez-vous des papers récents, des implémentations ou des benchmarks ?"
        
        if any(term in text for term in ['llm', 'large language', 'gpt', 'claude', 'gemini']):
            return "Je suis spécialisé dans les LLMs ! Je peux chercher les derniers modèles, benchmarks ou papers. Que voulez-vous savoir ?"
        
        if any(term in text for term in ['diffusion', 'stable diffusion', 'dall-e', 'midjourney']):
            return "Génération d'images par diffusion ! Je peux vous montrer les derniers modèles et papers. Précisez votre besoin ?"
        
        if any(term in text for term in ['transformer', 'attention', 'bert', 'encoder']):
            return "Architecture Transformer ! Je peux chercher les variantes récentes, optimisations ou applications. Qu'est-ce qui vous intéresse ?"

        if "aide" in text or "besoin" in text:
            return "Je peux vous aider avec : 📚 Papers arXiv • 🤗 Modèles HF • 📊 Benchmarks • 🌐 News IA. Dites-moi ce que vous cherchez !"

        if len(text) < 5:
            return "Précisez votre question sur l'IA/ML ?"

        return (
            "Je suis votre assistant IA spécialisé ! Je peux chercher des papers (arXiv), "
            "modèles (Hugging Face), benchmarks ou actualités. Précisez votre besoin ?"
        )

    def _extract_last_user_message(self, messages: List[Dict[str, Any]]) -> str:
        for message in reversed(messages):
            if message.get('role') == 'user':
                candidate = message.get('content', '').strip()
                if candidate:
                    return candidate
        return ""

    def _strip_markdown_links(self, text: str) -> str:
        return re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)

    def _maybe_search(self, messages: List[Dict[str, Any]]) -> str | None:
        """Optionally perform external lookups and return formatted snippets."""

        query = self._extract_last_user_message(messages)
        if not query:
            return None

        normalized = self._normalize_for_matching(query)
        tokens = set(normalized.split()) if normalized else set()

        contexts: List[str] = []
        notes: List[str] = []

        mt_bench_summary = None
        if self._should_curate_mt_bench(query):
            mt_bench_summary = self._curated_mt_bench_summary(query)
            if mt_bench_summary:
                contexts.append("📊 MT-Bench (référence LMSYS)\n" + mt_bench_summary)

        for tool_name, config in self.tool_configs.items():
            if not self.tools_enabled.get(tool_name, False):
                continue
            if config.get('requires_requests') and requests is None:
                continue
            api_attr = config.get('requires_api_key')
            if api_attr and not getattr(self, api_attr, None):
                continue
            predicate = config.get('predicate')
            if predicate and not predicate():
                continue

            assessment = self._assess_tool_query(tool_name, query, normalized, tokens)
            if not assessment['should_run']:
                if assessment.get('reason') == 'cooldown' and config.get('cooldown_message'):
                    if config['cooldown_message'] not in notes:
                        notes.append(config['cooldown_message'])
                continue

            raw_results = config['handler'](query)
            formatted = config['formatter'](raw_results)
            if formatted:
                contexts.append(f"{config['label']}\n{formatted}")
                self._register_tool_usage(tool_name)
                if assessment['strong_hits'] or assessment['weak_hits']:
                    logger.debug(
                        "Tool %s executed | strong=%s weak=%s",
                        tool_name,
                        ','.join(sorted(assessment['strong_hits'])),
                        ','.join(sorted(assessment['weak_hits'])),
                    )
            elif config.get('on_no_data'):
                notes.append(config['on_no_data'])
            else:
                logger.debug("Tool %s returned no data", tool_name)

        if notes and contexts:
            contexts.append("\n".join(notes))
        elif notes:
            contexts.extend(notes)

        if contexts:
            return "\n\n".join(contexts)

        return None

    def _should_curate_mt_bench(self, query: str) -> bool:
        text = query.lower()
        return 'mt-bench' in text or 'mt bench' in text

    def _get_mt_bench_entries(self) -> List[Dict[str, Any]]:
        """Return MT-Bench entries from cache or curated baseline."""
        if self._mt_bench_cache:
            return self._mt_bench_cache
        return self.CURATED_MT_BENCH

    def refresh_mt_bench_cache(self, force: bool = False) -> Dict[str, Any]:
        """Refresh MT-Bench cache from LMSYS API."""
        now = time.time()
        cache_ttl = 3600  # 1 hour
        
        if not force and self._mt_bench_cache and (now - self._mt_bench_cache_timestamp) < cache_ttl:
            return {
                'cached': True,
                'updated_at': self._mt_bench_cache_timestamp,
                'count': len(self._mt_bench_cache),
            }
        
        if requests is None:
            logger.warning('requests library not available for MT-Bench refresh')
            return {
                'error': 'requests library not available',
                'count': len(self.CURATED_MT_BENCH),
            }
        
        try:
            resp = requests.get(
                'https://chat.lmsys.org/api/leaderboard',
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            
            if isinstance(data, dict) and 'models' in data:
                models = data['models']
                self._mt_bench_cache = []
                
                for model_data in models:
                    if not isinstance(model_data, dict):
                        continue
                    
                    entry = {
                        'model': model_data.get('model', 'Unknown'),
                        'size': model_data.get('size', 'N/A'),
                        'mt_bench': model_data.get('mt_bench'),
                        'mmlu': model_data.get('mmlu'),
                        'source': 'LMSYS API',
                        'date': model_data.get('date'),
                        'link': 'https://chat.lmsys.org/?leaderboard',
                        'aliases': set(),
                    }
                    self._mt_bench_cache.append(entry)
                
                self._mt_bench_cache_timestamp = now
                logger.info('MT-Bench cache refreshed: %d models', len(self._mt_bench_cache))
                
                return {
                    'success': True,
                    'updated_at': now,
                    'count': len(self._mt_bench_cache),
                }
        except Exception as exc:
            logger.warning('Failed to refresh MT-Bench cache: %s', exc)
        
        return {
            'error': 'Failed to fetch from API, using curated baseline',
            'count': len(self.CURATED_MT_BENCH),
        }

    def _curated_mt_bench_summary(self, query: str) -> str | None:
        entries = self._get_mt_bench_entries()
        if not entries:
            return None

        normalized_query = self._normalize_for_matching(query)
        matches: List[Dict[str, Any]] = []

        for entry in entries:
            aliases = set(entry.get('aliases', set()) or set())
            aliases.add(entry.get('model', ''))
            normalized_aliases = {self._normalize_for_matching(alias) for alias in aliases if alias}
            if any(alias in normalized_query for alias in normalized_aliases):
                matches.append(entry)

        if not matches:
            matches = sorted(entries, key=lambda item: item.get('mt_bench') or 0, reverse=True)[:4]

        if not matches:
            return None

        header = "| Modèle | Taille | MT-Bench | MMLU | Source |\n| --- | --- | --- | --- | --- |"
        rows: List[str] = []
        notes: List[str] = []

        for entry in matches:
            model = entry.get('model', 'Modèle')
            size = entry.get('size', 'N/A')
            mt_bench = entry.get('mt_bench')
            mmlu = entry.get('mmlu')
            source = entry.get('source', 'LMSYS')
            link = entry.get('link')
            date = entry.get('date')
            note = entry.get('notes')

            source_text = f"{source}"
            if date:
                source_text += f" ({date})"
            if link:
                source_text = f"[{source_text}]({link})"

            rows.append(
                f"| {model} | {size} | {mt_bench if mt_bench is not None else 'N/A'} | "
                f"{mmlu if mmlu is not None else 'N/A'} | {source_text} |"
            )

            if note:
                notes.append(f"- {model} : {note}")

        table = "\n".join([header] + rows)
        if notes:
            table += "\n\n" + "\n".join(notes)

        table += "\n\nScores consolidés entre le snapshot LMSYS (API) et la liste organisée; vérifiez la source pour les mises à jour quotidiennes."
        return table

    def _should_search_huggingface(self, query: str) -> bool:
        assessment = self._assess_tool_query('huggingface_models', query, consider_cooldown=False)
        return assessment['should_run']

    def _should_search_ai_benchmarks(self, query: str) -> bool:
        assessment = self._assess_tool_query('ai_benchmarks', query, consider_cooldown=False)
        return assessment['should_run']

    def _should_search_arxiv_digest(self, query: str) -> bool:
        assessment = self._assess_tool_query('arxiv_digest', query, consider_cooldown=False)
        return assessment['should_run']

    def _prepare_huggingface_terms(self, query: str) -> str:
        normalized = unicodedata.normalize('NFKD', query)
        normalized = normalized.encode('ascii', 'ignore').decode('ascii')
        normalized = normalized.replace('-', ' ')
        cleaned = re.sub(r'[^\w\s-]', ' ', normalized.lower())
        tokens = [t for t in cleaned.split() if len(t) > 1]
        stopwords = {
            'les', 'des', 'aux', 'sur', 'entre', 'avec', 'pour', 'dans', 'une', 'un', 'le', 'la',
            'derniers', 'dernieres', 'dernier', 'dernières', 'derniere', 'quelles', 'quels', 'quoi',
            'comment', 'peux', 'peut', 'donner', 'donne', 'donnez', 'moi', 'tu', 'toi', 'cherche',
            'chercheur', 'chercher', 'chercheurs', 'modeles', 'modèles', 'modele', 'modèle', 'model',
            'models', 'huggingface', 'hugging', 'face', 'recherches', 'sur',
        }
        allowed_short = {'ia', 'ai', 'nlp', 'ml', 'cv'}
        filtered: List[str] = []
        for token in tokens:
            if token in stopwords:
                continue
            if len(token) <= 2 and token not in allowed_short:
                continue
            if token not in filtered:
                filtered.append(token)
        if not filtered:
            filtered = ['machine', 'learning', 'language', 'model']
        else:
            for kw in ['language', 'model']:
                if kw not in filtered:
                    filtered.append(kw)
        return ' '.join(filtered[:6])

    def _perform_huggingface_search(self, query: str) -> List[Dict[str, Any]]:
        terms = self._prepare_huggingface_terms(query)
        if not terms:
            return []

        results = self._fetch_huggingface_models(query, terms)
        if results:
            return results

        tokens = terms.split()
        if len(tokens) > 1:
            fallback_tokens = sorted(tokens, key=len, reverse=True)[:2]
            fallback_terms = ' '.join(fallback_tokens)
            if fallback_terms and fallback_terms != terms:
                logger.debug("Hugging Face fallback terms '%s' for query '%s'", fallback_terms, query)
                return self._fetch_huggingface_models(query, fallback_terms)

        return results

    def _fetch_huggingface_models(self, original_query: str, terms: str) -> List[Dict[str, Any]]:
        if not terms:
            return []
        
        # Cache check
        cache_key = f'hf:{terms}'
        if cache_key in self._result_cache:
            cached = self._result_cache[cache_key]
            if time.time() - cached['timestamp'] < self._cache_ttl:
                logger.debug("Using cached HF results for '%s'", terms)
                return cached['data']

        logger.debug("Hugging Face search with terms '%s' from query '%s'", terms, original_query)

        headers = {}
        if self.hf_token:
            headers['Authorization'] = f'Bearer {self.hf_token}'

        try:
            resp = requests.get(
                'https://huggingface.co/api/models',
                params={
                    'search': terms,
                    'sort': 'downloads',  # Amélioration: trier par popularité
                    'direction': -1,
                    'limit': 5,  # Récupérer plus pour filtrer
                },
                headers=headers,
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("HuggingFace API error: %s", exc)
            return []

        if not isinstance(data, list):
            return []

        # Amélioration: filtrer les modèles de qualité
        quality_models = []
        for model in data:
            downloads = model.get('downloads', 0)
            likes = model.get('likes', 0)
            
            # Critères de qualité: au moins 10 downloads OU 1 like
            if downloads >= 10 or likes >= 1:
                # Ajouter score de qualité
                model['_quality_score'] = downloads * 10 + likes * 100
                quality_models.append(model)
        
        # Trier par score de qualité et retourner top 3
        quality_models.sort(key=lambda m: m.get('_quality_score', 0), reverse=True)
        results = quality_models[:3]
        
        # Mise en cache
        cache_key = f'hf:{terms}'
        self._result_cache[cache_key] = {'data': results, 'timestamp': time.time()}
        
        return results

    def _prepare_ai_benchmark_terms(self, query: str) -> str:
        normalized = unicodedata.normalize('NFKD', query)
        normalized = normalized.encode('ascii', 'ignore').decode('ascii')
        cleaned = re.sub(r'[^\w\s-]', ' ', normalized.lower())
        tokens = [t for t in cleaned.split() if len(t) > 2]
        stopwords = {
            'les', 'des', 'aux', 'sur', 'entre', 'avec', 'pour', 'dans', 'une', 'un', 'le', 'la',
            'quel', 'quelle', 'quels', 'quelles', 'donne', 'donnez', 'donner', 'liste', 'montre',
            'state', 'art', 'etat', 'valeurs', 'scores', 'score', 'recents', 'recentes', 'dernier',
        }
        filtered: List[str] = []
        for token in tokens:
            if token in stopwords:
                continue
            if token not in filtered:
                filtered.append(token)
        if not filtered:
            return 'ai benchmark'
        return ' '.join(filtered[:5])

    def _perform_ai_benchmark_search(self, query: str) -> List[Dict[str, Any]]:
        terms = self._prepare_ai_benchmark_terms(query)
        if not terms:
            return []

        logger.debug("AI benchmark search with terms '%s'", terms)

        try:
            resp = requests.get(
                'https://huggingface.co/api/datasets',
                params={
                    'search': terms,
                    'sort': 'downloads',
                    'direction': -1,
                    'limit': 3,
                },
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        if isinstance(data, list) and data:
            return data[:3]

        tokens = terms.split()
        if len(tokens) > 1:
            fallback_tokens = sorted(tokens, key=len, reverse=True)[:2]
            fallback_terms = ' '.join(fallback_tokens)
            if fallback_terms and fallback_terms != terms:
                logger.debug("AI benchmark fallback terms '%s' for query '%s'", fallback_terms, query)
                return self._perform_ai_benchmark_search(fallback_terms)

        return []

    def _format_ai_benchmark_results(self, results: List[Dict[str, Any]]) -> str | None:
        if not results:
            return None

        formatted: List[str] = []
        total_downloads = sum(item.get('downloads', 0) for item in results)
        avg_downloads = total_downloads // len(results) if results else 0
        
        for idx, item in enumerate(results, 1):
            dataset_id = item.get('id') or 'Dataset'
            task_tags = [tag for tag in item.get('tags', []) if tag.startswith('task:')][:2]
            modalities = [tag for tag in item.get('tags', []) if tag.startswith('modality:')][:1]
            downloads = item.get('downloads', 0)
            likes = item.get('likes', 0)
            last_modified = (item.get('lastModified') or '')[:10]

            # Amélioration: indicateur de fiabilité
            reliability = ''
            is_official = any(org in dataset_id for org in ['openai', 'google', 'meta', 'bigscience', 'eleutherai'])
            
            # Tendance (comparé à la moyenne)
            trend = ''
            if downloads > avg_downloads * 2:
                trend = ' 📈 très populaire'
            elif downloads > avg_downloads:
                trend = ' 📊 populaire'
            
            if is_official:
                reliability = '✅ Officiel'
            elif downloads >= 10000:
                reliability = '🟢 Très utilisé'
            elif downloads >= 1000:
                reliability = '🟡 Populaire'
            else:
                reliability = '⚪ Standard'
            
            # Rang de pertinence
            rank = '🥇' if idx == 1 else '🥈' if idx == 2 else '🥉'

            details: List[str] = []
            if reliability:
                details.append(reliability)
            if task_tags:
                tasks = ', '.join(tag.split(':', 1)[-1] for tag in task_tags)
                details.append(f"📋 {tasks}")
            if modalities:
                mods = ', '.join(mod.split(':', 1)[-1] for mod in modalities)
                details.append(f"🎯 {mods}")
            if downloads:
                details.append(f"⬇️ {downloads:,} téléchargements")
            if likes:
                details.append(f"❤️ {likes} likes")
            if last_modified:
                details.append(f"🔄 MAJ {last_modified}")

            info = ' • '.join(details) if details else 'Infos indisponibles'
            url = f"https://huggingface.co/datasets/{dataset_id}"

            formatted.append(f"- [{dataset_id}]({url})\n  {info}")

        note = "\n\n💡 Privilégier datasets officiels (✅) ou très utilisés (🟢) pour benchmarks fiables"
        return '\n'.join(formatted) + note

    def _perform_arxiv_digest(self, query: str) -> List[Dict[str, Any]]:
        categories_env = os.getenv('ARXIV_DIGEST_CATEGORIES', 'cs.AI,cs.CL,cs.CV,cs.LG,stat.ML')
        categories = [cat.strip() for cat in categories_env.split(',') if cat.strip()]
        if not categories:
            categories = ['cs.AI', 'cs.CL', 'cs.CV', 'cs.LG', 'stat.ML']

        cat_clause = ' OR '.join(f'cat:{cat}' for cat in categories)
        terms = self._prepare_arxiv_terms(query)
        attempt_terms = list(terms)
        limit = min(self.max_arxiv_results, 3) if self.max_arxiv_results else 3
        limit = max(1, limit)

        tried: set[tuple[str, ...]] = set()
        results: List[Dict[str, Any]] = []

        while True:
            key = tuple(attempt_terms)
            if key in tried:
                break
            tried.add(key)

            search_query = self._compose_arxiv_clause(cat_clause, attempt_terms)
            results = self._query_arxiv_feed(search_query, limit)
            if results:
                break

            if not attempt_terms:
                break

            attempt_terms = attempt_terms[:-1]

        return results[:3]

    def _summarize_arxiv_abstract(self, summary: str, max_sentences: int = 2) -> str:
        clean = re.sub(r'\s+', ' ', summary.strip())
        if not clean:
            return 'Résumé indisponible'

        sentences = re.split(r'(?<=[.!?])\s+', clean)
        extracted = [s for s in sentences if s]
        if not extracted:
            return clean[:180] + '…' if len(clean) > 180 else clean
        tldr = ' '.join(extracted[:max_sentences])
        return tldr if len(tldr) <= 220 else tldr[:217] + '…'

    def _extract_keywords(self, text: str, limit: int = 3) -> List[str]:
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
        tokens = cleaned.split()
        stopwords = {
            'the', 'and', 'with', 'that', 'from', 'this', 'arxiv', 'paper', 'study', 'approach',
            'model', 'data', 'method', 'for', 'using', 'into', 'onto', 'results', 'based',
            'analysis', 'show', 'shows', 'novel', 'present', 'framework', 'task', 'new',
        }
        counts: Dict[str, int] = {}
        for token in tokens:
            if token in stopwords or len(token) < 4:
                continue
            counts[token] = counts.get(token, 0) + 1

        sorted_tokens = sorted(counts.items(), key=lambda item: item[1], reverse=True)
        return [token for token, _ in sorted_tokens[:limit]]

    def _format_arxiv_digest_results(self, results: List[Dict[str, Any]]) -> str | None:
        if not results:
            return None

        formatted: List[str] = []
        for item in results:
            title = item.get('title') or 'Titre indisponible'
            link = item.get('link') or ''
            pdf = item.get('pdf') or ''
            published = item.get('published') or 'Date inconnue'
            authors = item.get('authors') or []
            summary = item.get('summary') or ''

            tldr = self._summarize_arxiv_abstract(summary)
            keywords = self._extract_keywords(summary)

            title_line = f"- [{title}]({link}) ({published})" if link else f"- {title} ({published})"
            authors_line = ', '.join(authors[:2])
            if len(authors) > 2:
                authors_line += f" et {len(authors) - 2} autres"
            if not authors_line:
                authors_line = 'Auteurs non renseignés'

            parts = [title_line]
            parts.append(f"  TL;DR : {tldr}")
            parts.append(f"  Auteurs : {authors_line}")
            if keywords:
                parts.append(f"  Mots-clés : {', '.join(keywords)}")
            if pdf:
                parts.append(f"  PDF : {pdf}")

            formatted.append('\n'.join(parts))

        return '\n'.join(formatted)

    def _format_huggingface_results(self, results: List[Dict[str, Any]]) -> str | None:
        if not results:
            return None

        formatted: List[str] = []
        for idx, item in enumerate(results, 1):
            model_id = item.get('modelId') or item.get('id') or 'Modèle inconnu'
            pipeline = item.get('pipeline_tag') or 'pipeline non renseigné'
            downloads = item.get('downloads', 0)
            likes = item.get('likes', 0)
            last_modified = (item.get('lastModified') or '')[:10]
            private = item.get('private', False)
            quality_score = item.get('_quality_score', 0)

            # Amélioration: indicateur de fiabilité
            reliability = '🔵'
            if downloads >= 10000 and likes >= 50:
                reliability = '🟢 Très populaire'
            elif downloads >= 1000 and likes >= 10:
                reliability = '🟡 Populaire'
            elif downloads >= 100 or likes >= 5:
                reliability = '🟡 En émergence'
            else:
                reliability = '⚪ Nouveau'
            
            # Score de pertinence (1-3 étoiles)
            relevance = '⭐' * (4 - idx) if idx <= 3 else ''

            parts = [f"- {relevance} [{reliability}] {model_id}"]
            details: List[str] = []
            if pipeline and pipeline != 'pipeline non renseigné':
                details.append(f"📌 {pipeline}")
            if downloads:
                details.append(f"⬇️ {downloads:,} téléchargements")
            if likes:
                details.append(f"❤️ {likes} likes")
            if quality_score > 0:
                details.append(f"📊 Score: {quality_score:,}")
            if private:
                details.append('🔒 privé')
            if last_modified:
                details.append(f"🔄 MAJ {last_modified}")

            details_line = ' • '.join(details) if details else 'Infos indisponibles'
            url = f"https://huggingface.co/{model_id}"

            formatted.append(
                f"{parts[0]}\n  {details_line}\n  🔗 {url}"
            )

        return '\n'.join(formatted)

    def _perform_ai_trends_analysis(self, query: str) -> Dict[str, Any]:
        """Analyse multi-source des tendances IA : GitHub trending + Papers With Code + arXiv stats."""
        trends_data = {
            'github_trending': [],
            'papers_with_code': [],
            'arxiv_hot_topics': [],
            'timestamp': time.time()
        }
        
        # 1. GitHub Trending AI/ML repos
        try:
            # Utiliser API GitHub publique (pas besoin de token)
            resp = requests.get(
                'https://api.github.com/search/repositories',
                params={
                    'q': 'machine learning OR deep learning OR artificial intelligence',
                    'sort': 'stars',
                    'order': 'desc',
                    'per_page': 5
                },
                headers={'Accept': 'application/vnd.github.v3+json'},
                timeout=8
            )
            if resp.status_code == 200:
                data = resp.json()
                for repo in data.get('items', [])[:5]:
                    trends_data['github_trending'].append({
                        'name': repo.get('full_name'),
                        'description': repo.get('description', '')[:150],
                        'stars': repo.get('stargazers_count', 0),
                        'language': repo.get('language', 'N/A'),
                        'url': repo.get('html_url'),
                        'updated': repo.get('updated_at', '')[:10]
                    })
        except Exception as exc:
            logger.debug("GitHub trending fetch failed: %s", exc)
        
        # 2. Papers With Code - SOTA methods
        try:
            resp = requests.get(
                'https://paperswithcode.com/api/v1/papers/',
                params={'ordering': '-stars', 'page': 1},
                timeout=8
            )
            if resp.status_code == 200:
                data = resp.json()
                for paper in data.get('results', [])[:3]:
                    trends_data['papers_with_code'].append({
                        'title': paper.get('title', ''),
                        'abstract': (paper.get('abstract') or '')[:200],
                        'stars': paper.get('stars', 0),
                        'url': paper.get('url_abs', ''),
                        'date': paper.get('published', '')
                    })
        except Exception as exc:
            logger.debug("Papers With Code fetch failed: %s", exc)
        
        # 3. arXiv hot topics (catégories les plus actives)
        ai_categories = ['cs.AI', 'cs.LG', 'cs.CL', 'cs.CV', 'stat.ML']
        for category in ai_categories[:3]:  # Top 3 catégories
            try:
                search_query = f'cat:{category}'
                resp = requests.get(
                    'https://export.arxiv.org/api/query',
                    params={
                        'search_query': search_query,
                        'start': 0,
                        'max_results': 2,
                        'sortBy': 'submittedDate',
                        'sortOrder': 'descending'
                    },
                    timeout=8
                )
                if resp.status_code == 200:
                    root = ET.fromstring(resp.text)
                    ns = {'atom': 'http://www.w3.org/2005/Atom'}
                    count = len(root.findall('atom:entry', ns))
                    if count > 0:
                        trends_data['arxiv_hot_topics'].append({
                            'category': category,
                            'recent_count': count,
                            'activity': '🔥' if count >= 2 else '📊'
                        })
            except Exception as exc:
                logger.debug("arXiv category %s fetch failed: %s", category, exc)
        
        return trends_data

    def _perform_web_search(self, query: str) -> List[Dict[str, Any]]:
        try:
            resp = requests.get(
                'https://serpapi.com/search.json',
                params={
                    'engine': 'google',
                    'q': query,
                    'hl': 'fr',
                    'api_key': self.search_api_key,
                },
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get('organic_results', [])[:3]
        except Exception:
            return []

    def _format_ai_trends_results(self, results: Dict[str, Any]) -> str | None:
        """Formate l'analyse multi-source des tendances IA."""
        if not results or not isinstance(results, dict):
            return None
        
        sections = []
        
        # Section 1: GitHub Trending
        github_repos = results.get('github_trending', [])
        if github_repos:
            sections.append("### 🌟 Repositories GitHub Populaires\n")
            for idx, repo in enumerate(github_repos[:5], 1):
                stars = repo.get('stars', 0)
                star_indicator = '🔥' if stars > 50000 else '⭐' if stars > 10000 else '✨'
                sections.append(
                    f"{idx}. {star_indicator} [{repo.get('name')}]({repo.get('url')}) "
                    f"({stars:,} ⭐)\n"
                    f"   💡 {repo.get('description', 'Pas de description')[:100]}\n"
                    f"   🔧 {repo.get('language', 'N/A')} | 🔄 MAJ {repo.get('updated')}\n"
                )
        
        # Section 2: Papers With Code SOTA
        pwc_papers = results.get('papers_with_code', [])
        if pwc_papers:
            sections.append("\n### 🏆 Papers State-of-the-Art (Papers With Code)\n")
            for idx, paper in enumerate(pwc_papers[:3], 1):
                sections.append(
                    f"{idx}. 📄 [{paper.get('title')}]({paper.get('url')})\n"
                    f"   ⭐ {paper.get('stars', 0)} stars | 📅 {paper.get('date', 'N/A')}\n"
                    f"   📝 {paper.get('abstract', 'Pas de résumé')[:150]}...\n"
                )
        
        # Section 3: arXiv Hot Topics
        hot_topics = results.get('arxiv_hot_topics', [])
        if hot_topics:
            sections.append("\n### 🔥 Catégories arXiv Actives\n")
            category_names = {
                'cs.AI': 'Intelligence Artificielle',
                'cs.LG': 'Machine Learning',
                'cs.CL': 'NLP/Linguistique',
                'cs.CV': 'Computer Vision',
                'stat.ML': 'ML Statistiques'
            }
            for topic in hot_topics:
                cat = topic.get('category', '')
                sections.append(
                    f"• {topic.get('activity', '📊')} **{cat}** - {category_names.get(cat, cat)} "
                    f"({topic.get('recent_count', 0)} publications récentes)\n"
                )
        
        # Résumé et insights
        if sections:
            timestamp = results.get('timestamp', time.time())
            from datetime import datetime
            time_str = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
            
            summary = (
                f"\n\n💡 **Insights** :\n"
                f"• {len(github_repos)} repos GitHub analysés\n"
                f"• {len(pwc_papers)} papers SOTA identifiés\n"
                f"• {len(hot_topics)} catégories arXiv actives\n"
                f"• Analyse effectuée à {time_str}\n\n"
                f"⚡ **Action recommandée** : Explorer les repos 🔥 pour code production-ready, "
                f"lire papers 🏆 pour SOTA, surveiller catégories actives pour veille."
            )
            sections.append(summary)
        
        return ''.join(sections) if sections else None

    def _format_search_results(self, results: List[Dict[str, Any]]) -> str | None:
        if not results:
            return None
        formatted = []
        for idx, item in enumerate(results, 1):
            title = item.get('title') or 'Résultat'
            link = item.get('link') or ''
            snippet = item.get('snippet') or ''
            
            # Amélioration: indicateur de source
            source_indicator = ''
            if link:
                if 'wikipedia.org' in link:
                    source_indicator = '📖 '
                elif any(domain in link for domain in ['github.com', 'arxiv.org', 'scholar.google']):
                    source_indicator = '🎓 '
                elif any(domain in link for domain in ['.edu', '.gov']):
                    source_indicator = '🏛️ '
            
            # Amélioration: formatage avec lien
            if link:
                formatted.append(f"- {source_indicator}[{title}]({link})\n  {snippet}")
            else:
                formatted.append(f"- {source_indicator}{title}\n  {snippet}")
        
        # Amélioration: note sur les sources
        reliability_note = "\n\n💡 Conseil : Privilégier sources académiques (🎓) et officielles (🏛️)"
        return "\n".join(formatted) + reliability_note

    def _should_search(self, query: str) -> bool:
        assessment = self._assess_tool_query('google_search', query, consider_cooldown=False)
        return assessment['should_run']

    def _should_search_arxiv(self, query: str) -> bool:
        assessment = self._assess_tool_query('arxiv_lookup', query, consider_cooldown=False)
        return assessment['should_run']

    def _perform_arxiv_search(self, query: str) -> List[Dict[str, Any]]:
        if self.max_arxiv_results <= 0:
            return []

        terms = self._prepare_arxiv_terms(query)
        attempt_terms = list(terms)
        limit = max(1, self.max_arxiv_results)

        tried: set[tuple[str, ...]] = set()
        results: List[Dict[str, Any]] = []

        while True:
            key = tuple(attempt_terms)
            if key in tried:
                break
            tried.add(key)

            search_query = self._compose_arxiv_clause('cat:cs.AI', attempt_terms)
            results = self._query_arxiv_feed(search_query, limit)
            if results:
                break

            if not attempt_terms:
                break

            attempt_terms = attempt_terms[:-1]

        if results:
            return results

        return self._build_arxiv_search_fallback(' '.join(terms))

    def _build_arxiv_search_fallback(self, terms: str, quota_exceeded: bool = False) -> List[Dict[str, Any]]:
        """Return a fallback entry pointing to arXiv search when API queries fail."""
        if not terms.strip():
            terms = 'artificial intelligence'

        if quota_exceeded:
            summary = (
                "Quota arXiv atteint pour la recherche automatique. Rendez-vous directement"
                " sur arXiv pour consulter les publications récentes."
            )
        else:
            summary = (
                "Aucune publication n'a pu être récupérée automatiquement. Pensez à relancer"
                " la recherche plus tard sur arXiv."
            )

        return [{
            'title': 'Aucune publication arXiv récupérée automatiquement',
            'summary': summary,
            'published': '',
            'authors': [],
            'pdf': '',
            'link': '',
        }]

    def _format_arxiv_results(self, results: List[Dict[str, Any]]) -> str | None:
        if not results:
            return None

        formatted: List[str] = []
        for item in results:
            title = item.get('title') or 'Titre indisponible'
            published = item.get('published') or 'Date inconnue'
            authors = item.get('authors') or []
            summary = item.get('summary') or ''
            pdf = item.get('pdf') or ''
            link = item.get('link') or ''

            # Amélioration: indicateur de fraîcheur
            freshness = ''
            if published and published != 'Date inconnue':
                try:
                    from datetime import datetime
                    pub_date = datetime.strptime(published[:10], '%Y-%m-%d')
                    days_old = (datetime.now() - pub_date).days
                    if days_old <= 7:
                        freshness = '🆕 '
                    elif days_old <= 30:
                        freshness = '📅 '
                    elif days_old > 365:
                        freshness = '📚 '
                except:
                    pass

            summary_clean = re.sub(r'\s+', ' ', summary)
            if len(summary_clean) > 280:
                summary_clean = summary_clean[:277] + '…'

            authors_line = ', '.join(authors[:3])
            if len(authors) > 3:
                authors_line += f" et {len(authors) - 3} autres"
            
            # Estimation de l'impact (basé sur l'âge)
            impact_estimate = ''
            try:
                from datetime import datetime
                if published and published != 'Date inconnue':
                    pub_date = datetime.strptime(published[:10], '%Y-%m-%d')
                    days_old = (datetime.now() - pub_date).days
                    if days_old <= 30:
                        impact_estimate = '🔥 Très récent'
                    elif days_old <= 90:
                        impact_estimate = '📈 Récent'
                    elif days_old <= 365:
                        impact_estimate = '📊 Cette année'
            except:
                pass

            if pdf:
                pdf_note = f"📄 [PDF direct]({pdf})"
            else:
                pdf_note = '⚠️ PDF non disponible'

            if link:
                title_line = f"- {freshness}[{title}]({link}) ({published})"
            else:
                title_line = f"- {freshness}{title} ({published})"

            # Amélioration: note de fiabilité
            reliability_note = "\n  ⚠️ Preprint non peer-reviewed - Vérifier citations avant utilisation"

            # Estimation de l'impact (basé sur l'âge)
            impact_estimate = ''
            try:
                from datetime import datetime
                if published and published != 'Date inconnue':
                    pub_date = datetime.strptime(published[:10], '%Y-%m-%d')
                    days_old = (datetime.now() - pub_date).days
                    if days_old <= 30:
                        impact_estimate = '🔥 Très récent'
                    elif days_old <= 90:
                        impact_estimate = '📈 Récent'
                    elif days_old <= 365:
                        impact_estimate = '📊 Cette année'
            except:
                pass
            
            formatted.append(
                f"{title_line}\n"
                f"  👥 {authors_line or 'Non renseigné'} | {impact_estimate}\n"
                f"  📝 {summary_clean or 'Résumé non disponible'}\n"
                f"  {pdf_note}{reliability_note}"
            )
        
        # Suggestions basées sur les résultats
        suggestions = (
            "\n\n💡 **Suggestions** :\n"
            "• Vérifier les citations sur Google Scholar\n"
            "• Consulter le code source si disponible sur GitHub\n"
            "• Comparer avec versions peer-reviewed (conf/journal)"
        )

        return "\n".join(formatted) + suggestions

    def _prepare_arxiv_terms(self, query: str) -> List[str]:
        cleaned = re.sub(r'[^\w\s]', ' ', query.lower())
        tokens = [t for t in cleaned.split() if len(t) > 2]

        normalized: List[str] = []
        replacements: Dict[str, List[str] | str] = {
            'intelligence': ['artificial', 'intelligence'],
            'artificielle': ['artificial', 'intelligence'],
            'artificielles': ['artificial', 'intelligence'],
            'ia': ['artificial', 'intelligence'],
            'ai': ['artificial', 'intelligence'],
            'machine': ['machine', 'learning'],
            'apprentissage': ['machine', 'learning'],
            'learning': ['machine', 'learning'],
            'profond': ['deep', 'learning'],
            'profonds': ['deep', 'learning'],
            'profondres': ['deep', 'learning'],
            'rag': ['retrieval', 'augmented', 'generation'],
            'retrievers': ['retriever'],
            'retriever': ['retriever'],
            'retrieval': ['retrieval'],
            'augmented': ['augmented'],
            'llm': ['large', 'language', 'model'],
            'llms': ['large', 'language', 'model'],
            'transformer': ['transformer'],
            'transformers': ['transformer'],
            'attention': ['attention', 'mechanism'],
            'bert': ['bert'],
            'gpt': ['gpt'],
            'diffusion': ['diffusion', 'model'],
            'gan': ['generative', 'adversarial'],
            'reinforcement': ['reinforcement', 'learning'],
            'embedding': ['embedding'],
            'embeddings': ['embedding'],
            'finetuning': ['fine', 'tuning'],
            'pretraining': ['pre', 'training'],
            'pfe': ['internship'],
            'stage': ['internship'],
        }

        for token in tokens:
            if token in self._arxiv_stopwords:
                continue
            mapped = replacements.get(token, token)
            mapped_terms = mapped if isinstance(mapped, list) else [mapped]
            for term in mapped_terms:
                if not term or term in self._arxiv_stopwords:
                    continue
                if term.isdigit():
                    continue
                if term not in normalized:
                    normalized.append(term)

        if not normalized:
            return ['artificial', 'intelligence']

        return normalized[:6]

    def _compose_arxiv_clause(self, cat_clause: str, terms: List[str]) -> str:
        clause = cat_clause if cat_clause.startswith('(') else f'({cat_clause})'
        if not terms:
            return clause
        keyword_clause = ' AND '.join(f'all:"{term}"' for term in terms)
        return f'{clause} AND ({keyword_clause})'

    def _query_arxiv_feed(self, search_query: str, limit: int) -> List[Dict[str, Any]]:
        if requests is None or limit <= 0:
            return []

        try:
            resp = requests.get(
                'https://export.arxiv.org/api/query',
                params={
                    'search_query': search_query,
                    'start': 0,
                    'max_results': limit,
                    'sortBy': 'submittedDate',
                    'sortOrder': 'descending',
                },
                timeout=8,
            )
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
        except Exception as exc:  # noqa: BLE001
            logger.debug('arXiv query failed (%s): %s', search_query, exc)
            return []

        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        results: List[Dict[str, Any]] = []

        for entry in root.findall('atom:entry', ns):
            title = (entry.findtext('atom:title', default='', namespaces=ns) or '').strip()
            summary = (entry.findtext('atom:summary', default='', namespaces=ns) or '').strip()
            published = (entry.findtext('atom:published', default='', namespaces=ns) or '')[:10]
            authors = [
                (author.findtext('atom:name', default='', namespaces=ns) or '').strip()
                for author in entry.findall('atom:author', ns)
            ]
            link = (entry.findtext('atom:id', default='', namespaces=ns) or '').strip()
            pdf_link = ''
            for link_node in entry.findall('atom:link', ns):
                href = link_node.attrib.get('href', '')
                if link_node.attrib.get('title') == 'pdf' or link_node.attrib.get('type') == 'application/pdf':
                    pdf_link = href
                    break
            if not pdf_link:
                pdf_link = link

            results.append({
                'title': title,
                'summary': summary,
                'published': published,
                'authors': [a for a in authors if a],
                'link': link,
                'pdf': pdf_link,
            })

        return results


_agent_instance: QuantumMindAgent | None = None
_mt_bench_scheduler_thread: threading.Thread | None = None


def get_agent(api_key: str | None = None, model: str = 'gemini-2.5-flash-lite', temperature: float = 0.5) -> QuantumMindAgent:
    global _agent_instance

    if _agent_instance is None:
        _agent_instance = QuantumMindAgent(api_key, model, temperature)

    return _agent_instance


def reset_agent() -> None:
    global _agent_instance
    _agent_instance = None


def start_mt_bench_scheduler(interval_seconds: int | None = None) -> threading.Thread | None:
    """Start background thread to refresh MT-Bench cache."""
    global _mt_bench_scheduler_thread

    if interval_seconds is None:
        try:
            interval_seconds = int(os.getenv('MT_BENCH_REFRESH_INTERVAL', '14400'))
        except ValueError:
            interval_seconds = 14400

    if interval_seconds <= 0:
        return None

    if _mt_bench_scheduler_thread and _mt_bench_scheduler_thread.is_alive():
        return _mt_bench_scheduler_thread

    def _worker() -> None:
        agent = get_agent()
        while True:
            try:
                agent.refresh_mt_bench_cache(force=True)
                logger.debug('MT-Bench cache refreshed automatically')
            except Exception as exc:  # noqa: BLE001
                logger.warning('MT-Bench auto-refresh failed: %s', exc)
            time.sleep(interval_seconds)

    _mt_bench_scheduler_thread = threading.Thread(
        target=_worker,
        name='mt-bench-refresh',
        daemon=True,
    )
    _mt_bench_scheduler_thread.start()
    return _mt_bench_scheduler_thread
