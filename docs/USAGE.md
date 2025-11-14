## 📖 Guide d'Utilisation - QUANTUM MIND v1.0

QUANTUM MIND est un copilote de recherche IA doté de 6 outils spécialisés (SerpAPI, arXiv Lookup, arXiv Digest, Benchmarks IA, Hugging Face Hub, AI Trends). Ce guide explique chaque étape de l’expérience utilisateur.

---

## 1. Lancer le mode démo

```bash
cd QUANTUM-MIND
del data\quantum_mind.db  # Windows
rm data/quantum_mind.db    # Linux/Mac
python main.py
```

Créez un compte test sur `http://localhost:5000` pour découvrir l’interface.

---

## 2. Authentification

| Étape | Détails |
|-------|---------|
| Inscription | Bouton **Pas encore inscrit ?** → identifiant ≥3 caractères + mot de passe fort |
| Connexion | Entrer identifiants → accès aux conversations et paramètres |
| Déconnexion | Bouton **Déconnexion** en bas de la sidebar |

Les comptes sont stockés dans `data/quantum_mind.db` avec mots de passe bcrypt.

---

## 3. Conversations

- **Nouvelle conversation** : bouton `+` dans la sidebar
- **Reprise** : cliquer sur une entrée pour charger l’historique instantanément
- **Suppression** : icône 🗑️ (confirmation requise)
- **Recherche** : barre en tête de sidebar pour filtrer par mot-clé

Chaque session conserve modèle, température, top-k/p et outils actifs.

---

## 4. Interface

| Zone | Fonction |
|------|----------|
| Sidebar gauche | Logo QUANTUM MIND, actions (Nouveau, Export, Paramètres), liste conversations |
| Zone centrale | Messages en bulles avec badges d’outils utilisés, animation « agent écrit » |
| Panneau droit | Sliders modèle/température, toggles outils, onglet Statistiques |

Editeur : Markdown simple, multi-lignes, raccourci `Ctrl+Enter` pour envoyer.

---

## 5. Outils intégrés

| Outil | Description | Pré-requis |
|-------|-------------|------------|
| Google Search (SerpAPI) | Résumés web + sources | `SERPAPI_API_KEY` |
| arXiv Lookup | Méta-données détaillées d’un papier | Aucun |
| arXiv Digest | Synthèses multi-papiers tendance | Aucun |
| AI Benchmarks | Comparaison de modèles SOTA | Aucun |
| Hugging Face Hub | Recherche de modèles/datasets | `HUGGINGFACE_API_TOKEN` (optionnel) |
| AI Trends | Analyse actualités IA | Aucun |

Activez/désactivez chaque outil via l’onglet **Outils** de la sidebar.

---

## 6. Statistiques & Export

- **Stats** : total messages, tokens, répartition user/agent, temps de réponse moyen, sparkline
- **Export** : Markdown/JSON/PDF depuis le bouton Export ; fichiers signés QUANTUM MIND

Exemple Markdown :

```markdown
# Conversation QUANTUM MIND
Exportée le: 2025-11-12 14:30:00
```
❌ Erreur: "API Key not found"
→ Contactez l'admin, clé API invalide
```

### Le port 5000 est occupé

```bash
# Redémarrez le serveur sur un autre port
API_PORT=5001 python main.py
```

### Données perdues

Vos données sont sauvegardées dans la base de données.  
Si vous supprimez accidentellement une conversation :
- ⚠️ Elle **ne peut pas être récupérée**
- 💡 Exportez régulièrement vos conversations

---

## 📱 11. Mode Mobile

L'application est **responsive** et fonctionne sur mobile :

✅ Petit écran (< 768px)
✅ Tactile optimisé
✅ Données sauvegardées

---

## 🚀 12. Raccourcis Clavier

| Touche | Action |
|--------|--------|
| Entrée | Envoyer le message |
| Esc | Fermer les modales |
| Ctrl+K | Recherche (bientôt) |

---

## 📞 Besoin d'Aide ?

- 📖 Consultez cette documentation
- 🐛 Vérifiez les logs de la console (F12)
- 💬 Contactez l'administrateur

---

**Amusez-vous bien avec QUANTUM MIND !** 🎉

Version: 4.0  
Dernière mise à jour: Novembre 2025
