# Profile Completion, Validation et Extraction CV

## Objectif

Ce document resume les points a expliquer pendant la soutenance:

- calcul du score de completude du profil;
- controles de saisie frontend/backend;
- extraction CV par IA locale;
- valeur ajoutee pour les recommandations;
- role des fichiers principaux.

## 1. Score de completude profil

Le score est calcule cote backend et expose dans l'API profil:

```json
profile_completion: {
  "score": 0,
  "missing": []
}
```

Fichier:

- `backend/users/profile_completion.py`

La formule est une somme ponderee sur 100:

| Signal | Poids |
|---|---:|
| First name | 7 |
| Last name | 7 |
| Experience level | 8 |
| Years of experience | 8 |
| Locations | 8 |
| Work modes | 7 |
| Contract types | 6 |
| Opportunity type | 4 |
| Skills | 10 |
| Target roles | 10 |
| Sectors | 10 |
| Resume | 15 |

```text
score = somme des poids des champs remplis
```

Le CV a le poids le plus eleve, 15%, car il enrichit directement les signaux utilises par le moteur de recommandation.

## 2. Affichage du score

Le score est affiche dans la page profil avec:

- pourcentage;
- barre de progression;
- maximum 3 suggestions de champs manquants, triees par importance.

Fichier:

- `frontend/src/features/profile/ProfilePage.jsx`

Exemples:

- `Upload your resume (+15%)`
- `Add at least one skill`
- `Add a target role`
- `Choose at least one sector`

## 3. Controles de saisie

### 3.1 Frontend

Le frontend guide l'utilisateur avant l'envoi API.

Fichiers:

- `frontend/src/features/profile/profileValidation.js`
- `frontend/src/features/profile/profilePreferences.js`
- `frontend/src/features/profile/ProfilePage.jsx`
- `frontend/src/features/onboarding/OnboardingPage.jsx`
- `frontend/src/features/onboarding/onboardingState.js`

Controles principaux:

| Champ | Controle |
|---|---|
| First name / Last name | 2 a 100 caracteres si rempli |
| Years of experience | entier entre 0 et 60 |
| Salary | TND/mois, min <= max |
| Resume | PDF/DOCX/DOC/RTF/TXT, max 5 MB |
| Sectors | au moins un secteur, valeurs controlees |
| Locations | requis si onsite/hybrid, max 10 |
| Skills | au moins une competence en onboarding |
| Target roles | au moins un role cible en onboarding |
| Contract types | valeurs controlees |
| Work modes | valeurs controlees |

Composants:

- `BusinessFamilySelect.jsx`
- `LocationMultiSelect.jsx`
- `ProfileAutocompleteInput.jsx`
- `PreferenceChipGroup.jsx`
- `ResumeSection.jsx`

### 3.2 Backend

Le backend revalide les donnees avec Django REST Framework.

Fichier:

- `backend/users/serializers.py`

Elements importants:

- `ProfilUpdateSerializer`
- `ProfileTextListField`
- `PreferredLocationsField`
- `EmploymentTypesField`
- `WorkModePreferencesField`
- `ProfileResumeSerializer`

Garanties backend:

- listes nettoyees et dedupliquees;
- maximum 30 items pour les listes texte;
- maximum 10 localisations;
- rejet des secteurs inconnus;
- rejet des types de contrat inconnus;
- validation taille/type/extension du CV;
- protection contre valeurs non textuelles ou markup dangereux.

## 4. Coherence onboarding vs profil

L'onboarding collecte les signaux minimums pour demarrer les recommandations:

- opportunity type;
- work mode;
- location si necessaire;
- skills;
- sectors;
- salary optionnel;
- contract types optionnels;
- target roles;
- visibility.

La page profil permet ensuite de corriger et completer ces signaux.

Vocabulaire partage:

- `frontend/src/features/profile/profilePreferences.js`
- `frontend/src/features/profile/profileValidation.js`
- `frontend/src/features/onboarding/onboardingState.js`

## 5. Pipeline CV IA

Le CV n'est pas seulement stocke comme fichier. Il est transforme en signaux IA exploitables.

Pipeline actuel:

```text
Upload CV
-> validation fichier
-> parsing texte asynchrone
-> nettoyage texte leger
-> extraction JSON structuree par Qwen2.5 via Ollama
-> validation schema
-> stockage ProfileResume
-> suggestions profil
-> utilisation dans embeddings / recommandations
```

### 5.1 Parsing

Le parsing est asynchrone via Celery.

Formats texte supportes:

- PDF via `pypdf`;
- DOCX via `python-docx`.

Fichiers:

- `backend/users/tasks.py`
- `backend/users/resume_parsing/service.py`
- `backend/users/resume_parsing/cleaners.py`
- `backend/users/resume_parsing/exceptions.py`
- `backend/users/resume_processing.py`

### 5.2 Extraction IA officielle

L'extraction officielle est basee sur Qwen2.5 local via Ollama.

Fichiers:

- `backend/users/resume_semantic/structured_llm.py`
- `backend/users/resume_semantic/service.py`
- `backend/users/resume_semantic/models.py`
- `backend/users/resume_semantic/normalization.py`

Principes:

- Qwen est la source officielle unique des signaux CV.
- L'ancien pipeline manuel de skills CV a ete retire du pipeline CV officiel.
- Pas de profil partiel concurrent avant la fin de Qwen.
- Si Qwen echoue, le statut passe en `FAILED`, le CV reste stocke.
- L'UI reste non bloquante.

Configuration:

- `PROFILE_RESUME_STRUCTURED_LLM_ENABLED=true`
- `PROFILE_RESUME_STRUCTURED_LLM_FALLBACK_ENABLED=false`
- `PROFILE_RESUME_QWEN_TEMPERATURE=0.0`
- `PROFILE_RESUME_QWEN_MAX_TOKENS=300`
- `PROFILE_RESUME_QWEN_TEXT_CHARS=1200`
- `PROFILE_RESUME_QWEN_KEEP_ALIVE=30m`

### 5.3 Signaux extraits

Stockage principal:

- modele `ProfileResume` dans `backend/users/models.py`

Champs importants:

| Champ | Role |
|---|---|
| `parsed_text` | texte extrait du CV |
| `resume_text_embedding_source` | texte prepare pour embeddings |
| `extracted_skills` | competences extraites par Qwen |
| `extracted_domains` | domaines professionnels libres |
| `extracted_tools` | outils et plateformes |
| `extracted_languages` | langues explicitement listees dans le CV |
| `semantic_resume_status` | etat IA: PENDING, PROCESSING, SUCCEEDED, FAILED... |
| `semantic_resume_confidence` | confiance globale |
| `semantic_resume_version` | version du pipeline |
| `semantic_resume_metadata` | role canonique, familles metier, suggestions profil, audit IA |

Dans `semantic_resume_metadata`:

- `canonical_role`;
- `target_roles`;
- `business_families`;
- `family_confidence`;
- `llm_enrichment.result`;
- `llm_enrichment.profile_suggestions`;
- `warnings`.

## 6. Suggestions profil apres CV

Apres upload et analyse reussie, l'interface peut proposer:

```text
Add to your profile?
We found these from your resume — select what to keep
```

Fichier:

- `frontend/src/features/profile/components/ResumeSection.jsx`

Regles UX:

- affiche uniquement apres un nouvel upload;
- n'apparait pas a chaque visite;
- `Skip` masque la carte pour ce CV via `sessionStorage`;
- `Add selected to profile` merge les donnees avec le profil;
- ne remplace jamais les donnees existantes;
- ne depasse jamais 30 skills;
- affiche seulement les skills absents du profil;
- affiche le role detecte seulement s'il est absent des target roles actuels.

API utilisee:

- `PUT /api/profile/me/`
- `GET /api/profile/resume/`

## 7. Performance

Mesures locales observees avec Ollama:

| Etape | Temps typique |
|---|---:|
| Parsing PDF/DOCX | 1 a 3 s |
| Qwen local | 30 a 60 s selon machine/cache |
| Total analyse CV | souvent 30 a 60 s |

Points importants:

- Le temps long vient surtout de l'inference Ollama locale.
- L'upload et l'analyse sont asynchrones via Celery.
- L'utilisateur peut continuer a naviguer.
- En production, un GPU ou un provider LLM rapide peut reduire fortement le temps sans changer l'architecture.

Message soutenance:

> Le temps d'analyse depend du moteur local Ollama. L'architecture est deja asynchrone et production-ready: on peut remplacer l'inference locale par un serveur GPU ou une API LLM plus rapide sans changer le flux produit.

## 8. Utilisation dans la recommandation

Les signaux CV ameliorent:

- la representation du candidat;
- la detection de competences implicites;
- les roles cibles;
- les secteurs professionnels;
- le ranking via embeddings et scoring metier;
- l'explicabilite des recommandations.

Fichiers lies:

- `backend/ai/user_features.py`
- `backend/ai/embeddings.py`
- `backend/ai/recommendation_service.py`
- `backend/ai/business_families.py`

Message jury:

> Le CV est transforme en signaux IA exploitables. Il ne sert pas seulement de piece jointe: il enrichit le matching candidat/offre et ameliore la qualite des recommandations.

## 9. Fichiers a citer

Backend profil / validation:

- `backend/users/profile_completion.py`
- `backend/users/serializers.py`
- `backend/users/models.py`
- `backend/users/views.py`

Backend CV:

- `backend/users/tasks.py`
- `backend/users/resume_parsing/service.py`
- `backend/users/resume_processing.py`
- `backend/users/resume_semantic/service.py`
- `backend/users/resume_semantic/structured_llm.py`
- `backend/users/resume_semantic/models.py`
- `backend/users/resume_semantic/normalization.py`

Backend IA:

- `backend/ai/business_families.py`
- `backend/ai/user_features.py`
- `backend/ai/embeddings.py`
- `backend/ai/recommendation_service.py`

Frontend:

- `frontend/src/features/profile/ProfilePage.jsx`
- `frontend/src/features/profile/components/ResumeSection.jsx`
- `frontend/src/features/profile/profileValidation.js`
- `frontend/src/features/profile/profilePreferences.js`
- `frontend/src/features/onboarding/onboardingState.js`

Tests utiles:

- `backend/tests/test_resume_parsing.py`
- `backend/tests/test_resume_semantic.py`
- `frontend/scripts/profileValidationChecks.mjs`
- `frontend/scripts/candidateFlowChecks.mjs`

## 10. Commandes de verification

Backend:

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py test tests.test_resume_semantic tests.test_resume_parsing --keepdb
```

Test CV reel:

```bash
docker compose exec backend python manage.py test_resume_processing /app/benchmark_inputs/cvs/cv_data_engineer.pdf --structured-llm --timeout-seconds 210
```

## 11. CV recommandes pour la demo

Des CV de test existent deja dans:

- `backend/benchmark_inputs/cvs/`

CV les plus recommandes pour une demonstration fiable:

| Fichier | Pourquoi l'utiliser |
|---|---|
| `cv_data_engineer.pdf` | CV structure, role clair, skills techniques explicites, bon test pour `data_ai` |
| `cv_devops_engineer.pdf` | Bon test pour DevOps/cloud, outils clairs: Docker, Kubernetes, Terraform, AWS |
| `cv_commercial.pdf` | Bon test non-technique, valide la robustesse hors IT |

CV utiles pour montrer la generalisation:

| Fichier | Domaine |
|---|---|
| `cv_comptable_junior.pdf` | comptabilite / finance |
| `cv_infirmier.pdf` | sante |
| `cv_assistante_admin.pdf` | administration |
| `cv_marketing_junior.pdf` | marketing |
| `cv_support_it_junior.pdf` | support IT |

Recommandation soutenance:

- utiliser d'abord `cv_data_engineer.pdf` pour montrer le meilleur cas technique;
- utiliser ensuite `cv_commercial.pdf` pour prouver que le systeme n'est pas limite aux profils IT;
- eviter de tester un CV image/scanne pendant la soutenance, car `pypdf` extrait le texte mais ne fait pas d'OCR.

Benchmark Qwen:

```bash
docker compose exec backend python manage.py benchmark_qwen_resume_extraction /app/benchmark_inputs/cvs --variant official --page-limits 2 --text-chars 1200 --max-tokens 300 --temperature 0 --timeout-seconds 180
```

Frontend:

```bash
npm.cmd --prefix frontend run build
```
