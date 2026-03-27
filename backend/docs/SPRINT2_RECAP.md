# Sprint 2 — Gestion Profils & Opportunités

## Overview (problème + objectif)

Sprint 2 met en place la couche data centrale pour les opportunités afin de préparer le moteur de recommandation de Sprint 3.

Problèmes adressés :
- données d’opportunités hétérogènes (sources multiples, texte bruité)
- besoin d’une API de consultation fiable et sécurisée
- besoin d’une similarité sémantique exploitable en production

Objectifs atteints :
- ingestion + normalisation des opportunités
- pipeline NLP appliqué avant embeddings
- endpoint de similarité `/api/opportunities/{id}/similar/`
- sécurisation API + optimisations performance adaptées à un dataset petit (~400 items)

---

## System Architecture (pipeline)

Flux global backend :

1. **Scraping sources**  
2. **Parser / Normalisation** (mapping vers modèle `Opportunite`)  
3. **NLP preprocessing** (nettoyage + enrichissement texte)  
4. **Embeddings generation** (Sentence Transformers)  
5. **Stockage DB** (`embedding_vector`, `embedding_model`)  
6. **Similarity retrieval API** (cosine similarity + filtres)

Architecture fonctionnelle :

- `scraping/*` : collecte brute
- `scraping/parser.py` : normalisation opportunité
- `nlp_preprocessing.py` : texte prêt pour embeddings
- `embeddings/service.py` : encodage embeddings
- `similarity.py` : recherche similaire
- `views.py` : exposition endpoint REST

---

## NLP Pipeline (détaillé et clair)

Le pipeline NLP prépare un texte stable avant encodage.

Étapes principales :
- nettoyage HTML, URLs, emails
- normalisation (minuscules, accents, espaces)
- réduction bruit (boilerplate, répétitions)
- traitement par type de contenu (job vs tender)
- extraction heuristique (organisation, signaux structurés)
- contrôle de longueur pour éviter les dumps de page

Sortie :
- texte compact, lisible, cohérent pour embeddings
- fallback sécurisé si texte incomplet

Exemple simplifié :
- Entrée brute : `type: job title: ...` + phrases répétées
- Sortie NLP : texte nettoyé sans artefacts inutiles

---

## Embedding & Similarity Logic

Embeddings :
- modèle Sentence Transformers configuré en settings
- embeddings stockés en base
- version tracée via `embedding_model` (`model@version`)

Similarité :
- base = **cosine similarity**
- si vecteurs normalisés, dot product = cosine

Formule :
- `similarity(A,B) = dot(A,B) / (||A|| * ||B||)`

Logique actuelle de ranking :
- score sémantique de base
- bonus léger de récence (borné)
- exclusion candidats sous seuil minimal (`MIN_SIMILARITY = 0.52`)

---

## Deduplication Strategy

Déduplication au niveau résultats similaires :

- fingerprint contenu basé sur SHA1
- source fingerprint calculé depuis `titre + description` normalisés
- candidat ignoré si fingerprint identique à la source
- dédup top-k : un seul résultat par fingerprint

Bénéfice :
- évite les quasi-doublons dans les recommandations similaires
- améliore la diversité immédiate du top-k

---

## API Design (`/similar/`)

Endpoint :
- `GET /api/opportunities/{id}/similar/`

Paramètres :
- `k` (ou `top_k`) avec clamp serveur `[1, 50]`

Réponse :
- minimale et publique, sans fuite de détails ML internes

Exemple :
```json
[
  {
    "id": 320,
    "titre": "Téléconseillers (Appels, Chat & Email)",
    "similarity_score": 0.88
  }
]
```

Important :
- `embedding_vector` et `embedding_model` ne sont pas exposés

---

## Performance Optimizations

Optimisations appliquées (sans complexité excessive) :

- filtres candidats :
  - `statut = ACTIVE`
  - même `type_opportunite`
  - même `embedding_model`
- fenêtre temporelle : **90 derniers jours**
- limite candidats : **1000 max**
- `top_k` borné `[1,50]`
- throttling DRF : **20 requêtes/minute** sur `/similar/`
- logging de traitement : `processed_candidates`, `returned`

Pourquoi ce choix :
- dataset actuel petit (~400) → in-memory exact search reste adapté
- optimisation ciblée sans introduire de dette d’architecture

---

## Security Considerations

Mesures appliquées :

- suppression des champs sensibles d’API (`embedding_vector`, `embedding_model`)
- throttling endpoint similarité (anti-abus)
- validation serveur des bornes (`k`)
- filtrage côté serveur (pas de confiance aux paramètres client pour la logique métier)

---

## Engineering Decisions (WHY)

Choix majeurs et justification :

- **In-memory similarity** : suffisant à ce volume, plus simple et maintenable
- **Fingerprint SHA1 texte normalisé** : dédup robuste à faible coût
- **Seuil minimal de similarité** : réduit le bruit sémantique
- **Réponse API minimale** : meilleure sécurité + meilleur temps de réponse
- **Optimisations incrémentales** : priorité à la stabilité production

---

## Trade-offs & Limitations

Trade-offs assumés :

- pas d’ANN (FAISS/pgvector) pour l’instant
- pas de reranker ML complexe
- heuristiques NLP simples (robustes mais imparfaites)

Limitations actuelles :

- certaines similarités peuvent rester “linguistiques” plus que “fonction métier”
- qualité dépend de la propreté des descriptions source
- dataset petit donc variance des résultats possible selon source

---

## Improvements Made During Sprint 2

Améliorations clés livrées :

- NLP preprocessing stabilisé
- génération embeddings versionnée
- endpoint similarité opérationnel
- dedup top-k par fingerprint
- exclusion quasi-doublons source
- seuil de similarité minimal
- filtres candidats + fenêtre 90 jours + cap 1000
- clamp `k` et throttling `20/min`
- suppression exposition embeddings dans API

---

## Final System Behavior (état actuel)

Ce qui fonctionne aujourd’hui :

- collecte, normalisation et stockage opportunités
- texte nettoyé avant embeddings
- embeddings générés et persistés
- endpoint `/similar/` stable, sécurisé et testé
- résultats plus pertinents grâce à :
  - déduplication
  - seuil minimal
  - filtres métier de base
  - contraintes performance

Statut :
- **version stable, testée et validée pour Sprint 2**
- prête pour extension contrôlée en Sprint 3 (recommandation avancée)
