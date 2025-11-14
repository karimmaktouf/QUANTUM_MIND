# 📚 Documentation de l'API QUANTUM MIND v1.0

## Vue d'ensemble

L'API REST fournit tous les endpoints nécessaires pour interagir avec l'agent conversationnel, gérer les utilisateurs, les conversations et les paramètres.

**Base URL (dev):** `http://localhost:5000/api`

---

## 🔐 Authentification

### POST `/api/register`

Créer un nouveau compte utilisateur.

**Request:**
```json
{
  "username": "john_doe",
  "password": "secure_password_123"
}
```

**Response (201):**
```json
{
  "status": "success",
  "message": "Inscription réussie"
}
```

**Erreurs:**
- `400` - Nom d'utilisateur/mot de passe manquant
- `400` - Utilisateur existe déjà

---

### POST `/api/login`

Connecter un utilisateur existant.

**Request:**
```json
{
  "username": "john_doe",
  "password": "secure_password_123"
}
```

**Response (200):**
```json
{
  "status": "success",
  "message": "Connexion réussie",
  "user_id": 1
}
```

**Erreurs:**
- `401` - Identifiants invalides

---

### POST `/api/logout`

Déconnecter l'utilisateur actuel.

**Response (200):**
```json
{
  "status": "success"
}
```

---

### GET `/api/user`

Récupérer les informations de l'utilisateur actuellement connecté.

**Response (200):**
```json
{
  "user_id": 1,
  "username": "john_doe"
}
```

---

## 💬 Chat

### POST `/api/chat`

Envoyer un message à l'agent.

**Request:**
```json
{
  "message": "Bonjour, comment vas-tu?",
  "session_id": "session_1234567890"
}
```

**Response (200):**
```json
{
  "response": "Bonjour! Je vais bien, merci de demander. Comment puis-je vous aider?"
}
```

**Erreurs:**
- `400` - Message manquant
- `500` - Erreur de traitement

---

## 📂 Conversations

### GET `/api/conversations`

Récupérer la liste de toutes les conversations de l'utilisateur.

**Response (200):**
```json
{
  "conversations": [
    {
      "session_id": "session_001",
      "user_name": "John Doe",
      "created_at": "2025-11-12T10:30:00",
      "updated_at": "2025-11-12T11:45:00",
      "model": "gemini-2.5-flash",
      "temperature": 0.7,
      "message_count": 5,
      "total_tokens": 1250
    }
  ]
}
```

---

### GET `/api/history/<session_id>`

Récupérer l'historique complet d'une conversation.

**Response (200):**
```json
{
  "history": [
    {
      "role": "user",
      "content": "Qu'est-ce que Python?",
      "timestamp": "2025-11-12T10:30:00",
      "tokens": 12
    },
    {
      "role": "agent",
      "content": "Python est un langage de programmation...",
      "timestamp": "2025-11-12T10:30:15",
      "tokens": 145
    }
  ]
}
```

---

### DELETE `/api/delete/<session_id>`

Supprimer une conversation.

**Response (200):**
```json
{
  "status": "success"
}
```

**Erreurs:**
- `500` - Erreur lors de la suppression

---

## 🔍 Recherche

### POST `/api/search`

Rechercher dans les conversations.

**Request:**
```json
{
  "query": "Python"
}
```

**Response (200):**
```json
{
  "results": [
    {
      "session_id": "session_001",
      "user_name": "Python Discussion",
      "created_at": "2025-11-12T10:30:00",
      "updated_at": "2025-11-12T11:45:00"
    }
  ]
}
```

---

## ⚙️ Paramètres

### POST `/api/settings/<session_id>`

Mettre à jour les paramètres d'une conversation.

**Request:**
```json
{
  "model": "gemini-2.5-pro",
  "temperature": 0.9
}
```

**Response (200):**
```json
{
  "status": "success"
}
```

---

### GET `/api/tools`

Récupérer la liste des outils disponibles.

**Response (200):**
```json
{
  "tools": {
    "google_search": {
      "enabled": true,
      "description": "Recherche Google"
    },
    "code_execution": {
      "enabled": false,
      "description": "Exécution de code"
    }
  },
  "enabled": ["google_search"]
}
```

---

### POST `/api/tools/<tool_name>`

Activer/désactiver un outil.

**Request:**
```json
{
  "enabled": true
}
```

**Response (200):**
```json
{
  "status": "success",
  "enabled_tools": ["google_search", "code_execution"]
}
```

---

## 📊 Export & Statistiques

### GET `/api/export/<session_id>/<format>`

Exporter une conversation.

**Formats supportés:**
- `markdown` - Fichier Markdown
- `json` - Fichier JSON
- `pdf` - Fichier PDF

**Response (200):**
```json
{
  "content": "# Conversation...",
  "filename": "conversation_session_001.md"
}
```

**Pour PDF, le contenu est en base64.**

---

### GET `/api/statistics/<session_id>`

Récupérer les statistiques d'une conversation.

**Response (200):**
```json
{
  "total_messages": 10,
  "user_messages": 5,
  "agent_messages": 5,
  "total_tokens": 2500,
  "avg_tokens": 250
}
```

---

## 📋 Codes de Statut HTTP

| Code | Signification |
|------|---------------|
| 200 | Succès |
| 201 | Ressource créée |
| 400 | Requête invalide |
| 401 | Non authentifié |
| 404 | Non trouvé |
| 500 | Erreur serveur |

---

## 🔄 Flux d'Authentification Typique

1. **Inscription/Connexion**
   - POST `/api/register` ou `/api/login`
   - Récupérer `user_id`

2. **Commencer un Chat**
   - POST `/api/chat` avec `session_id` et message
   - Recevoir la réponse de l'agent

3. **Récupérer l'Historique**
   - GET `/api/conversations` pour lister
   - GET `/api/history/<session_id>` pour les détails

4. **Exporter**
   - GET `/api/export/<session_id>/<format>`

5. **Déconnexion**
   - POST `/api/logout`

---

## 🛡️ Authentification des Requêtes

Toutes les requêtes sont associées à l'utilisateur connecté via la session.

Exemple avec cURL:
```bash
# Inscription
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username":"user","password":"pass"}'

# Login
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user","password":"pass"}'

# Chat
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Bonjour","session_id":"session_001"}'
```

---

## 📞 Limites de Taux (Rate Limiting)

- Max 100 requêtes par minute par utilisateur
- Max 5000 caractères par message
- Max 1000 messages par conversation

---

**Version de l'API:** 1.0  
**Dernière mise à jour:** Novembre 2025
