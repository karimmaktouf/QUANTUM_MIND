# 🚀 Guide d'Installation - QUANTUM MIND v1.0

Ce document explique comment installer, configurer et vérifier QUANTUM MIND (assistant IA spécialisé).

## ✅ Prérequis

- Windows 10/11, macOS ou Linux
- Python 3.13+ recommandé
- `pip` à jour
- Clés API actives : Google Gemini, SerpAPI, Hugging Face
- Git (facultatif)

## ⚡ Installation Express

### Windows
1. Placez le dossier `QUANTUM-MIND` sur votre machine
2. `start.bat` crée un venv, installe les dépendances et lance l'app
3. Navigateur → `http://localhost:5000`

### Linux / macOS
```bash
git clone https://github.com/votre-username/QUANTUM_MIND.git
cd QUANTUM_MIND
./start.sh
```

## 🛠️ Installation Manuelle (toutes plateformes)

### 1. Récupérer le code
```bash
git clone https://github.com/votre-username/QUANTUM_MIND.git
cd QUANTUM_MIND
```

### 2. Environnement virtuel
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Dépendances
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurer `.env`

```bash
cp .env.example .env
```

Éditez le fichier :
```env
GOOGLE_API_KEY=votre_cle_gemini
GEMINI_API_KEY=votre_cle_gemini   # alias optionnel
SERPAPI_API_KEY=votre_cle_serpapi
HUGGINGFACE_API_TOKEN=votre_token_hf
DEFAULT_MODEL=gemini-2.5-flash
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=change-me
MT_BENCH_REFRESH_INTERVAL=14400
```

### 5. Lancer QUANTUM MIND
```bash
python main.py
```
Interface disponible sur `http://localhost:5000`.

## 🧾 Structure installée
```
QUANTUM_MIND/
├── app/
├── config/
├── data/quantum_mind.db
├── docs/
├── requirements.txt
├── main.py
└── ...
```

## ✅ Vérification rapide
1. `python main.py`
2. Naviguer vers `http://localhost:5000`
3. Créer un compte test
4. Poser une question (“Quelles tendances IA aujourd’hui ?”)
5. Vérifier que `data/quantum_mind.db` est créé

## 🧹 Réinitialiser l'application

```bash
del data\quantum_mind.db   # Windows
rm data/quantum_mind.db     # Linux/Mac
python main.py
```

## 🛡️ Dépannage & FAQ

| Problème | Solution |
|----------|----------|
| `ModuleNotFoundError` | `pip install -r requirements.txt --force-reinstall`
| Clé Gemini non trouvée | Vérifier `.env` (`GOOGLE_API_KEY` **ou** `GEMINI_API_KEY`)
| SerpAPI quota | Mettre à jour clé ou réduire requêtes web |
| Port 5000 occupé | Modifier `FLASK_PORT` dans `.env`
| Export PDF vide | `pip install reportlab`

## 🚀 Suite

- Lire `docs/USAGE.md` pour les scénarios d’utilisation
- Consulter `docs/DEPLOYMENT.md` pour la mise en production
- Explorer `README.md` pour la vision globale

Bon déploiement avec **QUANTUM MIND** !
