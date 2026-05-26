# Plan post-soutenance - nettoyage IA et recommandation

Ce fichier sert de pense-bete pour retrouver rapidement les elements legacy, les renommages et les migrations a traiter apres la soutenance. Avant livraison finale, ne pas supprimer ces fichiers sans revalidation benchmark.

## Priorites immediates avant benchmark final

- Lancer l'enrichissement LLM complet cette nuit sur la base.
- Telecharger le CrossEncoder en cache local cette nuit.
- Regenerer les embeddings JobBERT apres enrichissement.
- Reconstruire l'index autocomplete apres enrichissement pour exposer les nouveaux skills dans le profil:
  `docker compose exec backend python manage.py rebuild_profile_autocomplete`.
- Relancer le benchmark final le matin suivant.
- Continuer l'audit `opportunities/` et `tests/` avant le benchmark final.

## Jour 1 post-soutenance

- Renommer la commande `enrich_opportunities_with_gemini` vers `enrich_opportunities_with_llm`.
- Renommer la version d'enrichissement `gemini-opportunity-enrichment-v2` vers `llm-opportunity-enrichment-v3`.
- Activer CrossEncoder proprement avec `local_files_only=True` et fallback explicite si le modele est absent.
- Centraliser la taxonomie des familles dans `backend/ai/business_families.py` comme source unique.
- Ajouter un README court pour `backend/ai/recommendation_benchmark/`.

## Jour 2-3

- Planifier la migration ESCO complete seulement apres benchmark stable.
- Creer un remplacement minimal `backend/ai/skill_storage.py` si ESCO est retire du pipeline actif.
- Remplacer progressivement les imports ESCO actifs par la couche LLM/JobBERT/taxonomie.
- Supprimer les fichiers ESCO uniquement apres tests et benchmark de non-regression.
- Archiver les commandes ESCO dans `backend/docs/archive/legacy_commands/`.
- Ajouter `devops` et `data_science` comme familles canoniques si le benchmark post-CrossEncoder confirme le besoin.

## Semaine suivante

- Automatiser le pipeline nuit via Celery beat:
  1. `enrich_opportunities_with_gemini` sur un batch de 100 nouvelles offres.
  2. `generate_jobbert_embeddings` uniquement sur les offres modifiees.
  3. `rebuild_profile_autocomplete` pour mettre a jour les suggestions profil, notamment les nouveaux skills LLM indexes.
- Preparer le deploiement Railway.app avec Groq API a la place d'Ollama si necessaire.
- Renforcer la penalite cross-family si le benchmark post-CrossEncoder confirme encore du bruit metier.
- Deplacer la configuration benchmark depuis les tests vers `backend/benchmark_inputs/`.
- Ajouter une documentation benchmark: profils, offres fixtures, metriques, seuils et interpretation.
- Auditer l'encodage UTF-8/mojibake dans `backend/opportunities/normalization/*.py`.
- Ajouter des tests avec de vraies chaines accentuees et arabes lisibles pour la normalisation.
- Corriger progressivement les alias de normalisation apres validation tests + benchmark.
- Clarifier si `backend/opportunities/core/pipeline_flow.py` devient l'orchestrateur officiel ou s'il doit etre supprime comme doublon de `processing.py`.
- Rendre publique proprement la logique importee depuis `_merge_duplicate_fields` si la commande `cleanup_linkedin_opportunities.py` reste maintenue.
- Verifier la politique `local_files_only` pour `opportunities/embeddings/service.py` afin d'eviter les telechargements surprise en production.
- Verifier si l'import legacy `SKILLS` dans `backend/opportunities/enrichment/text_enrichment.py` est encore necessaire.
- Corriger le mojibake dans `backend/opportunities/enrichment/text_enrichment.py` apres tests ciblés.
- Documenter la difference entre `opportunities/enrichment` local deterministe et `ai/llm` LLM.
- Splitter `backend/opportunities/nlp/nlp_preprocessing.py` en modules dedies: cleaning, embedding_text, classification, organization.
- Corriger le mojibake dans `backend/opportunities/nlp/*.py` avec tests NLP ciblés.
- Remplacer ou enrichir `backend/opportunities/nlp/skills.py` par une source plus propre si ESCO est retire ou remplace par taxonomie/LLM.
- Corriger le mojibake dans `backend/opportunities/extraction/profile_terms.py`.
- Documenter que `backend/opportunities/extraction/profile_terms.py` alimente l'autocomplete profil, pas le ranking final.
- Envisager de deplacer les alias de `profile_terms.py` vers des fichiers de donnees ou une taxonomie centralisee.
- Documenter le pipeline autocomplete separement du pipeline recommandation.
- Centraliser progressivement les alias skills/roles/interests aujourd'hui disperses entre extraction, autocomplete et industries.
- Ajouter des metriques autocomplete simples: suggestions actives, taux de cache, top recherches si disponibles.
- Documenter la difference entre `backend/opportunities/quality/` et `backend/ai/quality_gates.py`.
- Verifier l'usage reel de `ready_for_recommendation` sur `Opportunite`.
- Clarifier le role de `ml_text` par rapport a `prepare_combined_text`.
- Documenter `quality_score` comme score qualite de donnee, distinct du score de matching candidat.
- Decider si les alias `compute_quality_score_v3` et `compute_quality_score_v4` restent ou si on conserve seulement `compute_quality_score`.
- Externaliser eventuellement `SOURCE_RELIABILITY`, `JOB_SIGNAL_WEIGHTS` et `PROJECT_SIGNAL_WEIGHTS` vers une configuration.
- Documenter `backend/opportunities/scraping/` comme entree officielle du pipeline: source scrapers -> `RawOpportunite` -> materialisation -> embeddings -> recommandation.
- Decouper progressivement les gros scrapers `keejob.py`, `linkedin.py`, `emploitunisie.py` et `marchespublics.py` en parsing, fetch HTTP, detail extraction et mapping payload.
- Marquer LinkedIn comme source fragile/non officielle dans la documentation technique et verifier ses limites de pagination/rate-limit avant exploitation production.
- Centraliser les helpers d'environnement repetes dans les scrapers (`_get_env_int`, `_get_env_float`, `_get_env_bool`) sans changer le comportement.
- Corriger le mojibake dans `backend/opportunities/scraping/**/*.py` apres tests sources dedies.
- Conserver `backend/opportunities/scraping/PIPELINE_ARCHITECTURE.md` et l'aligner avec le document de pipeline final si le flux evolue.
- Documenter les commandes `backend/opportunities/management/commands/` par categorie: production, maintenance donnees, benchmark, diagnostic.
- Reevaluer post-livraison les commandes ponctuelles `backfill_keejob_details.py`, `cleanup_linkedin_opportunities.py`, `deduplicate_opportunities.py` et `rebalance_source_dominance.py` pour savoir si elles restent en maintenance ou vont en archive.
- Reevaluer `benchmark_embeddings.py` apres choix definitif du modele d'embedding; archiver si le benchmark modele n'est plus utile.
- Garder `benchmark_opportunity_search.py` comme outil performance tant que `backend/docs/PERFORMANCE.md` le reference.
- Ajouter une option JSON ou un README court pour les commandes de diagnostic `audit_opportunities_dataset.py`, `dataset_metrics.py` et `embedding_status.py`.
- Documenter `backend/opportunities/api/services/` comme couche queryset/search/facets de l'API publique, separee du scoring IA.
- Surveiller le cache facets: ajouter eventuellement des tests sur invalidation/version `OPPORTUNITY_FACET_CACHE_VERSION`.
- Documenter `backend/opportunities/services/scheduler_monitoring.py` comme couche monitoring scheduler, non liee au ranking IA.
- Garder `backend/opportunities/utils/` comme utilitaires partages; eviter d'y ajouter de la logique metier lourde.
- Nettoyer localement les dossiers `__pycache__/` si besoin, sans les versionner.

## Fichiers ESCO a garder avant soutenance

Ces fichiers restent actifs ou lies a la normalisation secondaire. Ne pas supprimer avant migration dediee.

- `backend/ai/esco_mapper.py`
- `backend/ai/esco_recommendation_signals.py`
- `backend/ai/esco_skill_storage.py`
- `backend/ai/esco_skill_normalization.py`
- `backend/ai/esco_skill_index.py`
- `backend/ai/esco_skill_embeddings.py`

## Fichiers ESCO a archiver post-livraison

Ces fichiers sont surtout des outils d'ingestion, recuperation ou maintenance legacy.

- `backend/ai/esco_catalog_ingestion.py`
- `backend/ai/esco_normalization_recovery.py`
- `backend/ai/skill_alias_suggestions.py`

## Donnees ESCO a archiver post-livraison

Ces fichiers ne font pas partie du pipeline principal JobBERT + LLM + taxonomie. Ils restent utiles uniquement tant que les commandes ESCO legacy existent.

- `backend/ai/data/esco/`
- `backend/ai/data/esco/raw/skills_en.csv`
- `backend/ai/data/esco/raw/skills_fr.csv`
- `backend/ai/data/esco/raw/occupations_en.csv`
- `backend/ai/data/esco/raw/occupations_fr.csv`
- `backend/ai/data/esco/raw/occupationSkillRelations_en.csv`
- `backend/ai/data/esco/raw/occupationSkillRelations_fr.csv`
- `backend/ai/data/esco/raw/skillsHierarchy_en.csv`
- `backend/ai/data/esco/raw/skillsHierarchy_fr.csv`
- `backend/ai/data/esco_occupations.json`
- `backend/ai/data/bidwise_skill_alias_review.csv`
- `backend/ai/data/bidwise_skill_aliases_seed_v1.csv`
- `backend/ai/data/bidwise_skill_aliases_seed_v2.csv`

## Commandes ESCO a archiver post-livraison

- `backend/ai/management/commands/backfill_esco_normalization.py`
- `backend/ai/management/commands/report_esco_normalization.py`
- `backend/ai/management/commands/generate_esco_skill_embeddings.py`
- `backend/ai/management/commands/import_esco_catalog.py`
- `backend/ai/management/commands/load_esco.py`
- `backend/ai/management/commands/load_bidwise_skill_aliases.py`
- `backend/ai/management/commands/suggest_skill_aliases.py`

## Commandes experimentales deja archivees

Ces commandes ont deja ete deplacees vers `backend/docs/archive/legacy_commands/`.

- `audit_cv_recommendation_benchmark.py`
- `audit_jobbert_recommendations.py`
- `benchmark_gemini_enrichment.py`
- `benchmark_recommendation_stability.py`

## Nettoyages recommandes mais non urgents

- Decouper `backend/ai/recommendation_service.py` en modules plus petits apres livraison.
- Extraire l'orchestration lourde de `backend/ai/views.py`.
- Renommer les references historiques a Gemini dans les noms de commandes et versions.
- Garder `OpenAI` comme provider optionnel dans `embeddings.py`, mais documenter que le pipeline final utilise les embeddings locaux coherents avec les offres.
- Verifier si certaines fonctions utilitaires de `user_features.py` peuvent etre simplifiees apres migration ESCO.

## Regle de securite

Avant chaque suppression post-soutenance:

1. Chercher les imports avec `rg`.
2. Lancer les tests cibles.
3. Lancer `test_profile_recommendations` sur profils critiques.
4. Relancer le benchmark global.
5. Comparer precision, noise rate, top-3 et CV uplift avant/apres.
