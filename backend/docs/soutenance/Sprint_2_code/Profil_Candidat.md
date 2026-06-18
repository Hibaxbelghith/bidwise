# Sprint 2 - Profil candidat, completude et extraction CV

## Objectif

Cette partie explique comment BidWise construit un profil candidat exploitable par le moteur de recommandation.

Le profil candidat n'est pas un simple formulaire statique. Il s'agit d'un cycle complet :

- creation automatique du compte apres authentification ;
- onboarding initial pour collecter les premiers signaux ;
- edition du profil sur web et mobile ;
- calcul du score de completude ;
- upload d'un CV ;
- extraction textuelle ;
- extraction semantique par IA locale ;
- suggestions de profil ;
- rafraichissement des embeddings pour la recommandation.

L'idee forte a transmettre au jury est la suivante :

`le profil BidWise est une base de signaux structuree qui alimente directement la personnalisation et la recommandation`

## Valeur ajoutee metier

Le profil candidat repond a trois besoins importants de BidWise :

- personnaliser les opportunites affichees a l'utilisateur ;
- eviter des recommandations trop generiques ;
- reduire le temps passe a re-saisir manuellement les memes informations.

Autrement dit, le profil sert de pont entre :

- ce que l'utilisateur declare explicitement ;
- ce que le CV permet de recuperer automatiquement ;
- ce que le moteur IA utilise ensuite pour scorer les opportunites.

## Cycle complet du profil candidat

```text
Authentification reussie
-> creation automatique du compte candidat
-> onboarding initial
-> profil partiellement rempli
-> calcul du score de completude
-> edition manuelle du profil
-> upload du CV
-> parsing asynchrone
-> extraction semantique Qwen via Ollama
-> suggestions de profil
-> validation utilisateur
-> refresh embeddings profil
-> recommandations plus pertinentes
```

## 1. Parcours fonctionnel candidat

### 1.1 Apres authentification

Apres verification OTP ou Google OAuth, le backend retourne les JWT puis le frontend appelle :

`GET /api/profile/me/`

Le profil complet est alors charge avec :

- informations personnelles ;
- preferences de recherche ;
- score de completude ;
- CV actif si disponible ;
- statut d'analyse du CV ;
- suggestions CV si l'analyse est terminee.

Si l'utilisateur est nouveau ou incomplet, il est redirige vers l'onboarding.

### 1.2 Onboarding initial

L'onboarding collecte les signaux minimums pour commencer la personnalisation :

1. type d'opportunite ;
2. mode de travail et localisation ;
3. competences ;
4. domaines d'interet ;
5. salaire attendu optionnel ;
6. types de contrat ;
7. roles cibles ;
8. visibilite du profil.

Deux comportements existent :

- `Finish` : le frontend exige que les etapes obligatoires soient coherentes avant validation finale ;
- `Skip` : le frontend sauvegarde une progression partielle et redirige vers `/opportunities?tab=explore`.

Ce comportement est important a expliquer :

`BidWise n'oblige pas l'utilisateur a remplir 100% du profil avant de naviguer, mais il lui montre clairement que la qualite des recommandations dependra de la richesse du profil.`

### 1.3 Edition du profil apres onboarding

Une fois l'utilisateur dans l'application, il peut completer et corriger son profil depuis la page profil.

Sur web, la page regroupe notamment :

- informations personnelles ;
- preferences de recherche ;
- signaux de carriere ;
- section CV ;
- visibilite.

Sur mobile, le meme contenu est reparti sur plusieurs ecrans plus ergonomiques.

## 2. Fichiers principaux

### Backend

- `backend/users/models.py`
  - modeles `Profil` et `ProfileResume`
- `backend/users/views.py`
  - `profile_detail`
  - `profile_resume`
  - `apply_resume_profile_suggestions`
  - endpoints de suggestions
- `backend/users/serializers.py`
  - validation, nettoyage et normalisation metier
- `backend/users/profile_completion.py`
  - calcul du score de completude
- `backend/users/tasks.py`
  - tache Celery du pipeline CV
- `backend/users/resume_parsing/service.py`
  - extraction du texte PDF/DOCX
- `backend/users/resume_processing.py`
  - preparation du texte d'embedding
- `backend/users/resume_semantic/service.py`
  - orchestration de l'extraction semantique
- `backend/users/resume_semantic/structured_llm.py`
  - prompt, schema JSON et post-traitement de la sortie Qwen
- `backend/users/resume_semantic/normalization.py`
  - nettoyage du texte avant passage au LLM
- `backend/users/storage.py`
  - stockage local ou Cloudinary

### Frontend web

- `frontend/src/features/profile/ProfilePage.jsx`
- `frontend/src/features/profile/profilePreferences.js`
- `frontend/src/features/profile/profileValidation.js`
- `frontend/src/features/profile/profileEditorState.js`
- `frontend/src/features/profile/components/ResumeSection.jsx`
- `frontend/src/features/profile/components/ProfileAutocompleteInput.jsx`
- `frontend/src/features/profile/components/BusinessFamilySelect.jsx`
- `frontend/src/features/profile/components/LocationMultiSelect.jsx`
- `frontend/src/features/profile/components/PreferenceChipGroup.jsx`
- `frontend/src/features/onboarding/OnboardingPage.jsx`

### Mobile

- `bidwise-mobile/src/features/profile/components/ProfileScreen.tsx`
- `bidwise-mobile/src/features/profile/components/ProfileEditScreen.tsx`
- `bidwise-mobile/src/features/profile/components/ProfileBasicInformationScreen.tsx`
- `bidwise-mobile/src/features/profile/components/ProfileCareerSignalsScreen.tsx`
- `bidwise-mobile/src/features/profile/components/ProfilePreferencesScreen.tsx`
- `bidwise-mobile/src/features/profile/components/ProfileResumeScreen.tsx`
- `bidwise-mobile/src/features/profile/components/ResumeSection.tsx`
- `bidwise-mobile/src/features/profile/components/ProfileAutocompleteInput.tsx`
- `bidwise-mobile/src/features/profile/components/ProfileEditorPage.tsx`
- `bidwise-mobile/src/features/profile/constants/profileOptions.ts`
- `bidwise-mobile/src/features/profile/services/profileService.ts`

## 3. Controle de saisie et conditions

Le systeme applique deux niveaux de protection :

- guidage frontend pour une bonne UX ;
- revalidation backend pour la securite et la coherence.

### 3.1 Regles principales cote frontend

Fichiers :

- `frontend/src/features/profile/profileValidation.js`
- `frontend/src/features/profile/profilePreferences.js`
- `frontend/src/features/onboarding/OnboardingPage.jsx`
- `bidwise-mobile/src/features/profile/constants/profileOptions.ts`

Controles importants :

- prenom et nom : entre 2 et 100 caracteres si renseignes ;
- annees d'experience : entier entre 0 et 60 ;
- salaire : TND par mois, avec plage bornee et `min <= max` ;
- CV : taille max 5 MB ;
- localisation : obligatoire en onboarding si le mode de travail contient `ON_SITE` ou `HYBRID` ;
- competences : au moins une en onboarding ;
- secteurs : au moins un en onboarding ;
- roles cibles : au moins un en onboarding ;
- types de contrat : limites aux valeurs canoniques du systeme ;
- visibilite : booleen simple active/desactive.

### 3.2 Regles principales cote backend

Fichier :

- `backend/users/serializers.py`

Le backend :

- nettoie les listes ;
- deduplique les valeurs ;
- borne le nombre maximal d'elements ;
- rejette les valeurs non textuelles ;
- controle les localisations ;
- controle les types de contrat ;
- controle les types d'opportunites ;
- controle les modes de travail ;
- controle la taille, l'extension et le type du CV.

Ce point est important a dire :

`meme si le frontend est contourne, le backend garde la main sur la coherence des donnees ecrites en base.`

### 3.3 Alignement des valeurs canoniques

Le systeme a ete aligne pour utiliser les memes types defendables dans tout le flux principal :

- opportunites : `JOB`, `INTERNSHIP`, `CALLS_FOR_TENDER`
- modes de travail : `REMOTE`, `HYBRID`, `ON_SITE`
- types de contrat principaux : `CDI`, `CDD`, `SIVP`, `FREELANCE`
- `INTERNSHIP` n'apparait comme type de contrat que si l'utilisateur cible aussi les opportunites de stage

Cette coherence evite qu'un utilisateur saisisse des preferences impossibles a exploiter dans la recommandation.

## 4. Suggestions et autocompletion

Le profil ne repose pas uniquement sur des listes statiques frontend.

Le frontend appelle des endpoints de suggestion :

- `GET /api/profile/skills/suggest/`
- `GET /api/profile/roles/suggest/`
- `GET /api/profile/interests/suggest/`

Le backend utilise :

- des termes consolides en base ;
- des alias metier ;
- des regles de nettoyage ;
- un scoring de recherche.

Objectifs :

- guider l'utilisateur ;
- reduire les variations inutiles ;
- garder des signaux plus homogenes pour la recommandation.

Limite assumee :

`l'utilisateur peut encore saisir certaines valeurs libres, mais le systeme applique des garde-fous pour eviter les entrees aberrantes.`

## 5. Score de completude du profil

Le score est calcule cote backend dans :

- `backend/users/profile_completion.py`

Poids utilises :

| Signal | Poids |
|---|---:|
| First name | 7 |
| Last name | 7 |
| Experience level | 8 |
| Years of experience | 8 |
| Locations | 8 |
| Work modes | 7 |
| Employment types | 6 |
| Opportunity types | 4 |
| Skills | 10 |
| Target roles | 10 |
| Interests | 10 |
| Resume | 15 |

Le CV a le poids le plus eleve car il enrichit fortement les signaux du profil.

Ce score n'est pas decoratif. Il sert a :

- expliquer a l'utilisateur pourquoi son profil est faible ;
- l'encourager a completer les zones importantes ;
- justifier que des recommandations plus fines demandent un profil plus riche.

## 6. Cycle complet du CV

## 6.1 Upload et creation du `ProfileResume`

L'utilisateur envoie son CV via :

`POST /api/profile/resume/`

Le serializer :

- verifie le fichier ;
- cree un `ProfileResume` ;
- stocke les metadonnees de base ;
- marque le statut de parsing a `PENDING`.

Ensuite, `transaction.on_commit(...)` declenche :

`enqueue_profile_resume_parse(resume_id)`

Ce choix evite de lancer le traitement tant que la transaction base n'est pas committee.

## 6.2 Stockage local ou Cloudinary

Le stockage est gere par :

- `backend/users/storage.py`

Si `PROFILE_RESUME_USE_CLOUDINARY=false` :

- stockage classique sur le disque applicatif.

Si `PROFILE_RESUME_USE_CLOUDINARY=true` :

- le fichier est stocke dans Cloudinary en `raw upload`.

Pourquoi c'est defendable :

- en production, on evite de dependre du disque local du container ;
- le backend garde la logique metier, les statuts et les metadonnees ;
- le binaire du CV est externalise dans un stockage adapte.

Formulation simple pour le jury :

`Cloudinary sert au stockage durable du fichier, tandis que le backend conserve le cycle d'analyse et les signaux metier.`

## 6.3 Traitement asynchrone avec Celery

Le pipeline CV est traite en arriere-plan via :

- `backend/users/tasks.py`

Tache principale :

- `parse_profile_resume`

Interet :

- ne pas bloquer la requete HTTP ;
- ne pas figer l'interface utilisateur ;
- mieux absorber les traitements plus lourds du CV et du LLM.

La queue metier a retenir est :

- `profile_resume`

## 6.4 Parsing du CV

Le parsing correspond a la lecture technique du fichier.

Fichier :

- `backend/users/resume_parsing/service.py`

Bibliotheques utilisees :

- PDF : `PyMuPDF`
- DOCX : `python-docx`

Role du parsing :

- lire le contenu textuel du CV ;
- detecter si le fichier est vide, corrompu ou non supporte ;
- produire un texte brut nettoyable.

Sorties utiles :

- `parsed_text`
- `parsing_status`
- `parsing_error`
- `parsed_at`

Statuts possibles :

- `PENDING`
- `PROCESSING`
- `SUCCEEDED`
- `EMPTY`
- `FAILED`
- `UNSUPPORTED`

Point important :

`le parsing n'essaie pas encore de comprendre le sens du CV ; il se contente de recuperer un texte exploitable.`

## 6.5 Nettoyage du texte

Le texte extrait est nettoye avant l'etape IA.

Fichier :

- `backend/users/resume_semantic/normalization.py`

Le nettoyage :

- retire les caracteres de controle ;
- normalise l'Unicode ;
- compacte les espaces ;
- tronque a une longueur maitrisee.

Ce nettoyage sert a fournir au LLM une entree plus stable.

## 6.6 Extraction semantique par Qwen local via Ollama

Une fois le texte extrait, le backend lance :

- `process_profile_resume_semantics(...)`

Fichier :

- `backend/users/resume_semantic/service.py`

La vraie extraction semantique est definie dans :

- `backend/users/resume_semantic/structured_llm.py`

Architecture retenue :

- parsing classique pour lire le document ;
- LLM local pour interpreter le texte ;
- validation schema + post-traitement backend pour garder le controle.

### Pourquoi un LLM local ?

Choix defendable pour BidWise :

- meilleure confidentialite des CV ;
- plus de controle sur l'infrastructure ;
- pas de dependance directe a une API externe payante ;
- plus de cohérence avec une architecture maitrisee de bout en bout.

### Prompt

Le prompt est construit par :

- `build_resume_extraction_prompt(text)`

Principes imposes au modele :

- retourner du JSON uniquement ;
- utiliser seulement des preuves explicites du CV ;
- ne pas inventer ;
- distinguer `canonical_role`, `target_roles`, `skills`, `tools`, `domains`, `business_families` ;
- structurer aussi l'experience, les langues, les lieux et les types de contrat.

### Schema JSON

Le schema officiel attend notamment :

- `target_roles`
- `canonical_role`
- `skills`
- `tools`
- `domains`
- `business_families`
- `family_confidence`
- `experience_level`
- `years_experience`
- `languages`
- `contract_types`
- `locations`
- `confidence`

Ce point est tres fort a la soutenance :

`le LLM ne retourne pas un texte libre ; on lui impose une structure JSON controlee, puis cette structure est revalidee avant d'etre stockee.`

### Parametres importants

Configuration actuelle :

- `PROFILE_RESUME_STRUCTURED_LLM_ENABLED=true`
- `PROFILE_RESUME_STRUCTURED_LLM_FALLBACK_ENABLED=false`
- `PROFILE_RESUME_QWEN_TEMPERATURE=0.0`
- `PROFILE_RESUME_QWEN_MAX_TOKENS=300`
- `PROFILE_RESUME_QWEN_TEXT_CHARS=1200`
- `PROFILE_RESUME_QWEN_KEEP_ALIVE=30m`

Defense rapide :

- `temperature=0.0` : stabiliser les sorties et limiter les variations
- `max_tokens=300` : obtenir un JSON compact, pas une reponse bavarde
- `text_chars=1200` : concentrer le modele sur la partie utile du CV et maitriser la latence
- `keep_alive=30m` : reduire le cout de rechargement du modele

## 6.7 Normalisation de la sortie du LLM

La normalisation n'est pas dans un seul fichier.

Elle existe a trois niveaux :

1. nettoyage du texte avant passage au LLM
   - `backend/users/resume_semantic/normalization.py`
2. nettoyage de la sortie LLM
   - `backend/users/resume_semantic/structured_llm.py`
3. validation metier avant ecriture dans le profil
   - `backend/users/serializers.py`

Exemples de normalisation :

- suppression des doublons ;
- nettoyage des espaces ;
- decoupage de valeurs combinees comme `CDI / CDD` ;
- filtrage de valeurs vides ;
- harmonisation des labels ;
- limitation du nombre d'elements.

Position defendable :

`le backend ne pretend pas comprendre tous les cas possibles. Son role est de nettoyer, borner et harmoniser les signaux extraits par l'IA pour qu'ils restent exploitables.`

## 6.8 Signaux stockes dans `ProfileResume`

Le modele `ProfileResume` conserve notamment :

- `parsed_text`
- `resume_text_embedding_source`
- `extracted_skills`
- `extracted_raw_skills`
- `extracted_domains`
- `extracted_tools`
- `extracted_languages`
- `semantic_resume_status`
- `semantic_resume_confidence`
- `semantic_resume_version`
- `semantic_resume_metadata`

Dans `semantic_resume_metadata`, on retrouve notamment :

- `canonical_role`
- `target_roles`
- `business_families`
- `family_confidence`
- `llm_enrichment.result`
- `llm_enrichment.profile_suggestions`
- `warnings`

## 6.9 Suggestions de profil apres analyse CV

Une fois l'analyse reussie, l'interface peut afficher des suggestions comme :

- role detecte ;
- competences detectees ;
- domaines ;
- localisations ;
- types de contrat ;
- niveau et annees d'experience.

L'utilisateur peut :

- accepter tout ;
- selectionner seulement certaines suggestions ;
- ignorer ;
- remplacer le CV ;
- supprimer le CV.

Pourquoi ce choix est bon :

- on garde l'humain dans la boucle ;
- on limite les faux positifs ;
- on evite d'ecraser brutalement le profil utilisateur.

## 6.10 Rafraichissement des embeddings profil

Quand un CV actif est parse avec succes, le systeme declenche aussi un refresh des embeddings du profil.

Cela permet d'injecter les nouveaux signaux du CV dans la recommandation.

L'idee importante :

`le CV n'est pas seulement affiche dans l'interface ; il enrichit effectivement le moteur de matching.`

## 7. Scenario de demo recommande

Scenario simple, stable et defendable pendant la soutenance :

1. se connecter avec un nouveau compte candidat ;
2. terminer l'onboarding avec :
   - `JOB`
   - `HYBRID`
   - `Tunis`
   - quelques skills comme `Python`, `Django`
   - secteur `software_web` ou `backend`
   - contrat `CDI`
   - role cible `Backend Developer`
3. montrer que le profil a un score intermediaire ;
4. completer les informations personnelles :
   - prenom
   - nom
   - niveau d'experience
   - annees d'experience
5. montrer que le score augmente ;
6. uploader un CV texte propre ;
7. montrer les statuts :
   - upload
   - analyse en cours
   - analyse terminee
8. ouvrir le CV si besoin ;
9. afficher les suggestions CV ;
10. appliquer seulement certaines suggestions ;
11. actualiser le profil ;
12. montrer que le profil est enrichi et plus complet.

## 8. CV recommandes pour la demo

CV principal recommande :

- `backend/benchmark_inputs/cvs/cv_developpeur_backend.pdf`

Pourquoi :

- coherent avec BidWise et un jury technique ;
- mots-cles faciles a commenter ;
- deja valide par le benchmark d'extraction.

CV de secours :

- `backend/benchmark_inputs/cvs/cv_data_ai.pdf`
- `backend/benchmark_inputs/cvs/cv_data_engineer.pdf`

Conseil pratique :

- garder aussi un CV que tu as deja teste dans l'UI de bout en bout sur ta machine ;
- eviter les CV scannes en image ou tres graphiques pour la demo en direct.

## 9. Commandes de test utiles

### Benchmark extraction textuelle reelle

```powershell
docker compose run --rm backend python manage.py benchmark_resume_extraction_quality --fail-under-average-recall 0.95 --fail-on-fixture-failure
```

### Meme benchmark en JSON

```powershell
docker compose run --rm backend python manage.py benchmark_resume_extraction_quality --fail-under-average-recall 0.95 --fail-on-fixture-failure --json
```

### Test unitaire / integration du benchmark

```powershell
docker compose run --rm backend python manage.py test tests.test_resume_extraction_quality
```

### Test d'un CV unique dans le pipeline

```powershell
docker compose exec backend python manage.py test_resume_processing /app/benchmark_inputs/cvs/cv_developpeur_backend.pdf --structured-llm --timeout-seconds 210
```

Cette derniere commande est utile si un expert veut voir :

- le statut de parsing ;
- le statut semantique ;
- les skills extraites ;
- les domaines ;
- les outils ;
- la confiance ;
- les suggestions generees.

## 10. Fichiers a montrer ou a envoyer a un expert si necessaire

Pour prouver la robustesse du module profil/CV, les fichiers les plus utiles sont :

- `backend/benchmark_inputs/cvs/cv_developpeur_backend.pdf`
- `backend/benchmark_inputs/cvs/cv_data_ai.pdf`
- `backend/tests/recommendation_benchmark/resumes/cv_extraction_expectations.json`
- `backend/tests/test_resume_extraction_quality.py`
- `backend/users/management/commands/benchmark_resume_extraction_quality.py`
- `backend/users/management/commands/test_resume_processing.py`

Si l'expert veut verifier le prompt ou le schema :

- `backend/users/resume_semantic/structured_llm.py`

Si l'expert veut verifier le stockage et les statuts :

- `backend/users/models.py`
- `backend/users/views.py`
- `backend/users/tasks.py`

## 11. Forces et limites a assumer devant le jury

### Forces

- profil pense comme source de signaux et non simple formulaire ;
- score de completude explicable ;
- controle de saisie frontend + backend ;
- onboarding progressif ;
- pipeline CV asynchrone avec Celery ;
- parsing separe de l'interpretation IA ;
- LLM local pour la confidentialite et le controle ;
- suggestions non appliquees automatiquement ;
- benchmark d'extraction sur de vrais CV.

### Limites assumees

- la lecture est surtout fiable sur des CV texte propres ;
- les CV scannes en image demanderaient idealement une couche OCR ;
- un LLM peut sur-interpreter certains signaux, d'ou la validation utilisateur ;
- la normalisation est repartie sur plusieurs couches et pourrait etre davantage factorisee a l'avenir.

## 12. Message final a retenir pour la soutenance

La partie profil candidat de BidWise est defendable car elle combine :

- experience utilisateur fluide ;
- validation metier ;
- extraction automatique du CV ;
- IA locale controlee ;
- stockage et traitement asynchrones ;
- et surtout un profil qui sert directement au moteur de recommandation.

La phrase la plus simple a retenir est :

`dans BidWise, le profil candidat n'est pas une fiche passive ; c'est la source principale de personnalisation et de matching intelligent.`
