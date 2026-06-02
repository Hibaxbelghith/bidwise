# Enrichissement LLM des offres via Celery

Last updated: 2026-05-29

## Objectif

Le scraping collecte les offres depuis les sources externes. Certaines sources, surtout LinkedIn, fournissent parfois des descriptions longues mais peu de skills structures. L'enrichissement LLM ajoute progressivement des skills exploitables a partir de ces descriptions.

Cet enrichissement est volontairement asynchrone et offline:

- il ne bloque pas l'API;
- il ne s'execute pas pendant une recommandation utilisateur;
- il ne remplace pas le pipeline de scraping;
- il complete les donnees apres materialisation.

## Architecture Celery

Les taches lourdes sont separees par queue:

```text
celery_worker
  queue: celery
  role: scraping, materialisation, embeddings, monitoring

celery_enrichment
  queue: opportunity_enrichment
  role: backfill LLM des offres

celery_profile
  queue: profile_resume
  role: parsing CV et embeddings profil
```

Cette separation est importante parce qu'un modele local Ollama peut prendre du temps. Si le LLM partageait la queue principale, il pourrait retarder `collect_opportunities`, `collect_source`, `materialize_opportunities` ou `generate_embeddings`.

## Services Docker

Le worker dedie est declare dans `docker-compose.yml`:

```text
celery_enrichment
  command: celery -A config worker -l info -Q opportunity_enrichment --concurrency=1 --prefetch-multiplier=1
```

Le choix `concurrency=1` protege la machine locale et evite de lancer plusieurs appels LLM en parallele. Le choix `prefetch-multiplier=1` evite que le worker reserve trop de taches a l'avance.

## Routage des taches

Dans `backend/config/settings.py`, les taches LLM opportunites sont routees vers la queue dediee:

```python
CELERY_TASK_ROUTES = {
    "ai.enrich_opportunity_llm_backfill": {"queue": "opportunity_enrichment"},
    "ai.enrich_opportunity_with_llm": {"queue": "opportunity_enrichment"},
}
```

Le scraping reste sur la queue principale:

```text
opportunities.collect_opportunities
opportunities.collect_source
opportunities.materialize_opportunities
opportunities.generate_embeddings
opportunities.monitor_pipeline
```

## Tache periodique

Celery Beat peut declencher:

```text
ai.enrich_opportunity_llm_backfill
```

La tache appelle la commande existante:

```text
python manage.py enrich_opportunities_with_gemini
```

Le nom de commande contient encore `gemini` pour compatibilite historique. En pratique, le provider peut etre Ollama local selon la configuration.

## Parametres

Les principaux parametres sont:

```text
OPPORTUNITY_LLM_BACKFILL_ENABLED=true
OPPORTUNITY_LLM_BACKFILL_SOURCE=all
OPPORTUNITY_LLM_BACKFILL_LIMIT=5
OPPORTUNITY_LLM_BACKFILL_MIN_DESCRIPTION_CHARS=1000
OPPORTUNITY_LLM_BACKFILL_DELAY_SECONDS=2.0
OPPORTUNITY_LLM_BACKFILL_WORKERS=1
OPPORTUNITY_LLM_BACKFILL_LOCK_SECONDS=1800
OPPORTUNITY_LLM_BACKFILL_CRON_MINUTE=7,37
```

Ces valeurs limitent le volume traite par passage et reduisent le risque de surcharge.

## Garde-fous

Le backfill LLM ne doit pas enrichir tout le dataset sans controle. Les garde-fous actuels sont:

- uniquement les opportunites actives;
- uniquement les offres de type `EMPLOI`;
- exclusion des sources non-job comme `MarchesPublics`;
- description minimale, par defaut 1000 caracteres;
- mode `weak-skills-only` pour cibler les offres sans skills ou avec skills trop generiques;
- verrou Redis/cache `ai:opportunity_llm_backfill:lock` pour eviter deux runs simultanes;
- batch limite, par defaut 5 offres par passage.

## Verification rapide

Verifier les services:

```bash
docker compose ps
```

Verifier les queues consommees:

```bash
docker compose exec backend celery -A config inspect active_queues
```

Resultat attendu:

```text
celery_worker       -> queue celery
celery_enrichment   -> queue opportunity_enrichment
celery_profile      -> queue profile_resume
```

Verifier les taches actives:

```bash
docker compose exec backend celery -A config inspect active
```

Si le LLM tourne, il doit apparaitre sur `opportunity_enrichment`, pas sur la queue principale.

Verifier les files Redis:

```bash
docker compose exec redis redis-cli -n 0 llen celery
docker compose exec redis redis-cli -n 0 llen opportunity_enrichment
```

La queue `celery` ne doit pas se remplir a cause du LLM.

## Audit des donnees

Verifier la couverture par source:

```bash
docker compose exec backend python manage.py shell -c "from opportunities.models import Opportunite; from django.db.models import Count; qs=Opportunite.objects.select_related('source'); [print(row['source__nom'], 'total', row['total'], 'skills', qs.filter(source__nom=row['source__nom']).exclude(skills=[]).count(), 'llm', qs.filter(source__nom=row['source__nom'], extra_data__llm_enrichment__isnull=False).count()) for row in qs.values('source__nom').annotate(total=Count('id')).order_by('source__nom')]"
```

Interpretation:

- `Keejob`, `EmploiTunisie`, `LinkedIn` peuvent avoir des skills enrichis.
- `MarchesPublics` doit rester hors enrichissement LLM opportunite.
- LinkedIn peut progresser lentement car ses descriptions detaillees sont plus longues a recuperer et enrichir.

## Test sans appel LLM

Avant de lancer un vrai enrichissement, utiliser le mode audit:

```bash
docker compose exec backend python manage.py enrich_opportunities_with_gemini --source all --weak-skills-only --min-description-chars 1000 --limit 10 --audit --json
```

Ce mode ne consomme pas le LLM. Il montre seulement les candidats selectionnes.

## Message pour la soutenance

L'enrichissement LLM est un traitement de qualite de donnees en arriere-plan. Il est separe du scraping par une queue Celery dediee. Ainsi, meme si le modele local est lent, la collecte des offres, la materialisation et les embeddings continuent de fonctionner. Le systeme reste observable via Celery inspect, Redis, `PipelineRun`, les logs et le dashboard admin.
