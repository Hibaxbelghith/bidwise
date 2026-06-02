# Pipeline recommandation IA et page For You

Last updated: 2026-06-02

## Objectif

Ce document explique le fonctionnement du moteur de recommandation et de la page `For You`.

Il couvre:

- preparation des offres;
- enrichissement LLM;
- embeddings et JobBERT;
- retrieval candidats;
- scoring metier;
- quality gates;
- cache;
- affichage frontend.

## Preparation des offres

Les opportunites viennent de plusieurs sources externes.

Pipeline simplifie:

```text
Scrapers
  -> SourceItem brut
  -> materialisation
  -> Opportunite normalisee
  -> embeddings
  -> For You
```

Champs importants:

- titre;
- organisation;
- ville;
- type;
- source;
- URL source;
- description;
- date publication;
- contrat;
- disponibilite / mode de travail;
- skills;
- extra_data.

Fichiers importants:

- `backend/opportunities/pipeline.py`
- `backend/opportunities/materialization/service.py`
- `backend/opportunities/models.py`

## Dedupe et republication

Le systeme evite les doublons visibles.

Principes:

- normalisation source + titre + organisation + ville + type;
- exclusion des organisations generiques;
- dedupe dans la materialisation;
- dedupe supplementaire dans le ranking For You.

Objectif:

```text
Ne pas afficher deux fois la meme offre republiee.
```

## Enrichissement LLM des offres

Certaines offres ont une longue description mais peu ou pas de skills structures.

Le LLM peut extraire:

- skills techniques;
- outils;
- domaines;
- signaux metier;
- tags utiles pour l'explication.

Mais il fonctionne en offline:

```text
Opportunite active avec skills faibles
  -> Celery queue opportunity_enrichment
  -> LLM provider Ollama/Gemini
  -> extra_data.llm_enrichment
  -> skills enrichis
  -> date_modification mise a jour
  -> cache For You invalide automatiquement
```

Pourquoi offline:

- evite de bloquer For You;
- controle le cout/temps LLM;
- garde le scraping fluide;
- permet des batchs limites.

Fichiers importants:

- `backend/ai/llm/opportunity_enrichment.py`
- `backend/ai/llm/providers.py`
- `backend/ai/tasks.py`
- `backend/ai/management/commands/enrich_opportunities_with_gemini.py`
- `backend/docs/LLM_OPPORTUNITY_ENRICHMENT_CELERY.md`

## JobBERT

JobBERT est le modele semantique specialise emploi.

Il est utilise pour comparer:

- profil utilisateur;
- CV/resume text;
- roles cibles;
- titre et description de l'offre;
- skills de l'offre.

Configuration:

- `JOBBERT_MODEL=TechWolf/JobBERT-v3`
- embeddings normalises;
- cache par modele;
- score de similarite par dot product.

Fichiers importants:

- `backend/ai/jobbert.py`
- `backend/ai/views.py`
- `backend/users/management/commands/generate_jobbert_profile_embeddings.py`

## Retrieval candidats

For You ne score pas toute la base de donnees dans le detail UI.

Le backend recupere d'abord un ensemble de candidats:

- offres actives;
- embeddings disponibles;
- filtres de base;
- top candidats semantiques;
- shortlist JobBERT.

Ensuite, le scoring final travaille sur ce pool.

Fichiers importants:

- `backend/ai/retrieval.py`
- `backend/ai/views.py`

## Scoring metier

Le scoring combine plusieurs familles de signaux.

Signaux principaux:

- similarite semantique;
- score JobBERT;
- role target aligned;
- skill match;
- famille metier;
- localisation;
- mode de travail;
- type contrat;
- experience;
- seniority;
- preuves CV/profil.

Pourquoi ce n'est pas seulement un score IA:

```text
Un modele semantique peut rapprocher deux offres parce qu'elles partagent des mots, mais le produit doit savoir si l'offre est vraiment actionnable pour ce profil.
```

Fichiers importants:

- `backend/ai/recommendation_service.py`
- `backend/ai/business_families.py`
- `backend/ai/hierarchy.py`
- `backend/ai/explainability.py`

## Formule de scoring actuelle

La formule de base en mode complet est:

```text
score_base =
  0.70 * ranking_semantic_score
  +
  0.30 * business_signal
  +
  feedback_bonus
```

Avec:

```text
ranking_semantic_score = max(embedding_score, jobbert_score)
business_signal = business_score / BUSINESS_BONUS_CAP
```

Puis le score est ajuste par des garde-fous:

```text
score =
  score_base
  - penalty_if_no_metier_evidence
  + role_match_final_boost
  + metier_density_adjustment
  - business_family_mismatch_penalty
  - experience_gap_penalty
  * hierarchy_score_multiplier
  + jobbert_adjustment
```

Enfin, plusieurs plafonds peuvent limiter le score:

- cap si une seule competence isolee matche;
- cap si l'offre correspond seulement par famille metier;
- cap si le role est sparse, par exemple titre court sans description/skills;
- cap si le profil vise un role explicite mais l'offre ne prouve pas ce role;
- cap en cas d'ecart seniority fort.

### Pourquoi cette formule?

La formule donne plus de poids au signal IA semantique, mais elle garde une partie metier indispensable.

```text
70% semantic:
  mesurer la proximite profil/offre avec embeddings et JobBERT.

30% business:
  verifier que l'offre est vraiment actionnable: role, skills, localisation,
  mode de travail, contrat, experience, famille metier.
```

Le score final n'est donc pas un simple `cosine similarity`. C'est une decision produit.

### JobBERT adjustment

JobBERT ajoute un ajustement limite:

```text
jobbert_score >= 0.65  -> +0.08
jobbert_score >= 0.55  -> +0.04
jobbert_score < 0.45   -> -0.04
```

Cet ajustement est volontairement borne. Il aide une bonne offre a monter, mais il ne doit pas annuler les garde-fous de seniority ou de metier.

Exemple:

```text
Une offre tres similaire semantiquement mais Senior pour un profil Junior
peut garder un score correct, mais rester en Related opportunities.
```

### Mode profil partiel

Quand le profil est incomplet, la formule est plus prudente:

```text
score_partial =
  0.50 * ranking_semantic_score
  +
  0.30 * business_signal
  +
  0.20 * popularity_score
  +
  feedback_bonus
```

Pourquoi?

- si le profil manque de roles ou skills, la popularite/recence peut aider a proposer des pistes;
- mais la recommandation reste marquee comme moins certaine;
- les quality gates evitent de presenter ces resultats comme des recommandations fortes.

### Exemple simple d'explication orale

```text
Si une offre Backend Python a un bon score JobBERT, des skills Python/SQL,
une localisation acceptee et un niveau d'experience compatible, elle monte en
Strong Match.

Si une offre partage seulement SQL mais que le role est Data ou Support,
elle peut rester visible en Related mais elle ne devient pas Strong.
```

## Pourquoi JobBERT?

JobBERT est adapte au domaine RH/emploi, contrairement a un embedding generaliste.

Avantages:

- comprend mieux les textes de poste;
- rapproche un profil et une offre meme si les mots ne sont pas identiques;
- aide sur les titres en anglais/francais;
- compare role, description et skills dans un espace semantique metier;
- fonctionne localement une fois le modele dans le cache HuggingFace.

Pourquoi ne pas utiliser uniquement JobBERT?

- certains termes restent ambigus: `Excel`, `SQL`, `reporting`, `analyse`;
- JobBERT ne connait pas toutes les preferences utilisateur;
- il ne decide pas seul junior vs senior, contrat, ville ou mode de travail;
- le produit doit rester explicable.

Conclusion:

```text
JobBERT fournit la comprehension semantique. Le scoring metier transforme cette
comprehension en recommandation exploitable.
```

## Quality gates

Les quality gates transforment le score en decision produit.

Buckets:

- `STRONG_MATCH`: preuves fortes.
- `RELATED_REVIEW`: interessant mais a verifier.
- fallback/empty: si profil insuffisant ou preuves faibles.

Raisons possibles:

- role fort mais seniority a verifier;
- skills presents mais role different;
- meme famille metier mais specialisation differente;
- localisation ou contrat a confirmer;
- signal trop generique.

Fichiers importants:

- `backend/ai/quality_gates.py`
- `backend/ai/explainability.py`
- `frontend/src/features/opportunities/utils/recommendationUtils.js`

## Validation LLM hierarchy

Le LLM peut aider a valider certains cas ambigus de hierarchie:

- junior vs senior;
- responsable/manager;
- qualification trop elevee;
- poste hors niveau.

Mais dans la version finale:

```text
For You utilise le LLM hierarchy en cache-only.
```

Cela signifie:

- si une decision LLM est deja en cache, elle peut etre appliquee;
- sinon, l'API ne bloque pas;
- le deterministic scoring reste prioritaire.

Fichier important:

- `backend/ai/recommendation_llm.py`

## Pourquoi le LLM reranking n'est pas active

Un reranker LLM offline/cache-first a ete prototype.

Il a ete retire de la version finale parce que:

- le modele local retournait parfois une liste incomplete;
- le JSON pouvait etre tronque;
- certains classements etaient instables;
- le temps d'attente etait trop eleve;
- il n'ameliorait pas suffisamment les profils valides.

Decision finale:

```text
LLM pour enrichissement offline et validation cache-only, pas pour reranking principal.
```

Cette decision augmente la stabilite produit.

## Cache For You

La reponse For You complete est cachee quelques minutes.

Objectif:

- premier calcul acceptable;
- refresh instantane;
- pas de recalcul lourd a chaque retour page;
- pas de flicker UI.

La cle de cache depend notamment:

- user id;
- profile id;
- limit;
- signature features profil;
- hash/updated_at embeddings profil;
- nombre d'offres actives;
- derniere modification opportunite;
- opportunites suivies.

Si une offre est enrichie par LLM et que ses skills changent, `date_modification` change aussi. Le cache For You devient alors automatiquement different.

Fichier important:

- `backend/ai/views.py`

Header utile:

```text
X-BidWise-Recommendations-Cache: hit | miss | skip
```

## Serialization complete

La page For You recoit maintenant les donnees d'offre completes:

- titre;
- organisation;
- logo;
- ville;
- source;
- URL apply;
- description;
- skills;
- extra_data;
- recommendation.

Avant, le frontend devait parfois appeler le detail de chaque offre. Maintenant, For You peut afficher directement les cartes et le panneau detail.

Avantages:

- moins d'appels API;
- moins de latence;
- pas de description vide;
- bouton Apply disponible;
- UI plus stable.

Fichiers importants:

- `backend/ai/views.py`
- `frontend/src/features/opportunities/hooks/useOpportunityRecommendations.js`

## UI For You

La page separe les offres en deux blocs.

```text
Strong matches
  -> meilleures offres, preuves fortes

Related opportunities to review
  -> offres proches, mais avec point a verifier
```

Elements affiches:

- titre;
- entreprise;
- logo;
- source;
- date `Published X days ago`;
- localisation;
- contrat;
- score;
- niveau de confiance;
- raisons;
- details a confirmer;
- description;
- skills avec badge `AI` si enrichis par LLM;
- bouton Apply.

Fichiers importants:

- `frontend/src/features/opportunities/components/recommendations/ForYouFeed.jsx`
- `frontend/src/features/opportunities/components/recommendations/ForYouPreviewCard.jsx`
- `frontend/src/features/opportunities/components/recommendations/OpportunitySplitDetailPanel.jsx`
- `frontend/src/features/opportunities/components/recommendations/RecommendationInsightPanel.jsx`
- `frontend/src/features/opportunities/components/detail/OpportunitySkillsSection.jsx`

## Performance et scalabilite

Mesures prises:

- Celery pour traitements longs;
- queues separees: scraping, profile_resume, opportunity_enrichment;
- Redis cache;
- cache For You;
- cache facets Explore;
- page size limitee;
- queryset optimises avec `select_related`;
- embeddings precomputes;
- JobBERT soft timeout / skip si indisponible;
- LLM hors chemin critique.

Pourquoi c'est scalable:

- ajouter un worker Celery ne change pas l'API;
- la queue LLM peut etre limitee sans bloquer scraping;
- Redis evite les recalculs repetes;
- les embeddings precomputes evitent de recalculer a chaque requete;
- For You peut servir un cache court pour les retours utilisateur.

## Securite et robustesse

Points principaux:

- endpoints recommandations lies a l'utilisateur authentifie;
- fallback si embeddings ou LLM indisponibles;
- LLM avec timeouts;
- cache invalidable par changement profil/offres;
- pas de dependance temps reel au LLM;
- scores explicables;
- separation des offres douteuses en review.

## Commandes utiles soutenance

Check backend:

```bash
docker compose exec backend python manage.py check
```

Build frontend:

```bash
npm.cmd --prefix frontend run build
```

Test recommendation profil:

```bash
docker compose exec backend python manage.py test_profile_recommendations --profile-id <PROFILE_ID> --candidate-limit 2500 --rerank-candidates 120 --top-k 20 --exclude-benchmark
```

Audit enrichissement LLM sans appel LLM:

```bash
docker compose exec backend python manage.py enrich_opportunities_with_gemini --source all --weak-skills-only --min-description-chars 1000 --limit 10 --audit --json
```

## Message soutenance

```text
La page For You est le resultat d'un pipeline complet: profil et CV deviennent des features IA, les offres sont normalisees et enrichies, JobBERT donne une similarite semantique specialisee emploi, le scoring metier ajoute les contraintes utilisateur, les quality gates protegent contre les faux positifs, puis l'UI explique les resultats. Les traitements lents sont asynchrones et le cache garantit une experience utilisable.
```
