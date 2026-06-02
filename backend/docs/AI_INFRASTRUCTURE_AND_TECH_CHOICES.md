# Infrastructure IA et choix techniques

Last updated: 2026-06-02

## Objectif

Ce document explique les choix techniques autour de l'infrastructure IA:

- Docker;
- PostgreSQL + pgvector;
- Redis;
- Celery;
- HuggingFace;
- JobBERT;
- Ollama/Gemini;
- cache;
- scalabilite et securite.

## Vue d'ensemble

```text
Frontend React
    |
    v
Backend Django API
    |
    +--> PostgreSQL + pgvector
    +--> Redis cache / broker
    +--> Celery workers
    +--> HuggingFace models
    +--> Ollama/Gemini providers
```

## Docker Compose

Le projet utilise Docker Compose pour lancer tous les services necessaires.

Services:

| Service | Role |
| --- | --- |
| `backend` | API Django, migrations, endpoints |
| `celery_worker` | taches generales: scraping, materialisation, embeddings |
| `celery_profile` | taches CV/profil |
| `celery_enrichment` | enrichissement LLM opportunites |
| `celery_beat` | planification periodique |
| `flower` | monitoring Celery |
| `db` | PostgreSQL + pgvector |
| `redis` | broker Celery + cache Django |

## Avantages Docker

- environnement reproductible;
- moins de problemes d'installation locale;
- separation des responsabilites;
- base PostgreSQL/pgvector prete;
- Redis inclus;
- workers Celery faciles a isoler;
- cache HuggingFace partage entre backend et workers;
- demo soutenance plus stable.

Phrase a dire:

```text
Docker me permet de presenter une architecture proche production, pas seulement un script local.
```

## PostgreSQL + pgvector

PostgreSQL gere les donnees metier:

- utilisateurs;
- profils;
- resumes;
- opportunites;
- sources;
- metadonnees d'enrichissement;
- decisions LLM cachees.

pgvector gere les representations vectorielles:

- embeddings opportunites;
- similarite profil/offre;
- retrieval semantique.

Pourquoi ce choix:

- evite d'ajouter une vector database separee;
- garde les donnees et les vecteurs dans la meme base;
- simplifie la maintenance;
- adapte au volume actuel.

Limite:

```text
A tres grande echelle, on pourrait evaluer une solution vectorielle dediee, mais pour cette version pgvector est un bon compromis.
```

## Redis

Redis est utilise pour:

- broker Celery;
- result backend Celery;
- cache Django;
- locks de taches;
- cache For You;
- cache facets Explore.

Pourquoi:

- tres rapide;
- simple avec Django;
- standard pour Celery;
- permet de ne pas recalculer les memes reponses.

## Celery

Celery deplace les traitements longs hors de l'API.

Queues:

```text
celery
  scraping, materialisation, embeddings, monitoring

profile_resume
  parsing CV, extraction CV, embeddings profil

opportunity_enrichment
  LLM enrichissement opportunites
```

Pourquoi plusieurs queues:

- prioriser les actions utilisateur;
- isoler le LLM lent;
- eviter qu'une tache longue bloque tout;
- rendre le systeme observable.

## HuggingFace cache

Les modeles IA sont caches localement:

```text
.cache/huggingface -> /home/appuser/.cache/huggingface
```

Avantages:

- evite de telecharger le modele a chaque lancement;
- compatible Docker;
- reduit le temps de demarrage;
- permet un fonctionnement plus stable pendant la soutenance.

## Modele embedding generaliste

Modele:

```text
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

Usage:

- embeddings opportunites classiques;
- similarite multilingue;
- recherche semantique generale.

Pourquoi:

- leger;
- multilingue;
- adapte aux donnees francais/anglais;
- dimensions 384, donc stockage raisonnable.

## JobBERT

Modele:

```text
TechWolf/JobBERT-v3
```

Usage:

- matching profil/offre specialise RH;
- reranking semantique emploi;
- role semantic score;
- ajustement du score.

Pourquoi JobBERT:

- specialise dans les textes emploi;
- meilleur pour comprendre role, skills, description de poste;
- utile quand les titres ne sont pas exactement identiques.

Pourquoi pas seulement JobBERT:

- ne gere pas les preferences utilisateur;
- peut etre trompe par des mots generiques;
- ne remplace pas les controles seniority/contrat/localisation.

## Ollama

Ollama sert a executer un LLM localement.

Usages retenus:

- enrichissement offline des offres;
- extraction de skills depuis longues descriptions;
- eventuellement validation hierarchy si decision deja cachee.

Avantages:

- local;
- pas de cout API;
- utile pour tests;
- controle du modele;
- donnees moins exposees.

Limites:

- lent selon modele/prompt;
- JSON parfois instable;
- pas adapte au reranking temps reel For You.

Decision:

```text
Ollama est utilise hors ligne, pas comme dependance directe de la page For You.
```

## Gemini

Gemini reste disponible comme provider LLM externe.

Avantages:

- modele puissant;
- meilleure qualite possible selon cle API;
- fallback possible.

Pourquoi ne pas en dependre totalement:

- quota;
- latence reseau;
- cout;
- confidentialite;
- soutenance locale plus fragile.

## Cache For You

Le cache For You stocke la reponse complete de recommandation pendant un TTL court.

Cle basee sur:

- utilisateur;
- profil;
- limite;
- signature profil;
- embeddings profil;
- nombre d'offres actives;
- derniere modification d'offre;
- opportunites suivies.

Avantages:

- refresh instantane;
- moins de calcul IA repete;
- UX plus fluide;
- invalidation automatique quand les donnees changent.

## Securite

Mesures:

- endpoints profil lies a l'utilisateur authentifie;
- CV associe uniquement au profil proprietaire;
- validation type fichier;
- stockage cloud optionnel;
- timeouts LLM;
- fallback si provider indisponible;
- pas d'appel LLM bloquant avec donnees utilisateur pendant For You;
- pas d'execution du contenu CV.

## Scalabilite

Le systeme peut evoluer par:

- ajout de workers Celery;
- augmentation de batch embeddings;
- cache Redis plus robuste;
- deploiement PostgreSQL/pgvector plus puissant;
- separation future du vector search si volume tres eleve;
- monitoring via Flower/logs;
- enrichissement LLM batch par source.

## Message court soutenance

```text
L'infrastructure est pensee pour separer le temps reel des traitements lourds. Django sert l'API, PostgreSQL/pgvector stocke donnees et embeddings, Redis gere cache et queues, Celery execute CV/scraping/LLM en arriere-plan, et Docker rend l'ensemble reproductible.
```
