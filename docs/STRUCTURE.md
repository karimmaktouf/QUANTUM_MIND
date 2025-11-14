# 📁 Structure du Projet QUANTUM MIND v1.0

```
QUANTUM_MIND/
│
├── 📄 README.md                    # Documentation principale du projet
├── 📄 INSTALLATION.md              # Guide d'installation détaillé
├── 📄 API.md                       # Documentation de l'API REST
├── 📄 USAGE.md                     # Guide d'utilisation de l'application
├── 📄 STRUCTURE.md                 # Ce fichier - Structure du projet
│
├── 📋 requirements.txt             # Dépendances Python pour production
├── 📋 requirements-dev.txt         # Dépendances additionnelles pour développement
├── 📋 .env.example                 # Template d'environnement (copier en .env)
├── 📋 .env                         # Variables d'environnement (ne pas commiter)
├── 📋 .gitignore                   # Fichiers à ignorer dans Git
│
├── 🚀 main.py                      # Point d'entrée principal (QUANTUM MIND)
├── 🚀 start.bat                    # Script de démarrage Windows
├── 🚀 start.sh                     # Script de démarrage Linux/Mac
│
├── 📁 app/                         # Package application principale
│   ├── 📄 __init__.py              # Factory Flask et configuration globale
│   ├── 📄 database.py              # Gestion de la base de données SQLite
│   ├── 📄 auth.py                  # Authentification et gestion utilisateurs
│   ├── 📄 agent.py                 # Agent IA (6 outils spécialisés)
│   ├── 📄 routes.py                # Endpoints API REST (blueprints)
│   ├── 📄 utils.py                 # Fonctions utilitaires (exports, format, etc.)
│   │
│   ├── 📁 templates/               # Templates HTML (Jinja2)
│   │   └── 📄 index.html           # Interface web principale (SPA)
│   │
│   ├── 📁 static/                  # Fichiers statiques (CSS, JS, images)
│   │   ├── 📁 css/
│   │   │   └── style.css           # Styles CSS (optionnel - inline dans HTML)
│   │   ├── 📁 js/
│   │   │   └── app.js              # Code JavaScript (optionnel - inline dans HTML)
│   │   └── 📁 images/
│   │       └── logo.png            # Logo de l'application
│   │
│   └── 📁 __pycache__/             # Cache Python (généré automatiquement)
│
├── 📁 config/                      # Configuration de l'application
│   └── 📄 config.py                # Classes de configuration (Dev, Prod, Test)
│
├── 📁 data/                        # Données persistantes
│   ├── quantum_mind.db             # Base de données SQLite (créée automatiquement)
│   └── logs/                       # Fichiers logs (optionnel)
│
├── 📁 docs/                        # Documentation complète
│   ├── 📄 API.md                   # Endpoints API avec exemples
│   ├── 📄 INSTALLATION.md          # Instructions d'installation
│   ├── 📄 USAGE.md                 # Guide d'utilisation
│   ├── 📄 STRUCTURE.md             # Structure du projet (ce fichier)
│   └── 📄 DEPLOYMENT.md            # Guide de déploiement en production
│
└── 📁 venv/                        # Environnement virtuel Python (créé par start.bat/sh)
    ├── Scripts/ ou bin/            # Exécutables Python
    └── Lib/                        # Paquets installés
```

## 🔍 Détail des Fichiers Importants

### Point d'Entrée
- **main.py** - Script principal à exécuter pour démarrer l'application
  - Initialise la base de données
  - Crée l'application Flask
  - Lance le serveur de développement

### Application (dossier `app/`)
- **__init__.py** - Factory Flask et configuration
  - Crée l'application Flask
  - Configure les sessions
  - Sert la page HTML principale
  
- **database.py** - Gestion SQLite
  - `init_database()` - Crée les tables
  - `save_message()` - Sauvegarde les messages
  - `get_conversation_history()` - Récupère l'historique
  - `search_conversations()` - Recherche
  
- **auth.py** - Authentification
  - `create_user()` - Créer un compte
  - `verify_user()` - Vérifier identifiants
  - `hash_password()` - Hasher mot de passe
  
- **agent.py** - Agent QUANTUM MIND
  - `QuantumMindAgent` (classe principale) avec 6 outils : HuggingFace, arXiv lookup, arXiv digest, AI benchmarks, Google Search, AI Research Trends
  - Cache 1h + cooldowns par outil
  - Formatage des résultats et gestion LLM Gemini
  
- **routes.py** - API REST
  - `/api/register` - Créer un compte
  - `/api/login` - Se connecter
  - `/api/chat/<session_id>` - Envoyer un message
  - `/api/conversations` - Lister les conversations
  - Et 10+ autres endpoints
  
- **utils.py** - Utilitaires
  - `export_to_markdown()` - Export Markdown
  - `export_to_json()` - Export JSON
  - `export_to_pdf()` - Export PDF
  - Validation et formatage

### Frontend (app/templates/)
- **index.html** - Interface web complète
  - HTML5 + CSS3 + JavaScript
  - Single Page Application (SPA)
  - Mode sombre/clair
  - Authentification
  - Chat en temps réel
  - Gestion des conversations

### Configuration
- **.env** - Variables d'environnement (copier depuis `.env.example`)
  - `GOOGLE_API_KEY` ou `GEMINI_API_KEY`
  - `SERPAPI_API_KEY`
  - `HUGGINGFACE_API_TOKEN`
  - `DEFAULT_MODEL=gemini-2.5-flash`
  - Options serveur (`FLASK_HOST`, `FLASK_PORT`)
  
- **config/config.py** - Classes de configuration
  - Valeurs par défaut adaptées à QUANTUM MIND (DB `data/quantum_mind.db`, agent `quantum_mind`)
  - `DevelopmentConfig`, `ProductionConfig`, `TestingConfig`

### Documentation
- **README.md** - Vue d'ensemble du projet
- **INSTALLATION.md** - Étapes d'installation
- **API.md** - Référence complète de l'API
- **USAGE.md** - Guide d'utilisation pour l'utilisateur
- **STRUCTURE.md** - Ce fichier

## 📊 Base de Données

SQLite avec 4 tables :

```sql
users              -- Comptes utilisateurs
  ├── id
  ├── username
  ├── password_hash
  └── created_at

conversations      -- Sessions de chat
  ├── id
  ├── session_id (UUID)
  ├── user_id
  ├── model
  ├── temperature
  ├── created_at
  └── updated_at

messages           -- Messages individuels
  ├── id
  ├── session_id
  ├── role (user/assistant)
  ├── content
  ├── tokens_used
  └── timestamp

statistics         -- Statistiques par conversation
  ├── id
  ├── session_id
  ├── total_messages
  ├── total_tokens
  ├── response_time_avg
  └── created_at
```

## 🔗 Flux d'Application

```
User
  ↓
start.bat/start.sh  (Script de démarrage)
  ↓
main.py             (Point d'entrée)
  ↓
app/__init__.py     (Crée Flask app)
  ↓
app/routes.py       (Enregistre API)
  ↓
index.html          (Interface web)
  ↓
API Requests
  ├→ app/auth.py    (Login/Register)
  ├→ app/database.py (CRUD données)
  ├→ app/agent.py   (Réponses IA)
  └→ app/utils.py   (Exports)
  ↓
SQLite Database
```

## 🎯 Pour Démarrer

1. **Windows** : `start.bat`
2. **Linux/Mac** : `bash start.sh`
3. Ouvrir : `http://localhost:5000`

## 📦 Dépendances Principales

- **Flask 3.0+** - Framework web
- **google-generativeai** - SDK Google GenAI (Gemini)
- **python-dotenv** - Variables d'environnement
- **Flask-CORS** - Cross-origin requests
- **reportlab** - Génération PDF
- **markdown** - Parsing Markdown

Voir `requirements.txt` pour la liste complète.

---

**Version** : 1.0.0  
**Dernière mise à jour** : Novembre 2025
