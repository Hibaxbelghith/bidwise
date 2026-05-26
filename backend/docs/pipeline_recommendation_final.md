# Pipeline final du système de recommandation BidWise

Date de synthèse: 2026-05-24

Ce document décrit le pipeline réel retenu pour la livraison du système IA de recommandation. Il distingue le coeur actif du système, les couches secondaires conservées par prudence, et les éléments legacy planifiés pour nettoyage après livraison.

## 1. Vue d'ensemble

Pipeline final:

```text
Sources d'offres
  -> scraping / ingestion opportunités
  -> normalisation et matérialisation des offres
  -> enrichissement LLM optionnel des offres
  -> embeddings opportunités + JobBERT
  -> construction des signaux profil / CV
  -> retrieval des candidats
  -> scoring métier + sémantique
  -> quality gates
  -> CrossEncoder optionnel
  -> API recommandations
  -> explications utilisateur
```

Le moteur principal actuel est:

```text
JobBERT + LLM enrichment + taxonomie métier business_families + quality gates
```

ESCO n'est plus le moteur principal. Il reste branché comme couche secondaire de normalisation des skills, afin de ne pas risquer une régression avant la soutenance.

## 2. Pipeline bout en bout

### 2.1 Scraping et ingestion

Les offres sont récupérées par le pipeline `opportunities/`.

```text
scrapers sources
  -> opportunities/core/pipeline_flow.py
  -> opportunities/processing.py
  -> opportunities/materialization/service.py
  -> Opportunite
```

Rôle:

- créer ou mettre à jour les opportunités;
- nettoyer titre, description, lieu, contrat, disponibilité;
- stocker les skills bruts;
- déclencher la normalisation secondaire des skills;
- préparer les données consommées ensuite par l'IA.

Point d'attention: cette partie est volontairement non touchée pendant l'audit, car elle est critique pour le pipeline scraping existant.

### 2.2 Enrichissement LLM des offres

Module principal:

```text
backend/ai/llm/
```

Flux:

```text
enrich_opportunities_with_gemini
  -> ai.llm.opportunity_enrichment.enrich_opportunity_with_llm
  -> ai.llm.enrichment.enrich_opportunity_text
  -> ai.llm.providers.get_llm_provider
  -> Gemini / Ollama / fallback provider
  -> ai.llm.schemas.validate_llm_extraction
  -> ai.llm.opportunity_post_validation
  -> Opportunite.extra_data.llm_enrichment
```

Données produites:

```text
canonical_role
target_roles
skills
tools
domains
soft_skills
business_families
family_confidence
experience_level
years_experience
responsibilities
requirements
languages
contract_types
work_modes
locations
salary
education_level
```

Usage dans le ranking:

- `business_families` sert de garde-fou métier;
- `canonical_role`, `skills`, `tools`, `domains`, `responsibilities` enrichissent le texte JobBERT;
- `experience_level` et `years_experience` alimentent les pénalités de seniorité;
- les données LLM permettent de mieux comprendre les offres pauvres ou mal structurées.

### 2.3 Embeddings opportunités

Commandes et modules:

```text
opportunities/management/commands/generate_jobbert_embeddings.py
ai/jobbert.py
opportunities/nlp/nlp_preprocessing.py
```

Flux:

```text
Opportunite
  -> prepare_combined_text
  -> texte enrichi titre + description + LLM + skills
  -> JobBERT embedding
  -> embedding_vector / embedding_vector_pg / embedding_model
```

JobBERT est utilisé comme représentation sémantique spécialisée emploi. C'est le signal principal pour rapprocher profil, CV et offre.

### 2.4 Construction des signaux profil et CV

Fichiers clés:

```text
ai/user_features.py
users/resume_semantic/service.py
ai/embeddings.py
ai/jobbert.py
```

Flux:

```text
Profil utilisateur
  + compétences
  + rôles cibles
  + préférences
  + CV parsé
  + semantic resume metadata
  -> build_user_features
  -> embedding profil
  -> JobBERT profile embedding
```

Le CV peut enrichir:

- skills;
- tools;
- domains;
- business_families;
- target_roles;
- confidence sémantique.

### 2.5 Retrieval des candidats

Fichier:

```text
ai/retrieval.py
```

Rôle:

- récupérer un ensemble raisonnable d'opportunités candidates;
- utiliser les embeddings disponibles;
- limiter le volume envoyé au scoring;
- préserver un fallback si l'embedding est absent.

### 2.6 Scoring principal

Fichier central:

```text
ai/recommendation_service.py
```

Le score combine:

```text
score sémantique
+ JobBERT score / adjustment
+ signaux rôle et skills
+ business family bonus
- pénalité cross-family
- pénalité absence de preuve métier
- pénalité seniority / hierarchy gap
- pénalités signaux trop génériques
+ feedback utilisateur éventuel
```

Signaux importants:

- `profile_business_families`;
- `opportunity_llm_business_families`;
- `families_are_compatible`;
- `target_roles`;
- `profile_skills`;
- `normalized_skills` secondaire;
- `hierarchy_validation`;
- `jobbert_score`.

Pénalités récentes importantes:

```text
LLM_BUSINESS_FAMILY_MISMATCH_PENALTY = 0.10
STRICT_BUSINESS_FAMILY_MISMATCH_PENALTY = 0.15
```

Objectif: éviter qu'une offre d'une famille métier incompatible remonte uniquement grâce à des mots partagés comme Python, DevOps, data ou support.

### 2.7 Quality gates

Fichier:

```text
ai/quality_gates.py
```

Rôle:

- filtrer les recommandations faibles;
- classer les recommandations en buckets;
- produire la confiance `LOW`, `MEDIUM`, `HIGH`;
- éviter les recommandations trop génériques ou trop éloignées;
- gérer les profils sparse / CV-only / role-only.

Les quality gates sont le dernier garde-fou avant exposition API.

### 2.8 CrossEncoder optionnel

Dossier:

```text
ai/crossencoder/
```

Rôle:

- reranker un top-N de candidats;
- ne jamais casser le ranking si le modèle est absent;
- fonctionner en local-only par défaut.

Garde-fous:

```text
CROSS_ENCODER_ENABLED=False par défaut
CROSS_ENCODER_LOCAL_FILES_ONLY=True
timeout strict
fallback ranking inchangé
TTL si modèle indisponible
```

Le CrossEncoder est une optimisation de précision, pas une dépendance critique.

### 2.9 API et explications

Fichiers:

```text
ai/views.py
ai/explainability.py
ai/urls.py
```

Rôle:

- exposer les recommandations;
- sérialiser les scores, raisons et signaux;
- expliquer pourquoi une offre est recommandée;
- intégrer feedback et fallback.

## 3. Rôle des fichiers clés

| Fichier / dossier | Rôle |
|---|---|
| `ai/recommendation_service.py` | Scoring principal et combinaison des signaux |
| `ai/retrieval.py` | Sélection des candidats avant scoring |
| `ai/views.py` | API recommandations |
| `ai/quality_gates.py` | Filtrage, confiance, buckets |
| `ai/user_features.py` | Construction des features profil |
| `ai/embeddings.py` | Embeddings profil classiques |
| `ai/jobbert.py` | Embeddings et score JobBERT |
| `ai/business_families.py` | Taxonomie métier et compatibilité familles |
| `ai/hierarchy.py` | Validation déterministe seniorité / responsabilité |
| `ai/hierarchy_llm.py` | Validation hiérarchie assistée LLM avec cache |
| `ai/llm/` | Extraction structurée LLM CV/offres |
| `ai/crossencoder/` | Reranking optionnel |
| `ai/recommendation_benchmark/` | Benchmark qualité end-to-end |
| `ai/explainability.py` | Explications de recommandation |
| `ai/tasks.py` | Tâches Celery IA |
| `ai/models.py` | Modèles IA, ESCO legacy, cache LLM hierarchy |

## 4. Actif vs legacy

### Actif livraison

```text
JobBERT
LLM enrichment
business_families
recommendation_service
quality_gates
hierarchy validation
recommendation_benchmark
test_profile_recommendations
CrossEncoder optionnel
```

### Actif mais secondaire / legacy conservé

```text
ESCO skill normalization
BidWise skill aliases
normalized_skills bonus
ESCO maintenance commands
```

Justification: ESCO n'est plus le coeur du ranking, mais il reste importé par le stockage des skills, le CV semantic, les tâches Celery et quelques bonus secondaires. Le retirer avant soutenance présenterait un risque élevé pour un gain faible.

### Archivé maintenant

Les commandes expérimentales suivantes ont été déplacées vers:

```text
backend/docs/archive/legacy_commands/
```

```text
audit_cv_recommendation_benchmark.py
audit_jobbert_recommendations.py
benchmark_gemini_enrichment.py
benchmark_recommendation_stability.py
```

### À renommer post-livraison

```text
enrich_opportunities_with_gemini.py -> enrich_opportunities_with_llm.py
gemini-opportunity-enrichment-v2 -> llm-opportunity-enrichment-v3
```

## 5. Métriques benchmark actuelles

Dernier benchmark global communiqué:

```text
Precision@10: 0.46
Recall@10: 0.82
Noise Rate: 0.03
Exact Match Rate: 0.46
Sparse Profile Robustness: MEDIUM
CV Uplift: +23%
Multilingual Robustness: LOW
Semantic Extraction Precision: 0.29
Multilingual Extraction Robustness: GOOD
Confidence Calibration: GOOD
Recommendation Diversity: 0.90
False Positive Rate: 0.03
```

Signal fort pour la soutenance:

```text
Precision top-3: 0.70
Scénarios avec top-3 parfait: 20 / 50
```

Catégories fortes:

```text
marketing: GOOD, P=1.00
role_only: GOOD, P=0.71
accounting: MEDIUM, P=0.62
hr: MEDIUM, P=0.60
frontend: MEDIUM, P=0.57
non_tech: MEDIUM, P=0.60
english: MEDIUM, P=0.54
ai: MEDIUM, P=0.53
```

Catégories faibles connues:

```text
devops: LOW, P=0.22
data: LOW, P=0.28
backend: LOW, P=0.43
arabic: LOW, P=0.34
multilingual: LOW, P=0.40
nurse: LOW, P=0.30
sparse: LOW, P=0.30
```

Failure cases récurrents:

```text
Frontend profile -> Python Backend Developer
DevOps profile -> DevOps Accountant ERP Specialist
DevOps profile + CV -> DevOps Accountant ERP Specialist / Frontend React Developer
```

Interprétation: le système est déjà stable sur bruit global et CV uplift, mais manque encore de données enrichies et de fixtures réalistes pour certaines familles techniques.

## 6. Limites connues

### Couverture LLM incomplète

Une partie seulement des offres est enrichie. Les offres sans `llm_enrichment.business_families` ne bénéficient pas pleinement de la pénalité cross-family.

Plan:

```text
enrichissement complet par batch
régénération JobBERT
benchmark final
```

### Taxonomie à centraliser

La taxonomie existe dans plusieurs endroits:

```text
business_families.py
llm/schemas.py
llm/enrichment.py prompts
```

Plan post-livraison: faire de `business_families.py` la source unique.

### Familles canoniques incomplètes

Concepts comme:

```text
devops
data_science
software_development
```

ne sont pas encore des familles canoniques directes. Elles sont actuellement mappées vers:

```text
devops -> software_web / it_network_support / backend selon contexte
data -> data_ai
software development -> software_web
```

Plan: étendre proprement la taxonomie après benchmark final.

### CrossEncoder absent du cache local

Le CrossEncoder est prêt architecturalement, mais le modèle doit être téléchargé explicitement avant activation.

Plan:

```text
télécharger modèle CrossEncoder
garder CROSS_ENCODER_LOCAL_FILES_ONLY=True
activer CROSS_ENCODER_ENABLED=True
benchmark avant/après
```

### ESCO legacy encore branché

ESCO reste présent comme couche secondaire de normalisation. Migration annulée avant soutenance car risque estimé à 2-3 jours.

Plan post-livraison:

```text
mesurer impact sans bonus ESCO
créer ai/skill_storage.py neutre
retirer imports ESCO du runtime
archiver commandes ESCO
supprimer modèles/données ESCO si non nécessaires
```

## 7. Plan post-livraison

Priorités:

1. Enrichir toutes les offres utiles avec LLM par batch.
2. Régénérer les embeddings JobBERT.
3. Lancer benchmark final top-10 et top-20.
4. Ajouter fixtures benchmark DevOps/Data réalistes.
5. Étendre ou clarifier la taxonomie `business_families`.
6. Renommer les commandes Gemini vers LLM.
7. Centraliser la taxonomie dans `business_families.py`.
8. Évaluer puis retirer progressivement ESCO du pipeline actif.
9. Télécharger et benchmarker CrossEncoder.
10. Ajouter un README dans `ai/recommendation_benchmark/`.

## 8. Résumé pour soutenance

Le système final n'est pas une simple recherche par mots-clés. Il combine:

```text
compréhension sémantique emploi avec JobBERT
extraction structurée LLM
taxonomie métier contrôlée
garde-fous de qualité
validation seniorité / hiérarchie
benchmark end-to-end mesurable
```

Les expérimentations précédentes, notamment ESCO et audits isolés Gemini/JobBERT, ont été conservées ou archivées selon leur rôle. Le pipeline livré est maîtrisé, mesuré, et conçu pour rester robuste même quand une couche optionnelle comme CrossEncoder ou LLM est indisponible.

L'ajout d'un CV améliore la précision de +23%, confirmant que le système exploite réellement le contenu sémantique du profil candidat.
