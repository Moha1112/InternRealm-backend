# InternRealm - Backend

## Description

Ce projet correspond à la partie backend de la plateforme **InternRealm**, une API REST développée manuellement avec **Django** sans utiliser Django REST Framework.  
Il gère la logique métier, la gestion des utilisateurs, les offres de stages, les candidatures, et la recherche sémantique.

---

## Technologies utilisées

- **Python 3.12**
- **Django** : framework web utilisé pour construire l’API backend.
- **PostgreSQL** : base de données relationnelle utilisée pour stocker les données.
- **pgvector** : extension PostgreSQL utilisée pour le stockage des embeddings vectoriels.
- **sentence-transformers** : bibliothèque Python pour l’encodage sémantique des descriptions d’offres.
- **JWT remplacé par un token sécurisé transmis via HTTPS** (authentification personnalisée).

---

## Installation

1. Cloner le dépôt backend :
```bash
   git clone https://github.com/MohaIfk/InternRealm-backend.git
````

2. Créer un environnement virtuel Python et l’activer :

```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
```

3. Installer les dépendances :

```bash
   pip install -r requirements.txt
```

4. Configurer la base de données PostgreSQL et l’extension pgvector.

5. Appliquer les migrations :

```bash
   python manage.py migrate
```

6. Démarrer le serveur Django :

```bash
   python manage.py runserver
```

---

## API

L’API REST est construite manuellement, voici quelques points clés :

* Endpoints sécurisés via token HTTPS.
* Routes pour la gestion des utilisateurs, offres, candidatures, rapports, notifications, etc.
* Intégration de la recherche sémantique via sentence-transformers.
* Envoi d’emails pour notifications.

---

## Configuration

* Variables sensibles (base de données, clés secrètes, etc.) configurables dans `.env` ou via `settings.py`.
* Configurer l’URL du frontend pour les CORS si nécessaire.

---

## Structure du projet

* `internrealm/` : code principal Django (models, views, urls)
* `semantic_search/` : module pour la recherche sémantique
* `emails/` : gestion des notifications par email
* `manage.py` : outil de gestion Django

---

## Contribution

Merci de créer une branche dédiée pour vos modifications et de proposer une Pull Request.

---

## Licence

Ce projet est sous licence MIT.

---

## Contact

Pour toute question, merci de contacter **\[Mohammed Benzahouane]** à l’adresse email : \[[mohammed.benzahouane@uit.ac.ma](mohammed.benzahouane@uit.ac.ma)]
