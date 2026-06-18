# Sprint 3 - Recommandation intelligente IA

## Objectif fonctionnel

Le module de recommandation de BidWise a pour objectif de proposer au candidat des opportunites pertinentes a partir de son profil, de son CV et des opportunites collectees depuis plusieurs sources.

La valeur ajoutee principale n'est pas seulement de filtrer les offres, mais de transformer des donnees heterogenes en signaux exploitables:

- preferences saisies par le candidat;
- competences extraites du CV;
- description textuelle des offres;
- competences enrichies par IA pour les offres pauvres;
- similarite semantique entre profil et opportunite;
- regles metier de controle: role, localisation, contrat, experience, famille metier.

Le systeme est donc un moteur hybride: IA semantique + LLM hors ligne + regles metier explicables.

## Est-ce vraiment un systeme IA ?

Oui, mais ce n'est pas un systeme 100% LLM temps reel.

BidWise utilise plusieurs briques d'IA:

1. Extraction semantique du CV
   - Le texte du CV est parse puis analyse par un LLM local.
   - Le systeme extrait les roles cibles, competences, outils, domaines, langues et signaux d'experience.

2. Enrichissement IA des opportunites
   - Certaines sources fournissent des offres avec peu de competences structurees.
   - Un LLM analyse la description de l'offre et extrait des competences metier.
   - Exemple: une offre qui contenait seulement `excel` devient une offre avec `Saisie comptable`, `Rapprochement bancaire`, `Declarations fiscales`, `ComptaSig`, `Excel`, `Word`.

3. Similarite semantique JobBERT
   - Le profil et les opportunites sont transformes en embeddings.
   - JobBERT compare le sens metier global, pas seulement les mots exacts.

4. Validation hierarchique
   - Le systeme detecte les ecarts de niveau: junior, confirme, senior, responsable, etc.
   - Le LLM n'est pas appele en temps reel par defaut; il intervient seulement comme validation bornee pour certains cas ambigus caches.

Les regles metier ne remplacent pas l'IA. Elles rendent les resultats plus stables, explicables et defendables.

## Flux complet du scenario comptable

### 1. Preparation du profil candidat

Le candidat renseigne:

- role cible: `Comptable`;
- type d'opportunite: `Jobs`;
- localisations preferees: Tunis, Sousse, Sfax, etc.;
- modes de travail: remote, hybrid, on-site;
- contrats: CDI, CDD, SIVP, Freelance;
- experience: junior, 2 ans;
- secteur: `Accounting / Finance / Audit`;
- competences: comptabilite generale, saisie comptable, rapprochements bancaires, facturation, declarations fiscales, Excel, Sage, ERP.

Ces donnees sont stockees dans le profil candidat et servent a construire les features utilisateur.

Fichiers principaux:

- `backend/users/models.py`
- `backend/ai/user_features.py`
- `frontend/src/features/profile/ProfilePage.jsx`
- `frontend/src/features/profile/profilePreferences.js`

### 2. Analyse du CV

Le CV est d'abord converti en texte. Pour les PDF, BidWise utilise PyMuPDF afin d'extraire les blocs de texte avec une meilleure lecture des mises en page en colonnes.

Ensuite, un LLM local analyse le texte nettoye et retourne une structure exploitable:

- role detecte;
- competences;
- outils;
- domaines;
- niveau d'experience;
- langues;
- suggestions applicables au profil.

Fichiers principaux:

- `backend/users/resume_parsing/service.py`
- `backend/users/resume_semantic/structured_llm.py`
- `backend/users/resume_semantic/normalization.py`
- `backend/users/resume_semantic/service.py`

Point de defense:

> Le parsing extrait le texte, mais l'extraction semantique comprend le contenu. La normalisation nettoie les labels et les suggestions profil permettent a l'utilisateur de valider ce qu'il veut garder.

### 3. Enrichissement des opportunites faibles

Les sources externes sont heterogenes. Certaines offres arrivent avec une description riche mais peu de skills structures.

Exemple avant enrichissement:

- Offre Tecnocasa: `skills = ["excel"]`

Apres enrichissement LLM:

- `Saisie comptable`
- `Tenue de journaux comptables`
- `Lettrage de comptes`
- `Rapprochement bancaire`
- `Declarations fiscales`
- `Declarations sociales`
- `ComptaSig`
- `Excel`
- `Word`

L'enrichissement est execute hors ligne par commande, pas pendant la requete utilisateur. Cela protege le temps de reponse et evite une dependance directe au quota LLM.

Fichiers principaux:

- `backend/ai/llm/enrichment.py`
- `backend/ai/llm/opportunity_enrichment.py`
- `backend/ai/management/commands/enrich_opportunities_with_gemini.py`
- `backend/ai/management/commands/select_llm_enrichment_candidates.py`

Commande de demonstration ciblee:

```powershell
docker compose run --rm backend python manage.py enrich_opportunities_with_gemini --ids 4493,3653,5243,5886 --source all --force --limit 4 --workers 1 --delay-seconds 12 --json
```

Apres enrichissement, il faut regenerer les embeddings JobBERT des offres modifiees:

```powershell
docker compose run --rm backend python manage.py generate_jobbert_embeddings --ids 4493,3653,5243,5886 --force --batch-size 1
```

### 4. Construction du texte semantique

Pour comparer profil et opportunite, le systeme ne compare pas seulement les titres.

Il construit un texte riche a partir de:

- titre;
- description;
- organisation;
- localisation;
- contrat;
- competences;
- skills enrichies par IA;
- domaine metier;
- experience;
- informations de profil candidat.

Ce texte est ensuite transforme en embedding.

Fichiers principaux:

- `backend/ai/embeddings.py`
- `backend/opportunities/nlp/nlp_preprocessing.py`
- `backend/opportunities/management/commands/generate_jobbert_embeddings.py`
- `backend/ai/jobbert.py`

### 5. Recuperation des candidats

Le systeme commence par reduire l'espace de recherche:

- filtrage par statut actif;
- filtrage par type d'opportunite choisi dans le profil;
- exclusion des opportunites deja suivies;
- recuperation semantique via pgvector;
- recuperation lexicale complementaire pour eviter de rater une offre metier evidente;
- fallback JobBERT si les premiers resultats sont insuffisants.

Fichiers principaux:

- `backend/ai/views.py`
- `backend/ai/retrieval.py`
- `backend/ai/recommendation_service.py`

### 6. Scoring hybride

Le score final n'est pas un simple pourcentage de mots communs.

Il combine:

- similarite semantique;
- role cible aligne;
- competences communes;
- famille metier;
- localisation;
- mode de travail;
- type de contrat;
- experience;
- salaire quand disponible;
- feedback utilisateur et candidatures precedentes;
- penalisations lorsque les signaux sont faibles ou incoherents.

Exemples de constantes metier:

- bonus localisation;
- bonus role;
- bonus skills;
- bonus famille metier;
- penalite mismatch famille;
- penalite skill isole;
- penalite experience gap.

Fichier principal:

- `backend/ai/recommendation_service.py`

Point de defense:

> Le score n'est pas une probabilite statistique pure. C'est un score de pertinence combinant IA semantique et signaux metier ponderes.

### 7. Classification: Strong matches vs Related opportunities

Les opportunites ne sont pas toutes presentees de la meme maniere.

- `Strong matches`: le systeme a assez de preuves metier pour recommander l'offre.
- `Related opportunities`: l'offre est proche, mais necessite une verification humaine.

Cela evite de gonfler artificiellement les scores et rend le systeme plus transparent.

Fichiers principaux:

- `backend/ai/quality.py`
- `backend/ai/views.py`
- `frontend/src/features/opportunities/components/recommendations/ForYouFeed.jsx`

### 8. Explicabilite

Chaque recommandation expose les raisons:

- role aligne;
- competence matchee;
- famille metier;
- localisation;
- signal CV;
- details a confirmer.

Exemple Tecnocasa:

- `Comptable role aligned`
- `Target role aligned`
- `Strong Saisie comptable + Declarations fiscales alignment`
- `Same job family as your profile`
- `Location aligned: Sousse`

Fichiers principaux:

- `backend/ai/explainability.py`
- `backend/ai/quality.py`
- `frontend/src/features/opportunities/utils/recommendationUtils.js`
- `frontend/src/features/opportunities/components/recommendations/RecommendationInsightPanel.jsx`

## Lecture du resultat comptable

### Pourquoi Tecnocasa est en premier ?

Tecnocasa remonte en premier parce que les signaux forts sont nombreux:

- titre exact `Comptable`;
- role cible utilisateur `Comptable`;
- localisation alignee `Sousse`;
- skills enrichies depuis la description;
- meme famille metier;
- CV comptable analyse;
- score eleve et confiance forte.

Le message `Experience level above listed range` est un signal de vigilance. Il ne bloque pas l'offre, car les signaux metier sont plus importants.

### Pourquoi VEO est encore haut ?

VEO est moins comptable pure que Tecnocasa, mais reste une offre comptable-administrative:

- titre: `Comptable Admin des Fournisseurs - Litiges`;
- localisation alignee;
- famille metier comptabilite/administration;
- missions de litiges, analyse de dossiers, fournisseurs, donnees, Excel.

Il faut la presenter comme une bonne opportunite a verifier, pas comme le match parfait.

### Pourquoi certaines offres sont en Related ?

Une offre comme `Auditeur Interne` partage la famille comptable/audit et certaines competences, mais le role n'est pas exactement `Comptable Junior`. Elle reste donc pertinente, mais avec verification humaine.

## Qualite, limites et defense

### Points forts

- Systeme multi-sources.
- Matching personnalise selon le profil.
- Extraction CV exploitable.
- Enrichissement IA des offres pauvres.
- JobBERT pour la similarite semantique.
- Score explicable.
- Separation entre matches forts et opportunites secondaires.
- Pas de LLM temps reel obligatoire pendant la recommandation.

### Limites connues

- La qualite depend de la description source.
- Un LLM peut parfois extraire des labels trop generaux.
- Certaines sources fournissent des dates ou contrats moins fiables.
- L'experience est un signal de vigilance, pas un filtre strict.
- Les embeddings doivent etre regeneres apres enrichissement d'une offre.

### Reponse si le jury demande pourquoi ne pas utiliser uniquement un LLM

> Un LLM temps reel serait couteux, lent et instable pour chaque consultation. BidWise utilise le LLM hors ligne pour enrichir les donnees et JobBERT pour la similarite semantique rapide. Les regles metier assurent ensuite la stabilite, la transparence et le controle du score.

### Reponse si le jury demande pourquoi pas seulement des regles

> Les regles seules ne comprennent pas les formulations variees des offres. Par exemple, `saisie comptable`, `tenue des journaux`, `assistant comptable` et `comptable fournisseurs` sont proches semantiquement mais pas identiques. JobBERT et les embeddings permettent de capturer ces proximités.

### Reponse si le jury demande pourquoi pas ESCO

> Le projet a privilegie une approche semantique avec JobBERT plutot qu'une taxonomie rigide. Les offres collectees sont heterogenes, parfois bruitees, multilingues et issues de plusieurs sources. L'objectif est de comparer le sens metier global, pas seulement de mapper chaque terme a une nomenclature officielle.

## Performance et temps de reponse

Le systeme separe les traitements lourds et la consultation utilisateur.

Traitements hors ligne:

- scraping;
- enrichissement LLM;
- generation embeddings;
- preparation des donnees de recherche.

Traitements en ligne:

- chargement du profil;
- recuperation des candidats;
- scoring/reranking;
- serialisation des explications;
- cache des recommandations.

La vue de recommandation utilise un cache afin d'eviter de recalculer inutilement le ranking lorsque le profil n'a pas change.

Fichiers principaux:

- `backend/ai/views.py`
- `backend/ai/retrieval.py`
- `backend/ai/recommendation_service.py`

## Accuracy, scoring et interpretation des scores

Le score affiche n'est pas une probabilite de recrutement. C'est un score de pertinence calcule pour aider l'utilisateur a prioriser les opportunites.

Interpretation pratique:

- 75% et plus: forte recommandation lorsque les signaux metier sont nombreux.
- 60% a 74%: bonne opportunite, mais a verifier.
- 45% a 59%: opportunite liee ou partielle.
- moins de 45%: faible priorite ou fallback.

La qualite est evaluee par benchmarks metier plutot que par une accuracy classique supervisee, car le projet ne dispose pas d'un grand dataset annote "profil -> offre ideale".

Les criteres de validation utilises sont:

- les offres exactes du domaine doivent apparaitre en haut;
- les offres proches doivent rester visibles mais separees;
- les offres trop seniors ou hors domaine ne doivent pas etre recommandees comme matches forts;
- les raisons affichees doivent etre coherentes avec le texte de l'offre;
- l'enrichissement IA doit extraire des competences verifiables dans la description.

Pour le profil comptable teste:

- `Tecnocasa Khezama - Comptable`: 77%, strong match, role et skills alignes.
- `VEO Worldwide - Comptable Admin Fournisseurs`: 75%, fort mais a expliquer comme comptable-administratif.
- `CMR AUDIT - Comptables`: 66%, bon match Keejob avec skills comptables.
- `Legal Crea - Assistante Comptable et Administrative`: 66%, bon match administratif/comptable.
- `Auditeur Interne`: related, car famille proche mais role different.

Cette evaluation est defendable comme benchmark fonctionnel et qualitatif. Une future amelioration serait de construire un dataset annote par experts pour calculer des metriques comme Precision@K, Recall@K ou NDCG.

## Tests et validation

### Tests unitaires et integration

Commandes utiles:

```powershell
docker compose run --rm backend python manage.py test --keepdb tests.test_recommendation_jobbert_fallback
```

```powershell
docker compose run --rm backend python manage.py test --keepdb tests.test_recommendation_jobbert_fallback tests.test_recommendation_pgvector_retrieval tests.test_crossencoder_reranking tests.test_crossencoder_fallback tests.test_benchmark_llm_hierarchy_validation
```

Resultat deja valide:

- 33 tests executes;
- statut OK;
- fallback pgvector teste;
- fallback CrossEncoder teste;
- validation hierarchique LLM testee;
- fallback JobBERT teste.

### Benchmark final

Commande de benchmark presente dans la documentation technique:

```powershell
docker compose run --rm -e LLM_ENRICHMENT_ENABLED=true -e LLM_PROVIDER=ollama -e OLLAMA_MODEL=llama3.2:3b -e OLLAMA_TIMEOUT_SECONDS=180 backend python manage.py benchmark_final_recommendation_profiles --use-llm-validation --profiles comptable_junior,production_team_lead,civil_engineer_junior,it_helpdesk --candidate-limit 1700 --rerank-candidates 120 --top 15 --output-json backend/benchmark_reports/final_ai_recommendation_validation.json --json
```

Objectif du benchmark:

- verifier que les profils types recoivent des offres metier coherentes;
- verifier que les roles trop seniors ou hors domaine restent en review;
- verifier que le LLM n'est utilise que pour les cas ambigus;
- verifier que les erreurs LLM ne cassent pas le flux.

## Fichiers a ouvrir pendant la soutenance

### Backend

- `backend/ai/views.py`: orchestration API recommandation.
- `backend/ai/recommendation_service.py`: scoring metier et raisons.
- `backend/ai/retrieval.py`: recuperation semantique.
- `backend/ai/jobbert.py`: embeddings JobBERT.
- `backend/ai/user_features.py`: construction features profil.
- `backend/ai/llm/opportunity_enrichment.py`: enrichissement LLM des offres.
- `backend/users/resume_semantic/structured_llm.py`: extraction CV.
- `backend/opportunities/management/commands/generate_jobbert_embeddings.py`: generation embeddings offres.

### Frontend

- `frontend/src/features/opportunities/components/recommendations/ForYouFeed.jsx`: separation Strong / Related.
- `frontend/src/features/opportunities/utils/recommendationUtils.js`: affichage score, confiance, raisons.
- `frontend/src/features/opportunities/components/recommendations/RecommendationInsightPanel.jsx`: panel explicatif.
- `frontend/src/features/opportunities/components/recommendations/OpportunitySplitDetailPanel.jsx`: detail opportunite + assistant.

## Script oral court

> Pour la recommandation, BidWise utilise un moteur hybride. Le profil candidat et son CV sont transformes en signaux metier. Les offres collectees sont aussi enrichies, surtout lorsqu'elles n'ont pas de competences structurees. Ensuite, JobBERT compare semantiquement le profil et les opportunites, puis des regles metier ajoutent les signaux de role, localisation, contrat, experience et famille metier. Le resultat est classe en Strong matches ou Related opportunities et chaque recommandation est expliquee par des raisons visibles.

## Script oral detaille pour le profil comptable

> Dans cette demonstration, le candidat cherche un poste de Comptable. Son CV permet d'extraire des competences comme saisie comptable, declarations fiscales, rapprochements bancaires, Excel et Sage. Certaines offres externes n'avaient initialement qu'un skill comme Excel. Nous avons donc applique un enrichissement LLM hors ligne sur la description pour extraire les competences metier. Apres regeneration des embeddings JobBERT, les offres comptables sont classees en tete avec des raisons explicables: role aligne, competences communes, meme famille metier, localisation et signal CV. Les offres proches mais moins exactes, comme audit interne ou finance administrative, restent dans Related opportunities pour garder une verification humaine.
