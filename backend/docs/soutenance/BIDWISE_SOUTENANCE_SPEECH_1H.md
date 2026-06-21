# BidWise - Speech et conducteur de demo 1h

Date de preparation: 2026-06-19

Objectif: avoir un fil unique pour presenter toute l'application web BidWise a un jury qui la decouvre pour la premiere fois, avec un focus fort sur IA, scraping et monitoring.

Position generale a garder pendant toute la soutenance:

> BidWise est une plateforme full-stack de recherche, publication et recommandation d'opportunites. Elle collecte des offres depuis plusieurs sources, les normalise, les enrichit, les expose dans une interface web, puis utilise le profil candidat, le CV et des embeddings metier pour proposer des recommandations explicables. Les traitements lourds ne bloquent pas l'utilisateur: ils tournent en arriere-plan avec Celery, Redis et des workers specialises.

## Timing recommande

| Temps | Partie | Objectif |
| ---: | --- | --- |
| 0-5 min | Introduction + stack | Donner la vision produit et technique. |
| 5-15 min | Visiteur non connecte + scraping | Montrer Explore, filtres, details job/tender, expliquer ingestion multi-sources. |
| 15-22 min | Auth OTP + onboarding | Montrer inscription fluide et collecte des premiers signaux profil. |
| 22-30 min | Profil + CV | Montrer score de completude, champs structurants, extraction CV et suggestions. |
| 30-52 min | Recommandation IA | Partie centrale: moteur hybride, cas comptable, cas maintenance, preuves code/tests. |
| 52-56 min | BidWise AI Assistant | Montrer analyse CV/offre, lettre de motivation, optimisation CV. |
| 56-60 min | Candidature, organisation, notifications, admin monitoring | Boucler le cycle candidat/organisation/admin. |

Si le jury pose beaucoup de questions IA, reduire les parties 6 a 9, mais ne pas sacrifier les preuves de code et de benchmark.

## 0. Preparation avant d'entrer en soutenance

Onglets utiles a ouvrir:

- Application web: page d'accueil ou `/opportunities?tab=explore`.
- Compte candidat nouveau ou email de test pour OTP.
- Compte de demo comptable avec recommandations deja en cache.
- Compte de demo technicien maintenance avec recommandations deja en cache.
- Espace organisation.
- Espace admin.
- Flower: `http://localhost:5555`.
- Docs/code dans l'IDE:
  - `backend/docs/TECH_STACK_OVERVIEW.md`
  - `backend/docs/SPRINT2_RECAP.md`
  - `backend/docs/soutenance/Sprint_3_code/Recommendation_IA.md`
  - `backend/docs/soutenance/Sprint_3_code/Recommendation_IA_Demo_Cases.md`
  - `backend/ai/recommendation_service.py`
  - `backend/ai/quality_gates.py`
  - `backend/ai/jobbert.py`
  - `backend/users/resume_semantic/structured_llm.py`
  - `backend/opportunities/tasks.py`
  - `backend/opportunities/monitoring.py`
  - `backend/opportunities/views_admin.py`

Commandes a garder sous la main si on te demande une preuve:

```powershell
docker compose ps
docker compose exec backend python manage.py check
docker compose exec backend celery -A config inspect active_queues
docker compose exec backend python manage.py test tests.test_recommendation_quality_gates --keepdb
docker compose exec backend python manage.py test tests.test_user_recommendations --keepdb
```

## 1. Introduction et stack - 5 min

### Ce que tu montres

Ouvre rapidement `TECH_STACK_OVERVIEW.md`, puis montre l'application.

### Speech

> Bonjour, je vais presenter BidWise, une plateforme web qui centralise plusieurs types d'opportunites: offres d'emploi, stages, emplois saisonniers et appels d'offres. L'idee est de reduire la dispersion des opportunites en Tunisie et de proposer une experience personnalisee pour le candidat.

> La plateforme ne se limite pas a afficher des annonces. Elle collecte des donnees multi-sources, les normalise, les enrichit, les rend consultables par tous, puis utilise le profil candidat et son CV pour proposer des recommandations intelligentes.

> Techniquement, BidWise est une application full-stack. Le frontend est en React avec Vite. Le backend est en Django REST Framework. La base de donnees est PostgreSQL avec pgvector pour les embeddings. Les traitements lourds sont externalises vers Celery avec Redis: scraping, materialisation, embeddings, analyse CV, notifications et enrichissement LLM. Docker Compose permet de lancer les services de maniere reproductible.

> L'architecture suit cette logique: React appelle une API Django, Django lit et ecrit dans PostgreSQL, Celery traite les taches lentes en arriere-plan, et le dashboard admin supervise l'etat du pipeline, des workers et des modules IA.

Phrase importante:

> Le navigateur ne scrape jamais les sites externes. Il consomme uniquement des opportunites deja nettoyees et materialisees par le backend.

## 2. Visiteur non connecte, Explore et scraping multi-sources - 10 min

### Ce que tu montres

1. Ouvrir `/opportunities?tab=explore` sans etre connecte.
2. Montrer la liste dans `OpportunitiesBrowseResults.jsx`.
3. Montrer le compteur, pagination, filtres et recherche.
4. Filtrer par type: Job, Stage, Call for tender.
5. Filtrer par source: LinkedIn, Keejob, EmploiTunisie, MarchesPublics.
6. Ouvrir une offre d'emploi.
7. Revenir et ouvrir un appel d'offre.
8. Montrer que les details sont accessibles aux visiteurs.
9. Montrer qu'une incitation existe pour creer un profil ou voir les matches personnalises.

### Speech

> Ici je commence par le scenario d'un utilisateur non connecte. BidWise reste utile meme sans compte: il peut consulter les opportunites, chercher, filtrer et ouvrir le detail d'une offre.

> La liste n'est pas une collection manuelle. Elle vient d'un pipeline de scraping multi-sources. Les sources actives sont LinkedIn, Keejob, EmploiTunisie et MarchesPublics. Chaque source a sa cadence, sa priorite et son comportement d'extraction.

> LinkedIn est plus dynamique et plus sensible au rate limit, donc sa cadence est plus courte mais son execution est surveillee. Keejob est une source plus structuree pour les offres locales. EmploiTunisie apporte d'autres annonces avec des champs parfois differents. MarchesPublics sert aux appels d'offres, qui changent moins vite que les offres d'emploi.

> Le pipeline se fait en plusieurs etapes. D'abord on collecte les donnees brutes. Ensuite on les stocke dans une table raw pour pouvoir auditer et rejouer. Puis on normalise les champs: titre, organisation, ville, type, contrat, date, deadline, source URL. Apres, on enrichit le texte pour extraire des skills, langues, salaire ou experience quand les sources ne les fournissent pas clairement. Ensuite on applique un score qualite, on materialise vers le modele canonique `Opportunite`, puis on genere les embeddings.

> Cette architecture est importante parce que les sources ne parlent pas le meme langage. Un appel d'offre MarchesPublics n'a pas la meme structure qu'une annonce LinkedIn. BidWise transforme donc des donnees heterogenes en opportunites canoniques exploitables.

### Points de demo filtres

Quand tu manipules les filtres:

> Les filtres sont cote API, pas seulement visuels. Le backend expose des filtres par type, ville, source, mode de travail, experience, date de publication et deadline. Les facettes permettent aussi de montrer les volumes par categorie.

Fichiers a citer si question:

- UI liste: `frontend/src/features/opportunities/components/browse/OpportunitiesBrowseResults.jsx`
- UI filtres: `frontend/src/features/opportunities/components/browse/OpportunitiesBrowseFilters.jsx`
- Hook browse: `frontend/src/features/opportunities/hooks/useOpportunitiesBrowse.js`
- Filtres backend: `backend/opportunities/filters.py`
- Facettes: `backend/opportunities/api/services/facets.py`
- Pipeline scraping: `backend/opportunities/pipeline.py`
- Raw ingestion: `backend/opportunities/scraping/pipeline.py`
- Processing: `backend/opportunities/processing.py`

### Enrichissement LLM des offres

> Certaines sources donnent de longues descriptions mais peu de skills. Dans ce cas, BidWise peut lancer un enrichissement LLM offline. Cet enrichissement ne s'execute pas pendant la consultation utilisateur. Il tourne dans une queue Celery dediee `opportunity_enrichment`.

> L'interet est double: ameliorer la qualite des skills pour les recommandations, et eviter de bloquer le scraping ou l'API si le modele local est lent.

Fichiers:

- `backend/docs/LLM_OPPORTUNITY_ENRICHMENT_CELERY.md`
- `backend/ai/llm/opportunity_enrichment.py`
- `backend/ai/management/commands/enrich_opportunities_with_gemini.py`
- `backend/config/settings.py` pour le routage de queue.

## 3. Inscription OTP et onboarding - 7 min

### Ce que tu montres

1. Page login.
2. Saisie d'un nouvel email.
3. Modal Turnstile si active.
4. Demande OTP.
5. Verification du code.
6. Creation automatique du compte.
7. Redirection onboarding.
8. Onboarding recherche d'emploi: type, mode, localisation, competences, domaines, salaire, contrats, roles, visibilite.

### Speech

> Pour l'inscription, BidWise utilise un flux passwordless par email OTP. L'utilisateur saisit son email, recoit un code temporaire, puis son compte est cree uniquement apres verification reussie.

> Ce choix reduit la friction. L'utilisateur n'a pas besoin de creer un mot de passe. Mais ce n'est pas une authentification faible: l'OTP est temporaire, stocke hashe, a usage unique, limite en tentatives, avec cooldown, throttling et Turnstile cote web.

> Apres verification, le backend delivre des JWT. L'OTP sert a prouver l'identite au moment de l'entree; les JWT servent ensuite a maintenir la session web et mobile.

> Le point important est que l'onboarding n'est pas un simple formulaire d'inscription. C'est le debut de la personnalisation. Les reponses collectees ici servent ensuite au moteur de recommandation.

Phrase de transition:

> A ce stade, BidWise connait deja ce que le candidat cherche: types d'opportunites, localisations, modes de travail, competences, domaines et roles cibles. On peut donc passer du mode exploration generique au mode personnalise.

Fichiers:

- Backend OTP: `backend/users/views.py`, `backend/users/models.py`, `backend/users/otp_service.py`, `backend/users/tasks.py`
- Frontend login: `frontend/src/features/auth/LoginPage.jsx`
- Onboarding: `frontend/src/features/onboarding/OnboardingPage.jsx`
- Options/validation profil: `frontend/src/features/profile/profilePreferences.js`, `frontend/src/features/profile/profileValidation.js`

## 4. Profil candidat, score et CV - 8 min

### Ce que tu montres

1. Page profil.
2. Score de completude.
3. Champs obligatoires et champs structurants.
4. Suggestions/autocomplete competences, roles, secteurs.
5. Upload ou affichage d'un CV deja analyse.
6. Statuts parsing/analyse.
7. Suggestions extraites du CV.
8. Application partielle des suggestions.

### Speech

> Le profil candidat est la base de signaux pour la recommandation. Ce n'est pas une fiche passive. Il contient des informations explicites saisies par l'utilisateur, mais aussi des signaux extraits du CV.

> Le score de completude est calcule cote backend. Il ne sert pas juste a decorer l'interface. Il explique a l'utilisateur pourquoi ses recommandations peuvent etre faibles et quels champs ameliorer. Les signaux les plus importants sont les competences, roles cibles, domaines, localisations, modes de travail, types de contrat et CV.

> Le CV a le poids le plus eleve parce qu'il donne souvent des signaux plus riches que l'onboarding: outils, experiences, roles reels, langues, domaines et niveau.

### Analyse CV

> Le pipeline CV a deux niveaux. D'abord, on parse le fichier pour extraire le texte. Pour PDF on utilise PyMuPDF, pour DOCX on utilise python-docx. Ensuite, ce texte nettoye est envoye a une extraction semantique par LLM local via Ollama/Qwen.

> Le LLM ne retourne pas une phrase libre. On lui impose un JSON structure avec `canonical_role`, `target_roles`, `skills`, `tools`, `domains`, `business_families`, `years_experience`, `experience_level`, `languages`, `contract_types`, `locations` et `confidence`.

> Ensuite le backend nettoie, limite, deduplique et transforme cette sortie en suggestions. L'utilisateur garde le controle: il peut accepter certaines suggestions et ignorer les autres.

Phrase forte:

> Le parsing lit le document. L'extraction semantique comprend le contenu. La validation backend garde le controle sur ce qui est stocke.

Fichiers:

- Score: `backend/users/profile_completion.py`
- Upload/statuts: `backend/users/views.py`, `backend/users/models.py`
- Parsing: `backend/users/resume_parsing/service.py`
- Pipeline Celery: `backend/users/tasks.py`
- Prompt/schema LLM: `backend/users/resume_semantic/structured_llm.py`
- Service semantique: `backend/users/resume_semantic/service.py`
- Frontend CV: `frontend/src/features/profile/components/ResumeSection.jsx`

## 5. Recommandation IA - 22 min

Cette partie doit prendre environ la moitie de la soutenance si le jury est specialise IA.

### Message central

> La recommandation BidWise est un moteur hybride. Elle combine IA semantique, enrichissement LLM offline, extraction CV et regles metier explicables. Le LLM ne decide pas seul. Les scores et les buckets sont calcules par le backend a partir de signaux controles.

### Architecture orale simple

> D'abord, BidWise construit les features du profil: roles cibles, skills, domaines, experience, contrats, localisations et signaux CV. Ensuite, chaque opportunite a ses propres signaux: titre, description, source, skills, famille metier, experience, contrat, localisation et embeddings.

> Le systeme recupere des candidats par recherche semantique et lexicale. Puis il applique un scoring hybride: similarite semantique, score business, qualite de l'offre, feedback, source, experience, role, skills et famille metier.

> Enfin, il classe les resultats en deux sections: `Strong matches` et `Related opportunities to review`. Le bucket est tres important: deux offres avec des scores proches peuvent etre dans deux sections differentes si l'une a des preuves metier plus solides.

### Les briques IA a nommer clairement

1. Extraction CV par LLM local:
   - lit le CV,
   - extrait roles, outils, competences, domaines, experience,
   - produit des suggestions profil.

2. Enrichissement LLM des opportunites:
   - offline,
   - cible les offres pauvres en skills,
   - enrichit les metadonnees et les skills.

3. JobBERT:
   - modele `TechWolf/JobBERT-v3`,
   - transforme profil et offres en vecteurs metier,
   - compare le sens global, pas seulement les mots exacts.

4. Quality gates:
   - empechent les faux positifs,
   - separent Strong et Related,
   - verifient role, skills, famille, experience, source et qualite.

### Preuve code rapide

Ouvrir `backend/ai/recommendation_service.py` autour de `rank_opportunities`.

Dire:

> Ici on voit que le score n'est pas une simple recherche par mot-cle. Le score combine une similarite semantique, un business score, des ajustements de qualite, des penalites d'experience, des boosts de role, des penalites de famille metier et l'ajustement JobBERT.

Ouvrir `backend/ai/quality_gates.py` autour de `classify_recommendation_bucket`.

Dire:

> Ici se trouve la decision Strong/Related. Par exemple, si une offre a des skills communs mais que le role exact n'est pas confirme, elle peut rester en `RELATED_REVIEW`. C'est volontaire: on prefere une recommandation prudente a un faux positif.

Ouvrir `backend/ai/jobbert.py`.

Dire:

> JobBERT calcule des embeddings normalises. Si l'offre a deja un embedding JobBERT stocke, le systeme utilise ce score directement. Cela rend la recommandation rapide et evite de recalculer tout en temps reel.

## 5.1 Cas demo Comptable Junior

### Profil

Compte documente: `hibabelg7@gmail.com`

Signaux:

- role cible: `Comptable Junior`
- experience: junior, 2 ans
- localisations: Tunis, Sousse, Sfax
- contrats: CDI, CDD, SIVP
- secteur: comptabilite / gestion / audit
- competences: comptabilite generale, saisie comptable, rapprochements bancaires, declarations fiscales, Excel, Sage, ERP

### Ce que tu montres

1. Ouvrir le compte comptable.
2. Aller dans For You / recommandations.
3. Montrer la section Strong matches.
4. Ouvrir une offre Strong.
5. Montrer score, raisons, skills, localisation, details.
6. Ouvrir une offre Related comme `Vneuron` ou `HAMADI controle de gestion`.
7. Expliquer pourquoi elle reste visible mais pas prioritaire.

### Resultats documentes a citer

Artefact: `backend/benchmark_reports/reco_comptable_after_jobbert.json`

| Offre | Score benchmark | JobBERT | Bucket | Lecture |
| --- | ---: | ---: | --- | --- |
| INTERNATIONAL GLOBAL ACCOUNTING SEVICES - Comptable | 88.87% | 75.07% | STRONG_MATCH | Role et semantique tres alignes. |
| CMR AUDIT - Comptables | 74.81% | 62.26% | STRONG_MATCH | Cabinet comptable, preuves metier fortes. |
| Vneuron - Comptable Confirmee | 68.00% | 48.33% | RELATED_REVIEW | Proche, mais niveau confirme au-dessus du profil. |

Dans le benchmark final, on retrouve aussi:

- CMR AUDIT en `STRONG_MATCH`, score autour de 75%.
- Vneuron en `RELATED_REVIEW`, raison: `Slight hierarchy gap; keep as reviewable`.

### Speech comptable

> Pour ce profil, le candidat cherche un poste de Comptable Junior. Le systeme utilise le role cible, l'experience, les localisations, les contrats et les competences du profil et du CV.

> Les offres comme INTERNATIONAL et CMR AUDIT remontent en Strong parce qu'elles ont des preuves directes: titre comptable, missions comptables, experience compatible et score semantique JobBERT fort.

> Vneuron est interessant parce que ce n'est pas une mauvaise offre. Elle partage des skills comptables, mais elle parle de `Comptable Confirmee` et demande un niveau plus eleve. BidWise ne la cache pas, mais la met en Related Review. C'est precisement ce que je veux: garder l'opportunite visible sans la sur-promettre au candidat.

> HAMADI controle de gestion est aussi un bon cas defensif. C'est proche de la finance, mais ce n'est pas exactement comptable. Le quality gate comptable empeche ce type d'offre de passer en Strong sans preuves comptables centrales.

Phrase si le jury demande "est-ce de l'IA ou des regles ?":

> C'est volontairement les deux. JobBERT apporte la similarite semantique, le LLM enrichit les donnees faibles, et les regles metier rendent la decision explicable et stable. Un systeme 100% LLM serait plus lent, plus cher et plus difficile a auditer.

## 5.2 Cas demo Technicien Maintenance

### Profil

Signaux:

- role cible: `Technicien Maintenance Industrielle`
- experience: junior, 2 ans
- localisations: Ben Arous, Tunis, Sousse
- mode: on-site
- contrats: CDI, CDD, SIVP
- secteur: industrie / maintenance / production
- competences: maintenance preventive, maintenance corrective, diagnostic de pannes, electricite industrielle, mecanique industrielle, automatisme, GMAO, lecture de plans, securite industrielle

### Ce que tu montres

1. Ouvrir le compte maintenance.
2. Aller dans recommandations.
3. Montrer les Strong matches.
4. Ouvrir `TECHNICIEN SUPERIEUR MAINTENANCE`.
5. Ouvrir `ORIENT TEA - Technicien de maintenance industrielle`.
6. Montrer un Related comme `DICK ELEVAGE GROUPE POULINA` ou `ASTEELFLASH`.
7. Insister sur la difference entre score et bucket.

### Resultats benchmark final

Artefact: `backend/benchmark_reports/reco_final_demo_profiles.json`

| Offre | Score benchmark | JobBERT | Bucket | Lecture |
| --- | ---: | ---: | --- | --- |
| TECHNICIEN SUPERIEUR MAINTENANCE | 75.34% | 63.35% | STRONG_MATCH | Role, skills et semantique alignes. |
| ORIENT TEA - Technicien de maintenance industrielle | 71.72% | 62.74% | STRONG_MATCH | Role exact et maintenance industrielle. |
| TUNIPA - Technicien Maintenance Industrielle | 71.49% | 70.88% | STRONG_MATCH | Tres bon signal JobBERT. |
| DICK ELEVAGE GROUPE POULINA - Des Techniciens de maintenances | 65.46% | 64.75% | RELATED_REVIEW | Proche, mais preuves role/skills insuffisantes selon gates. |
| ASTEELFLASH - Technicien Maintenance | 61.04% | 58.71% | RELATED_REVIEW | Role aligne mais skill evidence limitee. |

### Speech maintenance

> Ce profil montre un comportement tres important: le systeme ne trie pas seulement par score numerique. Les trois premiers Strong sont des offres clairement dans le coeur du metier maintenance industrielle. Elles combinent role, contexte industriel, skills et semantique forte.

> DICK ELEVAGE est un excellent cas defensif. Son score JobBERT est eleve parce que le contenu est proche du domaine industriel, mais le moteur reste prudent. Il garde l'offre en Related Review car la preuve de role exact ou de skills coeur n'est pas assez solide.

> ASTEELFLASH a un titre tres proche, mais le quality gate indique que les preuves de skills sont limitees. Cela montre que BidWise ne s'arrete pas au titre. Il verifie aussi la description, les skills et les signaux metier.

Phrase a dire en montrant `quality_gates.py`:

> Cette separation est implementee dans le backend. Le message `Role aligned, but skill evidence is limited` ou `Skill match without confirmed role alignment` correspond a une condition reelle, pas a un texte invente pour l'interface.

## 5.3 Questions IA probables et reponses

### "Pourquoi ce n'est pas juste une recherche par mots-cles ?"

> Parce que le moteur utilise JobBERT pour comparer le sens global du profil et des offres. Par exemple, maintenance preventive, entretien des equipements et diagnostic de pannes peuvent etre proches metier meme si les mots exacts different. Ensuite les quality gates verifient les preuves concretes.

### "Pourquoi ne pas utiliser uniquement un LLM ?"

> Un LLM temps reel sur chaque recommandation serait lent, couteux et moins stable. BidWise utilise le LLM offline pour enrichir les donnees et l'extraction CV, puis utilise JobBERT et des regles explicables pour classer rapidement les offres.

### "Le score est-il une probabilite d'embauche ?"

> Non. C'est un score de pertinence pour prioriser les opportunites. Il ne predit pas la decision d'un recruteur. Il indique a quel point l'offre est alignee avec le profil, le CV, les preferences et les signaux metier.

### "Pourquoi une offre a 75% peut etre en Related ?"

> Parce que le pourcentage mesure l'intensite du match, alors que le bucket mesure la confiance metier. Une offre peut etre proche semantiquement mais manquer de preuve de role exact ou avoir un gap d'experience. Dans ce cas, elle reste en Related Review.

### "Comment verifier que JobBERT influence vraiment le ranking ?"

> On a des benchmarks et des regenerations d'embeddings. Dans le cas comptable, apres regeneration JobBERT, INTERNATIONAL est remontee fortement. Le code utilise `jobbert_score` dans `recommendation_service.py`, et les resultats sont stockes dans `backend/benchmark_reports`.

### "Comment eviter les hallucinations ?"

> Les hallucinations sont limitees parce que le LLM ne decide pas seul. Pour le CV, on lui impose un JSON strict et on valide la sortie. Pour les opportunites, l'enrichissement est offline et stocke avec metadonnees. Pour les recommandations, les scores viennent du backend, pas du LLM conversationnel.

### "Avez-vous des tests ?"

> Oui. Les tests couvrent les quality gates, les faux positifs, le fallback JobBERT, le retrieval pgvector et l'assistant IA. Les benchmarks metier servent aussi a verifier que les profils types recoivent des offres coherentes.

Commandes:

```powershell
docker compose exec backend python manage.py test tests.test_recommendation_quality_gates --keepdb
docker compose exec backend python manage.py test tests.test_user_recommendations --keepdb
```

## 6. BidWise AI Assistant - 4 min

### Ce que tu montres

1. Ouvrir une recommandation ou une page detail.
2. Ouvrir BidWise AI.
3. Poser: `Explain this opportunity`.
4. Poser: `Is my resume a good match for this role?`
5. Poser: `Generate a motivation letter`.
6. Eventuellement: `Optimize my CV for this role`.

### Speech

> BidWise AI est l'assistant de candidature. Il ne remplace pas le moteur de recommandation. Il explique et aide l'utilisateur a agir.

> L'assistant recoit un contexte structure: offre, profil, CV analyse, score de recommandation, score ATS, mots-cles couverts et manquants, gaps et raisons. Il utilise ensuite un LLM pour formuler une reponse naturelle ou generer des contenus de candidature.

> Les scores ne sont pas inventes par Gemini. Ils sont calcules par le backend. Le LLM sert a expliquer, reformuler et generer une lettre ou une optimisation CV a partir des donnees controlees.

Fichiers:

- `backend/ai/resume_match/evidence.py`
- `backend/ai/resume_match/llm.py`
- `backend/ai/resume_match/chatbot.py`
- `backend/ai/views.py`
- `frontend/src/features/opportunities/components/recommendations/ResumeMatchPanel.jsx`
- `frontend/src/features/opportunities/components/recommendations/OpportunityAssistantChat.jsx`

## 7. Candidature candidat et espace organisation - 4 min

### Ce que tu montres

1. Depuis une offre organisation active, cliquer postuler.
2. Selectionner CV, ajouter lettre de motivation si besoin.
3. Soumettre.
4. Aller dans espace candidat et montrer candidature.
5. Ouvrir espace organisation.
6. Montrer les opportunites publiees, statut, actions.
7. Montrer creation ou edition d'une opportunite si le temps permet.

### Speech

> BidWise couvre aussi le cycle apres recommandation. Le candidat peut postuler directement aux opportunites publiees par les organisations sur la plateforme. Les appels d'offres gardent leur logique propre, mais les jobs, stages et saisonniers peuvent accepter une candidature directe.

> Cote organisation, l'espace permet de publier et gerer ses opportunites. Les organisations ne voient que leurs propres offres. Le backend valide les champs selon le type d'opportunite, applique un rate limit, Turnstile si configure, et une moderation LLM avant publication directe ou passage en review.

> Une opportunite rejetee ou en attente ne peut pas etre activee par simple changement de statut. Les transitions sont controlees pour ne pas contourner la moderation.

Fichiers:

- `backend/docs/ORGANIZATION_DASHBOARD.md`
- Endpoints organisation: `backend/opportunities/views.py` ou vues organisation associees
- Table UI: `frontend/src/features/organization/components/OrganizationOpportunitiesTable.jsx`
- Formulaires organisation: `frontend/src/features/organization/pages/OrganizationLandingPage.jsx`

## 8. Notifications asynchrones - 2 min

### Speech

> Les notifications sont volontairement asynchrones. Les emails OTP, les emails de decision admin pour les organisations, les notifications de candidature et le digest de recommandations ne doivent pas bloquer les requetes HTTP.

> Ces taches sont routees vers la queue `notifications`, consommee par un worker dedie. Cela evite qu'un envoi SMTP ou SendGrid retarde le scraping, les embeddings ou l'analyse CV.

> Le digest candidat est aussi interessant: BidWise peut envoyer chaque jour une courte liste d'opportunites pertinentes, sans spammer l'utilisateur et sans recalculer tout en temps reel.

Fichiers:

- `backend/config/settings.py` pour `CELERY_TASK_ROUTES`
- `backend/opportunities/tasks.py`
- modules `notifications`
- `backend/docs/ORGANIZATION_DASHBOARD.md`, section notifications

## 9. Admin monitoring - 4 min

### Ce que tu montres

1. Dashboard admin global.
2. Operations monitoring.
3. AI supervision.
4. Sources monitoring.
5. Scheduler.
6. Pipeline health.
7. Alerts.
8. Analytics si temps.
9. Flower pour prouver les workers.

### Speech

> L'espace admin n'est pas une page de statistiques decorative. Il est concu comme un espace de supervision. J'ai separe les vues pour ne pas melanger les choses: business overview, operations, AI supervision, sources, scheduler, pipeline, alerts et analytics.

> Le global overview donne la lecture produit: utilisateurs, candidatures, opportunites, croissance. Les operations donnent l'etat runtime: backlog raw, alertes actives, couverture embeddings, media coverage. Les sources montrent quelle source est healthy, running, degraded ou failed.

> Le scheduler explique pourquoi une source va tourner ou attendre. C'est important parce que le scraping n'est pas un simple cron aveugle. Il tient compte de la fraicheur, des echecs, de l'activite et des durees.

> Pipeline health montre le moteur d'ingestion: dernier run, backlog, embeddings manquants et etat Celery. Alerts centralise les anomalies. Analytics est historique, pas une alerte temps reel.

Phrase forte:

> Un monitoring fiable doit distinguer incident actuel, tendance historique, couverture qualite et decision scheduler. C'est cette separation qui rend le dashboard defensible.

### Flower

En ouvrant Flower:

> Ici on peut voir les workers Celery nommes: scraping, enrichment, profile, notifications. Cela prouve que les traitements lourds sont separes. Si le LLM local est lent, il n'occupe pas la queue principale du scraping.

Fichiers:

- `backend/docs/ADMIN_MONITORING_SPEECH.md`
- `backend/opportunities/views_admin.py`
- `backend/opportunities/monitoring.py`
- `backend/opportunities/tasks.py`
- `frontend/src/features/admin/DashboardAdminPage.jsx`

## Conclusion - 1 min

> Pour conclure, BidWise est une plateforme qui va au-dela d'un simple annuaire d'offres. Elle collecte des donnees multi-sources, les nettoie, les enrichit, les rend consultables, puis personnalise l'experience candidat a partir du profil et du CV.

> La partie IA est volontairement hybride et explicable: extraction CV par LLM local, enrichissement offline des offres, embeddings JobBERT, scoring metier, quality gates et benchmarks. Le systeme ne pretend pas etre parfait, mais il est controle, observable et testable.

> Enfin, l'architecture asynchrone et le monitoring admin montrent que le projet a ete pense comme une vraie plateforme operationnelle: API rapide, workers specialises, alertes, dashboard, logs et preuves de fonctionnement.

Phrase finale courte:

> BidWise transforme des opportunites dispersees et heterogenes en recommandations personnalisees, explicables et supervisables.

## Liste rapide: quoi ouvrir si le jury demande le code

### Scraping

- `backend/opportunities/pipeline.py`: scheduler, sources, cadence.
- `backend/opportunities/tasks.py`: Celery collect/source/materialize/embeddings/monitor.
- `backend/opportunities/scraping/pipeline.py`: raw persistence, hash, fingerprint.
- `backend/opportunities/processing.py`: normalisation, enrichment, scoring, materialisation.
- `backend/opportunities/monitoring.py`: anomalies, Discord, recovery.

### Profil et CV

- `backend/users/profile_completion.py`: poids du score profil.
- `backend/users/resume_parsing/service.py`: parsing PDF/DOCX.
- `backend/users/resume_semantic/structured_llm.py`: prompt JSON du CV.
- `backend/users/resume_semantic/service.py`: pipeline semantique CV.
- `backend/users/tasks.py`: tache Celery CV.

### Recommandation IA

- `backend/ai/views.py`: endpoint recommandations et assistant.
- `backend/ai/retrieval.py`: retrieval semantique.
- `backend/ai/recommendation_service.py`: scoring hybride.
- `backend/ai/quality_gates.py`: Strong vs Related.
- `backend/ai/jobbert.py`: modele et scores JobBERT.
- `backend/ai/explainability.py`: raisons affichees.
- `backend/benchmark_reports/reco_comptable_after_jobbert.json`
- `backend/benchmark_reports/reco_final_demo_profiles.json`

### Assistant IA

- `backend/ai/resume_match/evidence.py`: contexte structure.
- `backend/ai/resume_match/llm.py`: prompts RH/ATS.
- `backend/ai/resume_match/chatbot.py`: chatbot controle.
- `frontend/src/features/opportunities/components/recommendations/OpportunityAssistantChat.jsx`

### Admin monitoring

- `backend/opportunities/views_admin.py`: API dashboard admin.
- `backend/opportunities/monitoring.py`: anomalies et alertes.
- `frontend/src/features/admin/DashboardAdminPage.jsx`

## Formulations a eviter

- Eviter: "L'IA choisit automatiquement les meilleures offres."
- Dire: "Le moteur calcule un score de pertinence et classe les offres avec des preuves explicables."

- Eviter: "Le score est une probabilite d'embauche."
- Dire: "Le score sert a prioriser les opportunites; il ne predit pas la decision du recruteur."

- Eviter: "Le LLM fait toute la recommandation."
- Dire: "Le LLM enrichit et explique; le ranking est calcule par embeddings et regles metier."

- Eviter: "Le scraping tourne en direct quand on ouvre la page."
- Dire: "Le scraping est asynchrone; l'interface lit les opportunites materialisees."

## Plan B si la demo live a un probleme

Si OTP email est lent:

> Les emails OTP sont asynchrones via Celery. Pour la soutenance, je peux soit attendre le worker notifications, soit utiliser un compte deja prepare. Le flux reste celui-ci: request OTP, verification, creation compte, JWT.

Si le LLM est lent:

> Les appels LLM sont volontairement offline ou caches. Je vais montrer les resultats deja stockes et le code qui produit ces traitements. C'est justement un choix d'architecture: ne pas rendre la demo dependante d'un appel LLM temps reel.

Si une source de scraping est bloquee:

> Les sources externes peuvent changer ou limiter les requetes. C'est pour cela que BidWise stocke les raw records, applique des cadences, des retries, des locks, et surveille les anomalies dans l'admin dashboard.

Si une recommandation n'apparait plus exactement comme dans la doc:

> Le dataset evolue avec le scraping. Je vais ouvrir les benchmarks versionnes pour montrer le comportement valide et expliquer que les scores exacts changent avec les donnees, mais que la logique Strong/Related, JobBERT et quality gates reste la meme.
