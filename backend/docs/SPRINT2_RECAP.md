# Sprint 2 — Récapitulatif Technique (Focus Keejob)

## 1. Ce que fait le système

Le système transforme des annonces web hétérogènes en opportunités propres, structurées et exploitables par l'application (frontend + IA).

Objectifs atteints sur la source Keejob :
- scraping fiable de la page détail
- extraction de champs métier utiles
- normalisation canonique cohérente
- qualité de données contrôlée
- exposition API stable pour le frontend
- préparation des embeddings pour la similarité

Champs métier couverts (Keejob) :
- titre
- organisation_nom
- ville
- contract_type
- experience_min / experience_max
- education_level
- availability
- salary
- languages
- description
- source_item_url

---

## 2. Architecture Sprint 2 (réelle dans le code)

Pipeline complet :

Scraper -> RawOpportunite -> Processing -> Normalization -> Enrichment -> Quality Gate -> Materialization -> Opportunite -> API -> Embeddings -> Similarity

Modules clés :
- scraping/keejob_scraper.py
- scraping/pipeline.py
- scraping/normalization.py
- enrichment/text_enrichment.py
- quality/quality_gate.py
- scraping/materialization.py
- processing.py
- similarity.py
- dataset_metrics.py
- management/commands/*

---

## 3. Comment fonctionne le pipeline pour Keejob

### Étape A — Scraping détail

Le scraper Keejob lit la page listing, puis la page détail de chaque annonce.

Il extrait les champs structurés depuis la sidebar et le contenu principal :
- Type de contrat
- Expérience
- Niveau d'études
- Disponibilité
- Salaire
- Langues
- Lieu précis
- Description

### Étape B — Ingestion RAW (source de vérité)

Chaque record est stocké dans RawOpportunite avec :
- payload brut complet
- hashes de déduplication
- status de traitement (NEW / MATERIALIZED / REJECTED)

Cela garantit :
- audit
- replay
- traçabilité

### Étape C — Processing orchestré

processing.py traite les raws NEW de façon déterministe :
1. normalize_raw_opportunity
2. enrich_opportunity_text
3. evaluate_opportunity
4. materialize_opportunity

### Étape D — Normalization

La normalisation convertit le payload brut vers le modèle canonique Opportunite :
- mapping type/statut/date
- nettoyage de texte
- parsing experience range (min/max)
- mapping contract_type
- préservation d'une ville affichable (ex: Sbikha, Kairouan)

### Étape E — Enrichment

Le module enrichment ajoute des signaux NLP déterministes :
- salary fallback depuis texte
- skills
- languages_fallback
- experience_min/max et compatibilité legacy

### Étape F — Quality Gate

Le quality gate vérifie que la donnée est exploitable :
- description assez riche
- URL de détail valide
- contraintes qualité par source

### Étape G — Materialization

La matérialisation persiste dans Opportunite avec :
- déduplication canonique
- merge non destructif
- conservation des champs les plus fiables

### Étape H — API, Embeddings, Similarity

L'API DRF expose des réponses stables.

Les embeddings sont stockés en :
- embedding_vector (JSON)
- embedding_vector_pg (pgvector)

La similarité utilise :
- pgvector si activé
- fallback Python sinon

---

## 4. Problèmes réels résolus sur Keejob

### Problème 1 — contract_type manquant

Symptôme : contract_type null alors que la page affiche Type de contrat: CDI.

Correction :
- extraction renforcée du label Type de contrat dans le scraper
- fallback de normalisation sur plusieurs clés payload
- backfill des enregistrements existants

Résultat : contract_type correctement rempli sur la majorité des annonces Keejob actives.

### Problème 2 — source_item_url manquant

Symptôme : annonces sans lien source, bloquant la redirection frontend.

Correction :
- nettoyage dataset des opportunités sans source_item_url

Résultat validé :
- 0 source_item_url null
- 0 source_item_url vide

### Problème 3 — description répétée

Symptôme : blocs de description dupliqués dans certaines annonces.

Correction :
- déduplication des blocs de texte avant nettoyage ML

Résultat : descriptions plus propres et plus lisibles côté API.

### Problème 4 — perte de granularité de ville

Symptôme : ville simplifiée (ex: Kairouan au lieu de Sbikha, Kairouan).

Correction :
- conservation de la valeur de localisation détaillée
- enrichissement depuis le texte descriptif

Résultat : meilleure précision géographique pour frontend et matching.

---

## 5. Tests réalisés (Sprint 2)

Tests exécutés et validés :
- tests scraper Keejob (fixtures HTML réalistes)
- tests enrichment (salary, skills, languages, experience)
- tests API (forme de réponse, champs structurés)
- tests pipeline (processing + materialization + merge)
- validation dataset via métriques

Points de test importants :
- extraction contract_type
- parsing experience min/max
- source_item_url présent
- fallback API compatible legacy
- robustesse en cas de champs partiels

---

## 6. Métriques qualité (snapshot de validation)

Indicateurs observés :
- 0 organisation vide
- 0 ville vide
- 0 lien source null (après nettoyage)
- taux de succès pipeline proche de 100%
- coverage enrichment ~15 à 20%

Interprétation :
- le dataset Keejob est maintenant utilisable en production pour affichage et recommandation de base.

---

## 7. Version simplifiée (présentation orale, 5 à 8 points)

1. Nous avons construit un pipeline complet qui transforme des pages Keejob en données fiables.
2. Chaque annonce brute est d'abord stockée dans RawOpportunite pour audit et replay.
3. Ensuite on normalise, enrichit, contrôle la qualité, puis on matérialise dans Opportunite.
4. Nous extrayons maintenant les champs utiles au frontend: contrat, salaire, expérience, langues, localisation.
5. Nous avons corrigé trois bugs critiques: contract_type null, liens source manquants, descriptions dupliquées.
6. Les tests scraper, API, enrichment et pipeline sont passés.
7. Les embeddings sont prêts avec pgvector et fallback Python pour la similarité.
8. Le résultat est une base stable pour Sprint 3 (matching profil/CV).

---

## 8. Key Messages pour jury

### Pourquoi ce pipeline est important

Il transforme des données web instables en données produit stables, testables et exploitables par l'IA.

### Pourquoi RawOpportunite est clé

RawOpportunite garantit la traçabilité: on ne perd jamais la source, on peut auditer, rejouer, corriger sans re-scraper.

### Pourquoi pgvector est utile

pgvector permet une montée en charge de la similarité sémantique côté base, avec fallback Python pour rester robuste.

### Pourquoi séparer scraping et enrichment est intelligent

Le scraping collecte les faits bruts; l'enrichment ajoute des signaux calculés.
Cette séparation réduit les bugs, facilite les tests et simplifie le debug.

---

## 9. Conclusion

Sprint 2 (focus Keejob) est terminé avec un pipeline propre, démontrable et défendable techniquement.

Le socle est prêt pour passer à la source suivante tout en gardant la même discipline :
- ingestion traçable
- normalisation stricte
- qualité contrôlée
- API stable
- similarité prête à scaler
