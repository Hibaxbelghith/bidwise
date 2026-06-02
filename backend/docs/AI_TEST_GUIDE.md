# Guide de test soutenance - Recommandation IA

Last updated: 2026-06-01

## Objectif

Ce document sert de guide de démonstration pour tester le moteur de recommandation IA pendant la soutenance.

Il couvre pour chaque profil:

- les paramètres exacts du profil utilisateur;
- les offres attendues dans la page `For You`;
- l'explication du ranking;
- les points forts observables;
- les limites connues et les améliorations possibles.

Le but n'est pas de montrer uniquement un score élevé, mais de prouver que le système combine plusieurs signaux: rôle cible, similarité JobBERT, skills, famille métier, localisation, mode de travail, expérience, type de contrat, enrichissement LLM et garde-fous qualité.

## Commande de validation backend

Pour valider un profil depuis le backend, utiliser un pool réaliste. Ne pas utiliser `--candidate-limit 30`, car cela ne teste que les 30 offres les plus récentes avant reranking.

Commande recommandée:

```bash
docker compose exec backend python manage.py test_profile_recommendations --profile-id <PROFILE_ID> --candidate-limit 2500 --rerank-candidates 120 --top-k 20 --exclude-benchmark
```

Interprétation:

- `candidate-limit 2500`: récupère un volume suffisant d'offres actives avec embeddings JobBERT.
- `rerank-candidates 120`: garde les meilleurs candidats sémantiques avant scoring métier.
- `top-k 20`: affiche assez de résultats pour analyser les `Strong matches` et les `Related opportunities`.
- `--exclude-benchmark`: exclut les offres internes de benchmark.

## Checklist UI

Avant de valider un profil dans la page `For You`, vérifier:

- les offres ont un bouton `Apply` quand une URL source existe;
- les descriptions sont présentes quand elles existent côté backend;
- les skills apparaissent, avec le badge `AI` quand ils viennent de l'enrichissement LLM;
- les doublons évidents ne sont pas affichés deux fois;
- les scores élevés en `Related opportunities` ont une raison lisible, par exemple seniority gap ou spécialisation;
- les offres sans alignement métier fort restent en review, même si elles partagent un skill générique comme `Excel`;
- le premier bloc contient des offres réellement alignées avec le métier cible.

## Profil 1 - Comptable / Audit

### Paramètres du profil

```text
Niveau: Junior
Expérience: 2 ans
Titre cible: Comptable
Localisations: Tunis, Ben Arous, Sousse, Sfax
Mode de travail: ON_SITE
Contrats: CDI, CDD, SIVP
Skills: Comptabilité, Audit, Excel, Déclarations fiscales, Outils bureautiques
Secteur: Audit / Finance / Accounting
CV: non fourni
```

### Résultat attendu

Le bloc `Strong matches` doit contenir en priorité des offres de type:

- `Assistant Comptable`;
- `Comptable - Tunis`;
- `Comptable Junior`;
- `Auditeurs comptable`;
- `Assistant comptable fiscal`;
- offres cabinet comptable / audit / fiscalité.

Exemples validés:

```text
ALMA INT - Assistant Comptable - Tunis
AUDIT TAX & CONSULTING - Comptable - Tunis
ACCOUNTING ADVISORS TUNISIA - Assistant(e) Comptable
RAYON CONSULT - Auditeurs comptable
HR PARTNERS - Comptable Junior - Tunis
NTAS - Assistante Comptable
```

Les offres plus seniors, spécialisées ou légèrement éloignées doivent rester dans `Related opportunities to review`.

Exemples:

```text
LIBRA TAX & ACCOUNTANCY - Comptable Expérimenté Consolidation
HR PARTNERS - Comptable Confirmé
OECT - Responsable Financier et Comptable
FINOPTI TN - Comptabilité française
```

### Explication du ranking

Le système ne classe pas seulement par titre exact. Il combine:

- alignement métier: `Comptable`, `Assistant Comptable`, `Auditeurs comptable`;
- skills directs: `Comptabilité`, `Excel`, `Audit`, `Déclarations fiscales`;
- famille métier: `accounting_finance_audit`;
- préférences utilisateur: localisation et `ON_SITE`;
- niveau d'expérience: junior avec 2 ans;
- garde-fous qualité: les offres trop seniors ou trop spécialisées peuvent garder un score élevé mais passer en `Related opportunities`.

Exemple d'interprétation:

```text
RAYON CONSULT - Auditeurs comptable
Pourquoi c'est pertinent:
- même famille métier comptabilité / audit;
- missions d'audit légal et contractuel;
- skills enrichis par IA: Audit légal, Audit contractuel, Analyse financière, Normes comptables;
- localisation Tunis;
- contrat CDI;
- profil junior compatible.
```

Exemple de review volontaire:

```text
LIBRA TAX & ACCOUNTANCY - Comptable Expérimenté Consolidation
Pourquoi ce n'est pas automatiquement Strong:
- bon alignement comptabilité;
- bons skills Excel / Comptabilité;
- mais spécialisation consolidation et expérience plus avancée;
- donc le système l'affiche en Related avec explication.
```

### Points forts à montrer

- Les offres principales sont cohérentes avec un profil comptable junior.
- Le système comprend les variantes métier: `Comptable`, `Assistant Comptable`, `Auditeur comptable`, `Fiscalité`.
- Les doublons de republication sont masqués dans la page `For You`.
- Les offres enrichies par LLM affichent des skills utiles même si la source initiale ne fournissait pas de skills structurés.
- Les offres avec score élevé mais besoin de vérification restent séparées dans `Related opportunities`.
- Le bouton `Apply`, la source, la description et les skills sont affichés directement dans la carte, sans chargement incomplet.

### Points à améliorer

- Certaines offres de sources externes arrivent avec peu de skills; elles dépendent du backfill LLM pour devenir mieux explicables.
- L'enrichissement LLM est volontairement asynchrone et limité par batch, donc toutes les offres ne sont pas enrichies immédiatement.
- Les intitulés très génériques comme `Comptable` ou `Auditeurs` restent plus difficiles à expliquer sans description détaillée.
- Les offres proches mais pas strictement comptables, comme finance administrative ou recouvrement, peuvent apparaître en review si elles partagent la famille métier et des skills.

### Verdict du profil

Le profil `Comptable / Audit` est validé pour la soutenance.

Le ranking est cohérent, les meilleurs résultats sont alignés métier, les offres discutables sont séparées dans `Related opportunities`, et l'interface affiche les données complètes: source, bouton `Apply`, description et skills.

## Profil 2 - Backend Developer / API

### Paramètres du profil

```text
Niveau: Junior
Expérience: 2 ans
Titre cible: Backend Developer
Localisations: Tunis, Sousse, Ben Arous, Ariana, Sfax
Mode de travail: ON_SITE, REMOTE, HYBRID
Contrats: CDI, CDD, SIVP
Skills: Django, Python, SQL, Docker, Git, PostgreSQL, REST API
Secteur: Backend / Software Engineering / IT
CV: non fourni
```

### Résultat attendu

Le bloc `Strong matches` doit mettre en avant les offres backend ou backend/full-stack réellement proches du profil.

Exemples validés:

```text
Orisha - Python Backend Developer
DJAM DKS - Full Stack Engineer
```

Les offres backend pertinentes mais avec une stack différente, un scope plus large ou un point à vérifier doivent rester dans `Related opportunities to review`.

Exemples validés:

```text
DNEXT Intelligence SA - Back End Developer
PixiMind - Développeur(se) Python (Django)
Rakam AI - Backend/Cloud engineer
Advantry X - Web Developer
Tendanz Group - Développeur Backend Junior Java / Spring Boot
```

Les offres Data, DevOps, support ou exploitation peuvent apparaître plus bas si elles partagent `SQL`, `Docker`, `API` ou `Python`, mais elles doivent rester en review.

### Explication du ranking

Ce profil est volontairement plus difficile que le profil comptable, car plusieurs métiers techniques partagent les mêmes termes:

```text
backend
api
sql
docker
python
web developer
full-stack
cloud
data
devops
```

Le système combine:

- alignement du rôle cible: `Backend Developer`, `Python Backend Developer`, `Back End Developer`;
- similarité sémantique JobBERT;
- skills techniques: `Python`, `Django`, `REST API`, `PostgreSQL`, `Docker`, `SQL`;
- localisation et mode de travail;
- garde-fous qualité qui gardent les offres ambiguës dans `Related opportunities`.

Exemple fort:

```text
Orisha - Python Backend Developer
Pourquoi c'est top:
- le titre correspond au rôle cible;
- localisation Tunis;
- skill Python détecté;
- fort score sémantique;
- bucket Strong Match.
```

Exemple défendable:

```text
DJAM DKS - Full Stack Engineer
Pourquoi c'est dans Strong:
- la description annonce Backend / Full-Stack Engineer;
- stack backend: Python FastAPI, PostgreSQL, SQL, REST/WebSocket APIs;
- expérience 2+ ans, cohérente avec le profil;
- même si le titre contient Full Stack, le contenu backend est fort.
```

Exemple de review volontaire:

```text
Advantry X - Web Developer
Pourquoi ce n'est pas Strong:
- l'offre partage SQL, Docker, API et backend;
- mais la stack principale est PHP / Laravel / React;
- expérience demandée 5+ ans;
- le système la garde en Related pour revue humaine.
```

Exemple de bonne détection mais review:

```text
PixiMind - Développeur(se) Python (Django)
Pourquoi c'est pertinent:
- Python + Django sont exactement alignés;
- localisation Sfax acceptée;
- offre web/backend;
- reste en Related car le moteur garde une prudence sur le périmètre full-stack/front-end mentionné dans l'offre.
```

### Points forts à montrer

- Le système retrouve un vrai poste `Python Backend Developer` en premier.
- Il comprend les variantes de titre: `Backend`, `Back End`, `Développeur Python Django`, `Full Stack` avec contenu backend.
- Les offres proches mais imparfaites restent séparées en `Related opportunities`.
- Les offres DevOps/Data/Support ne sont pas vendues comme recommandations fortes.
- Les cartes affichent les descriptions, skills, source et bouton `Apply`.
- Le cache `For You` rend les refresh instantanés après le premier calcul.

### Points à améliorer

- Certaines offres très pertinentes peuvent rester en `Related opportunities` si elles ont un titre mixte ou une stack partiellement différente.
- Une offre PHP/Laravel peut apparaître avant une offre Python/Django si elle partage beaucoup de signaux génériques comme `backend`, `SQL`, `Docker`, `API`.
- Un reranker LLM offline/cache-first a été prototypé, mais il n'est pas activé par défaut car le modèle local testé n'a pas retourné des rerankings suffisamment fiables.

### Verdict du profil

Le profil `Backend Developer / API` est validé pour la soutenance comme test difficile.

Le résultat n'est pas présenté comme un ranking parfait, mais comme une recommandation IA prudente: le meilleur match est en tête, les offres proches sont visibles et les cas discutables sont clairement séparés dans `Related opportunities`.

## Profil 3 - DevOps / Cloud

### Paramètres du profil

```text
Niveau: Junior / Confirmé léger
Expérience: 3 ans
Titre cible: DevOps Engineer
Localisations: Tunis, Ben Arous, Sousse, Ariana
Mode de travail: HYBRID, REMOTE, ON_SITE
Contrats: CDI, CDD
Skills: AWS, Azure, Terraform, CI/CD, Docker, Linux, Grafana
Secteur: Cloud / Infrastructure / DevOps
CV: non fourni
```

### Résultat attendu

Le bloc `Strong matches` doit mettre en avant les postes DevOps directs ou Cloud/Infrastructure très proches.

Exemples validés:

```text
MASS Analytics - Junior DevOps Engineer
Orisha - DevOps Engineer / AI Ops
Collaboration Betters the World TN - Cloud Engineer
```

Les offres proches mais avec un écart de seniorité, de périmètre ou de localisation doivent rester dans `Related opportunities to review`.

Exemples validés:

```text
AFRICASHORE - DevOps Engineer (M/F)
Scope Merge - Senior Infrastructure & Systems Administrator
MOONSIDE CONSULTING & SERVICES - Ingénieur DevOps Senior
CBTW IT & Technology / Positive Thinking Company - Cloud Engineer
Devoteam - Junior AI Engineer
```

### Explication du ranking

Ce profil valide la capacité du système à reconnaître un métier technique spécialisé, avec beaucoup de termes partagés avec d'autres métiers IT.

Le système combine:

- alignement du rôle cible: `DevOps Engineer`, `Junior DevOps Engineer`, `Cloud Engineer`;
- skills d'infrastructure: `AWS`, `Azure`, `Terraform`, `CI/CD`, `Docker`, `Linux`, `Grafana`;
- famille métier: cloud / infrastructure / DevOps;
- signaux de localisation et mode de travail;
- garde-fous sur la seniorité et le périmètre du poste.

Exemple fort:

```text
MASS Analytics - Junior DevOps Engineer
Pourquoi c'est top:
- rôle DevOps explicite;
- profil junior compatible;
- Azure, AWS, Docker et cloud platform détectés;
- localisation Tunis;
- bucket Strong Match.
```

Exemple fort avec enrichissement LLM:

```text
Orisha - DevOps Engineer / AI Ops
Pourquoi c'est très pertinent:
- rôle DevOps explicite;
- Azure, AWS, Terraform, CI/CD, Grafana;
- skills enrichis par IA visibles dans l'UI;
- même famille métier cloud / infrastructure;
- localisation Tunis.
```

Exemple de review volontaire:

```text
MOONSIDE - Ingénieur DevOps Senior
Pourquoi ce n'est pas Strong:
- très fort match technique: CI/CD, Azure, Kubernetes, Terraform, Docker, Linux;
- mais poste senior avec 5 à 7 ans d'expérience;
- le profil testé est junior / confirmé léger;
- donc l'offre reste en Worth reviewing.
```

Exemple de périmètre proche mais différent:

```text
Scope Merge - Senior Infrastructure & Systems Administrator
Pourquoi c'est en Related:
- Azure, AWS, Docker, Linux et infrastructure sont alignés;
- mais le poste est plus orienté administration systèmes / support interne;
- seniorité plus élevée;
- donc review humaine nécessaire.
```

### Points forts à montrer

- Les deux meilleurs résultats sont des postes DevOps explicites.
- Le système comprend les signaux techniques cloud: `Azure`, `AWS`, `Terraform`, `CI/CD`, `Docker`, `Linux`.
- Les offres Cloud/Infrastructure proches sont conservées mais séparées en review.
- Les offres Senior ou Support ne sont pas présentées comme recommandations fortes.
- Les skills enrichis par LLM sont visibles avec le badge `AI`.
- Le résultat est cohérent même avec des offres hybrides entre IA, Cloud, Infrastructure et DevOps.

### Points à améliorer

- Les offres Cloud Engineer peuvent parfois être proches du profil DevOps sans être strictement DevOps.
- Certaines offres génériques de recrutement ou de future campaign peuvent avoir un bon score mais restent en review.
- Les offres Senior très riches en skills peuvent obtenir un score honorable, mais les garde-fous de seniorité les empêchent de devenir des Strong matches.

### Verdict du profil

Le profil `DevOps / Cloud` est validé pour la soutenance.

Le ranking est très cohérent: les offres DevOps directes sont en tête, les offres Cloud/Infrastructure proches sont séparées pour revue, et les écarts de seniorité sont correctement signalés.

## Profil 4 - Data Analyst / Business Intelligence

### Paramètres du profil

```text
Niveau: Junior
Expérience: 2 ans
Titre cible: Data Analyst / Business Intelligence
Localisations: Tunis, Sousse, Ariana, Ben Arous
Mode de travail: ON_SITE, HYBRID
Contrats: CDI, CDD, SIVP
Skills: Visualisation données, Tableaux de bord, KPIs, Power BI, Reporting
Secteur: Data / Analytics / BI
CV: non fourni
```

### Résultat attendu

Le bloc `Strong matches` ou les premiers résultats doivent mettre en avant les offres Data Analyst, BI, reporting ou analytics.

Exemples validés:

```text
ROSE BLANCHE GROUP - Data Analyst Marketing
Skwad - Data Analyst (H/F) - Sousse
Infor - Data Analyst, Senior
Odixcity Consulting - Data Operations Analyst
```

Les offres reporting, finance, projet ou management qui partagent seulement `Power BI`, `reporting` ou `KPIs` doivent rester en `Related opportunities to review`.

Exemples:

```text
Wimbee - Responsable de gestion de projets
EY - Consultant Senior en gestion des risques
KPMG Tunisia - Consultant Junior MOA Finance
FNZ - Reporting Engineer
```

### Explication du ranking

Ce profil teste la compréhension sémantique autour de la data décisionnelle, pas seulement le mot `Data Analyst`.

Le système combine:

- alignement du rôle cible: `Data Analyst`, `Business Intelligence`, `Data Operations Analyst`;
- skills BI: `Power BI`, `Reporting`, `KPIs`, `Tableaux de bord`, `Visualisation données`;
- similarité JobBERT entre les missions de reporting, dashboards et analyse de données;
- localisation et mode de travail;
- garde-fous sur la seniorité et la spécialisation.

Exemple fort:

```text
ROSE BLANCHE GROUP - Data Analyst Marketing
Pourquoi c'est pertinent:
- rôle Data Analyst explicite;
- Power BI détecté;
- missions d'analyse, visualisation, indicateurs et insights business;
- même famille Data / Analytics;
- score suffisant pour recommandation.
```

Exemple de review volontaire:

```text
Skwad - Data Analyst (H/F)
Pourquoi ce n'est pas forcément Strong:
- rôle parfaitement aligné;
- missions SQL, PostgreSQL, datavisualisation, dashboards, KPIs et reporting;
- mais niveau d'expérience / Bac+5 à vérifier pour un profil junior;
- donc l'offre reste dans Related avec une raison explicable.
```

Exemple de proximité partielle:

```text
Wimbee - Responsable de gestion de projets
Pourquoi c'est en Worth reviewing:
- contient reporting et Power BI;
- mais le rôle principal est ERP Project Manager;
- donc le système le garde en review, pas en Strong.
```

### Points forts à montrer

- Le système retrouve des offres Data Analyst et BI même avec un profil formulé autour des usages métiers: tableaux de bord, KPIs et reporting.
- Les offres avec un simple signal `reporting` ne dominent pas automatiquement le classement.
- Les offres seniors ou spécialisées restent en review.
- L'enrichissement LLM améliore certaines offres avec des skills comme `Power BI`, `Excel`, `Reporting`.
- Le résultat illustre la séparation entre Data Analyst, Data Operations, Reporting Engineer et Project Manager.

### Points à améliorer

- La base contient peu d'offres Data Analyst junior parfaitement alignées.
- Certains rôles reporting hors data peuvent remonter en Related si les skills sont proches.
- Les offres Data Analyst senior ou spécialisées peuvent avoir un bon score mais nécessitent une revue humaine.

### Verdict du profil

Le profil `Data Analyst / Business Intelligence` est validé comme profil de couverture Data / BI.

Il montre que le système comprend les signaux décisionnels (`Power BI`, `KPIs`, `reporting`, dashboards) tout en gardant les offres partiellement alignées dans `Related opportunities`.
