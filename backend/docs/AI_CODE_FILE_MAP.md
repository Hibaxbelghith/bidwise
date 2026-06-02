# Fiche fichiers IA - Explication rapide soutenance

Last updated: 2026-06-02

## Objectif

Cette fiche sert si l'expert ouvre un fichier au hasard et demande son role.

Elle donne une explication courte des fichiers principaux du systeme IA BidWise.

## Backend - Profil et CV

### `backend/users/models.py`

Contient les modeles utilisateur, profil et resume.

A dire:

```text
Ce fichier stocke les informations profil qui servent aux recommandations: skills, roles cibles, experience, preferences et CV actif.
```

### `backend/users/views.py`

Expose les endpoints profil:

- upload CV;
- activation/suppression CV;
- application des suggestions CV;
- suggestions skills/roles/interests.

A dire:

```text
Ce fichier controle les actions utilisateur autour du profil. Il verifie que chaque CV appartient bien au profil courant.
```

### `backend/users/tasks.py`

Taches Celery liees au profil:

- parsing CV;
- extraction semantique;
- generation embeddings profil.

A dire:

```text
Les traitements lents du CV ne bloquent pas l'API. Ils passent par Celery sur la queue profile_resume.
```

### `backend/users/resume_parsing/service.py`

Extrait le texte brut des fichiers CV.

A dire:

```text
Ce service transforme le fichier CV en texte exploitable par le pipeline semantique.
```

### `backend/users/resume_semantic/`

Nettoie et structure le contenu du CV.

A dire:

```text
Ce module extrait des signaux utiles du CV: skills, role probable, domaines, outils et resume semantique.
```

## Backend - Features et embeddings

### `backend/ai/user_features.py`

Construit les features utilisateur a partir du profil.

A dire:

```text
C'est le point de conversion entre les donnees profil et les signaux utilises par le moteur de recommandation.
```

### `backend/ai/embeddings.py`

Construit le texte d'embedding profil et gere l'embedding classique.

A dire:

```text
Ce fichier transforme le profil en representation semantique exploitable pour la recherche et la similarite.
```

### `backend/ai/jobbert.py`

Gere JobBERT:

- chargement modele;
- embeddings profil/offre;
- scores de similarite;
- cache et timeout.

A dire:

```text
JobBERT est le modele specialise emploi. Il donne le signal semantique principal entre profil et opportunites.
```

## Backend - Recommandation

### `backend/ai/views.py`

Endpoint principal For You.

Responsabilites:

- lecture profil;
- cache recommandations;
- ranking;
- fallback;
- serialization complete des opportunites;
- header cache.

A dire:

```text
C'est le point d'entree API de la page For You. Il orchestre le ranking et renvoie des opportunites completes avec explications.
```

### `backend/ai/retrieval.py`

Recupere les candidats a recommander.

A dire:

```text
Avant de scorer, le systeme selectionne un pool de candidats pertinents pour eviter de traiter toute la base inutilement.
```

### `backend/ai/recommendation_service.py`

Calcule le score final.

Responsabilites:

- similarite;
- role alignment;
- skills;
- business signals;
- score final;
- tri.

A dire:

```text
Ce fichier combine l'IA semantique et les signaux metier pour produire un score exploitable.
```

### `backend/ai/quality_gates.py`

Decide si une offre devient `STRONG_MATCH` ou reste `RELATED_REVIEW`.

A dire:

```text
Ce fichier protege la qualite. Il evite qu'une offre avec un score correct mais un doute important soit affichee comme recommandation forte.
```

### `backend/ai/explainability.py`

Construit les raisons visibles dans l'UI.

A dire:

```text
Ce fichier transforme les signaux internes en explications lisibles: pourquoi l'offre correspond et quoi verifier.
```

### `backend/ai/business_families.py`

Regroupe les metiers proches.

A dire:

```text
Il permet de comprendre qu'un poste peut etre proche du profil meme si le titre exact est different.
```

### `backend/ai/hierarchy.py`

Detecte les ecarts de seniority, responsabilite et qualification.

A dire:

```text
Il evite par exemple de recommander trop fortement un poste senior a un profil junior.
```

### `backend/ai/recommendation_llm.py`

Validation LLM limitee aux cas de hierarchie ambigus.

A dire:

```text
Le LLM n'est pas le moteur principal. Il sert seulement de reviewer cache-only sur certains cas ambigus.
```

## Backend - LLM enrichissement

### `backend/ai/llm/providers.py`

Abstraction des providers LLM:

- Gemini;
- Ollama;
- fallback.

A dire:

```text
Ce fichier permet de changer de provider LLM sans changer le reste du pipeline.
```

### `backend/ai/llm/opportunity_enrichment.py`

Prompt et logique d'extraction skills opportunite.

A dire:

```text
Il enrichit les offres avec peu de skills en analysant la description, mais il tourne hors ligne.
```

### `backend/ai/tasks.py`

Taches Celery IA:

- enrichissement opportunites;
- backfill;
- orchestration.

A dire:

```text
Les traitements LLM sont decales en arriere-plan pour ne pas ralentir l'utilisateur.
```

### `backend/ai/management/commands/enrich_opportunities_with_gemini.py`

Commande historique d'enrichissement.

A dire:

```text
Le nom contient Gemini pour compatibilite historique, mais le provider peut etre Ollama local selon la configuration.
```

## Backend - Opportunites

### `backend/opportunities/pipeline.py`

Orchestration scraping/materialisation/embeddings.

A dire:

```text
Ce fichier coordonne la collecte et la preparation des opportunites avant qu'elles deviennent recommandables.
```

### `backend/opportunities/materialization/service.py`

Convertit les donnees scrapees en `Opportunite`.

Responsabilites:

- normalisation;
- source;
- date;
- description;
- skills;
- dedupe;
- republication.

A dire:

```text
Il nettoie les offres brutes et evite les doublons visibles dans For You.
```

## Frontend - Profil

### `frontend/src/features/profile/components/ResumeSection.jsx`

UI upload CV.

A dire:

```text
Ce composant permet d'uploader un CV, suivre l'analyse, previsualiser le fichier et appliquer les suggestions extraites.
```

### `frontend/src/features/profile/components/ProfileAutocompleteInput.jsx`

Autocomplete skills/roles/interests.

A dire:

```text
Il guide l'utilisateur vers des termes plus propres pour ameliorer la qualite des recommandations.
```

## Frontend - For You

### `frontend/src/features/opportunities/hooks/useOpportunityRecommendations.js`

Charge les recommandations.

A dire:

```text
Ce hook recupere les recommandations completes depuis l'API et evite les appels detail par offre.
```

### `frontend/src/features/opportunities/components/recommendations/ForYouFeed.jsx`

Organise les resultats For You.

A dire:

```text
Il separe Strong matches et Related opportunities pour rendre le ranking plus clair et plus prudent.
```

### `frontend/src/features/opportunities/components/recommendations/ForYouPreviewCard.jsx`

Carte offre dans la liste For You desktop.

A dire:

```text
Elle affiche les informations importantes: entreprise, source, date, localisation, contrat, score et raisons principales.
```

### `frontend/src/features/opportunities/components/recommendations/OpportunitySplitDetailPanel.jsx`

Panneau detail lateral For You.

A dire:

```text
Il permet de lire la description, les skills, l'explication IA et le bouton Apply sans quitter la page.
```

### `frontend/src/features/opportunities/components/recommendations/RecommendationInsightPanel.jsx`

Bloc explication du match.

A dire:

```text
Il affiche le score, la confiance, les raisons du match et les points a verifier.
```

### `frontend/src/features/opportunities/components/detail/OpportunitySkillsSection.jsx`

Affichage skills.

A dire:

```text
Il affiche les competences de l'offre et le badge AI quand elles viennent de l'enrichissement LLM.
```

## Fichiers a ne pas presenter comme code actif

### Migrations anciennes ESCO

Les migrations historiques peuvent encore mentionner ESCO.

A dire:

```text
Ce sont des migrations d'historique base de donnees. Le code ESCO actif a ete retire de la version finale.
```

### Benchmarks et rapports

Les rapports benchmark servent a la validation.

A dire:

```text
Ce ne sont pas des services runtime. Ils documentent les tests et resultats utilises pour valider le systeme.
```

### LLM reranker

Le reranker LLM a ete prototype puis retire.

A dire:

```text
Il n'est pas dans la version finale parce qu'il etait moins stable que l'architecture JobBERT + scoring metier.
```
