from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from ai.jobbert import generate_jobbert_embeddings_batch, jobbert_model_name
from ai.embeddings import get_cached_profile_embedding_or_enqueue
from ai.retrieval import retrieve_recommendation_candidates
from opportunities.models import Opportunite, StatutOpportunite
from opportunities.nlp.nlp_preprocessing import prepare_combined_text
from users.models import Profil


class Command(BaseCommand):
    help = "Generate local JobBERT embeddings for opportunities without touching pgvector embeddings."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--source", default="all")
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--batch-size", type=int, default=16)
        parser.add_argument("--max-text-chars", type=int, default=2200)
        parser.add_argument(
            "--profile-id",
            type=int,
            default=None,
            help="Generate embeddings for the semantic candidate pool of one profile.",
        )
        parser.add_argument(
            "--ids",
            default="",
            help="Comma-separated opportunity ids to embed explicitly.",
        )
        parser.add_argument(
            "--segment",
            default="",
            choices=["", "accounting-finance-audit", "it-dev", "industry-methods"],
            help="Generate embeddings for a curated business segment.",
        )

    def handle(self, *args, **options):
        limit = max(1, min(int(options.get("limit") or 100), 5000))
        source_name = str(options.get("source") or "all").strip()
        force = bool(options.get("force"))
        batch_size = max(1, int(options.get("batch_size") or 16))
        max_text_chars = max(500, int(options.get("max_text_chars") or 2200))
        profile_id = options.get("profile_id")
        raw_ids = str(options.get("ids") or "").strip()
        segment = str(options.get("segment") or "").strip()
        model_name = jobbert_model_name()

        base_queryset = Opportunite.objects.filter(statut=StatutOpportunite.ACTIVE).select_related("source")
        if source_name and source_name.casefold() != "all":
            base_queryset = base_queryset.filter(source__nom__iexact=source_name)
        if segment == "accounting-finance-audit":
            base_queryset = base_queryset.filter(type_opportunite="EMPLOI").filter(
                Q(titre__icontains="comptable")
                | Q(titre__icontains="accountant")
                | Q(titre__icontains="accounting")
                | Q(titre__icontains="auditeur")
                | Q(titre__icontains="audit")
                | Q(titre__icontains="finance")
                | Q(titre__icontains="financier")
                | Q(titre__icontains="contrôleur de gestion")
                | Q(titre__icontains="controleur de gestion")
                | Q(titre__icontains="consolidation")
                | Q(titre__icontains="payroll")
                | Q(extra_data__company_sector__icontains="comptabilité")
                | Q(extra_data__company_sector__icontains="audit")
                | Q(extra_data__company_sector__icontains="finance")
                | Q(extra_data__company_sector__icontains="banque")
                | Q(skills__icontains="Comptabilité")
                | Q(skills__icontains="Finance")
                | Q(skills__icontains="Audit")
                | Q(description__icontains="comptabilit")
                | Q(description__icontains="rapprochement bancaire")
                | Q(description__icontains="factures fournisseurs")
                | Q(description__icontains="declarations fiscales")
                | Q(description__icontains="dÃ©clarations fiscales")
                | Q(description__icontains="audit")
                | Q(description__icontains="finance")
            ).distinct()
        elif segment == "it-dev":
            base_queryset = base_queryset.filter(type_opportunite="EMPLOI").filter(
                Q(titre__icontains="developer")
                | Q(titre__icontains="développeur")
                | Q(titre__icontains="developpeur")
                | Q(titre__icontains="frontend")
                | Q(titre__icontains="front-end")
                | Q(titre__icontains="backend")
                | Q(titre__icontains="back-end")
                | Q(titre__icontains="fullstack")
                | Q(titre__icontains="full-stack")
                | Q(titre__icontains="software")
                | Q(titre__icontains="web")
                | Q(titre__icontains="javascript")
                | Q(titre__icontains="python")
                | Q(titre__icontains="django")
                | Q(titre__icontains="react")
                | Q(titre__icontains="node")
                | Q(titre__icontains="java")
                | Q(titre__icontains=".net")
                | Q(titre__icontains="php")
                | Q(titre__icontains="informatique")
                | Q(titre__icontains="devops")
                | Q(titre__icontains="sre")
                | Q(titre__icontains="qa engineer")
                | Q(titre__icontains="software tester")
                | Q(titre__icontains="testeur logiciel")
                | Q(titre__icontains="wordpress")
                | Q(titre__icontains="sharepoint")
                | Q(titre__icontains="sap developer")
                | Q(skills__icontains="Python")
                | Q(skills__icontains="Django")
                | Q(skills__icontains="FastAPI")
                | Q(skills__icontains="React")
                | Q(skills__icontains="JavaScript")
                | Q(skills__icontains="Typescript")
                | Q(skills__icontains="TypeScript")
                | Q(skills__icontains="Node")
                | Q(skills__icontains="Java")
                | Q(skills__icontains="PHP")
                | Q(skills__icontains="HTML")
                | Q(skills__icontains="CSS")
                | Q(description__icontains="frontend")
                | Q(description__icontains="front-end")
                | Q(description__icontains="backend")
                | Q(description__icontains="back-end")
                | Q(description__icontains="fullstack")
                | Q(description__icontains="full-stack")
                | Q(description__icontains="React")
                | Q(description__icontains="JavaScript")
                | Q(description__icontains="TypeScript")
                | Q(description__icontains="Node.js")
                | Q(description__icontains="Python")
                | Q(description__icontains="Django")
                | Q(description__icontains="FastAPI")
                | Q(description__icontains="API REST")
                | Q(description__icontains="HTML")
                | Q(description__icontains="CSS")
                | Q(extra_data__company_sector__icontains="informatique")
                | Q(extra_data__company_sector__icontains="internet")
                | Q(extra_data__company_sector__icontains="telecom")
            ).distinct()
        elif segment == "industry-methods":
            base_queryset = base_queryset.filter(type_opportunite="EMPLOI").filter(
                Q(titre__icontains="technicien")
                | Q(titre__icontains="methodes")
                | Q(titre__icontains="mÃ©thodes")
                | Q(titre__icontains="industrialisation")
                | Q(titre__icontains="production")
                | Q(titre__icontains="qualit")
                | Q(titre__icontains="maintenance")
                | Q(skills__icontains="Lean")
                | Q(skills__icontains="Production")
                | Q(skills__icontains="Qualit")
                | Q(skills__icontains="Maintenance")
                | Q(description__icontains="methodes")
                | Q(description__icontains="mÃ©thodes")
                | Q(description__icontains="amelioration continue")
                | Q(description__icontains="amÃ©lioration continue")
                | Q(description__icontains="gammes de fabrication")
                | Q(description__icontains="procedes industriels")
                | Q(description__icontains="procÃ©dÃ©s industriels")
                | Q(description__icontains="chronometrage")
                | Q(description__icontains="chronomÃ©trage")
                | Q(description__icontains="lean")
                | Q(description__icontains="production")
                | Q(description__icontains="qualit")
                | Q(description__icontains="maintenance")
                | Q(description__icontains="industrialisation")
                | Q(extra_data__company_sector__icontains="industrie")
                | Q(extra_data__company_sector__icontains="industri")
                | Q(extra_data__company_sector__icontains="mecanique")
                | Q(extra_data__company_sector__icontains="mÃ©canique")
            ).distinct()

        explicit_ids = []
        if raw_ids:
            for item in raw_ids.split(","):
                try:
                    explicit_ids.append(int(item.strip()))
                except (TypeError, ValueError):
                    continue

        if explicit_ids:
            queryset = list(base_queryset.filter(id__in=explicit_ids))
            queryset.sort(key=lambda opportunity: explicit_ids.index(opportunity.id))
        elif profile_id:
            profile = Profil.objects.get(pk=profile_id)
            user_embedding = get_cached_profile_embedding_or_enqueue(profile)
            queryset = retrieve_recommendation_candidates(
                user_embedding,
                base_queryset,
                limit,
                embedding_model=getattr(profile, "embedding_model", ""),
            )
        else:
            queryset = (
                base_queryset
                .only(
                    "id",
                    "titre",
                    "description",
                    "organisation_nom",
                    "ville",
                    "contract_type",
                    "normalized_contract_types",
                    "experience_min",
                    "experience_max",
                    "experience_years",
                    "education_level",
                    "availability",
                    "normalized_work_mode",
                    "normalized_schedule",
                    "salary",
                    "skills",
                    "raw_skills",
                    "normalized_skills",
                    "normalized_industries",
                    "languages",
                    "languages_fallback",
                    "extra_data",
                    "type_opportunite",
                    "jobbert_embedding_vector",
                    "jobbert_embedding_model",
                    "jobbert_embedding_updated_at",
                    "source__nom",
                )
                .order_by("-date_publication", "-id")
            )
            if not force:
                queryset = queryset.exclude(jobbert_embedding_vector__isnull=False, jobbert_embedding_model=model_name)

        candidates = []
        texts = []
        iterable = queryset if isinstance(queryset, list) else queryset.iterator(chunk_size=200)
        for opportunity in iterable:
            if (
                not force
                and opportunity.jobbert_embedding_vector
                and opportunity.jobbert_embedding_model == model_name
            ):
                continue
            text = " ".join(prepare_combined_text(opportunity).split())
            if max_text_chars and len(text) > max_text_chars:
                text = text[:max_text_chars].rstrip()
            if not text:
                continue
            candidates.append(opportunity)
            texts.append(text)
            if len(candidates) >= limit:
                break

        total = len(candidates)
        if total <= 0:
            self.stdout.write("No JobBERT opportunity embeddings to generate.")
            return

        self.stdout.write(f"Generating JobBERT embeddings model={model_name} total={total} batch_size={batch_size}")
        updated = 0
        errors = 0
        for start in range(0, total, batch_size):
            batch_opportunities = candidates[start:start + batch_size]
            batch_texts = texts[start:start + batch_size]
            try:
                vectors = generate_jobbert_embeddings_batch(
                    batch_texts,
                    model_name=model_name,
                    batch_size=batch_size,
                )
            except Exception as exc:  # noqa: BLE001 - batch command should continue
                errors += len(batch_opportunities)
                self.stderr.write(f"Batch failed start={start}: {exc}")
                continue

            now = timezone.now()
            rows = []
            for opportunity, vector in zip(batch_opportunities, vectors):
                opportunity.jobbert_embedding_vector = vector
                opportunity.jobbert_embedding_model = model_name
                opportunity.jobbert_embedding_updated_at = now
                rows.append(opportunity)

            Opportunite.objects.bulk_update(
                rows,
                fields=["jobbert_embedding_vector", "jobbert_embedding_model", "jobbert_embedding_updated_at"],
                batch_size=batch_size,
            )
            updated += len(rows)
            self.stdout.write(f"Processed {min(start + batch_size, total)}/{total}...")

        self.stdout.write(self.style.SUCCESS("JobBERT opportunity embeddings completed."))
        self.stdout.write(f"Updated: {updated}")
        self.stdout.write(f"Errors: {errors}")
