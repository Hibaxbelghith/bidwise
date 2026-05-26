# Profile Completion Score and Input Validation

## Objectif

Ce document resume deux points a presenter pendant la soutenance:

- comment le score de completude du profil candidat est calcule;
- comment les champs du profil et de l'onboarding sont controles cote frontend et cote backend.

## 1. Score de Completude Profil

Le score est deja calcule cote backend et expose dans l'API profil via le champ:

```json
profile_completion: {
  "score": 0,
  "missing": []
}
```

Fichier principal:

- `backend/users/profile_completion.py`

Le score est une somme ponderee sur 100. Chaque signal rempli ajoute son poids:

| Signal | Poids |
|---|---:|
| First name | 7 |
| Last name | 7 |
| Experience level | 8 |
| Years of experience | 8 |
| Locations | 8 |
| Work modes | 7 |
| Contract types | 6 |
| Opportunity types | 4 |
| Skills | 10 |
| Target roles | 10 |
| Sectors | 10 |
| Resume | 15 |

Formule:

```text
score = round((poids des champs remplis / poids total) * 100)
```

Comme le poids total vaut 100, le score correspond directement a la somme des poids des champs remplis.

Exemple:

```text
skills + sectors + target roles + resume
= 10 + 10 + 10 + 15
= 45%
```

Le CV a le poids le plus eleve, 15%, car le benchmark montre que l'ajout d'un CV ameliore la precision des recommandations de +23%.

## 2. Affichage du Score

Le score est affiche dans la page profil sous forme de carte "Profile strength".

Fichier frontend:

- `frontend/src/features/profile/ProfilePage.jsx`

La carte affiche:

- le pourcentage;
- une barre de progression;
- jusqu'a 3 suggestions de champs manquants, triees par importance.

Exemples de suggestions:

- `Upload your resume (+15%)`
- `Add at least one skill`
- `Add a target role`
- `Choose at least one sector`

## 3. Controle de Saisie Frontend

Le frontend applique des validations pour guider l'utilisateur avant l'envoi API.

Fichiers principaux:

- `frontend/src/features/profile/profileValidation.js`
- `frontend/src/features/profile/profilePreferences.js`
- `frontend/src/features/onboarding/onboardingState.js`
- `frontend/src/features/profile/ProfilePage.jsx`
- `frontend/src/features/onboarding/OnboardingPage.jsx`

Controles importants:

| Champ | Controle frontend |
|---|---|
| First name / Last name | 2 a 100 caracteres si rempli |
| Years of experience | entier entre 0 et 60 |
| Salary | TND/mois, minimum 500, maximum 30000, max >= min |
| Resume | PDF/DOCX/DOC/RTF/TXT, maximum 5 MB |
| Sectors | au moins un secteur, liste controlee |
| Locations | requis si onsite/hybrid, maximum 10 |
| Skills | au moins une competence en onboarding |
| Target roles | au moins un role cible en onboarding |
| Contract types | valeurs controlees |
| Work mode | valeurs controlees |
| Opportunity type | valeurs controlees |

Les composants frontend utilises:

- `BusinessFamilySelect.jsx` pour les secteurs;
- `LocationMultiSelect.jsx` pour les localisations;
- `ProfileAutocompleteInput.jsx` pour skills et target roles;
- `PreferenceChipGroup.jsx` pour les preferences;
- `ResumeSection.jsx` pour le CV.

## 4. Controle de Saisie Backend

Le backend ne fait pas confiance au frontend. Les memes donnees sont revalidees dans les serializers Django REST Framework.

Fichier principal:

- `backend/users/serializers.py`

Classes et fonctions importantes:

- `ProfilUpdateSerializer`
- `ProfileTextListField`
- `PreferredLocationsField`
- `EmploymentTypesField`
- `WorkModePreferencesField`
- `_normalize_profile_business_families`
- `_normalize_safe_profile_list`
- `_normalize_location_list`
- `_normalize_profile_employment_types`
- `ProfileResumeSerializer`

Exemples de securite backend:

- rejet des listes invalides;
- rejet des secteurs non presents dans la taxonomie controlee;
- rejet des types de contrat inconnus;
- rejet des localisations non textuelles ou trop longues;
- limite de 10 localisations;
- limite de 30 items pour les listes texte;
- detection de HTML, scripts ou markup dangereux;
- validation stricte des fichiers CV par extension, taille et type MIME.

## 5. Coherence Onboarding vs Profile

L'onboarding collecte les signaux minimums necessaires pour demarrer les recommandations:

- opportunity type;
- work mode;
- location si necessaire;
- skills;
- sectors;
- salary optionnel;
- contract types optionnels;
- target roles;
- visibility.

La page profil permet ensuite de completer et corriger ces informations.

Le meme vocabulaire est partage entre onboarding et profile via:

- `profilePreferences.js`
- `profileValidation.js`
- `onboardingState.js`

## 6. Extraction CV et Signaux IA

Le CV n'est pas seulement un fichier attache au profil. Il est parse et transforme en signaux semantiques pour ameliorer les recommandations.

Le benchmark a confirme que l'ajout d'un CV ameliore la precision de +23%. C'est pour cette raison que le CV a le poids le plus eleve dans le score de completude: 15%.

### 6.1 Pipeline CV

```text
Upload CV
-> validation fichier
-> parsing asynchrone du texte
-> nettoyage du texte
-> extraction semantique
-> normalisation des skills
-> stockage des signaux CV
-> utilisation dans embedding / scoring recommendation
```

### 6.2 Outils de parsing CV

Le parsing est asynchrone via Celery.

Formats actuellement parses pour le texte:

- PDF via `pypdf`;
- DOCX via `python-docx`.

Les autres formats acceptes a l'upload peuvent etre stockes, mais l'extraction texte avancee est principalement supportee pour PDF/DOCX.

Fichiers principaux:

- `backend/users/tasks.py`
- `backend/users/resume_parsing/service.py`
- `backend/users/resume_parsing/cleaners.py`
- `backend/users/resume_parsing/exceptions.py`
- `backend/users/resume_processing.py`

### 6.3 Informations extraites du CV

Les informations extraites sont stockees dans le modele `ProfileResume`.

Fichier:

- `backend/users/models.py`

Champs importants:

| Champ | Role |
|---|---|
| `parsed_text` | Texte brut extrait du CV |
| `resume_text_embedding_source` | Texte nettoye prepare pour les embeddings |
| `extracted_skills` | Skills semantiques canoniques extraites |
| `extracted_raw_skills` | Mentions brutes de skills avant normalisation |
| `extracted_normalized_skills` | Skills normalisees avec la couche ESCO/stockage |
| `extracted_domains` | Domaines semantiques detectes |
| `extracted_tools` | Outils et plateformes detectes |
| `extracted_languages` | Langues detectees dans le CV |
| `semantic_resume_confidence` | Niveau de confiance de l'extraction |
| `semantic_resume_status` | Etat du pipeline semantique |
| `semantic_resume_version` | Version de l'extraction semantique |
| `semantic_resume_metadata` | Details d'audit: business families, roles, warnings, LLM metadata |

### 6.4 Signaux semantiques avances

Le pipeline CV peut aussi stocker dans `semantic_resume_metadata`:

- `business_families`;
- `family_confidence`;
- `canonical_role`;
- `target_roles`;
- `llm_enrichment`;
- `warnings`;
- candidats rejetes ou mappes pour audit qualite.

Fichier principal:

- `backend/users/resume_semantic/service.py`

Fichiers lies:

- `backend/users/resume_semantic/extraction.py`
- `backend/ai/embeddings.py`
- `backend/ai/business_families.py`
- `backend/ai/crossencoder/service.py`

### 6.5 Exposition API et affichage frontend

L'API expose aujourd'hui surtout l'etat du CV:

- fichier;
- URL;
- statut de parsing;
- statut semantique;
- confiance semantique;
- version semantique;
- date de mise a jour.

Fichier:

- `backend/users/serializers.py` avec `ProfileResumeSerializer`

Frontend:

- `frontend/src/features/profile/components/ResumeSection.jsx`

Important: les signaux detailles comme `extracted_skills`, `extracted_tools`, `extracted_domains` et `extracted_languages` existent en base et servent au moteur IA, mais ils ne sont pas encore affiches directement dans la page profil.

### 6.6 Utilisation dans la recommandation

Les signaux CV sont utilises pour enrichir le profil candidat:

- meilleure representation semantique du candidat;
- detection de competences implicites non saisies manuellement;
- detection de domaines et outils;
- amelioration du ranking via JobBERT / embeddings;
- meilleure robustesse multilingue grace aux langues detectees.

Message soutenance:

> Le CV est transforme en signaux IA exploitables. Il ne sert pas seulement de piece jointe: il enrichit le matching semantique et explique l'uplift mesure de +23% dans le benchmark.

## 7. Fichiers a Citer Pendant la Soutenance

Backend:

- `backend/users/profile_completion.py`
- `backend/users/serializers.py`
- `backend/users/models.py`
- `backend/users/tasks.py`
- `backend/users/resume_parsing/service.py`
- `backend/users/resume_semantic/service.py`
- `backend/users/resume_processing.py`
- `backend/ai/business_families.py`
- `backend/ai/embeddings.py`
- `backend/opportunities/normalization/employment.py`

Frontend:

- `frontend/src/features/profile/ProfilePage.jsx`
- `frontend/src/features/profile/profileValidation.js`
- `frontend/src/features/profile/profilePreferences.js`
- `frontend/src/features/onboarding/onboardingState.js`
- `frontend/src/features/profile/components/BusinessFamilySelect.jsx`
- `frontend/src/features/profile/components/LocationMultiSelect.jsx`
- `frontend/src/features/profile/components/ProfileAutocompleteInput.jsx`
- `frontend/src/features/profile/components/ResumeSection.jsx`

Tests / gardes UX:

- `frontend/scripts/profileValidationChecks.mjs`
- `frontend/scripts/candidateFlowChecks.mjs`
- `backend/users/tests.py`

## 8. Message Jury

Le score de completude n'est pas un simple indicateur visuel. Il represente la qualite des signaux disponibles pour le moteur de recommandation IA. Les champs les plus importants pour le matching, comme le CV, les skills, les secteurs et les roles cibles, ont donc les poids les plus eleves.

Les controles sont appliques en double: frontend pour l'experience utilisateur, backend pour la securite et l'integrite des donnees.

Le CV est un signal central du systeme: il est parse, enrichi semantiquement, normalise et exploite par le moteur de recommandation pour ameliorer la precision.
