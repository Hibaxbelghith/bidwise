# Sprint 0 - Justifications techniques pour la soutenance

## 1. Objectif du document

Ce document conserve les décisions prises pendant l'actualisation du Sprint 0.
Il complète le rapport académique avec les arguments nécessaires à la
soutenance technique.

Pour chaque décision, il distingue :

- ce qui est réellement implémenté dans BidWise ;
- la raison du choix ;
- la limite à reconnaître devant le jury ;
- une réponse orale courte.

Ce document doit évoluer après l'audit des besoins, des diagrammes UML et du
Product Backlog.

## 2. Vocabulaire du domaine

### Décision

Le titre officiel du projet peut conserver l'expression « appels d'offres ».
Dans le contenu, le terme générique « opportunité » désigne les offres d'emploi,
les stages, les emplois saisonniers et les appels d'offres.

### Justification

Dans son sens professionnel strict, un appel d'offres correspond principalement
à une consultation ou à un marché auquel des prestataires répondent. Une offre
d'emploi ou de stage n'est pas normalement un appel d'offres.

Cette distinction est également cohérente avec le modèle actuel, qui contient
les catégories `EMPLOI`, `STAGE`, `SAISONNIER` et `PROJET`.

### Limite à reconnaître

Le titre historique du projet emploie « appels d'offres » dans un sens large.
Il faut donc définir le vocabulaire une fois dans le rapport pour éviter toute
ambiguïté.

### Réponse orale

> Le titre conserve la terminologie initiale du sujet. Dans notre modèle métier,
> nous utilisons cependant « opportunité » comme terme générique, tandis que
> « appel d'offres » désigne la catégorie spécifique des marchés et consultations.

## 3. Périmètre fonctionnel annoncé

### Décision

Remplacer « automatiser l'ensemble du cycle de vie » par une formulation plus
précise : BidWise couvre une chaîne allant de la collecte à l'assistance et au
suivi de la candidature.

### Justification

BidWise collecte, normalise, enrichit et recommande des opportunités. Il assiste
également le candidat dans l'analyse CV-offre et la préparation de contenus.
Toutefois, le mode de candidature dépend de l'origine de l'opportunité :

- une candidature peut être déposée directement pour une opportunité interne ;
- une opportunité externe redirige vers le site source, puis son état peut être
  suivi dans BidWise.

Parler d'automatisation complète pourrait laisser entendre que BidWise soumet
automatiquement toutes les candidatures, ce qui n'est pas le cas.

### Réponse orale

> Nous automatisons et assistons le processus, mais nous ne prétendons pas
> automatiser la décision ou la soumission sur toutes les plateformes externes.
> Pour ces dernières, BidWise centralise l'information, redirige le candidat et
> lui permet de suivre sa démarche.

## 4. Étude de l'existant

### Décision

Remplacer l'affirmation absolue « aucune solution existante » par « parmi les
solutions étudiées ».

### Justification

Une étude académique porte sur un périmètre et une période donnés. Il serait
difficile de prouver qu'aucune solution mondiale ne combine certaines
fonctionnalités. La nouvelle formulation limite correctement la conclusion au
panel comparé.

### Formulation défendable

> Parmi les solutions étudiées, aucune ne réunit simultanément, au sein d'une
> même plateforme Web et Mobile, la collecte automatisée d'opportunités issues
> de sources hétérogènes, la recommandation personnalisée et l'assistance
> contextuelle à la préparation des candidatures.

### Réponse orale

> Notre conclusion ne prétend pas couvrir toutes les solutions du marché. Elle
> résulte de la comparaison du panel défini dans l'étude de l'existant.

## 5. Planification des sprints

### Décision

La durée officielle est de trois à quatre semaines par sprint :

- Sprint 0 : 3 semaines ;
- Sprint 1 : 3 semaines ;
- Sprint 2 : 4 semaines ;
- Sprint 3 : 4 semaines ;
- Sprint 4 : 4 semaines ;
- Sprint 5 : 3 semaines.

La mention « deux à trois semaines » doit être supprimée.

### Justification

Cette durée correspond au tableau de planification retenu et varie selon la
complexité fonctionnelle et technique du périmètre.

### Réponse orale

> Nous avons adapté la durée entre trois et quatre semaines. Les sprints
> comportant les pipelines de données ou les modules IA ont nécessité quatre
> semaines, alors que les périmètres plus ciblés ont été planifiés sur trois.

## 6. Architecture globale retenue

### Décision

Présenter BidWise comme une architecture client-serveur multi-clients :

- une SPA Web React ;
- une application Mobile React Native avec Expo ;
- un backend centralisé Django REST Framework ;
- PostgreSQL avec pgvector ;
- Redis, Celery Workers et Celery Beat ;
- plusieurs sources de collecte externes.

### Justification

Les applications Web et Mobile sont deux clients indépendants qui consomment
les mêmes API REST. La logique métier et les données sont centralisées dans le
backend, ce qui évite de dupliquer les règles entre les deux interfaces.

### Réponse orale

> L'architecture globale est client-serveur multi-clients. React et React Native
> assurent la présentation, tandis que Django REST Framework centralise les API,
> les permissions et la logique métier.

## 7. Place de l'architecture MVT

### Décision

Ne pas supprimer MVT, mais ne pas présenter toute l'application comme une
architecture Web MVT classique.

### Justification

Django repose nativement sur Model-View-Template :

- les modèles représentent et persistent les données ;
- les vues et ViewSets DRF traitent les requêtes ;
- les templates Django sont très peu utilisés.

Dans BidWise, React et React Native prennent en charge la présentation. Le
backend renvoie principalement des réponses JSON et utilise également des
sérialiseurs, permissions, services métier et tâches asynchrones.

### Réponse orale

> MVT décrit le socle interne fourni par Django. Cependant, l'architecture
> globale de BidWise est orientée API REST : la couche de présentation est
> séparée et développée avec React et React Native.

## 8. Pourquoi un backend centralisé et non des microservices ?

### Décision

BidWise utilise un monolithe modulaire Django complété par des workers
asynchrones spécialisés. Les microservices n'ont pas été retenus pour cette
version.

### Raisons

1. **Taille et durée du projet**

   Le PFE dure six mois et l'équipe dispose de ressources limitées. Des
   microservices auraient ajouté des coûts de conception, de déploiement,
   d'observabilité et de tests distribués sans nécessité démontrée.

2. **Cohérence transactionnelle**

   Les utilisateurs, profils, opportunités et candidatures entretiennent des
   relations fortes. Un backend et une base relationnelle centralisés
   simplifient les transactions et évitent de gérer immédiatement la
   cohérence distribuée.

3. **Charge non démontrée**

   Le projet ne dispose pas encore d'un volume ou d'un trafic justifiant un
   découpage réseau des domaines. Choisir des microservices sans besoin mesuré
   aurait constitué une complexité prématurée.

4. **Modularité déjà présente**

   Le backend est séparé en applications métier, notamment `users`,
   `opportunities`, `applications`, `notifications` et `ai`. Cette organisation
   fournit des frontières fonctionnelles sans le coût opérationnel d'un système
   distribué.

5. **Isolation des traitements coûteux**

   Le besoin principal d'isolation concerne les traitements longs : collecte,
   analyse de CV, enrichissement IA et notifications. Celery et ses files
   spécialisées répondent à ce besoin sans transformer chaque domaine en
   service réseau autonome.

### Limites à reconnaître

Le monolithe modulaire ne fournit pas l'indépendance de déploiement ni
l'isolation de panne complète des microservices. Si un domaine acquiert une
charge, une équipe ou un cycle de déploiement autonome, il pourra être extrait
progressivement.

Les premiers candidats seraient les traitements de collecte ou certains
services IA, car ils sont coûteux, asynchrones et possèdent déjà des frontières
techniques relativement claires.

### Réponse orale

> Nous n'avons pas choisi les microservices parce que leur coût opérationnel
> n'était pas justifié par la taille de l'équipe ni par une charge mesurée. Nous
> avons préféré un monolithe modulaire, plus simple pour garantir la cohérence
> transactionnelle, avec Celery pour isoler les traitements coûteux. Le
> découpage actuel permet une extraction progressive future si un module exige
> un déploiement ou une montée en charge indépendante.

## 9. Pourquoi une API REST commune ?

### Décision

Les applications Web et Mobile consomment les mêmes API REST.

### Justification

- centralisation des règles métier et des permissions ;
- cohérence des données sur les deux clients ;
- limitation de la duplication ;
- possibilité d'ajouter ultérieurement un autre client ;
- contrat HTTP facilement testable avec des outils comme Postman.

### Limite à reconnaître

L'API commune doit éviter de devenir trop dépendante d'une seule interface.
Certaines adaptations de présentation restent donc gérées dans les clients.

### Réponse orale

> L'API commune mutualise les règles métier. Le Web et le Mobile adaptent
> l'affichage, mais ne réimplémentent pas les décisions fonctionnelles du
> backend.

## 10. Pourquoi PostgreSQL et pgvector ?

### Décision

Utiliser PostgreSQL pour les données relationnelles et pgvector pour les
représentations vectorielles.

### Justification

PostgreSQL convient aux relations fortes et aux transactions du domaine :
utilisateurs, organisations, opportunités et candidatures. pgvector permet de
conserver les vecteurs dans la même infrastructure et d'effectuer des recherches
par similarité sans introduire immédiatement une base vectorielle séparée.

### Limite à reconnaître

pgvector ne garantit pas automatiquement de bonnes performances à toute
échelle. Les index, la volumétrie et les requêtes doivent être mesurés. Une base
vectorielle dédiée ne serait justifiée qu'après identification d'une limite
réelle.

### Réponse orale

> PostgreSQL répond au besoin transactionnel principal. pgvector nous permet
> d'ajouter la recherche sémantique tout en conservant une architecture de
> données simple et cohérente pour la volumétrie actuelle.

## 11. Pourquoi Redis, Celery et Celery Beat ?

### Décision

- Redis sert de broker, de backend de résultats et de cache selon les usages ;
- les workers Celery exécutent les tâches en arrière-plan ;
- Celery Beat publie les tâches périodiques dans Redis ;
- les workers récupèrent ensuite ces tâches depuis le broker.

### Justification

Les traitements de collecte, d'analyse de CV, d'enrichissement et de
notification peuvent être longs ou périodiques. Les exécuter dans une requête
HTTP dégraderait la réactivité et augmenterait le risque de timeout.

### Flux correct

```text
Backend ------> Redis ------> Celery Workers
Celery Beat --> Redis
```

### Limite à reconnaître

L'asynchronisme améliore la réactivité perçue, mais augmente la complexité :
retries, idempotence, suivi des erreurs et supervision doivent être gérés.

### Réponse orale

> Celery sépare le cycle HTTP des traitements longs. Beat joue le rôle
> d'ordonnanceur, Redis transporte les messages et les workers exécutent les
> tâches. Ce choix évite de bloquer l'utilisateur pendant les traitements
> coûteux.

## 12. Pourquoi Docker Compose ?

### Décision

Orchestrer localement les services avec Docker Compose.

### Justification

BidWise dépend de plusieurs processus : backend, workers, Beat, Flower,
PostgreSQL et Redis. Docker Compose fournit un environnement reproductible et
documente les dépendances entre ces composants.

### Limite à reconnaître

Docker Compose est adapté au développement, à la démonstration et à un
déploiement simple. Il ne remplace pas une plateforme d'orchestration de
production distribuée et ne garantit ni haute disponibilité ni autoscaling.

### Réponse orale

> Compose nous donne un environnement reproductible pour plusieurs services.
> Nous ne le présentons pas comme une solution de haute disponibilité ; cette
> évolution dépendrait des contraintes réelles du déploiement.

## 13. Intégration de l'intelligence artificielle

### Décision

Présenter l'IA comme plusieurs composants spécialisés, et non comme un unique
LLM réalisant toute la plateforme.

### Architecture logique

- traitements de nettoyage, normalisation et règles métier ;
- extraction sémantique depuis les CV et les opportunités ;
- embeddings et JobBERT pour la représentation sémantique ;
- pgvector pour le stockage et la recherche vectorielle ;
- scoring hybride pour la recommandation ;
- modèles de langage pour l'enrichissement et la génération contextualisée.

Les modèles de langage peuvent être accessibles par API, comme Gemini, ou
exécutés localement, comme un modèle configuré avec Ollama.

### Justification

Les opérations déterministes ne doivent pas être confiées inutilement à un LLM.
La recommandation combine des signaux sémantiques et des règles métier, tandis
que la génération intervient sur des tâches adaptées : explication, analyse,
optimisation du CV, lettre de motivation et préparation à l'entretien.

### Limite à reconnaître

Les fonctionnalités génératives dépendent de la disponibilité et de la
configuration du fournisseur. Leurs sorties doivent rester fondées sur les
données disponibles et ne constituent pas des décisions automatiques.

### Réponse orale

> BidWise n'est pas un simple appel à un LLM. Nous séparons la collecte, la
> normalisation, les embeddings, le scoring métier et la génération. Le LLM
> intervient uniquement lorsque la tâche nécessite compréhension ou génération
> de langage.

## 14. Justifications architecturales conservées dans le rapport

Les justifications suivantes sont directement observables dans le code :

1. **Séparation des responsabilités** entre clients, API, données et tâches.
2. **Réutilisation des services** par les applications Web et Mobile.
3. **Modularité du backend** grâce aux applications métier Django.
4. **Réactivité** grâce à la délégation des traitements longs à Celery.
5. **Évolutivité technique** grâce à la séparation des clients, modules et
   workers.

Le rapport doit utiliser « facilite » ou « permet » plutôt que « garantit ».

## 15. Affirmations à éviter devant le jury

- « L'architecture garantit la scalabilité. »
- « L'application est hautement disponible. »
- « Tous les traitements prennent moins de deux secondes. »
- « L'ensemble du cycle de candidature est automatisé. »
- « Le LLM calcule seul les recommandations. »
- « Docker Compose est notre orchestration cloud de production. »
- « Les microservices auraient forcément été meilleurs. »

## 16. Lecture orale de l'architecture globale

> BidWise adopte une architecture client-serveur multi-clients. L'application
> Web React et l'application Mobile React Native consomment les mêmes API REST
> exposées par Django REST Framework. PostgreSQL stocke les données
> relationnelles et pgvector les représentations vectorielles. Les traitements
> longs ou périodiques sont distribués par Redis et exécutés par des workers
> Celery, tandis que Celery Beat assure leur planification. Nous avons retenu un
> monolithe modulaire plutôt que des microservices, car il répond au périmètre
> actuel avec moins de complexité distribuée tout en conservant des frontières
> permettant une évolution future.

## 17. Explication de la Figure 2.5

### Figure 2.5 - Architecture logicielle globale de BidWise

Cette figure présente les principaux composants logiciels de BidWise et les
communications établies entre eux.

### Applications clientes

BidWise possède deux clients :

- une application Web développée avec React.js ;
- une application Mobile développée avec React Native.

Ces clients ne communiquent pas directement avec la base de données. Ils
envoient leurs requêtes au backend à travers les API REST. Cette séparation
permet de centraliser les règles métier, l'authentification et les autorisations.

### Backend centralisé

Le backend Django REST Framework constitue le point central de l'architecture.
Il reçoit les requêtes des applications clientes, valide les données, applique
les permissions, exécute la logique métier et renvoie les réponses au format
JSON.

Il assure également la coordination avec la base de données, les sources
externes et l'infrastructure de traitements asynchrones.

### PostgreSQL et pgvector

PostgreSQL conserve les données relationnelles de la plateforme, notamment les
utilisateurs, profils, organisations, opportunités et candidatures.

La communication est bidirectionnelle : le backend lit et modifie les données.
L'extension pgvector permet de stocker et de comparer les représentations
vectorielles utilisées dans la recherche sémantique et la recommandation.

### Sources externes

Les opportunités peuvent provenir de Keejob, EmploiTunisie, LinkedIn et Marchés
Publics/HAICOP. Le backend coordonne leur collecte automatique puis transmet les
données au pipeline de normalisation, d'enrichissement et de stockage.

La flèche pointillée représente un traitement réalisé en arrière-plan plutôt
qu'une requête directe initiée par un utilisateur.

### Redis, Celery Workers et Celery Beat

Le backend publie les traitements longs dans Redis au lieu de les exécuter
entièrement pendant une requête HTTP. Redis joue le rôle de broker en conservant
les messages jusqu'à leur prise en charge.

Les workers Celery consomment ces messages et exécutent les tâches, notamment la
collecte, l'analyse de CV, l'enrichissement et les notifications.

Celery Beat est l'ordonnanceur. Il publie périodiquement des tâches dans Redis,
par exemple pour déclencher la collecte ou l'envoi d'un digest de
recommandations. Il ne réalise pas lui-même les traitements et ne communique pas
directement avec les workers.

### Signification des flèches

- les flèches continues représentent les communications synchrones, comme les
  appels API REST ou les échanges entre Django et PostgreSQL ;
- les flèches pointillées représentent les traitements asynchrones, planifiés
  ou exécutés en arrière-plan.

### Exemple de flux synchrone

Lorsqu'un utilisateur consulte une opportunité :

```text
Application Web ou Mobile
        -> API REST Django
        -> PostgreSQL
        -> réponse JSON
        -> interface utilisateur
```

L'application attend la réponse avant de mettre à jour l'interface.

### Exemple de flux asynchrone

Lors d'une collecte planifiée :

```text
Celery Beat
        -> Redis
        -> Celery Worker
        -> source externe
        -> pipeline de traitement
        -> PostgreSQL
```

Le traitement s'exécute en arrière-plan sans bloquer les applications clientes.

### Formulation pour le rapport

> La Figure 2.5 illustre l'architecture logicielle globale de BidWise. Les
> applications Web et Mobile communiquent avec un backend centralisé développé
> avec Django REST Framework à travers des API REST. Le backend assure la
> persistance des données dans PostgreSQL, complété par pgvector pour le stockage
> des représentations vectorielles. Les traitements longs ou périodiques sont
> distribués par Redis et exécutés par des workers Celery, tandis que Celery Beat
> assure leur planification. Cette architecture permet également la collecte
> automatisée d'opportunités provenant de plusieurs sources externes.

### Présentation orale courte

> La figure montre une architecture client-serveur avec deux clients, Web et
> Mobile, qui utilisent la même API Django REST. PostgreSQL stocke les données
> métier et pgvector les vecteurs utilisés par la recommandation. Les traitements
> longs sont placés dans Redis puis exécutés par les workers Celery. Celery Beat
> déclenche les tâches périodiques, notamment la collecte depuis les sources
> externes.

## 18. État de l'audit Sprint 0

Éléments déjà vérifiés :

- vocabulaire et périmètre du projet ;
- formulation de l'étude de l'existant ;
- durée des sprints ;
- architecture logicielle globale ;
- place de MVT ;
- composants asynchrones ;
- place générale des composants IA ;
- flux du diagramme d'architecture ;
- Product Backlog, MoSCoW, Story Points et état d'implémentation.

Éléments restant à auditer :

- besoins fonctionnels et non fonctionnels ;
- conformité avec le cahier des charges et l'implémentation ;
- diagramme global des cas d'utilisation ;
- diagramme global de classes.

L'audit détaillé du backlog est disponible dans
`SPRINT0_AUDIT_PRODUCT_BACKLOG.md`.
