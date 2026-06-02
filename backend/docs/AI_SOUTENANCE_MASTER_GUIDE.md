# Guide maitre soutenance - Systeme IA BidWise

Last updated: 2026-06-02

## Objectif du document

Ce document sert de support principal pour expliquer le travail IA pendant la soutenance.

Il complete les guides existants:

- `AI_TEST_GUIDE.md`: tests documentes.
- `AI_RECOMMENDATION_SOUTENANCE_TEST_GUIDE.md`: profils de demonstration.
- `AI_RECOMMENDATION_FINAL_VALIDATION.md`: validation finale du moteur de recommandation.
- `LLM_OPPORTUNITY_ENRICHMENT_CELERY.md`: enrichissement LLM des offres.
- `PERFORMANCE.md`: performance recherche et navigation opportunites.
- `AI_PROFILE_PIPELINE.md`: pipeline profil, CV, skills et suggestions.
- `AI_RECOMMENDATION_PIPELINE.md`: pipeline For You, JobBERT, scoring et UI.
- `AI_INFRASTRUCTURE_AND_TECH_CHOICES.md`: Docker, Redis, Celery, pgvector, JobBERT, Ollama.
- `AI_CODE_FILE_MAP.md`: role rapide des fichiers si l'expert ouvre le code.

## Message principal a dire

BidWise n'est pas un simple moteur de recherche par mots-cles. C'est un systeme hybride de recommandation qui combine:

- donnees utilisateur: profil, roles cibles, competences, preferences, CV;
- donnees opportunites: titre, description, source, localisation, contrat, skills;
- IA semantique: embeddings profil/offres et JobBERT specialise emploi;
- signaux metier: role, skills, famille professionnelle, experience, localisation, mode de travail;
- LLM hors ligne: enrichissement progressif des offres pauvres en skills;
- garde-fous qualite: separation entre `Strong matches` et `Related opportunities`;
- performance: cache court For You, Celery, Redis, queues separees;
- securite: API authentifiee, validation upload CV, stockage cloud optionnel, timeouts et fallbacks.

Phrase courte:

```text
Le moteur BidWise combine IA semantique, scoring metier, enrichissement LLM asynchrone et garde-fous qualite pour recommander des offres pertinentes sans bloquer l'utilisateur.
```

## Plan de speech 30 minutes

### 0 - 3 min: contexte et probleme

Dire:

```text
BidWise aide un utilisateur a trouver les opportunites les plus pertinentes selon son profil, son CV, ses competences, ses preferences et les offres collectees depuis plusieurs sources.
```

Points:

- beaucoup d'offres;
- sources heterogenes;
- descriptions parfois pauvres ou longues;
- skills parfois absents;
- profil utilisateur parfois incomplet;
- besoin d'un ranking explicable.

### 3 - 7 min: architecture generale

Presenter le schema global:

```text
Scraping -> materialisation -> embeddings/LLM enrichment -> profil/CV -> For You ranking -> UI explicable
```

Insister sur:

- separation backend/frontend;
- PostgreSQL + pgvector;
- Redis cache/broker;
- Celery pour taches longues;
- HuggingFace/JobBERT pour semantique;
- Ollama/Gemini pour LLM offline.

### 7 - 12 min: pipeline profil et CV

Expliquer:

- profil manuel;
- upload CV;
- stockage fichier, Cloudinary possible;
- parsing CV;
- extraction skills;
- suggestions appliquees par utilisateur;
- embeddings profil;
- profile strength.

Phrase utile:

```text
Le profil n'est pas statique: il peut etre enrichi par le CV et par des suggestions controlees par l'utilisateur.
```

### 12 - 18 min: pipeline opportunites et LLM

Expliquer:

- scraping multi-sources;
- materialisation;
- dedupe/republication;
- embeddings opportunite;
- LLM enrichissement offline pour skills manquants;
- badge AI dans l'UI.

Phrase utile:

```text
Le LLM n'est pas appele pendant la recommandation. Il ameliore la qualite des donnees en arriere-plan.
```

### 18 - 24 min: moteur de recommandation

Expliquer:

- retrieval candidats;
- JobBERT;
- formule score;
- business signals;
- quality gates;
- Strong vs Related;
- explications UI.

Formule a dire:

```text
Score de base = 70% similarite semantique + 30% signaux metier.
Ensuite j'applique des bonus, penalites et plafonds pour proteger la qualite.
```

### 24 - 27 min: performance, Docker, securite

Expliquer:

- cache For You;
- Redis;
- queues Celery separees;
- conteneurs Docker;
- timeouts;
- fallbacks;
- endpoints authentifies.

### 27 - 30 min: demo et limites

Demo:

- Comptable/Audit;
- Backend Developer;
- DevOps/Cloud;
- Data Analyst/BI.

Conclusion:

```text
La version finale privilegie la stabilite, l'explicabilite et la precision des Strong matches plutot qu'un score artificiellement eleve.
```

## Architecture globale

```text
Sources externes
  LinkedIn / Keejob / EmploiTunisie / autres
        |
        v
Scraping + materialisation
        |
        v
Opportunites normalisees
  titre, description, source, URL, ville, contrat, skills, date
        |
        +--> Embeddings opportunites
        +--> JobBERT embeddings opportunites
        +--> Enrichissement LLM offline si skills faibles

Utilisateur
  profil manuel + preferences + CV optionnel
        |
        v
Extraction CV + suggestions profil
        |
        v
Features IA profil
  roles, skills, experience, localisation, resume signals
        |
        v
For You API
  retrieval + JobBERT + scoring metier + quality gates + cache
        |
        v
UI For You
  Strong matches + Related opportunities + explications + Apply
```

## Architecture Docker et conteneurs

Le projet utilise Docker Compose pour rendre l'environnement reproductible.

Conteneurs principaux:

```text
backend
  role: API Django, endpoints, migrations, admin, recommandations
  port: 8000

celery_worker
  role: queue principale
  usages: scraping, materialisation, embeddings, monitoring

celery_profile
  role: queue profile_resume
  usages: parsing CV, extraction CV, embeddings profil

celery_enrichment
  role: queue opportunity_enrichment
  usages: enrichissement LLM des offres

celery_beat
  role: planification periodique
  usages: declencher des taches recurrentes

flower
  role: monitoring Celery
  port: 5555

db
  image: pgvector/pgvector:pg16
  role: PostgreSQL + vecteurs

redis
  role: broker Celery + cache Django
```

### Pourquoi Docker?

Avantages:

- meme environnement pour developpement, test et soutenance;
- dependances IA lourdes isolees;
- PostgreSQL/pgvector disponible sans installation manuelle;
- Redis et Celery faciles a lancer;
- HuggingFace cache monte dans `.cache/huggingface`;
- un service lent ne bloque pas tout le systeme;
- plus facile a expliquer comme architecture deployable.

### Pourquoi plusieurs workers Celery?

Un seul worker aurait pu tout faire, mais ce serait fragile.

Separation choisie:

```text
celery_worker:
  taches normales et pipeline opportunites

celery_profile:
  taches utilisateur sensibles, comme CV

celery_enrichment:
  taches LLM lentes et non critiques
```

Avantage:

```text
Si Ollama est lent pendant un enrichissement, l'upload CV et le scraping ne restent pas bloques derriere cette tache.
```

### Pourquoi PostgreSQL + pgvector?

PostgreSQL garde les donnees relationnelles classiques:

- utilisateurs;
- profils;
- resumes;
- opportunites;
- sources;
- taches et metadonnees.

pgvector permet de stocker et comparer les embeddings:

- embeddings opportunites;
- similarite semantique;
- acceleration future a plus grande echelle.

Choix pragmatique:

```text
Pas besoin d'ajouter Elasticsearch ou un vector database separe pour cette version. PostgreSQL + pgvector suffit et reduit la complexite.
```

### Pourquoi Redis?

Redis sert a deux choses:

- broker/result backend Celery;
- cache Django.

Cas d'usage:

- cache For You;
- cache facets Explore;
- locks d'enrichissement LLM;
- files de taches.

## Ce qu'il faut mettre en valeur

### 1. Le profil utilisateur est enrichi progressivement

Le systeme ne depend pas uniquement de champs saisis manuellement.

Il peut utiliser:

- competences saisies;
- roles cibles;
- localisation;
- type de contrat;
- mode de travail;
- niveau et annees d'experience;
- CV upload;
- extraction de skills depuis le CV;
- suggestion de roles et skills a appliquer au profil.

### 2. Le CV est traite de maniere asynchrone

L'upload du CV ne bloque pas toute l'application.

Pipeline:

```text
Upload CV
  -> sauvegarde fichier
  -> creation ProfileResume
  -> tache Celery profile_resume
  -> parsing texte
  -> extraction semantique
  -> suggestions profil
  -> embeddings profil
  -> For You s'ameliore
```

Le frontend montre l'etat de traitement et propose a l'utilisateur de garder ou ignorer les suggestions.

### 3. Les offres sont enrichies hors ligne

Certaines sources ne fournissent pas de skills propres. Le LLM extrait des skills depuis les descriptions longues, mais seulement en arriere-plan.

Choix important:

```text
Le LLM ne bloque pas la page For You.
```

Il est utilise comme traitement de qualite de donnees, pas comme dependance obligatoire du ranking en temps reel.

### 4. JobBERT donne le signal semantique principal

JobBERT est un modele specialise pour le domaine emploi/recrutement.

Il permet de comparer:

- texte profil;
- roles cibles;
- skills;
- resume;
- titre et description de l'offre.

Il aide a retrouver des offres proches meme quand le titre n'est pas exactement identique.

Pourquoi JobBERT et pas seulement MiniLM generaliste?

```text
MiniLM multilingual est utile pour une similarite generale, mais JobBERT est specialise dans les textes d'emploi. Il comprend mieux les relations entre profil, role, competences et description d'offre.
```

Limite:

```text
JobBERT n'est pas un juge final. Il donne une proximite semantique, puis le scoring metier decide si l'offre est vraiment recommandable.
```

### 5. Le scoring n'est pas seulement IA brute

La similarite semantique seule peut se tromper, surtout avec des mots generiques comme `Excel`, `SQL`, `reporting`, `backend`, `analyse`.

Le systeme ajoute donc des signaux metier:

- alignement du role cible;
- matching skills;
- famille professionnelle;
- seniority;
- contrat;
- localisation;
- mode de travail;
- experience;
- preuves fortes ou faibles.

Formule simplifiee a presenter:

```text
score_base = 0.70 * semantic_score + 0.30 * business_signal
```

Avec:

```text
semantic_score = max(score embedding classique, score JobBERT)
business_signal = role + skills + famille metier + localisation + contrat + experience
```

Puis:

```text
score_final = score_base + bonus - penalites - caps
```

Exemples de bonus:

- role cible detecte;
- plusieurs skills alignes;
- meme famille metier;
- localisation compatible;
- mode de travail compatible;
- JobBERT fort.

Exemples de penalites/caps:

- un seul skill generique;
- pas de preuve metier;
- seniority trop elevee;
- famille metier incompatible;
- role sparse sans description;
- offre proche mais trop differente du role cible.

Pourquoi cette complexite?

```text
Parce qu'une similarite brute peut etre trompeuse. Le score doit representer une decision de recommandation, pas seulement une distance mathematique.
```

### 6. Les garde-fous protegent la qualite

Le systeme ne force pas toutes les offres dans `Strong matches`.

Il separe:

- `Strong matches`: bonnes preuves role + skills + preference.
- `Related opportunities`: offres interessantes mais avec un doute.

Exemples de doute:

- poste senior pour profil junior;
- meme famille mais role different;
- skill generique seulement;
- localisation ou contrat a verifier;
- description pauvre.

Cette separation est une force, pas une faiblesse. Elle evite de vendre une mauvaise offre comme recommandation forte.

### 7. La performance est prise en compte

Optimisations principales:

- cache court de la reponse For You;
- cle cache dependante du profil et des offres;
- Celery pour CV, scraping, enrichissement;
- queue separee pour le LLM;
- Redis cache;
- pagination et filtres backend pour Explore;
- pas d'appel LLM bloquant dans l'API recommendation;
- full payload dans For You pour eviter les appels details par carte.

### 8. La securite est prise en compte

Points defendables:

- endpoints profil/CV attaches a l'utilisateur authentifie;
- un utilisateur ne peut manipuler que son CV;
- validation du fichier CV cote backend;
- stockage cloud optionnel via Cloudinary pour eviter de garder les fichiers localement en production;
- timeouts LLM;
- fallback si IA indisponible;
- pas d'execution de contenu CV;
- donnees sensibles limitees aux champs utiles.

## Pourquoi Ollama?

Ollama permet d'executer un LLM localement.

Avantages:

- pas besoin d'envoyer toutes les donnees a une API externe pendant les tests;
- utile pour soutenance et developpement local;
- controle des couts;
- controle du modele;
- fonctionne bien pour des taches offline comme extraction de skills;
- peut etre isole dans une queue Celery lente.

Pourquoi pas Ollama en temps reel sur For You?

```text
Parce qu'un LLM local peut prendre plusieurs secondes ou minutes selon le prompt. Pour une page utilisateur, j'ai choisi de ne pas bloquer l'API sur le LLM.
```

Utilisation finale:

- enrichissement offline des offres;
- validation hierarchy seulement si decision deja cachee;
- pas de reranking LLM en production finale.

## Pourquoi garder Gemini dans le code?

Le provider LLM est abstrait.

Cela permet:

- Gemini si une cle API est disponible;
- Ollama local en developpement/soutenance;
- fallback si un provider echoue;
- meme pipeline d'enrichissement peu importe le provider.

Le nom de la commande `enrich_opportunities_with_gemini` est historique. Le provider reel depend de `.env`.

## Choix rejetes ou limites assumees

### ESCO

ESCO a ete teste puis retire du code actif.

Pourquoi:

- integration lourde;
- beaucoup de donnees;
- complexite de normalisation;
- gain insuffisant pour la version finale;
- risque de confusion avant soutenance.

Decision:

```text
Garder une taxonomie metier interne plus controlee et JobBERT pour la semantique.
```

### LLM reranking

Un reranker LLM a ete prototype.

Pourquoi il n'est pas garde:

- reponses JSON incompletes;
- temps d'attente eleve;
- classement parfois incoherent;
- pas de gain stable sur les profils valides.

Decision:

```text
Ne pas livrer une feature instable juste pour dire que le LLM rerank. Le systeme final est plus fiable sans lui.
```

### Recommandation 100% automatique

Le systeme ne promet pas un ranking parfait.

Il promet:

- des Strong matches precis;
- des Related opportunities utiles;
- des explications;
- une separation claire des doutes.

## Demo conseillee

### Demo 1 - Profil Comptable / Audit

Objectif: montrer un profil simple mais metier.

A montrer:

- `Strong matches` avec comptable/audit;
- skills `Comptabilite`, `Audit`, `Excel`;
- explications `Why this matches`;
- une offre senior en `Related opportunities` pour montrer les garde-fous.

### Demo 2 - Profil Backend Developer

Objectif: montrer un profil technique avec variantes de titres.

A montrer:

- `Python Backend Developer` en tete;
- `Full Stack Engineer` justifie par Python/FastAPI/PostgreSQL;
- offres PHP/Laravel ou DevOps gardees en review;
- distinction entre role direct et role proche.

### Demo 3 - Profil DevOps / Cloud

Objectif: montrer un domaine technique riche.

A montrer:

- `Junior DevOps Engineer`;
- `DevOps Engineer / AI Ops`;
- skills Azure, AWS, Docker, Terraform, CI/CD;
- offres senior gardees en review.

### Demo 4 - Profil Data Analyst / BI

Objectif: montrer la comprehension semantique autour BI, reporting, KPIs.

A montrer:

- `Data Analyst Marketing`;
- `Data Analyst` / `Data Operations Analyst`;
- offres reporting/projet en review.

## Questions probables de l'expert

### Pourquoi ne pas utiliser seulement le LLM pour recommander?

Reponse:

```text
Parce qu'un LLM local est lent, couteux en temps et pas toujours stable. Pour une page For You, il faut une reponse fiable. J'utilise donc JobBERT et des signaux deterministes pour le ranking temps reel, et le LLM en offline pour enrichir les donnees.
```

### Pourquoi utiliser des regles si on a JobBERT?

Reponse:

```text
JobBERT comprend la proximite semantique, mais il ne connait pas toutes les contraintes produit: junior vs senior, contrat, localisation, mode de travail, ou risque d'un skill generique. Les regles ne remplacent pas l'IA, elles l'encadrent pour produire une recommandation exploitable.
```

### Pourquoi certaines offres pertinentes sont en Related?

Reponse:

```text
Related ne veut pas dire mauvais. Cela signifie que l'offre est interessante mais qu'il existe un point a verifier: seniority, specialisation, stack differente, ou preuve insuffisante. C'est un garde-fou pour eviter les faux positifs.
```

### Pourquoi le LLM reranking n'est pas active?

Reponse:

```text
Je l'ai prototype, mais le modele local teste ne renvoyait pas toujours un classement complet et stable. Pour la version finale, j'ai garde l'architecture la plus fiable: LLM offline pour enrichir les offres, JobBERT + scoring metier pour le ranking.
```

### Pourquoi Cloudinary?

Reponse:

```text
En production, les fichiers CV ne doivent pas dependre du disque local du container. Cloudinary permet de stocker les resumes de maniere externe, durable et accessible, tandis que le backend garde seulement les metadonnees et les resultats d'analyse.
```

### Comment le systeme evite l'attente 5 a 10 minutes?

Reponse:

```text
Les traitements longs sont sortis du chemin critique: CV et LLM tournent avec Celery. Pour For You, la reponse complete est cachee quelques minutes avec une cle qui change si le profil ou les offres changent.
```

## Fichiers importants a connaitre

### Profil et CV

- `backend/users/models.py`: profil, CV, champs semantiques.
- `backend/users/views.py`: upload CV, activation, suggestions.
- `backend/users/tasks.py`: parsing CV et embeddings profil.
- `backend/users/resume_parsing/`: extraction texte CV.
- `backend/users/resume_semantic/`: extraction semantique CV.
- `frontend/src/features/profile/components/ResumeSection.jsx`: UI upload, statut, suggestions.

### Suggestions profil

- `backend/opportunities/autocomplete/service.py`: suggestions roles, skills, interests.
- `frontend/src/features/profile/components/ProfileAutocompleteInput.jsx`: autocomplete frontend.

### Recommandation IA

- `backend/ai/views.py`: endpoint For You, cache, serialization.
- `backend/ai/user_features.py`: construction features profil.
- `backend/ai/embeddings.py`: texte embedding profil.
- `backend/ai/jobbert.py`: embeddings JobBERT.
- `backend/ai/retrieval.py`: recuperation candidats.
- `backend/ai/recommendation_service.py`: scoring final.
- `backend/ai/quality_gates.py`: buckets et filtres qualite.
- `backend/ai/explainability.py`: raisons affichees.
- `backend/ai/recommendation_llm.py`: validation hierarchy cache-only.

### LLM et enrichissement

- `backend/ai/llm/providers.py`: providers Gemini/Ollama.
- `backend/ai/llm/opportunity_enrichment.py`: extraction skills opportunites.
- `backend/ai/tasks.py`: taches Celery enrichissement.
- `backend/ai/management/commands/enrich_opportunities_with_gemini.py`: backfill historique.

### Offres et materialisation

- `backend/opportunities/pipeline.py`: orchestration pipeline opportunites.
- `backend/opportunities/materialization/service.py`: normalisation, dedupe, republication.
- `backend/opportunities/models.py`: modele Opportunite.

### Frontend For You

- `frontend/src/features/opportunities/hooks/useOpportunityRecommendations.js`: chargement recommandations.
- `frontend/src/features/opportunities/components/recommendations/ForYouFeed.jsx`: separation Strong/Related.
- `frontend/src/features/opportunities/components/recommendations/ForYouPreviewCard.jsx`: carte recommendation.
- `frontend/src/features/opportunities/components/recommendations/OpportunitySplitDetailPanel.jsx`: detail lateral.
- `frontend/src/features/opportunities/components/recommendations/RecommendationInsightPanel.jsx`: explication du fit.
- `frontend/src/features/opportunities/viewModels/opportunityDetail.vm.js`: normalisation detail.
- `frontend/src/features/opportunities/viewModels/opportunityList.vm.js`: normalisation carte.

## Limites assumees

Ces limites sont importantes a dire avec confiance:

- Le ranking parfait 10/10 sur tous les profils n'est pas realiste sans dataset annote.
- Les offres sans description ou skills restent plus difficiles.
- Les alias metier rares comme `QA` vs `Testeur` necessitent une taxonomie ou plus de donnees.
- Le LLM local est utile pour enrichir, mais pas assez stable pour reranker en temps reel.
- Le systeme privilegie la precision des `Strong matches` plutot que de gonfler artificiellement les scores.

## Conclusion a dire

```text
J'ai construit une architecture IA hybride et robuste: le profil et le CV enrichissent les signaux utilisateur, les offres sont normalisees et enrichies hors ligne, JobBERT fournit la similarite semantique, le scoring metier et les quality gates securisent le classement, et le cache/Celery garantissent une experience utilisable. La version finale est stable, explicable et prete pour la demonstration.
```
