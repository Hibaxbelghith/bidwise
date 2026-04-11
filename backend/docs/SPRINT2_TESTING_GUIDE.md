# Sprint 2 — Testing Guide (Focus Keejob)

Objectif : démontrer le pipeline Sprint 2 en live en 3 minutes, de la collecte à l'API.

---

## 1. Pré-requis

Depuis la racine du projet :

- Lancer les services
  docker compose up -d

- Vérifier l'état
  docker compose ps

Attendu :
- backend en état Up
- db en état healthy

---

## 2. Script de démo live (3 minutes)

### Étape 1 — Lancer la collecte Keejob

docker compose run --rm backend python manage.py collect_opportunities --source keejob

Attendu :
- Created ou Updated > 0
- pas de crash

### Étape 2 — Traiter les raws NEW vers canonique

docker compose run --rm backend python manage.py shell -c "from opportunities.processing import process_pending_raw_opportunities; print(process_pending_raw_opportunities(limit=500))"

Attendu :
- materialized > 0
- errors = 0 (ou très faible)

### Étape 3 — Vérifier les métriques pipeline

docker compose run --rm backend python manage.py shell -c "from opportunities.dataset_metrics import compute_pipeline_metrics; print(compute_pipeline_metrics())"

Attendu :
- backlog raisonnable
- success rate élevé

### Étape 4 — Vérifier une annonce Keejob clé

docker compose run --rm backend python manage.py shell -c "from rest_framework.test import APIClient; c=APIClient(); r=c.get('/api/opportunities/4996/', SERVER_NAME='localhost'); print({'status': r.status_code, 'contract_type': r.data.get('contract_type'), 'ville': r.data.get('ville'), 'salary': r.data.get('salary'), 'experience': r.data.get('experience')})"

Attendu :
- status = 200
- contract_type non null (ex: CDI)
- ville détaillée
- expérience structurée

---

## 3. Commandes de tests Sprint 2 validés

## 3.1 Tests scraping Keejob

docker compose run --rm backend python manage.py test tests.test_scrapers

Vérifie :
- extraction HTML simulée réaliste
- contrat, salaire, langues, localisation
- robustesse extraction sidebar/detail
- déduplication description

## 3.2 Tests pipeline + API + enrichment

docker compose run --rm backend python manage.py test opportunities.tests

Vérifie :
- enrichment salary/skills/languages/experience
- shape API (experience min/max)
- materialization et merge
- comportement fallback legacy

## 3.3 Tests ciblés ensemble

docker compose run --rm backend python manage.py test tests.test_scrapers opportunities.tests

---

## 4. Vérifications de qualité de données (Keejob)

## 4.1 Vérifier qu'il ne reste pas d'opportunités sans source_item_url

docker compose run --rm backend python manage.py shell -c "from opportunities.models import Opportunite; print({'null': Opportunite.objects.filter(source_item_url__isnull=True).count(), 'empty': Opportunite.objects.filter(source_item_url='').count()})"

Attendu :
- null = 0
- empty = 0

## 4.2 Vérifier les champs critiques manquants

docker compose run --rm backend python manage.py shell -c "from opportunities.models import Opportunite; qs=Opportunite.objects.filter(source__nom__iexact='Keejob'); print({'organisation_empty': qs.filter(organisation_nom='').count(), 'ville_empty': qs.filter(ville='').count(), 'contract_empty': qs.filter(contract_type='').count()})"

Attendu :
- organisation_empty proche de 0
- ville_empty proche de 0
- contract_empty faible

## 4.3 Audit dataset

docker compose run --rm backend python manage.py audit_opportunities_dataset

Attendu :
- cohérence globale dataset
- pas d'anomalies critiques

---

## 5. Endpoints API à tester

- Liste opportunités
  GET /api/opportunities/

- Détail opportunité
  GET /api/opportunities/{id}/

- Similarité
  GET /api/opportunities/{id}/similar/?k=5

- Sources
  GET /api/sources/

- Métriques pipeline (auth requise)
  GET /api/metrics/pipeline/

---

## 6. Exemples curl

- Liste opportunités
  curl -X GET http://localhost:8000/api/opportunities/

- Détail annonce
  curl -X GET http://localhost:8000/api/opportunities/4996/

- Similarité
  curl -X GET "http://localhost:8000/api/opportunities/4996/similar/?k=5"

- Sources
  curl -X GET http://localhost:8000/api/sources/

- Pipeline metrics (avec token JWT)
  curl -X GET http://localhost:8000/api/metrics/pipeline/ -H "Authorization: Bearer <ACCESS_TOKEN>"

---

## 7. Démonstration conseillée devant jury (chrono)

Minute 1 : collect + processing
- collect_opportunities keejob
- process_pending_raw_opportunities

Minute 2 : preuve qualité
- pipeline metrics
- vérification no null source_item_url
- vérification record 4996

Minute 3 : preuve produit
- GET /api/opportunities/4996/
- montrer contract_type, ville détaillée, experience min/max
- GET similar pour montrer la couche IA prête

---

## 8. Messages à dire pendant la démo

- Nous avons séparé acquisition brute et intelligence métier.
- RawOpportunite garantit audit, replay et robustesse.
- Le pipeline garde la qualité même quand le HTML source évolue.
- L'API est stable pour frontend et prête pour Sprint 3.
- pgvector prépare la montée en charge sans casser l'existant (fallback Python).