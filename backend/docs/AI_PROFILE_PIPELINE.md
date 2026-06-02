# Pipeline profil, CV, skills et suggestions

Last updated: 2026-06-02

## Objectif

Ce document explique comment BidWise transforme un profil utilisateur en signaux exploitables par le moteur IA.

Le but est de montrer que le systeme ne repose pas seulement sur un formulaire simple. Il combine donnees declarees, CV, suggestions, extraction semantique et embeddings.

## Entrees du profil

Le profil utilisateur contient notamment:

- niveau d'experience;
- annees d'experience;
- competences;
- roles cibles;
- centres d'interet / domaines;
- villes preferees;
- modes de travail;
- types de contrat;
- CV actif optionnel.

Ces informations sont transformees en `features` pour la recommandation.

Fichiers importants:

- `backend/users/models.py`
- `backend/users/serializers.py`
- `backend/ai/user_features.py`
- `backend/ai/embeddings.py`

## Upload CV

Pipeline:

```text
Frontend ResumeSection
  -> POST /profile/resume/
  -> creation ProfileResume
  -> sauvegarde fichier
  -> transaction.on_commit
  -> enqueue_profile_resume_parse
  -> Celery queue profile_resume
```

Le frontend affiche:

- upload en cours;
- analyse en cours;
- CV actif;
- preview si possible;
- suggestions extraites;
- possibilite de supprimer ou remplacer le CV.

Fichier frontend principal:

- `frontend/src/features/profile/components/ResumeSection.jsx`

## Stockage CV et Cloudinary

Le backend supporte un stockage cloud optionnel pour les resumes.

Objectif:

- eviter de dependre du disque local du container en production;
- garder un acces durable aux fichiers;
- separer le fichier binaire des metadonnees applicatives;
- faciliter le deploiement multi-container.

Configuration observee:

- `PROFILE_RESUME_USE_CLOUDINARY`
- credentials Cloudinary dans `.env`
- verification dans `backend/config/settings.py`

Point a dire:

```text
Cloudinary sert au stockage externe des CV. Le backend garde les metadonnees, l'etat d'analyse et les resultats semantiques, mais le fichier peut etre conserve dans un stockage cloud adapte a la production.
```

## Parsing CV

Le parsing extrait le texte brut du fichier.

Types acceptes cote frontend:

- PDF;
- DOCX;
- DOC;
- RTF;
- TXT.

Le backend nettoie ensuite le texte pour reduire le bruit avant extraction semantique.

Fichiers importants:

- `backend/users/resume_parsing/service.py`
- `backend/users/resume_semantic/normalization.py`

## Extraction semantique du CV

Apres parsing, le systeme extrait:

- skills;
- outils;
- domaines;
- role canonique possible;
- niveau ou indices d'experience;
- resume text utile pour l'IA.

Ces donnees alimentent:

- suggestions profil;
- embeddings profil;
- scoring For You;
- signaux de famille metier.

Fichiers importants:

- `backend/users/resume_semantic/`
- `backend/users/tasks.py`
- `backend/ai/user_features.py`

## Suggestions profil

Le systeme ne force pas automatiquement toutes les informations du CV dans le profil.

Il propose a l'utilisateur:

- un role detecte;
- des skills extraits;
- eventuellement des signaux utiles.

L'utilisateur peut:

- selectionner ce qu'il garde;
- ignorer les suggestions;
- supprimer le CV.

Pourquoi c'est important:

- controle utilisateur;
- evite d'ajouter des skills faux;
- ameliore progressivement le profil;
- rend le systeme explicable.

Fichiers importants:

- `backend/users/views.py`
- `frontend/src/features/profile/components/ResumeSection.jsx`

## Autocomplete skills, roles et interests

Le profil manuel utilise aussi des suggestions.

Endpoints:

- `/profile/skills/suggest/`
- `/profile/roles/suggest/`
- `/profile/interests/suggest/`

Objectifs:

- eviter trop de variations inutiles;
- guider l'utilisateur;
- augmenter la qualite des signaux;
- ameliorer la correspondance avec les offres.

Fichiers importants:

- `backend/users/views.py`
- `backend/opportunities/autocomplete/service.py`
- `frontend/src/features/profile/components/ProfileAutocompleteInput.jsx`

## Embeddings profil

Le profil est transforme en texte IA.

Exemple de contenu conceptuel:

```text
profile skills: Python, Django, SQL
target roles: Backend Developer
experience level: JUNIOR
years of experience: 2
locations: Tunis, Sousse
remote preference: ON_SITE
```

Ce texte sert a construire:

- embedding profil classique;
- embedding profil JobBERT;
- cache de contenu pour eviter de recalculer inutilement.

Fichiers importants:

- `backend/ai/embeddings.py`
- `backend/ai/jobbert.py`
- `backend/users/management/commands/generate_jobbert_profile_embeddings.py`

## Profile strength

Avant de recommander, BidWise verifie si le profil contient assez de signaux.

Signaux pris en compte:

- skills;
- roles;
- experience;
- preferences;
- resume;
- localisation.

Si le profil est trop faible, l'UI affiche un etat encourageant a completer le profil au lieu de donner de fausses recommandations.

Fichiers importants:

- `backend/ai/profile_strength.py`
- `frontend/src/features/opportunities/components/recommendations/ForYouEmptyState.jsx`

## Securite et qualite

Points importants:

- le CV appartient au profil de l'utilisateur authentifie;
- suppression/activation limitees aux CV du profil courant;
- validation type fichier;
- parsing asynchrone;
- pas d'execution de contenu du CV;
- suggestions appliquees uniquement si l'utilisateur les accepte;
- erreurs parsing/LLM isolees du reste de l'application.

## Message soutenance

```text
Le pipeline profil transforme une saisie utilisateur et un CV optionnel en signaux IA fiables. Le CV est parse en arriere-plan, les suggestions restent sous controle utilisateur, puis les features et embeddings alimentent JobBERT et le scoring For You.
```
