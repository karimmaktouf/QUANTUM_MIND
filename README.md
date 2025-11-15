# 🧠 QUANTUM MIND

Agent conversationnel spécialisé en **recherche d'intelligence artificielle**, propulsé par **Google Gemini** avec système d'outils multi-sources unique au monde.

## ✨ Fonctionnalités Principales

### 🧠 Outils de Recherche IA (6 outils spécialisés)

#### 🤗 Hugging Face Models
- Recherche de modèles récents sur Hugging Face Hub
- Filtrage par qualité (downloads×10 + likes×100)
- Support modèles français (Mistral, BLOOM, Camembert, etc.)
- Indicateurs visuels 🟢🟡⚪✅🆕

#### 📚 arXiv Lookup
- Recherche de papers récents sur arXiv
- 5 catégories IA (cs.AI, cs.CL, cs.CV, cs.LG, stat.ML)
- Expansion d'acronymes (RAG, LLM, BERT, GPT)
- Mots-clés conférences (NeurIPS, ICML, CVPR, ACL, EMNLP)

#### 📰 arXiv Digest
- Synthèse rapide des preprints IA
- TLDR automatique
- Résumés exécutifs

#### 📊 AI Benchmarks
- Scores MMLU, MT-Bench, GSM8K
- Leaderboards Open LLM
- Comparaisons modèles
- GLUE, SuperGLUE, HumanEval

#### 🌐 Google Search (SerpAPI)
- Actualités IA en temps réel
- Annonces officielles
- Réglementations

#### 🔥 AI Research Trends (UNIQUE)
**Outil unique au monde** croisant 3 APIs simultanément :
- 📈 GitHub Trending (repos IA populaires)
- 🏆 Papers With Code SOTA (meilleurs papers)
- 🔬 arXiv Hot Topics (sujets émergents)

### 🎨 Interface Dynamique
- 🌌 Réseau neuronal animé (Canvas 50 particules)
- ⌨️ Effet de frappe "QUANTUM MIND"
- 🔒 Indicateur force mot de passe (5 critères)
- 👁️ Toggle visibilité mot de passe
- 💫 Animations shake sur erreurs
- 📊 Barre de progression connexion
- 🎲 Slogan dynamique aléatoire
- 🏷️ Badge version footer

### 💾 Base de Données & Conversations
- SQLite 4 tables (users, conversations, messages, statistics)
- Noms élégants : 💬 Session 14:30, 📅 Hier 09:15, 📆 12 nov 16:45
- Cache 1h pour Hugging Face
- Cooldowns par outil (30-120s)

### 🔐 Authentification & Sécurité
- Login/register avec SHA256
- Sessions persistantes
- Multi-utilisateurs

### 📄 Export & Statistiques
- Export Markdown, JSON, PDF
- Comptage tokens par message
- Métadonnées complètes

---

## 📁 Structure du Projet

```
QUANTUM_MIND/
├── README.md                 # Ce fichier
├── requirements.txt          # Dépendances Python
├── main.py                   # Point d'entrée principal
├── config/
│   └── config.py            # Configuration de l'application
├── app/
│   ├── __init__.py
│   ├── database.py          # Gestion de la base de données
│   ├── auth.py              # Authentification utilisateurs
│   ├── agent.py             # Agent IA (1623 lignes)
│   ├── routes.py            # Routes Flask API
│   ├── utils.py             # Fonctions utilitaires
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   └── templates/
│       └── index.html       # Interface web (3159 lignes)
├── data/
│   └── quantum_mind.db      # Base de données SQLite
└── docs/
    ├── API.md               # Documentation API
    ├── INSTALLATION.md      # Guide d'installation
    └── USAGE.md             # Guide d'utilisation
```

---

## 🚀 Installation & Démarrage

### Prérequis
- Python 3.13+ (testé)
- pip (gestionnaire de paquets Python)
- Clés API nécessaires :
    - **Google Gemini** (`GOOGLE_API_KEY` ou `GEMINI_API_KEY`)
    - **SerpAPI** (`SERPAPI_API_KEY`)
    - **Hugging Face** (`HUGGINGFACE_API_TOKEN`)

### 1. Installation

```bash
# Cloner le repository
git clone https://github.com/votre-username/QUANTUM_MIND.git
cd QUANTUM_MIND

# Installer les dépendances
pip install -r requirements.txt
```

### 2. Configuration

Copiez le template puis complétez vos clés :

```bash
cp .env.example .env
```

Éditez ensuite `.env` :

```env
GOOGLE_API_KEY=votre_clé_google_gemini
GEMINI_API_KEY=votre_clé_google_gemini  # (alias accepté)
SERPAPI_API_KEY=votre_clé_serpapi
HUGGINGFACE_API_TOKEN=votre_token_hf
DEFAULT_MODEL=gemini-2.5-flash
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=votre_clé_secrète_aléatoire
MT_BENCH_REFRESH_INTERVAL=14400  # mettre 0 pour désactiver
```

### 3. Démarrage

```bash
python main.py
```

L'application sera disponible sur `http://localhost:5000`

---

## 📝 Utilisation

### Créer un Compte
1. Allez sur l'écran de connexion
2. Cliquez sur "Pas encore inscrit ? Créez un compte"
3. Entrez vos identifiants et créez votre compte

### Chat
1. Connectez-vous
2. Tapez votre message
3. Appuyez sur Envoyer
4. Parcourez vos conversations précédentes
5. Utilisez le bouton « Refresh MT-Bench » pour déclencher un rafraîchissement instantané des benchmarks si besoin

### Recherche
- Utilisez la barre de recherche dans la barre latérale
- Recherche en temps réel sur les titres et contenus

### Export
- Cliquez sur le bouton Export (🔽)
- Choisissez le format (Markdown, JSON, PDF)
- Téléchargez votre conversation

### Paramètres
- Cliquez sur Paramètres (⚙️)
- Modifiez le modèle, température, et outils
- Les modifications sont sauvegardées automatiquement

---

## 🔌 API Endpoints

### Authentification
- `POST /api/register` - Créer un compte
- `POST /api/login` - Se connecter
- `POST /api/logout` - Se déconnecter
- `GET /api/user` - Récupérer l'utilisateur actuel

### Chat
- `POST /api/chat` - Envoyer un message
- `GET /api/conversations` - Lister les conversations
- `GET /api/history/<session_id>` - Récupérer l'historique
- `DELETE /api/delete/<session_id>` - Supprimer une conversation

### Recherche & Filtrage
- `POST /api/search` - Rechercher dans les conversations

### Paramètres
- `POST /api/settings/<session_id>` - Mettre à jour les paramètres
- `GET /api/tools` - Lister les outils disponibles
- `POST /api/tools/<tool_name>` - Activer/désactiver un outil

### Export & Statistiques
- `GET /api/export/<session_id>/<format>` - Exporter une conversation
- `GET /api/statistics/<session_id>` - Récupérer les statistiques
- `POST /api/mt-bench/refresh` - Rafraîchir les données MT-Bench côté serveur

---

## 🛠️ Technologies Utilisées

### Backend
- **Flask** - Framework web léger
- **SQLite** - Base de données
- **Google GenAI SDK** - Accès aux modèles Gemini
- **Google Gemini** - Modèles IA (Flash/Pro)
- **ReportLab** - Génération PDF

### Frontend
- **HTML5/CSS3** - Structure et design
- **JavaScript ES6** - Interactivité
- **Marked.js** - Rendu Markdown
- **Font Awesome** - Icônes

---

## 📊 Structure de la Base de Données

### Table `users`
```sql
id INTEGER PRIMARY KEY
username TEXT UNIQUE
password TEXT (SHA256)
created_at TIMESTAMP
```

### Table `conversations`
```sql
id INTEGER PRIMARY KEY
session_id TEXT UNIQUE
user_id INTEGER (FK)
user_name TEXT
model TEXT
temperature REAL
created_at TIMESTAMP
updated_at TIMESTAMP
```

### Table `messages`
```sql
id INTEGER PRIMARY KEY
session_id TEXT (FK)
role TEXT (user|agent)
content TEXT
tokens_used INTEGER
timestamp TIMESTAMP
```

### Table `statistics`
```sql
id INTEGER PRIMARY KEY
session_id TEXT (FK)
total_messages INTEGER
total_tokens INTEGER
response_time_avg REAL
created_at TIMESTAMP
```

---

## 🔒 Sécurité

- ✅ Mots de passe hachés avec SHA256
- ✅ Sessions utilisateur sécurisées
- ✅ CORS configuré
- ✅ Input validation
- ✅ Erreur handling

---

## 📖 Documentation Complète

Voir les fichiers dans le dossier `docs/` :
- `INSTALLATION.md` - Guide d'installation détaillé
- `API.md` - Référence complète de l'API
- `USAGE.md` - Tutoriel d'utilisation

---

## 🐛 Dépannage

### Le navigateur ne s'ouvre pas
→ Ouvrez manuellement `http://localhost:5000`

### Erreur "Module not found"
→ Installez les dépendances : `pip install -r requirements.txt`

### Erreur "API Key not found"
→ Vérifiez que `GOOGLE_API_KEY` est défini dans `.env`

### Port 5000 déjà utilisé
→ Modifiez le port dans `config/config.py`

---

## 📄 Licence

Ce projet est fourni à titre d'exemple éducatif.

---

## 👨‍💻 Auteur

Créé avec ❤️ pour les développeurs IA et chatbot.

---

## 🤝 Support

Pour toute question ou problème :
1. Consultez la documentation dans `docs/`
2. Vérifiez les logs dans la console
3. Créez une issue si vous trouvez un bug

---

**Version:** 1.0  
**Dernière mise à jour:** 14 novembre 2025  
**Status:** ✅ Production-ready (85%) | Demo-ready (100%)
