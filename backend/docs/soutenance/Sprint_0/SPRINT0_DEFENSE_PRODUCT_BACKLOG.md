# Sprint 0 - Défense du Product Backlog

## 1. Objectif

Ce document prépare la défense du Product Backlog pendant la soutenance
technique. Il explique :

- la logique Scrum utilisée ;
- la signification des User Stories ;
- la priorisation MoSCoW ;
- l'estimation en Story Points ;
- la planification des sprints ;
- les réponses aux questions probables du jury.

Il ne remplace pas le rapport académique. Il sert de support oral et de grille
de réponse.

## 2. Comment présenter le Product Backlog

Phrase d'introduction :

> Le Product Backlog regroupe les fonctionnalités attendues de BidWise sous
> forme de User Stories. Chaque User Story exprime un besoin du point de vue
> d'un acteur, sa valeur métier, sa priorité MoSCoW et une estimation en Story
> Points. Ce backlog a servi de base pour organiser le développement en sprints
> progressifs.

Le backlog contient :

- 50 User Stories ;
- 181 Story Points ;
- 5 sprints de réalisation après le Sprint 0 ;
- des priorités Must Have, Should Have et Could Have.

## 3. Qu'est-ce qu'une User Story ?

Une User Story est une formulation courte d'un besoin utilisateur.

Format utilisé :

```text
En tant que [acteur],
je veux [fonctionnalité],
afin de [valeur métier].
```

Exemple :

```text
En tant que candidat,
je veux recevoir des opportunités personnalisées,
afin de gagner du temps dans ma recherche.
```

Elle ne décrit pas tous les détails techniques. Les détails sont précisés dans :

- les critères d'acceptation ;
- le Sprint Backlog ;
- les diagrammes de conception ;
- l'implémentation.

Réponse orale :

> Une User Story n'est pas un cahier technique détaillé. Elle exprime la valeur
> attendue pour un acteur. Les choix techniques, comme Celery, pgvector ou les
> modèles IA, sont ensuite détaillés dans la conception et la réalisation.

## 4. Différence entre User Story et cas d'utilisation UML

Une User Story est agile, courte et orientée valeur.

Un cas d'utilisation UML est plus détaillé. Il décrit :

- l'acteur principal ;
- les préconditions ;
- le scénario nominal ;
- les scénarios alternatifs ;
- les postconditions.

Réponse orale :

> Le Product Backlog donne une vision agile des besoins. Les diagrammes UML
> complètent cette vision en décrivant les interactions plus formelles entre les
> acteurs et le système.

## 5. Qu'est-ce que MoSCoW ?

MoSCoW est une technique de priorisation.

| Catégorie | Signification |
|---|---|
| Must Have | Fonction indispensable au produit |
| Should Have | Fonction importante mais négociable |
| Could Have | Fonction utile, valeur ajoutée, mais non critique |
| Won't Have | Hors périmètre de la version actuelle |

Dans BidWise, la priorisation finale est :

| Priorité | Interprétation dans BidWise |
|---|---|
| Must Have | Fonction nécessaire pour atteindre l'objectif principal |
| Should Have | Fonction importante pour améliorer l'usage ou la supervision |
| Could Have | Fonction complémentaire ou confort utilisateur |

## 6. Pourquoi certaines fonctionnalités sont Must Have ?

Les Must Have correspondent au noyau du projet :

- authentification et onboarding ;
- gestion des profils ;
- consultation et recherche d'opportunités ;
- collecte multi-source ;
- publication d'opportunités par les organisations ;
- recommandation personnalisée ;
- candidatures ;
- assistance IA principale.

Réponse orale :

> Nous avons classé Must Have les fonctionnalités sans lesquelles BidWise ne
> répondrait plus à sa problématique centrale : centraliser des opportunités,
> recommander les plus pertinentes et assister le candidat.

## 7. Pourquoi certaines fonctionnalités sont Should Have ?

Les Should Have sont importantes, mais le produit peut rester utilisable si
elles sont livrées plus tard ou sous une forme réduite.

Exemples :

- statistiques organisation ;
- explicabilité avancée ;
- supervision IA ;
- notifications ;
- modération avancée ;
- supervision des sources.

Réponse orale :

> Les Should Have renforcent la qualité, la confiance et la supervision, mais
> elles ne bloquent pas toutes le fonctionnement minimal de la plateforme.

## 8. Pourquoi 4.13, 5.1 et 5.2 sont Could Have ?

### 4.13 - Questions d'entretien IA

Cette fonctionnalité enrichit l'assistance IA mais n'est pas indispensable au
processus principal de candidature.

Réponse orale :

> La préparation aux entretiens a été classée Could Have parce qu'elle apporte
> une valeur ajoutée, mais elle n'est pas exigée comme noyau fonctionnel dans le
> cahier des charges.

### 5.1 et 5.2 - Favoris

Les favoris améliorent le confort utilisateur, mais la plateforme reste
fonctionnelle sans eux.

Réponse orale :

> Les favoris facilitent la navigation et la reprise de recherche, mais ils ne
> conditionnent pas la collecte, la recommandation ni la candidature.

## 9. Pourquoi il n'y a pas de Won't Have ?

Le backlog présenté correspond au périmètre retenu pour la version du projet.
Les fonctionnalités explicitement hors périmètre sont plutôt décrites dans les
limites ou perspectives.

Réponse orale :

> Dans notre rapport, nous avons surtout distingué ce qui est indispensable,
> important ou complémentaire. Les éléments hors périmètre, comme une messagerie
> interne complète ou une architecture microservices, sont traités dans les
> limites et perspectives plutôt que dans le Product Backlog.

## 10. Qu'est-ce qu'un Story Point ?

Un Story Point est une estimation relative de complexité.

Il ne correspond pas directement à un nombre d'heures ou de jours.

Il prend en compte :

- l'effort de développement ;
- la complexité technique ;
- l'incertitude ;
- les dépendances ;
- le risque ;
- les tests et l'intégration.

Réponse orale :

> Un Story Point n'est pas une durée. C'est une mesure relative qui nous permet
> de comparer la complexité des User Stories entre elles.

## 11. Sur quelle base les SP ont-ils été estimés ?

Les estimations ont été faites à partir de plusieurs critères :

| Critère | Exemple dans BidWise |
|---|---|
| Nombre d'écrans ou endpoints | auth simple vs dashboard admin |
| Complexité métier | candidature directe vs recommandation |
| Incertitude technique | scraping multi-source, IA |
| Dépendances | profil + CV + opportunité |
| Risque d'intégration | Celery, pgvector, LLM |
| Besoin de tests | sécurité, permissions, statuts |

Échelle utilisée :

| SP | Interprétation |
|---:|---|
| 1 | très simple |
| 2 | simple |
| 3 | moyen |
| 5 | complexe |
| 13 | très complexe / forte incertitude |

Réponse orale :

> Les SP ont été estimés de manière relative. Par exemple, une déconnexion est
> beaucoup plus simple qu'un pipeline de collecte multi-source. C'est pourquoi
> elle reçoit 1 SP, alors que la collecte reçoit 13 SP.

## 12. Pourquoi certaines stories ont 13 SP ?

Deux stories sont estimées à 13 SP :

- `2.8` : opportunités collectées automatiquement depuis plusieurs sources ;
- `3.1` : recommandations personnalisées à partir du profil, du CV et des
  caractéristiques de l'offre.

Ces stories présentent une forte complexité et une forte incertitude.

### 2.8 - Collecte multi-source

Elle implique :

- connecteurs de sources ;
- stockage des données brutes ;
- normalisation ;
- déduplication ;
- contrôle qualité ;
- planification périodique ;
- matérialisation des opportunités ;
- supervision des exécutions.

### 3.1 - Recommandation intelligente

Elle implique :

- exploitation du profil ;
- analyse du CV ;
- embeddings ;
- similarité sémantique ;
- règles métier ;
- classement ;
- exposition dans l'API et l'interface.

Réponse orale :

> Avec le recul, ces stories auraient pu être découpées davantage dans le
> Product Backlog. Pendant la réalisation, elles ont bien été divisées en tâches
> techniques dans les Sprint Backlogs.

## 13. Pourquoi les sprints ne sont pas équilibrés ?

Répartition :

| Sprint | SP |
|---|---:|
| Sprint 1 | 29 |
| Sprint 2 | 53 |
| Sprint 3 | 23 |
| Sprint 4 | 43 |
| Sprint 5 | 33 |

Cette répartition n'est pas parfaitement équilibrée, mais elle est explicable.

Raisons :

- les SP ne sont pas une durée exacte ;
- la vélocité n'était pas encore stabilisée ;
- le Sprint 2 contient une forte incertitude liée au pipeline de collecte ;
- certaines tâches techniques ont été parallélisées ;
- certaines User Stories complexes ont été découpées à l'intérieur du Sprint
  Backlog ;
- l'objectif était de livrer des incréments cohérents, pas des totaux SP
  identiques.

Réponse orale :

> Nous n'avons pas cherché à avoir le même nombre de Story Points par sprint.
> Nous avons regroupé les fonctionnalités par cohérence métier. Le Sprint 2 est
> plus lourd car il porte le socle des opportunités et de la collecte, qui est un
> élément central de BidWise.

## 14. Pourquoi ne pas avoir changé les SP après réalisation ?

Les SP sont des estimations initiales. Les modifier après coup peut donner une
vision artificielle du projet.

Réponse orale :

> Nous avons conservé les estimations historiques, car elles représentent notre
> planification initiale. L'écart entre estimation et complexité réelle fait
> partie du retour d'expérience Scrum.

## 15. Pourquoi planifier les sprints dans cet ordre ?

L'ordre respecte une progression fonctionnelle :

### Sprint 1 - Authentification et utilisateurs

Objectif :

- créer l'identité utilisateur ;
- sécuriser l'accès ;
- poser les rôles candidat, organisation et administrateur.

Sans authentification, les profils, candidatures et recommandations
personnalisées ne peuvent pas fonctionner.

### Sprint 2 - Profils, opportunités et collecte

Objectif :

- permettre aux utilisateurs de décrire leur profil ;
- centraliser les opportunités ;
- permettre aux organisations de publier ;
- alimenter la plateforme par collecte multi-source.

Ce sprint fournit la matière première de BidWise : les opportunités et les
profils.

### Sprint 3 - Recommandation intelligente

Objectif :

- exploiter les profils et opportunités ;
- calculer des correspondances personnalisées ;
- expliquer les recommandations.

Ce sprint dépend naturellement du Sprint 2.

### Sprint 4 - Candidatures et assistance IA

Objectif :

- transformer la recommandation en action ;
- permettre de candidater ;
- assister le candidat dans la préparation.

Ce sprint dépend des profils, opportunités et recommandations.

### Sprint 5 - Notifications, administration et supervision

Objectif :

- améliorer le suivi ;
- superviser la plateforme ;
- contrôler la qualité et les sources.

Ce sprint consolide le produit pour une utilisation plus professionnelle.

Réponse orale :

> L'ordre des sprints suit la chaîne de valeur : identifier l'utilisateur,
> construire son profil, collecter les opportunités, recommander, candidater,
> puis superviser et notifier.

## 16. Pourquoi Sprint 5 n'est plus nommé DevOps ?

Le titre initial mentionnait DevOps, mais les User Stories décrivent surtout :

- notifications ;
- administration ;
- supervision ;
- modération ;
- surveillance des sources.

Docker et les tâches techniques existent dans le projet, mais elles ne sont pas
formalisées comme User Stories utilisateur dans ce backlog.

Réponse orale :

> Nous avons retiré DevOps du titre du Sprint 5 pour rester fidèles au contenu
> réel du backlog. Les aspects Docker et environnement sont présentés comme des
> tâches techniques transversales, pas comme des User Stories fonctionnelles.

## 17. Comment défendre une User Story jugée vague ?

Si le jury dit :

> Cette User Story n'est pas assez précise.

Réponse :

> La User Story exprime volontairement le besoin à haut niveau. Les détails sont
> ensuite précisés par les critères d'acceptation et les tâches du Sprint
> Backlog. Nous avons d'ailleurs clarifié certaines stories après audit, par
> exemple la session sécurisée, la supervision IA et le contact candidat.

## 18. Stories sensibles et réponses prêtes

### 1.5 - Session sécurisée

Réponse :

> Cette story correspond au maintien de session via JWT, refresh token et
> rotation sécurisée. Elle a été reformulée pour éviter une expression trop
> vague.

### 2.8 - Collecte multi-source

Réponse :

> Le visiteur ne lance pas la collecte. La valeur côté visiteur est de consulter
> des opportunités régulièrement mises à jour depuis plusieurs sources. Le
> scraping est un mécanisme technique permettant de satisfaire cette valeur.

### 3.3 - Supervision IA

Réponse :

> Nous ne prétendons pas mesurer une précision globale abstraite. La supervision
> IA porte sur des métriques observables : couverture, statuts, confiance
> lorsqu'elle existe, fallbacks, avertissements et disponibilité des embeddings.

### 4.8 - Contacter un candidat

Réponse :

> Il ne s'agit pas d'une messagerie interne. BidWise ouvre un email prérempli
> vers le candidat à partir de l'interface organisation.

### 5.3 - Notifications

Réponse :

> Nous avons choisi une User Story globale car les notifications partagent une
> logique commune d'information utilisateur. Les types de notifications sont
> ensuite détaillés dans les critères d'acceptation et l'implémentation.

## 19. Questions Scrum probables

### Pourquoi Scrum ?

> Scrum était adapté parce que le projet combinait plusieurs risques :
> authentification, scraping, IA, recommandation, Web et Mobile. Les sprints ont
> permis de livrer progressivement et de valider les briques principales.

### Quelle différence entre Product Backlog et Sprint Backlog ?

> Le Product Backlog contient l'ensemble des besoins du produit. Le Sprint
> Backlog contient les User Stories sélectionnées pour un sprint et leur
> découpage en tâches concrètes.

### Qui priorise le Product Backlog ?

> Le Product Owner priorise selon la valeur métier, les contraintes du cahier
> des charges, les dépendances techniques et les risques.

### Qu'est-ce qu'une vélocité ?

> La vélocité est le nombre de Story Points qu'une équipe arrive généralement à
> terminer pendant un sprint. Elle devient fiable après plusieurs sprints, pas
> dès le début du projet.

### Pourquoi vos sprints n'ont-ils pas la même vélocité ?

> Au début, la vélocité n'était pas encore stabilisée. De plus, les sprints
> n'avaient pas le même niveau d'incertitude technique. Le Sprint 2 contenait un
> fort risque lié à la collecte multi-source.

### Est-ce grave d'avoir une story à 13 SP ?

> Ce n'est pas interdit, mais c'est un signal de complexité. Avec le recul, il
> aurait été préférable de découper ces stories en plusieurs User Stories plus
> petites.

### Est-ce qu'un Could Have peut être réalisé ?

> Oui. Could Have signifie que la fonctionnalité est moins prioritaire, pas
> qu'elle est interdite. Si l'équipe a la capacité de la réaliser, elle peut être
> livrée comme valeur ajoutée.

### Pourquoi ne pas avoir mis plus de Won't Have ?

> Les éléments hors périmètre sont plutôt traités dans les limites et
> perspectives du rapport. Le backlog se concentre sur les fonctionnalités
> retenues pour la version du projet.

## 20. Limites méthodologiques à reconnaître

Il est préférable de reconnaître calmement :

- certaines stories étaient larges ;
- le Sprint 2 était chargé ;
- MoSCoW aurait pu être plus discriminant dès le départ ;
- certaines estimations ont révélé de l'incertitude pendant la réalisation.

Phrase utile :

> Ces limites ne remettent pas en cause le projet. Elles montrent surtout les
> apprentissages méthodologiques réalisés pendant le PFE.

## 21. Réponse finale de défense

> Notre Product Backlog comprend 50 User Stories pour 181 Story Points. Il a été
> organisé selon la valeur métier et les dépendances techniques : d'abord
> l'identité utilisateur, ensuite les profils et opportunités, puis la
> recommandation, les candidatures et enfin la supervision. Les Story Points ont
> été estimés de manière relative selon la complexité, l'incertitude et les
> dépendances. Les sprints ne sont pas parfaitement équilibrés, notamment parce
> que le pipeline de collecte et la recommandation portaient une forte
> incertitude technique. Avec le recul, certaines stories auraient pu être
> découpées plus finement, mais le backlog reste cohérent avec l'objectif et la
> progression du projet BidWise.
