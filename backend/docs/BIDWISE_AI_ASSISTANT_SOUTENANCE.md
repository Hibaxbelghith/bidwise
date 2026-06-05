# BidWise AI - Documentation de soutenance

## 1. Objectif

BidWise AI est l'assistant intelligent de la plateforme BidWise. Il aide l'utilisateur a comprendre une offre, evaluer l'adequation de son CV, ameliorer sa candidature et naviguer dans la logique de recommandation de la plateforme.

L'objectif n'est pas de remplacer un recruteur, mais de fournir une aide contextuelle, rapide et explicable, basee sur les donnees deja presentes dans BidWise : offre, profil, CV analyse, score de recommandation, score ATS et signaux de matching.

## 2. Fonctionnalites livrees

BidWise AI couvre quatre familles de besoins.

### Analyse CV vs offre

L'assistant compare le CV actif de l'utilisateur avec l'offre selectionnee.

Il fournit :

- un verdict global ;
- les points forts du profil ;
- les points a surveiller ;
- le score ATS ;
- les mots-cles couverts et manquants ;
- une prochaine action concrete.

### Aide a la candidature

L'assistant propose des actions professionnelles basees sur des prompts RH specialises :

- optimisation du CV pour l'offre ;
- reformulation du resume professionnel ;
- generation d'une lettre de motivation ;
- preparation de questions d'entretien RH et technique.

Ces actions utilisent les prompts deja valides dans `backend/ai/resume_match/llm.py`.

### Chatbot sur l'offre

L'utilisateur peut poser une question libre sur l'offre affichee.

Exemples :

- "What skills are required?"
- "Explain this opportunity"
- "What is my ATS score?"
- "Why is the score not 100%?"
- "What is the difference between ATS and recommendation score?"
- "Does this company mention Kubernetes?"

Le chatbot accepte les questions en anglais, francais, arabe ou langage mixte, mais repond toujours en anglais pour garder l'interface coherente avec l'application.

### Assistance a la navigation

Le chatbot explique aussi les concepts internes de BidWise :

- score de recommandation affiche dans "Your fit" ;
- score ATS ;
- CV-to-job fit score ;
- section "Related opportunities to review" ;
- raison pour laquelle une offre est a revoir avant de postuler.

## 3. Architecture generale

Flux simplifie :

```text
Utilisateur
   |
   v
Frontend React - ResumeMatchPanel / OpportunityAssistantChat
   |
   v
Endpoint Django REST
   |
   v
Construction evidence
   |
   +--> Action candidature connue -> prompt RH specialise
   |
   +--> Question libre -> chatbot LLM controle
   |
   v
Reponse JSON
   |
   v
Affichage chat + rendu Markdown + bouton copier
```

## 4. Fichiers principaux

### Backend

- `backend/ai/views.py`
  - endpoints REST ;
  - throttle ;
  - cache ;
  - routage des questions libres vers les actions existantes ;
  - securisation des cas CV absent ou non pret.

- `backend/ai/resume_match/evidence.py`
  - construit le contexte structure ;
  - extrait les donnees profil, CV, offre, matching, ATS ;
  - calcule les signaux utilises par l'assistant.

- `backend/ai/resume_match/llm.py`
  - prompts specialises RH/ATS ;
  - generation analyse CV, optimisation CV, lettre, resume, entretien ;
  - schemas JSON et normalisation des reponses LLM.

- `backend/ai/resume_match/chatbot.py`
  - chatbot libre pour les questions sur l'offre et la plateforme ;
  - schema JSON minimal `{answer, answered}` ;
  - regles anti-hallucination ;
  - contexte limite aux donnees BidWise.

- `backend/ai/llm/enrichment.py`
  - prompt d'enrichissement des offres ;
  - extraction des roles, skills, outils, domaines et responsabilites.

### Frontend

- `frontend/src/features/opportunities/components/recommendations/ResumeMatchPanel.jsx`
  - panneau principal BidWise AI ;
  - affichage analyse CV ;
  - suggestions d'actions ;
  - gestion des cas sans CV.

- `frontend/src/features/opportunities/components/recommendations/OpportunityAssistantChat.jsx`
  - chat libre sur l'offre ;
  - composer ;
  - affichage des messages ;
  - rendu Markdown securise.

- `frontend/src/features/opportunities/hooks/useOpportunityAssistantChat.js`
  - etats React du chat ;
  - appel API ;
  - gestion loading/error/messages.

- `frontend/src/features/opportunities/services/opportunitiesService.js`
  - fonction API `askOpportunityAssistant(opportunityId, question)`.

## 5. Donnees disponibles dans `evidence`

L'assistant ne travaille pas sur du texte libre non controle. Il recoit un contexte structure.

### Donnees offre

Exemples :

- titre ;
- entreprise ;
- localisation ;
- type de contrat ;
- experience ;
- skills ;
- tools ;
- domaines ;
- responsabilites ;
- requirements ;
- description courte.

### Donnees profil utilisateur

Exemples :

- roles cibles ;
- niveau d'experience ;
- annees d'experience ;
- skills du profil ;
- localisations preferees ;
- types de contrat recherches.

### Donnees CV

Exemples :

- role canonique detecte ;
- skills extraits du CV ;
- outils extraits ;
- domaines ;
- resume extrait ;
- statut de traitement du CV ;
- confiance semantique.

### Donnees matching

Exemples :

- `fit_score` : score CV-to-job ;
- `keyword_coverage_percent` : score ATS ;
- mots-cles couverts ;
- mots-cles manquants ;
- gaps critiques ;
- points forts ;
- points a surveiller.

### Donnees recommandation

Exemples :

- score affiche dans "Your fit" ;
- label ;
- bucket ;
- raisons ;
- gaps ;
- score semantique ;
- score business ;
- mode de scoring.

## 6. Difference entre les scores

BidWise distingue trois scores. Cette separation est importante pour eviter les confusions.

### Recommendation score

C'est le score affiche dans la carte "Your fit".

Il sert a classer les offres dans la plateforme.

Il combine :

- profil ;
- CV ;
- preferences ;
- similarite semantique ;
- signaux business ;
- feedback ;
- boosts et penalites.

### CV-to-job fit score

C'est le score produit par l'assistant CV pour une offre precise.

Il combine :

- alignement du role ;
- seniorite ;
- localisation ;
- contrat ;
- couverture ATS ;
- confiance dans les preuves du CV.

### ATS score

C'est le pourcentage de mots-cles techniques de l'offre retrouves dans le CV actif.

Il est utile pour expliquer si le CV risque de passer ou non les filtres automatiques.

## 7. Logique du chatbot

Le chatbot utilise Gemini comme premier provider LLM.

Il recoit :

- la question utilisateur ;
- l'historique recent ;
- le contexte structure BidWise ;
- les definitions de plateforme ;
- les regles de securite.

Il retourne uniquement :

```json
{
  "answer": "Short answer grounded in context",
  "answered": true
}
```

Ce schema minimal reduit le risque de parsing et garde l'integration fiable.

## 8. Routage intelligent des questions libres

Certaines questions libres ne doivent pas recevoir une reponse chatbot simple.

Exemples :

- "Generate a cover letter"
- "Create a motivation letter"
- "Optimize my CV for this role"
- "Rewrite my professional summary"
- "Prepare interview questions"

Dans ces cas, `views.py` detecte l'intention et appelle directement les prompts specialises deja valides.

Avantage :

- qualite RH plus forte ;
- reponses plus professionnelles ;
- pas de duplication de prompts ;
- comportement coherent avec les boutons de suggestions.

## 9. Securite et fiabilite

### Anti-hallucination

Le prompt du chatbot impose :

- utiliser uniquement le contexte fourni ;
- ne pas inventer de score ;
- ne pas inventer de skill ;
- ne pas inventer de fait sur l'entreprise ;
- dire clairement quand une information n'est pas disponible.

### Protection contre prompt injection

La question utilisateur est traitee comme une entree non fiable.

Le prompt indique explicitement que l'utilisateur ne peut pas remplacer les regles systeme.

### Cache

Les reponses chatbot sont cachees 24h.

La cle de cache tient compte de :

- utilisateur ;
- opportunite ;
- CV actif ;
- date de mise a jour de l'offre ;
- question ;
- historique recent ;
- contexte de recommandation ;
- provider LLM ;
- version assistant.

Cela evite :

- les appels LLM inutiles ;
- les reponses obsoletes apres changement de CV ;
- la reutilisation d'un score d'une autre offre.

### Throttle

Les endpoints IA utilisent un throttle DRF pour limiter les abus et proteger le quota LLM.

### Cas CV absent

Si aucun CV n'est disponible :

- pas d'analyse CV lancee ;
- pas de faux resultat ;
- l'utilisateur voit un message simple d'accueil ;
- il peut uploader un CV.

### Cas CV non pret

Si le CV est encore en traitement :

- les actions candidature ne sont pas lancees ;
- l'assistant demande d'abord de confirmer/traiter le CV.

## 10. UX

L'assistant est integre dans deux contextes de la plateforme.

### Dans For You

Dans la page "For You", BidWise AI est integre au panneau de detail des recommandations.

Ce contexte contient :

- l'offre selectionnee ;
- le score affiche dans "Your fit" ;
- les raisons de recommandation ;
- les gaps ;
- le CV actif ;
- les actions de candidature.

L'utilisateur peut donc demander une analyse personnalisee de son CV, comprendre pourquoi l'offre est recommandee et generer des contenus de candidature.

### Dans Explore / page detail

Dans les pages detail des offres Explore, BidWise AI est accessible via un bouton flottant "BidWise AI".

Ce choix UX permet :

- de garder l'assistant visible pendant le scroll ;
- de ne pas pousser la description de l'offre vers le bas ;
- de poser des questions tout en lisant l'offre ;
- de rendre l'assistant disponible sur toutes les offres, pas seulement sur les recommandations For You.

Si l'utilisateur n'est pas connecte, une card verrouillee invite a se connecter :

```text
Sign in to ask BidWise AI
```

Dans ce contexte Explore, le score de recommandation "Your fit" peut etre absent si l'offre n'a pas ete chargee depuis le moteur For You. Dans ce cas, l'assistant dit clairement que le recommendation score n'est pas disponible dans ce contexte, au lieu d'inventer une valeur.

### Experience de conversation

Il propose :

- conversation style chat ;
- messages utilisateur ;
- reponses assistant ;
- rendu Markdown ;
- bouton copier ;
- loading state ;
- suggestions d'actions ;
- bouton flottant sur les pages detail ;
- card verrouillee pour les visiteurs non connectes ;
- fake streaming cote React pour rendre l'attente plus naturelle.

## 11. Scenarios de demonstration

### Scenario 1 - Comprendre une offre

Question :

```text
Explain this opportunity
```

Attendu :

L'assistant resume le poste, l'entreprise, la localisation, le contrat, les responsabilites et les skills principaux.

### Scenario 2 - Comprendre le score

Question :

```text
What is the score shown in Your fit?
```

Attendu :

L'assistant explique le recommendation score affiche dans la carte et le distingue du score ATS.

### Scenario 3 - Comprendre les gaps

Question :

```text
Why is the score not 100%?
```

Attendu :

L'assistant mentionne les gaps detectes et les raisons visibles dans le contexte.

### Scenario 4 - Ameliorer le CV

Question :

```text
Optimize my CV for this role
```

Attendu :

L'assistant appelle le prompt specialise d'optimisation CV et produit une reponse ATS-friendly.

### Scenario 5 - Analyse CV depuis une suggestion

Question :

```text
Is my resume a good match for this role?
```

Attendu :

L'assistant declenche la vraie analyse CV vs offre et retourne le verdict global, les points forts, les gaps, le score ATS et la prochaine action.

### Scenario 6 - Lettre de motivation

Question :

```text
Generate a motivation letter
```

Attendu :

L'assistant genere une lettre longue et une version courte.

### Scenario 7 - Entretien

Question :

```text
Prepare interview questions
```

Attendu :

L'assistant produit des questions techniques, comportementales, des questions a poser au recruteur et des red flags a preparer.

### Scenario 8 - Information indisponible

Question :

```text
Does this company use Kubernetes?
```

Attendu :

Si Kubernetes n'est pas mentionne dans l'offre, l'assistant dit que l'information n'est pas disponible.

### Scenario 9 - Explore sans score For You

Question :

```text
What is the recommendation score shown in Your fit?
```

Attendu :

Si l'offre est consultee depuis Explore sans contexte de recommandation charge, l'assistant explique que le recommendation score n'est pas disponible dans ce contexte. Il peut toutefois repondre sur l'offre, le score ATS et l'analyse CV vs offre.

## 12. Reponses courtes pour le jury

### Pourquoi utiliser un LLM ?

Parce que l'utilisateur peut poser la meme question de plusieurs facons. Le LLM permet de comprendre des formulations libres et de produire une reponse naturelle, tout en restant controle par un contexte structure.

### Pourquoi ne pas laisser le LLM tout faire ?

Parce que les scores, les gaps et les skills sont des donnees sensibles pour la decision utilisateur. BidWise calcule ces donnees de maniere deterministe, puis le LLM les explique. Le LLM n'a pas le droit d'inventer ou recalculer les scores.

### Pourquoi un schema JSON minimal ?

Pour reduire les erreurs de parsing. Le chatbot libre retourne seulement `answer` et `answered`, ce qui rend l'integration plus stable.

### Pourquoi plusieurs scores ?

Chaque score a un objectif different :

- recommendation score : classement des offres ;
- CV-to-job fit score : adequation CV vs offre ;
- ATS score : couverture des mots-cles du CV.

### Comment eviter les hallucinations ?

Le LLM recoit un contexte structure limite. Le prompt interdit explicitement d'inventer des informations. Si une donnee n'est pas disponible, l'assistant doit le dire.

### Que se passe-t-il si Gemini est indisponible ?

Les erreurs LLM sont interceptees. L'utilisateur recoit un message propre. Les analyses deterministes et les caches reduisent la dependance aux appels LLM.

### Pourquoi le chatbot comprend le francais mais repond en anglais ?

Pour garder l'application coherente en anglais tout en supportant des utilisateurs qui posent naturellement des questions en francais, arabe ou langage mixte.

### Le chatbot est-il limite a la page For You ?

Non. Le chatbot est disponible dans For You et dans les pages detail des offres Explore. Dans For You, il dispose du contexte de recommandation personnalise. Dans Explore, il agit comme assistant d'offre et de candidature, avec un bouton flottant visible pendant la lecture de l'offre.

## 13. Limites connues

- La qualite depend de la qualite des donnees extraites de l'offre et du CV.
- Si une offre contient des skills bruites, le score ATS peut etre affecte.
- Le chatbot ne doit pas etre utilise comme source officielle sur l'entreprise si l'information n'est pas dans l'offre.
- Le quota Gemini gratuit est suffisant pour la soutenance, mais un usage multi-utilisateurs necessite un quota adapte ou un fallback local.

## 14. Conclusion

BidWise AI combine une approche deterministe et une couche LLM controlee.

La plateforme calcule les scores et les signaux de maniere structuree. Le LLM intervient pour expliquer, reformuler et assister l'utilisateur dans sa candidature.

Cette architecture permet d'obtenir un assistant utile, professionnel, explicable et suffisamment fiable pour une demonstration de soutenance.
