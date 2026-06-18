# Sprint 3 - Cas de demo recommandations IA

Ce document prepare les scenarios a montrer pendant la soutenance pour expliquer la qualite des recommandations BidWise.

L'objectif est de montrer deux comportements importants:

- `Strong matches`: offres fortement alignees avec le profil, le CV et les preferences.
- `Related opportunities`: offres proches mais avec une preuve incomplete ou une incertitude qui necessite une verification humaine.

## Profil de demo Comptable Junior

Compte utilise:

```text
hibabelg7@gmail.com
```

Profil candidat:

- Role cible: `Comptable Junior`.
- Experience: `JUNIOR`, 2 ans.
- Localisations: Tunis, Sousse, Sfax.
- Contrats: CDI, CDD, SIVP.
- Secteur: `Comptabilite / Gestion / Audit`.
- Competences profil/CV: comptabilite generale, saisie comptable, rapprochements bancaires, declarations fiscales, Excel, Sage Comptabilite, Ciel Compta, ERP.

Ce profil est utile pour la soutenance parce qu'il permet de montrer:

- des `Strong matches` comptables directs;
- un cas `Related` plus senior pour prouver l'anti-faux-positif;
- un cas `Related` metier voisin pour montrer que le systeme separe domaine proche et metier exact.

### Mise au point importante avant demo

Pour ce profil, les trois offres comptables principales ont ete regenerees avec JobBERT:

```powershell
docker compose exec backend python manage.py generate_jobbert_embeddings --ids 5714,810,5283 --force --batch-size 1
```

Apres regeneration:

- `INTERNATIONAL GLOBAL ACCOUNTING SEVICES` est remontee en tete;
- `CMR AUDIT` est restee forte et tres propre;
- `HAMADI ABID - Assistant controle de gestion` est descendu en `Related`;
- les offres plus seniors comme `Vneuron` sont restees en `Related`.

Ce point est defendable techniquement:

> Le classement a change apres regeneration des embeddings JobBERT parce que certaines offres utilisaient encore l'ancien embedding generaliste. Une fois toutes les offres comparees avec le meme modele metier specialise emploi, le ranking devient plus coherent.

### Preuves techniques a citer au jury

Ce cas comptable est utile parce qu'il permet de montrer que le moteur n'est pas une simple recherche par mots-cles.

Les preuves les plus solides sont les suivantes:

1. `JobBERT a un effet mesurable sur le ranking`
   - commande rejouee:

   ```powershell
   docker compose exec backend python manage.py generate_jobbert_embeddings --ids 5714,810,5283 --force --batch-size 1
   ```

   - effet observe:
     - `INTERNATIONAL GLOBAL ACCOUNTING SEVICES` est passee de `67%` a `77%`;
     - le top Strong a change apres regeneration des embeddings;
     - cela prouve que la composante semantique metier n'est pas decorative.

2. `Le systeme sait separer metier exact et domaine proche`
   - `HAMADI ABID - Assistant controle de gestion` reste visible mais descend en `Related`;
   - `Vneuron - Comptable Confirmee` reste visible mais ne passe pas en `Strong`;
   - cela prouve qu'on ne fait pas une simple egalite sur le mot `finance` ou `Excel`.

3. `Les quality gates sont testes automatiquement`
   - fichier principal: [test_recommendation_quality_gates.py](/d:/Documents/BidWise/backend/tests/test_recommendation_quality_gates.py)
   - exemples de tests a citer par ordre de force:
     - `test_accounting_profile_keeps_management_control_role_in_related` ([test_recommendation_quality_gates.py](/d:/Documents/BidWise/backend/tests/test_recommendation_quality_gates.py:807))
       - miroir direct du cas `HAMADI ABID - Assistant controle de gestion`
       - assertion cle: `RELATED_REVIEW`
       - raison attendue: `Relevant finance role, but accounting evidence needs review`
     - `test_bucket_keeps_confirmed_accountant_in_review_despite_skill_evidence` ([test_recommendation_quality_gates.py](/d:/Documents/BidWise/backend/tests/test_recommendation_quality_gates.py:349))
       - miroir mecanique du cas `Vneuron - Comptable Confirmee`
       - assertion cle: une offre comptable confirmee avec preuves de skills reste en `RELATED_REVIEW` en presence d'un `hierarchy gap`
     - `test_isolated_excel_match_has_lower_score_than_comptable_role` ([test_recommendation_quality_gates.py](/d:/Documents/BidWise/backend/tests/test_recommendation_quality_gates.py:1066))
       - utile pour defendre `INTERNATIONAL` et `CMR AUDIT`
       - assertion cle: un simple match `Excel` est moins bien classe qu'un vrai role `Comptable`
     - `test_filter_orders_close_strong_matches_by_source_quality` ([test_recommendation_quality_gates.py](/d:/Documents/BidWise/backend/tests/test_recommendation_quality_gates.py:117))
       - utile pour expliquer le tri de presentation quand plusieurs `Strong` sont proches
       - assertion cle: une offre `Keejob` peut passer devant une offre `LinkedIn` proche en score brut
   - ce groupe de tests montre que le classement final depend d'un arbitrage metier explicable, pas seulement d'un score brut ou d'un simple mot-cle.

4. `La couche semantique JobBERT est elle aussi testee`
   - fichier: [test_user_recommendations.py](/d:/Documents/BidWise/backend/tests/test_user_recommendations.py)
   - tests utiles a montrer:
     - `test_jobbert_bonus_is_added_when_enabled`
     - `test_jobbert_and_title_skill_evidence_lift_backend_django_out_of_skill_only_cap`
     - `test_python_docker_ai_role_stays_capped_without_backend_title_evidence`
   - ces tests prouvent que JobBERT peut faire monter une offre quand le sens metier est bon, mais qu'il ne suffit pas a lui seul quand le role cible n'est pas confirme.

5. `Un test de mecanisme pur prouve la penalite anti-faux-positif`
   - test: `test_clear_devops_profile_strictly_penalizes_accounting_family` ([test_recommendation_quality_gates.py](/d:/Documents/BidWise/backend/tests/test_recommendation_quality_gates.py:1184))
   - c'est un test plus abstrait, mais tres fort techniquement:
     - meme titre
     - meme description
     - memes skills
     - seule la `business_family` change
   - assertions cles:
     - penalite exacte `0.15`
     - ecart de score garanti `>= 0.15`
   - ce test ne reproduit pas litteralement `Vneuron`, mais il prouve mathematiquement qu'une famille metier incompatible est penalisee par le moteur.

6. `Le comportement est rejouable par benchmark`
   - artefacts existants dans [backend/benchmark_reports](/d:/Documents/BidWise/backend/benchmark_reports):
     - [reco_comptable_after_jobbert.json](/d:/Documents/BidWise/backend/benchmark_reports/reco_comptable_after_jobbert.json)
     - [reco_source_priority_validation.json](/d:/Documents/BidWise/backend/benchmark_reports/reco_source_priority_validation.json)
     - [reco_source_balanced_validation.json](/d:/Documents/BidWise/backend/benchmark_reports/reco_source_balanced_validation.json)
     - [reco_final_demo_profiles.json](/d:/Documents/BidWise/backend/benchmark_reports/reco_final_demo_profiles.json)
   - ces fichiers permettent de montrer l'evolution du moteur apres calibration, priorisation des sources et regeneration JobBERT.

### Comment presenter ces preuves

Phrase courte et defendable:

> BidWise utilise un moteur hybride. JobBERT apporte la similarite semantique metier, puis des signaux explicables et des quality gates verifient le role, les competences coeur, l'experience, la source et les cas de faux positifs. Les tests automatiques et les benchmarks montrent que JobBERT change reellement le classement, mais qu'il reste controle par des regles metier explicables.

Si le jury demande une preuve plus precise:

> Pour HAMADI, nous avons un test miroir exact qui force `Assistant controle de gestion` a rester en `Related` pour un profil `Comptable`. Pour Vneuron, nous avons un test de meme logique sur `Comptable Confirme`, plus un test mecanique qui mesure numeriquement la penalite de famille metier incompatible.

### Preuves a montrer absolument

Pour la soutenance, il ne faut pas tout montrer. Les 4 preuves les plus utiles sont:

1. `Preuve UI metier`
   - montrer dans l'interface:
     - `INTERNATIONAL` en `Strong`
     - `CMR AUDIT` en `Strong`
     - `Vneuron` en `Related`
     - `HAMADI controle de gestion` en `Related`
   - c'est la preuve visible que le moteur separe recommandation forte, cas senior, et domaine voisin.

2. `Preuve technique score + bucket`
   - montrer le mini tableau suivant extrait du benchmark:

   | Offre | Final score | JobBERT | Bucket | Raison |
   | --- | ---: | ---: | --- | --- |
   | INTERNATIONAL | 88.87 | 75.07 | Strong | Strong role and semantic evidence |
   | CMR AUDIT | 74.81 | 62.26 | Strong | Strong role and semantic evidence |
   | Vneuron | 68.00 | 48.33 | Related | Slight hierarchy gap; keep as reviewable |

   - c'est la meilleure preuve que la decision finale ne repose pas seulement sur un pourcentage UI.

3. `Preuve test miroir`
   - montrer surtout:
     - `test_accounting_profile_keeps_management_control_role_in_related`
     - `test_bucket_keeps_confirmed_accountant_in_review_despite_skill_evidence`
   - c'est la preuve que les deux comportements critiques observes a l'ecran sont verrouilles automatiquement.

4. `Preuve avant / apres JobBERT`
   - montrer qu'apres regeneration JobBERT, `INTERNATIONAL` remonte clairement dans le classement
   - message simple:

   > Le classement change apres mise a jour de la couche semantique metier. Donc le moteur ne se limite pas a une regle statique ou a un simple matching par mots-cles.

Si tu dois etre tres concise devant le jury, garde seulement ces 4 preuves.

Important:

- ne pas dire `intelligence magique`;
- ne pas dire `100% automatique et parfait`;
- dire plutot `hybride`, `explicable`, `teste`, `rejouable`, `anti-faux-positif`.

### Commandes de validation a citer

Tests:

```powershell
docker compose exec backend python manage.py test tests.test_recommendation_quality_gates --keepdb
docker compose exec backend python manage.py test tests.test_user_recommendations --keepdb
```

Benchmark demo:

```powershell
docker compose exec backend python manage.py benchmark_final_recommendation_profiles --profiles comptable_junior,it_helpdesk,maintenance_technician,quality_controller,sales_representative --top 30 --candidate-limit 2500 --rerank-candidates 250 --output-json /app/benchmark_reports/reco_final_demo_profiles.json
```

### Ce qu'on peut honnêtement dire sur les fichiers before/after

Il existe deja des artefacts `after` tres utiles et partageables dans `backend/benchmark_reports`, surtout pour la calibration finale et le cas comptable apres JobBERT.

En revanche, il n'existe pas encore dans le repo un unique couple de fichiers officiellement nommes `before` et `after` pour le seul profil comptable. Donc la formulation la plus honnete est:

> Nous avons plusieurs benchmarks intermediaires et un benchmark final versionne dans le repo. Ils permettent de montrer l'evolution du moteur avant et apres calibration. Pour le cas comptable, l'effet le plus net est visible apres regeneration JobBERT.

### Cas 1 - Strong Match: INTERNATIONAL GLOBAL ACCOUNTING SEVICES

Offre:

```text
INTERNATIONAL GLOBAL ACCOUNTING SEVICES - Comptable
Score: 77%
Bucket: Strong Match
Source: Keejob
Contrat: SIVP
Experience: 1-2 ans
```

Pourquoi c'est le meilleur cas:

- titre exact `Comptable`;
- role extrait `Comptable Junior`;
- experience `1-2 ans` parfaitement alignee avec le profil;
- contrat `SIVP` coherent avec un profil junior;
- secteur `comptabilite / gestion / audit`;
- skills comptables coeur metier: `Saisie comptable`, `Controle comptable`, `Declarations fiscales`, `Declarations sociales`, `Bilans`, `Etats financiers`, `Excel`.

Ce que ce cas permet de dire au jury:

> C'est l'exemple le plus propre du moteur. Le role est exact, l'experience est compatible, la source est structuree et les competences metier sont nombreuses. Le score fort est donc defendable.

Detail technique utile si le jury pousse:

- cette offre avait un embedding generaliste mais pas encore d'embedding JobBERT;
- apres regeneration JobBERT, elle est passee de `67%` a `77%`;
- cela confirme que la qualite semantique depend aussi de la couverture effective des embeddings metier.

### Cas 2 - Strong Match: CMR AUDIT

Offre:

```text
CMR AUDIT - Comptables
Score: 72%
Bucket: Strong Match
Source: Keejob
Contrat: CDI
Experience: 1-2 ans
```

Pourquoi c'est un cas tres propre:

- cabinet d'expertise comptable;
- titre comptable direct;
- experience `1-2 ans` exactement compatible;
- skills visibles: `Saisie comptable`, `Declarations fiscales`, `Suivi de dossiers clients`, `Revision comptable`, `Logiciels comptables`.

Ce que ce cas montre:

- le moteur ne favorise pas seulement le titre;
- il reconnait aussi les missions d'un cabinet comptable classique;
- le score est un peu sous `INTERNATIONAL` car le score final combine semantic + signaux metier + qualite de l'offre, pas seulement le titre.

Phrase de defense:

> CMR AUDIT est probablement l'offre la plus intuitive pour un expert comptable humain. Son classement en deuxieme position reste logique et defendable.

### Cas 3 - Related Review: Vneuron Risk & Compliance

Offre:

```text
Vneuron Risk & Compliance - Comptable Confirmee
Score: 66%
Bucket: Related Review
Source: LinkedIn
Experience: 3 ans
```

Pourquoi c'est un excellent cas defensif:

- l'offre partage beaucoup de competences comptables: `Comptabilite generale`, `Comptabilite analytique`, `Saisie comptable`, `Declarations fiscales`, `Reporting`, `ERP`, `Excel`;
- elle a donc un bon score et reste visible;
- pourtant elle ne passe pas en `Strong`.

Pourquoi elle reste en `Related`:

- le titre implique un niveau plus confirme;
- l'experience minimale `3 ans` est au-dessus du profil a `2 ans`;
- l'UI affiche `Experience level above current profile`.

Phrase de defense:

> Ce cas prouve que BidWise ne transforme pas automatiquement une offre riche en skills en fausse recommandation forte. Le systeme garde l'offre visible, mais refuse de la sur-promettre au candidat.

### Cas 4 - Related Review: HAMADI ABID - Assistant controle de gestion

Offre:

```text
HAMADI ABID - Assistant controle de gestion
Score: 63%
Bucket: Related Review
Source: Keejob
Experience: 2-5 ans
```

Pourquoi ce cas est important:

- il appartient a une famille proche `finance / gestion`;
- il contient `Excel`, `reporting`, `KPI`, `budget`, `analyse de performance`;
- avant calibration, ce type d'offre pouvait remonter trop haut.

Pourquoi il est maintenant correctement en `Related`:

- le profil cible est `Comptable`, pas `Controle de gestion`;
- l'offre ne contient pas assez de competences coeur comptables pour justifier un `Strong`;
- une regle de quality gate comptable a ete ajoutee pour eviter qu'un role finance proche passe en `Strong` sans role comptable direct ni preuves comptables centrales.

Defense technique simple:

> Le moteur comprend que controle de gestion est un domaine voisin de la comptabilite, mais il le garde en `Related` tant que le role exact ou les competences coeur comptables ne sont pas assez fortes.

### Pourquoi certaines offres ont change de section apres regeneration JobBERT

Le changement n'est pas aleatoire. Il s'explique par deux points:

1. Alignement semantique re-evalue
   - `INTERNATIONAL` n'avait pas encore d'embedding JobBERT;
   - apres regeneration, son score semantique devient plus fiable et elle remonte.

2. Calibration metier plus stricte
   - une regle comptable empeche des offres finance voisines comme `controle de gestion` de rester en `Strong`;
   - les offres plus seniors ou plus ambigues restent en `Related`.

Exemples:

- `HAMADI ABID - Assistant controle de gestion`: descendu en `Related` car domaine proche mais metier non exact.
- `Vneuron`: reste en `Related` car seniorite superieure au profil.
- `BIGBOSS EXPRESS`: descend en `Related` car l'offre est moins propre pour un profil junior et contient un signal experience plus confirme.

### Metriques et validation a mentionner

Pour ce scenario comptable de demonstration:

- `Precision@3 = 100%`
  Les 3 premieres offres sont des roles comptables directs et pertinents.
- `Strong anti-faux-positif`
  `HAMADI controle de gestion` n'est plus en `Strong`.
- `Related defensif`
  `Vneuron` reste visible mais avec un gap d'experience clairement expose.

Tests techniques utiles a citer:

- `tests.test_recommendation_quality_gates`: `46 tests OK`
- le quality gate comptable a ete couvre par un test dedie pour verifier qu'un role `controle de gestion` reste en `Related` pour un profil `Comptable`.

### Script oral conseille pour le profil comptable

> Pour ce profil Comptable Junior, BidWise combine le role cible, les competences du CV, les preferences de localisation et les types de contrat. Ensuite, JobBERT compare le sens metier global des offres et le scoring hybride ajoute les signaux explicables: role, skills, famille metier, experience et qualite de la source. Les offres INTERNATIONAL et CMR AUDIT ressortent comme strong matches car elles sont comptables directes, juniors et bien structurees. A l'inverse, Vneuron reste en related car l'experience est au-dessus du profil, et HAMADI controle de gestion reste en related pour montrer que le systeme distingue domaine proche et metier exact.

## Profil de demo Technicien Maintenance

Profil candidat:

- Role cible: `Technicien Maintenance Industrielle`.
- Experience: junior, 2 ans.
- Localisations: Ben Arous, Tunis, Sousse.
- Mode de travail: On-site.
- Contrats: CDI, CDD, SIVP.
- Secteur: `Industrie / Maintenance / Production`.
- Competences profil/CV: maintenance preventive, maintenance corrective, diagnostic de pannes, electricite industrielle, mecanique industrielle, automatisme, GMAO, lecture de plans, intervention technique, securite industrielle.

Ce profil est utile pour la soutenance parce qu'il montre:

- plusieurs `Strong matches` tres propres sur une source bien structuree (`Keejob`);
- des scores forts dans `Related Review`, ce qui prouve que le pourcentage seul ne decide pas le bucket;
- une separation defendable entre une offre proche par competences et une offre dont le role exact est confirme.

### Resultats Strong a montrer

| Offre | Source | Score UI | Bucket | Pourquoi c'est defendable |
| --- | --- | ---: | --- | --- |
| TECHNICIEN SUPERIEUR MAINTENANCE | Keejob | 94% | Strong | Role cible, Ben Arous, CDI, maintenance preventive/curative, machines industrielles |
| ASTEELFLASH - Technicien Maintenance | Keejob | 75% | Strong | Role maintenance direct, maintenance preventive, diagnostic, securite industrielle |
| LABORATOIRES ADWYA - Technicien Maintenance Process | Keejob | 73% | Strong | Maintenance preventive/corrective, GMAO, equipements industriels, Tunis |
| ORIENT TEA - Technicien de maintenance industrielle | Keejob | 70% | Strong | Role exact maintenance industrielle, GMAO, diagnostic, maintenance preventive/curative |
| STE GOLDA GROUP - Technicien en Electricite Industrielle | EmploiTunisie | 71% | Strong | Domaine voisin tres proche: installation technique et maintenance industrielle |

Phrase de defense:

> Ce profil montre le comportement attendu: les premieres offres Strong sont dans le coeur du metier maintenance industrielle. Les sources sont majoritairement Keejob, avec des descriptions detaillees et des champs structures.

### Cas defensif - DICK ELEVAGE GROUPE POULINA en Related malgre 75%

Offre:

```text
DICK ELEVAGE GROUPE POULINA - Techniciens de Maintenance
Score UI: 75%
Bucket: Related Review
Source: Keejob
Experience: Entry level
```

Pourquoi ce n'est pas une erreur:

- l'offre est proche du profil: maintenance, diagnostic de pannes, securite industrielle, Ben Arous;
- le score est donc eleve;
- mais le moteur ne la met pas en `Strong`, car le role cible exact n'est pas confirme avec assez de preuves.

Extrait JSON reel a montrer si le jury demande une preuve:

```json
{
  "score": 0.7462,
  "semantic_score": 0.5134,
  "business_score": 0.36,
  "opportunity_quality_score": 0.96,
  "recommendation_bucket": "RELATED_REVIEW",
  "recommendation_bucket_reason": "Skill match without confirmed role alignment",
  "evidence_summary": {
    "skill_overlap": 2,
    "profile_skill_overlap": 2,
    "role_match": false,
    "title_overlap": false,
    "llm_family_match": true,
    "semantic_strength": "MEDIUM",
    "resume_signal": true
  },
  "ai_semantic_score": 0.4579,
  "ai_semantic_model": "JobBERT"
}
```

Lecture simple du JSON:

- `skill_overlap = 2`: le moteur trouve bien des competences communes.
- `llm_family_match = true`: l'offre est reconnue comme proche dans la famille metier.
- `semantic_strength = MEDIUM`: JobBERT detecte une proximite semantique, mais pas assez forte pour surclasser l'offre.
- `role_match = false` et `title_overlap = false`: le role cible exact n'est pas confirme.
- resultat: `RELATED_REVIEW`, pas `STRONG_MATCH`.

Phrase de defense:

> DICK n'est pas une mauvaise recommandation. C'est une opportunite proche. Le moteur detecte les competences et le domaine industriel, mais comme le role exact n'est pas confirme, il la garde volontairement en Related Review. C'est un anti-faux-positif.

### Cas defensif - LUXOR en Related malgre 73%

Offre:

```text
LUXOR - 02 Techniciens Superieurs
Score UI: 73%
Bucket: Related Review
Source: Keejob
Experience: Entry level
```

Pourquoi ce cas est utile:

- l'offre parle bien de maintenance preventive, maintenance corrective, GMAO et suivi de maintenance;
- elle est donc proche du profil;
- mais le titre `02 Techniciens Superieurs` est trop generique et ne confirme pas seul le role cible exact;
- le niveau `Entry level` est aussi a verifier pour un candidat junior avec 2 ans d'experience.

Phrase de defense:

> LUXOR est proche, mais le titre est generique. Le systeme conserve l'offre dans Related Review au lieu de la promouvoir fortement. Le candidat peut l'examiner, mais BidWise ne la presente pas comme une recommandation prioritaire.

### Fonctionnement a expliquer si le jury questionne

Le systeme detecte la proximite d'une offre avec un profil en plusieurs niveaux, pas avec un seul critere.

1. Il lit le profil candidat

Pour le profil maintenance, il recupere:

- role cible: `Technicien Maintenance Industrielle`;
- competences: maintenance preventive, maintenance corrective, diagnostic de pannes, electricite industrielle, mecanique, GMAO;
- localisation: Ben Arous, Tunis, Sousse;
- experience: junior / 2 ans;
- mode: On-site.

2. Il lit l'offre

Pour chaque offre, il recupere:

- titre;
- description;
- competences;
- localisation;
- contrat;
- experience;
- famille metier enrichie par IA;
- embedding JobBERT.

3. Il calcule la proximite semantique avec JobBERT

JobBERT transforme le profil et l'offre en vecteurs numeriques. Ensuite, le systeme calcule une similarite entre le profil et l'offre.

Exemples d'expressions proches:

- `maintenance preventive`;
- `entretien des equipements`;
- `diagnostic de pannes`.

Ces expressions ne sont pas identiques, mais elles sont proches metier. JobBERT permet donc de detecter une proximite semantique.

4. Il compare les competences

Le moteur cherche les competences communes:

- maintenance preventive;
- diagnostic de pannes;
- securite industrielle;
- GMAO;
- maintenance corrective;
- electricite industrielle.

Dans le JSON DICK:

```text
skill_overlap = 2
profile_skill_overlap = 2
```

Donc le moteur a trouve deux preuves de competences communes.

5. Il verifie le role exact

Ici, le moteur est volontairement strict. Il regarde si le titre ou le role extrait confirme directement le role cible:

- `Technicien maintenance`;
- `Technicien maintenance industrielle`;
- `Technicien support maintenance`.

Dans DICK:

```text
role_match = false
title_overlap = false
```

Donc le systeme dit:

> Je vois des competences proches, mais le titre ou le role n'est pas assez clairement confirme pour une recommandation forte.

6. Il verifie la famille metier

L'enrichissement IA classe l'offre dans une famille metier.

Dans DICK:

```text
llm_family_match = true
matched_llm_families = ["quality_industry_methods"]
```

Donc le systeme comprend que l'offre est dans un domaine industriel proche.

7. Il applique les quality gates

Decision finale:

- role exact + skills + semantique forte -> `Strong Match`;
- skills/famille proches mais role non confirme -> `Related Review`;
- trop faible ou hors domaine -> non priorise.

Pour DICK:

```text
skill_overlap = 2
llm_family_match = true
semantic_strength = MEDIUM
role_match = false
title_overlap = false
```

Resultat:

```text
recommendation_bucket = RELATED_REVIEW
recommendation_bucket_reason = Skill match without confirmed role alignment
```

Resume simple a dire:

> Le systeme detecte la proximite avec trois couches: JobBERT pour la similarite semantique, les competences communes pour les preuves concretes, et la famille metier IA pour comprendre le domaine. Ensuite, il verifie separement si le role exact est confirme. Si le role n'est pas confirme, l'offre reste en Related meme si elle est proche.

### Lignes de code a montrer si le jury demande

Detection stricte du role dans le scoring:

- [_role_matches dans recommendation_service.py](/d:/Documents/BidWise/backend/ai/recommendation_service.py:777)

Cette fonction compare les roles cibles avec:

- le titre de l'offre;
- le `canonical_role` enrichi par IA;
- les `target_roles` enrichis par IA;
- les tokens normalises du role.

Detection du role dans les quality gates:

- [_role_match dans quality_gates.py](/d:/Documents/BidWise/backend/ai/quality_gates.py:428)

Detection de la famille metier enrichie:

- [_llm_family_match dans quality_gates.py](/d:/Documents/BidWise/backend/ai/quality_gates.py:480)

Decision qui garde DICK/LUXOR en Related:

- [quality_gates.py](/d:/Documents/BidWise/backend/ai/quality_gates.py:757)

Logique resumee:

```python
if (
    not evidence.get("role_match")
    and not evidence.get("title_overlap")
    and role_semantic_score < ROLE_SEMANTIC_CAP_THRESHOLD
    and skill_overlap > 0
):
    return BUCKET_RELATED_REVIEW, "Skill match without confirmed role alignment"
```

Phrase de defense:

> Ce message n'est pas seulement un texte UI. Il correspond a une condition backend precise: skills presents, proximite detectee, mais role exact non confirme. C'est pour cela que DICK et LUXOR restent en Related Review.

## Profil de demo Data / IA

Compte utilise:

```text
amalsadkaoui40@gmail.com
```

Profil candidat:

- Roles cibles: `Data Scientist`, `Machine Learning Engineer`, `AI Engineer`, `Data Analyst`.
- Experience: junior, 2 ans.
- Localisations: Tunis, Sousse, Sfax.
- Modes de travail: Remote, Hybrid, On-site.
- Types d'opportunites: Jobs, Internships, Calls for tender.
- Contrats: CDI, CDD, SIVP, Freelance.
- Secteur: `Data / AI / BI`.
- Competences profil/CV: Data Analysis, Machine Learning, Deep Learning, Predictive Modeling, Data Cleaning, Feature Engineering, Data Visualization, Statistical Analysis, Model Evaluation, ETL, NLP, Python, SQL, Pandas, Scikit-learn, Power BI, NumPy, TensorFlow, Keras, PyTorch, Jupyter Notebook.

Le CV enrichit le profil avec des signaux techniques concrets. Ensuite, JobBERT et le scoring metier comparent ce profil aux offres disponibles.

## Cas 1 - Strong Match: Linedata

Offre:

```text
Linedata - Data Scientist/ML Engineer
Score: 73%
Bucket: Strong Match
```

Pourquoi c'est un bon match:

- Le titre contient deux roles cibles: `Data Scientist` et `ML Engineer`.
- La description mentionne clairement Machine Learning, IA generative, analyse de donnees, data pipelines, industrialisation et monitoring de modeles.
- Les technologies citees correspondent au profil: Python, pandas, scikit-learn, PyTorch, TensorFlow, SQL, NoSQL, cloud, Docker.
- La localisation `Tunis` et le mode de travail sont compatibles avec les preferences du candidat.
- Le signal CV est pris en compte.

Pourquoi le score n'est pas 90%:

- L'offre demande Bac+5.
- L'offre parle d'une experience de 2 a 5 ans dans le texte libre.
- L'experience n'est pas toujours extraite en champ structure depuis LinkedIn, donc le systeme reste prudent.
- Certaines competences affichees viennent de l'enrichissement et peuvent etre moins propres que la description complete.

Phrase de defense:

> Cette offre est un strong match parce que le systeme retrouve le role cible, les competences techniques du CV, la famille Data/IA et les preferences de localisation. Le score reste raisonnable car le systeme ne transforme pas une correspondance forte en certitude absolue.

Point a surveiller:

- Skill bruyant possible: `Esprit d'equipe, sens du service et excellente communication`.
- Ce label vient de l'enrichissement LLM et devrait idealement etre classe en soft skills ou separe en labels courts.
- Il n'affecte pas le coeur de la recommandation, qui repose surtout sur Python, SQL, ML, data pipelines et IA.

## Cas 2 - Strong Match: Yassir

Offre:

```text
Yassir - Data Scientist
Score: 71%
Bucket: Strong Match
```

Pourquoi c'est un bon match:

- Le titre correspond directement au role cible `Data Scientist`.
- L'offre parle d'analytics, data science, data analysis, produit, decision data-driven et experimentation.
- Les competences `SQL`, `Python`, `data analysis` correspondent au profil.
- L'offre est a Tunis et compatible avec le mode de travail.

Ce que ce cas montre:

- Le systeme ne recommande pas seulement les offres ML techniques.
- Il comprend aussi les offres Data Scientist orientees produit, business et analytics.

Point a surveiller:

- Le libelle `Experience level above listed range` peut apparaitre comme detail a confirmer.
- Pour la demo, il vaut mieux expliquer que les details a confirmer sont des signaux de prudence, pas des raisons de rejet.

Phrase de defense:

> Ici BidWise detecte une offre Data Scientist orientee produit. Le matching ne depend pas uniquement d'une liste de technologies, mais aussi du role, du contexte analytics et des signaux semantiques de la description.

## Cas 3 - Strong Match: Sopra Steria

Offre:

```text
Sopra Steria - AI Engineer
Score: 70%
Bucket: Strong Match
```

Pourquoi c'est important:

- Le titre n'est pas `Data Scientist`, mais `AI Engineer`.
- La description contient Machine Learning, IA predictive, IA generative, RAG, agents, MLOps, model monitoring, FastAPI et Python.
- Le profil contient Machine Learning, Deep Learning, NLP, Python, TensorFlow, PyTorch et API Development.

Ce que ce cas montre:

- C'est le meilleur exemple pour defendre l'intelligence semantique.
- Le systeme comprend qu'un profil Data/ML peut etre pertinent pour une offre AI Engineer.
- Ce n'est pas une simple egalite de mots-cles.

Limite:

- Les skills affiches sont parfois moins riches que la description.
- Exemple: `python`, `backend`, `integration`, `api`, `forecasting`.
- La description complete contient beaucoup plus de preuves que la liste courte affichee.

Phrase de defense:

> Cette recommandation montre la valeur de JobBERT. Meme si le titre exact differe, le systeme rapproche le profil Data/ML avec une offre AI Engineer grace au contenu semantique de la description.

## Cas 4 - Strong Match metier different: SYSTRA

Offre:

```text
SYSTRA - Charge d'etudes Mobilite / Data Science
Score: 66%
Bucket: Strong Match
```

Pourquoi c'est interessant:

- Le titre n'est pas un titre purement tech.
- Le domaine est la mobilite et le transport.
- Les missions sont pourtant clairement Data Science: collecte, preparation, analyse de donnees massives, modeles predictifs, dashboards, automatisation.
- Les skills enrichies affichent Python, R, SQL, Tableau et Power BI.

Ce que ce cas montre:

- Le systeme detecte une opportunite Data Science appliquee a un secteur metier specifique.
- Il ne depend pas seulement du mot exact `Data Scientist`.
- Il comprend que les competences du profil sont transferables a un contexte mobilite.

Phrase de defense:

> Cette offre montre que BidWise ne se limite pas aux titres classiques. Une offre de mobilite peut etre recommandee si la mission contient une vraie composante Data Science.

## Cas 5 - Related Review: Jems Group

Offre:

```text
Jems Group - Data Scientist H/F
Score: 65%
Bucket: Related Review
Skills: No structured skills provided.
```

Pourquoi l'offre reste pertinente:

- Le titre correspond au role cible `Data Scientist`.
- La localisation `Tunis` est compatible.
- Le domaine general est la donnee.
- Le profil et le CV sont dans le meme univers Data/IA.

Pourquoi elle n'est pas classee comme strong principale:

- La source ne fournit aucune competence structuree.
- La description reste generale: patrimoine data, cas d'usage, gestion de la donnee.
- Elle ne cite pas clairement Python, SQL, Machine Learning, Power BI ou d'autres preuves techniques.
- Le systeme a donc moins de preuves concretes pour recommander fortement.

Ce que ce cas montre:

- BidWise sait garder une offre proche sans la survaloriser.
- Le systeme separe les offres fortement prouvees des offres a verifier.
- L'absence de skills ne bloque pas totalement l'offre, mais limite sa confiance.

Phrase de defense:

> Cette offre illustre la gestion des donnees faibles. Le titre est tres proche du profil, donc l'offre reste pertinente. Mais comme la source ne donne pas de competences structurees et que la description est peu technique, BidWise la classe en Related Review plutot qu'en top recommandation.

## Comparaison Strong Match vs Related Review

| Cas | Score | Bucket | Explication |
| --- | ---: | --- | --- |
| Linedata | 73% | Strong Match | Role exact + fortes competences techniques + CV + localisation |
| Yassir | 71% | Strong Match | Role exact + analytics + Python/SQL + contexte data produit |
| Sopra Steria | 70% | Strong Match | Titre different mais contenu IA/ML tres proche |
| SYSTRA | 66% | Strong Match | Data Science appliquee a la mobilite, bon transfert semantique |
| Jems Group | 65% | Related Review | Titre proche, mais pas de skills structures ni preuves techniques fortes |

## Comment expliquer les scores

Le score n'est pas une probabilite d'etre recrute.

C'est un score de pertinence qui combine:

- alignement du role cible;
- competences du profil et du CV;
- similarite semantique JobBERT;
- famille metier;
- localisation;
- mode de travail;
- contrat;
- experience quand elle est disponible;
- qualite des donnees de l'offre.

Un score de 70% peut etre excellent si l'offre externe est incomplete. Le systeme reste prudent pour ne pas donner une fausse certitude.

## Pourquoi certains scores proches sont dans deux sections differentes

La section n'est pas basee uniquement sur le pourcentage.

Le backend utilise aussi un bucket qualitatif:

- `STRONG_MATCH`: assez de preuves metier pour recommander.
- `RELATED_REVIEW`: offre pertinente, mais une incertitude reste presente.

Exemple:

- Une offre a 66% avec role, skills, famille metier et localisation peut etre `Strong Match`.
- Une offre a 65% avec seulement un titre proche mais sans skills peut rester `Related Review`.

Phrase de defense:

> Le pourcentage donne l'intensite du match, mais le bucket indique le niveau de confiance metier. Deux offres avec des scores proches peuvent etre separees si l'une a des preuves techniques concretes et l'autre seulement un titre proche.

## Limites reconnues proprement

### Experience non extraite depuis certaines descriptions

Certaines offres LinkedIn affichent l'experience dans le texte libre, par exemple:

```text
Experience de 2 a 5 ans minimum dans un poste similaire
```

Si cette information n'est pas dans un champ structure, elle peut ne pas apparaitre dans les details courts.

Defense:

> Les champs structurels sont fiables quand la source les expose. Pour les exigences cachees dans la description, une amelioration future consiste a appliquer une extraction regex/LLM supplementaire pour remplir `experience_min` et `experience_max`.

### Skills LLM parfois trop longs

Exemple:

```text
Esprit d'equipe, sens du service et excellente communication
```

Ce label devrait idealement etre classe en soft skills ou separe en labels plus courts.

Defense:

> L'enrichissement LLM est utilise pour ameliorer les offres pauvres. Il peut parfois extraire une phrase comportementale trop longue, mais le matching fort reste porte par les signaux techniques et semantiques principaux.

### Qualite variable des sources

Certaines sources fournissent:

- descriptions longues mais peu de skills;
- skills tres courts;
- contrats ambigus;
- dates anciennes;
- intitules incomplets.

Defense:

> La qualite de recommandation depend aussi de la qualite des donnees source. BidWise compense par l'enrichissement IA et la similarite semantique, mais garde les cas incertains en Related Review.

## Script oral recommande

> Pour ce profil Data/IA, BidWise commence par utiliser les informations du profil et du CV: roles cibles, competences techniques, secteur, localisation et preferences. Ensuite, chaque offre est comparee avec ces signaux via JobBERT et un scoring metier explicable. Les offres Linedata, Yassir et Sopra Steria sont en Strong Match parce qu'elles combinent role, competences et contexte Data/IA. L'offre SYSTRA montre que le systeme comprend une mission Data Science meme dans un secteur mobilite. A l'inverse, Jems Group reste en Related Review: le titre est pertinent, mais l'offre ne fournit pas assez de competences structurees pour etre recommandee avec le meme niveau de confiance.

## Offres conseillees pour la demo

Ordre conseille:

1. Linedata - meilleur match global.
2. Sopra Steria - meilleur exemple d'intelligence semantique titre different.
3. SYSTRA - Data Science appliquee a un domaine metier different.
4. Jems Group - cas limite avec absence de skills.

Yassir peut etre utilise si le jury demande un deuxieme exemple Data Scientist classique.
