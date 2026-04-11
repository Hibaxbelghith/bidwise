# Architecture Pipeline BidWise (version débutant)

## 1. But du pipeline

Le pipeline transforme des annonces externes en données fiables pour BidWise.

Objectifs :
- garder la donnée source brute pour audit et replay
- normaliser de façon déterministe
- matérialiser des opportunités utilisables par le produit
- mesurer la santé du pipeline avec des métriques

---

## 2. Vue simple des couches

1. Couche scraping
- collecte des dictionnaires bruts depuis les sites externes

2. Couche raw ingestion (RawOpportunite)
- stocke le payload complet
- ajoute les métadonnées d'ingestion (hash, fingerprint, seen_count, status)

3. Couche normalisation (normalization.py)
- mapping canonique des champs
- parsing des dates
- validation stricte
- pas de NLP ici

4. Couche matérialisation (materialization.py)
- persistance dans Opportunite
- déduplication canonique
- update_or_create transactionnel

5. Couche orchestration (processing.py)
- traitement batch des raw NEW
- transitions d'état sûres
- isolement des erreurs par record

6. Couche métriques (dataset_metrics.py)
- calcul de backlog, succès, rejet, etc.

---

## 3. Flux bout en bout

1. Un scraper collecte des records
2. Chaque record est stocké dans RawOpportunite (status NEW)
3. process_pending_raw_opportunities récupère les NEW par ordre id asc
4. normalize_raw_opportunity produit un dict canonique
5. materialize_opportunity crée/met à jour Opportunite
6. Succès:
- status raw -> MATERIALIZED
- lien canonical défini si vide
- processed_at défini si vide
7. Erreur validation ou traitement:
- status raw -> REJECTED
- validation_errors enrichi
- payload brut conservé

---

## 4. Schéma ASCII

Sources externes
      |
      v
Scrapers
      |
      v
RawOpportunite (status=NEW)
      |
      v
process_pending_raw_opportunities
      |
      +--> process_raw_opportunity
               |
               +--> normalize_raw_opportunity
               |      (mapping + validation)
               |
               +--> materialize_opportunity
                      (persistence Opportunite)

Succès:
RawOpportunite -> MATERIALIZED -> Opportunite liée

Erreur:
RawOpportunite -> REJECTED -> validation_errors mis à jour

Monitoring:
compute_pipeline_metrics -> indicateurs opérationnels

---

## 5. États du pipeline

NEW
- record brut en attente de traitement

MATERIALIZED
- record brut traité avec succès et persistance canonique ok

REJECTED
- record brut rejeté (validation ou erreur inattendue)
- non supprimé, traçable et rejouable

VALIDATED
- état intermédiaire existant dans l'énumération (prévu pour extensions futures)

---

## 6. Déduplication et idempotence

Priorité des clés d'identité raw :
- source_record_id (si disponible)
- sinon source_item_url
- sinon fallback payload_hash (best effort)

Conséquence importante :
- Created augmente seulement pour une nouvelle identité
- Updated augmente quand une identité déjà connue est revue

Donc "Created: 0, Updated: 15" est un comportement normal (pas un bug).

---

## 7. Rôle de pgvector dans l'architecture

Opportunite stocke 2 formats d'embedding :
- embedding_vector (JSON)
- embedding_vector_pg (VectorField pgvector, 384 dimensions)

Recherche similarité :
- mode pgvector activable via OPPORTUNITY_PGVECTOR_ENABLED
- sinon fallback Python (cosine in-memory)

Bénéfice :
- préparation à la montée en charge sans rupture fonctionnelle

---

## 8. Commandes utiles

Depuis le dossier backend :

1. Collecte
```bash
python manage.py collect_opportunities --source keejob
```

2. Traitement raw en attente
```bash
python manage.py shell -c "from opportunities.processing import process_pending_raw_opportunities; print(process_pending_raw_opportunities(limit=100))"
```

3. Métriques pipeline
```bash
python manage.py shell -c "from opportunities.dataset_metrics import compute_pipeline_metrics; print(compute_pipeline_metrics())"
```

4. Génération embeddings
```bash
python manage.py generate_embeddings --batch-size 32
```

---

## 9. Mini FAQ opérationnelle

Pourquoi processed=0 parfois ?
- parce qu'il n'y a plus de NEW (backlog vide)

Pourquoi total_raw ne monte pas à chaque collecte ?
- parce que la collecte met à jour des records existants (idempotence)

Pourquoi garder les records REJECTED ?
- pour audit, correction des règles, puis replay

---

## 10. Résultat opérationnel

Ce pipeline donne à BidWise :
- une ingestion robuste et rejouable
- une traçabilité complète des erreurs
- des états de traitement clairs
- des métriques exploitables
- une base prête pour le moteur de recommandation IA de Sprint 3