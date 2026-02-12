# Ligue 1 Dashboard - Data Engineering Project

## Présentation du Projet
Ce projet est une application web interactive permettant de suivre les statistiques de la **Ligue 1 McDonald's (Saison 2025/2026)**. L'application récupère automatiquement des données en temps réel via du **web scraping**, les stocke dans une base de données relationnelle et les expose via un dashboard dynamique.

### Fonctionnalités principales :
* **Classement en direct** : Visualisation du classement complet avec logos des clubs.
* **Meilleurs Buteurs & Passeurs** : Statistiques détaillées avec photos des joueurs et logos d'équipes.
* **Palmarès Historique** : Liste des clubs les plus titrés et historique des vainqueurs par saison.
* **Moteur de Recherche** : Recherche globale de joueurs à travers toutes les statistiques.
* **Analyse de Performance** : Graphique interactif des contributions (Buts + Passes) par joueur.

---

## Stack Technique
* **Langage** : `Python 3.12`
* **Scraping** : 
    * `Playwright` : Pour gérer le rendu JavaScript dynamique (essentiel pour Foot Mercato).
    * `BeautifulSoup4` : Pour le parsing précis du HTML.
* **Base de données** : `PostgreSQL 16` (Stockage structuré et persistant).
* **Dashboard** : `Streamlit` & `Altair` (Visualisation de données moderne).
* **Conteneurisation** : `Docker` & `Docker-Compose`.

---

## Installation et Lancement

### Prérequis
* Docker et Docker Compose installés sur votre machine.

### Démarrage rapide
1.  **Cloner le dépôt** :
    ```bash
    git clone [https://github.com/VOTRE_NOM_UTILISATEUR/VOTRE_REPO.git](https://github.com/VOTRE_NOM_UTILISATEUR/VOTRE_REPO.git)
    cd Project_DataEngineering
    ```
2.  **Lancer l'application avec Docker** :
    ```bash
    docker-compose up --build
    ```
3.  **Accéder au Dashboard** :
    Une fois le déploiement terminé (le terminal affichera "Starting Streamlit"), ouvrez votre navigateur sur : `http://localhost:8501`

---

## 🏗 Architecture & Choix Techniques

### Stratégie de Scraping
Nous utilisons **Playwright** en mode *headless*. Ce choix est dicté par la nature du site source (Foot Mercato), qui utilise du chargement asynchrone pour ses tableaux. 
Les scrapers sont orchestrés par `scraper/run_all.py` et lancés automatiquement au démarrage du conteneur via un script `entrypoint.sh` qui s'assure que la base de données est prête avant de commencer.



### Modèle de Données (SQL)
Les données sont normalisées dans PostgreSQL. Nous utilisons la clause `ON CONFLICT` (Upsert) pour garantir que le dashboard affiche toujours les données les plus récentes sans jamais créer de doublons, même si le scraper est relancé plusieurs fois.

### Dockerisation
Le projet est segmenté en deux micro-services :
1.  **Service `db`** : Base PostgreSQL avec volume persistant (`postgres_data`) pour ne pas perdre les données entre deux redémarrages.
2.  **Service `web`** : Conteneur Python contenant l'application et les navigateurs nécessaires au scraping.

---

## Structure du projet
```text
Project_DataEngineering/
├── app/
│   ├── app.py              # Code de l'interface Streamlit
│   └── style.css           # Personnalisation visuelle
├── scraper/
│   ├── __init__.py         # ¨Permet l'import python
│   ├── fetch.py            # Logique Playwright
│   ├── db.py               # Connexion à la base pour les scrapers
│   ├── run_all.py          # Orchestrateur
│   ├── standings.py        # Scraper Classement
│   ├── scorers.py          # Scraper Buteurs
│   ├── assists.py          # Scraper Passeurs
│   └── palmares.py         # Scraper Palmarès
├── sql/
│   └── schema.sql          # Création des tables (utilisé par Docker)
├── .dockerignore           # Pour ne pas copier les fichiers inutiles
├── .env                    # Tes variables secrètes (MDP, DB)
├── .gitignore              # Pour ne pas envoyer .env sur GitHub
├── docker-compose.yml      # Orchestration des services
├── Dockerfile              # Instructions de build
├── entrypoint.sh           # Script de démarrage
├── requirements.txt        # Liste des bibliothèques Python
└── README.md               # Documentation
