# Sprint 0 - Défense du diagramme de classes global

## 1. Objectif du diagramme

Le diagramme de classes global présente les principales entités métier de
BidWise et leurs relations.

Il s'agit d'un diagramme conceptuel. Il ne reprend pas tous les champs
techniques du backend Django, comme les index, contraintes, champs internes ou
tables de support. Son objectif est de montrer la structure du domaine :

- utilisateurs et profils ;
- opportunités et sources ;
- collecte des données brutes ;
- candidatures ;
- CV ;
- notifications.

Phrase de défense :

> Ce diagramme est volontairement conceptuel. Il représente les entités métier
> principales et leurs relations, tandis que les détails techniques propres à
> Django sont présentés dans la partie réalisation.

## 2. Pourquoi ne pas tout mettre dans le diagramme ?

Le backend contient davantage de modèles que le diagramme global. Certains
modèles sont techniques ou liés à la supervision, comme les runs de pipeline,
les états du scheduler ou les journaux d'audit.

Ils ne sont pas tous affichés afin de préserver la lisibilité.

Phrase de défense :

> Un diagramme global doit rester lisible. Les classes techniques de support
> sont volontairement simplifiées ou omises, puis détaillées dans les sprints
> concernés.

## 3. Classe Utilisateur

### Rôle

`Utilisateur` représente le compte principal de la plateforme. Il porte les
informations communes à tous les rôles : candidat, organisation et
administrateur.

### Attributs principaux

| Attribut | Rôle |
|---|---|
| `id` | identifiant unique du compte |
| `nom`, `prenom` | identité de l'utilisateur |
| `email` | adresse utilisée pour l'authentification et les notifications |
| `dateCreation` | date de création du compte |
| `dateModification` | date de dernière modification |
| `statut` | état du compte : actif ou suspendu |
| `role` | rôle fonctionnel : candidat, organisation ou administrateur |

### Méthodes

| Méthode | Rôle |
|---|---|
| `seDeconnecter()` | permet de terminer la session utilisateur |
| `recevoirNotification()` | représente la réception d'une notification |

Phrase de défense :

> L'utilisateur est placé au centre du modèle car toutes les fonctionnalités
> authentifiées dépendent d'un compte : profil, organisation, candidature ou
> notification.

## 4. Profils candidat et organisation

### Pourquoi deux profils séparés ?

Un utilisateur peut être candidat ou organisation. Les informations nécessaires
ne sont pas les mêmes.

Le candidat possède des compétences, préférences et CV. L'organisation possède
des informations institutionnelles et publie des opportunités.

### Relations avec Utilisateur

```text
Utilisateur 1 -- 0..1 ProfilCandidat
Utilisateur 1 -- 0..1 ProfilOrganisation
```

Ces relations peuvent être représentées par composition, car les profils
dépendent du cycle de vie du compte utilisateur.

Contrainte métier :

```text
{Un utilisateur possède au maximum un profil candidat ou un profil organisation
selon son rôle.}
```

Phrase de défense :

> J'ai choisi des associations entre Utilisateur et les profils plutôt qu'une
> généralisation, car dans l'implémentation les profils sont liés au compte
> utilisateur et le rôle est porté par le compte.

## 5. Classe ProfilCandidat

### Rôle

`ProfilCandidat` regroupe les informations utilisées pour personnaliser
l'expérience du candidat et calculer les recommandations.

### Attributs

| Attribut | Rôle |
|---|---|
| `competences` | compétences déclarées ou extraites |
| `domainesInterets` | domaines professionnels ciblés |
| `urlCV` | lien vers le CV actif ou principal |
| `preferred_locations` | régions ou villes préférées |
| `typeOpportunite` | types d'opportunités recherchés |
| `typeContratRecherches` | contrats ou modes d'engagement souhaités |
| `salaireMin` | attente minimale de rémunération |
| `annees_experience` | niveau d'expérience en années |
| `target_roles` | rôles ou métiers recherchés |
| `work_modes` | préférences de travail : remote, hybride, onsite |
| `profile_completion_score` | niveau de complétion du profil |

### Méthodes

| Méthode | Rôle |
|---|---|
| `importerCV(file)` | déclenche l'import et l'analyse du CV |
| `consulterRecommandations()` | permet d'obtenir les opportunités recommandées |

Phrase de défense :

> Le profil candidat est central pour l'IA, car les recommandations dépendent
> des compétences, préférences, rôles ciblés et informations extraites du CV.

## 6. Classe CVProfil

### Rôle

`CVProfil` représente un CV importé par un candidat et les informations issues
de son analyse.

### Attributs

| Attribut | Rôle |
|---|---|
| `id` | identifiant du CV |
| `fichier` | fichier importé |
| `texteExtrait` | texte récupéré après lecture du document |
| `statutAnalyse` | état du traitement sémantique |
| `competencesExtraites` | compétences extraites automatiquement |
| `confianceAnalyse` | confiance associée à l'analyse lorsqu'elle existe |
| `dateImport` | date d'import du CV |

### Relations

```text
ProfilCandidat 1 -- 0..* CVProfil
Candidature 0..* -- 0..1 CVProfil
```

Un candidat peut importer plusieurs CV. Une candidature peut utiliser un CV, et
un même CV peut être réutilisé dans plusieurs candidatures.

Phrase de défense :

> J'ai séparé le CV du profil candidat parce que le CV possède son propre cycle
> de traitement : import, extraction de texte, analyse sémantique et réutilisation
> éventuelle dans plusieurs candidatures.

## 7. Classe ProfilOrganisation

### Rôle

`ProfilOrganisation` représente les informations d'une organisation qui publie
des opportunités sur BidWise.

### Attributs

| Attribut | Rôle |
|---|---|
| `nomOrganisation` | nom affiché de l'organisation |
| `secteur` | secteur d'activité |
| `siteWeb` | site officiel |
| `logoURL` | logo de l'organisation |
| `phone` | contact téléphonique |
| `type` | type d'organisation |

### Méthodes

| Méthode | Rôle |
|---|---|
| `publierOpportunite(opportunite)` | création d'une opportunité interne |
| `consulterCandidatures(opportunite)` | consultation des candidatures reçues |

### Relation avec Opportunite

```text
ProfilOrganisation 1 -- 0..* Opportunite
```

Une organisation peut publier plusieurs opportunités. Une opportunité interne
peut être rattachée à une organisation.

Phrase de défense :

> Le profil organisation est séparé du compte utilisateur pour distinguer
> l'identité de connexion et les informations institutionnelles utilisées lors
> de la publication d'opportunités.

## 8. Classe SourceOpportunite

### Rôle

`SourceOpportunite` représente une source externe ou interne alimentant la
plateforme en opportunités.

Exemples :

- Keejob ;
- EmploiTunisie ;
- LinkedIn ;
- Marchés Publics / HAICOP.

### Attributs

| Attribut | Rôle |
|---|---|
| `id` | identifiant de la source |
| `nom` | nom de la source |
| `url` | adresse de la source |
| `typeSource` | type de source : emploi, stage, portail d'appels d'offres |

### Relations

```text
SourceOpportunite 1 -- 0..* OpportuniteBrute
SourceOpportunite 1 -- 0..* Opportunite
```

La première relation peut être une composition, car les opportunités brutes
dépendent directement de la source qui les produit.

La relation avec `Opportunite` est une association simple, car une opportunité
normalisée devient une entité métier exploitée par le reste de la plateforme.

Phrase de défense :

> J'ai utilisé une composition entre SourceOpportunite et OpportuniteBrute, car
> la donnée brute dépend directement de sa source. En revanche, Opportunite est
> une entité normalisée utilisée dans les recherches, recommandations et
> candidatures ; elle est donc reliée par association simple.

## 9. Classe OpportuniteBrute

### Rôle

`OpportuniteBrute` représente une donnée collectée avant sa normalisation.

Elle est importante car BidWise ne transforme pas directement une page externe
en opportunité finale. Le système conserve d'abord la donnée brute afin de
permettre la traçabilité et la reprise du traitement.

### Attributs

| Attribut | Rôle |
|---|---|
| `id` | identifiant de l'enregistrement brut |
| `donneesBrutes` | contenu collecté sous forme JSON |
| `titreBrut` | titre original |
| `descriptionBrute` | description originale |
| `urlSource` | lien de l'élément collecté |
| `empreinteContenu` | signature utilisée pour détecter les doublons |
| `statutTraitement` | état de traitement de la donnée brute |
| `erreursValidation` | erreurs détectées lors de la normalisation |
| `premiereDetection` | première date de détection |
| `derniereDetection` | dernière date de détection |

### Relation avec Opportunite

```text
OpportuniteBrute 0..* -- 0..1 Opportunite
```

Interprétation :

- une opportunité brute peut ne pas encore être normalisée ;
- une opportunité brute peut produire au maximum une opportunité normalisée ;
- plusieurs opportunités brutes peuvent pointer vers la même opportunité finale
  en cas de doublons ou de recoupements.

Phrase de défense :

> OpportuniteBrute permet de séparer la collecte et la normalisation. Cette
> séparation rend le pipeline plus traçable et permet de rejouer un traitement
> sans relancer obligatoirement le scraping.

## 10. Classe Opportunite

### Rôle

`Opportunite` représente l'opportunité normalisée visible et exploitable dans
BidWise.

Elle peut provenir d'une source externe ou être publiée par une organisation.

### Attributs

| Attribut | Rôle |
|---|---|
| `id` | identifiant |
| `titre` | titre normalisé |
| `description` | description affichée |
| `datePublication` | date de publication |
| `dateLimite` | date limite de candidature ou réponse |
| `secteur` | domaine ou secteur |
| `type` | emploi, stage, appel d'offres |
| `sourceURL` | lien vers l'annonce d'origine |
| `localisation` | lieu |
| `salaire` | rémunération ou budget lorsqu'il existe |
| `typeContrat` | type de contrat |
| `annees_experience` | expérience demandée |
| `competencesRequises` | compétences nécessaires |
| `statut` | état de visibilité de l'opportunité |

### Méthode

| Méthode | Rôle |
|---|---|
| `estExpiree()` | indique si l'opportunité a dépassé sa date limite |

### Relations

```text
SourceOpportunite 1 -- 0..* Opportunite
ProfilOrganisation 1 -- 0..* Opportunite
Opportunite 1 -- 0..* Candidature
```

Phrase de défense :

> Opportunite est l'entité métier centrale du projet. Elle est utilisée dans la
> recherche, la recommandation, la candidature et la supervision.

## 11. Classe Candidature

### Rôle

`Candidature` représente la démarche d'un candidat vis-à-vis d'une opportunité.

Elle couvre deux cas :

- candidature directe sur BidWise ;
- suivi d'une candidature externe après redirection vers la source.

### Attributs

| Attribut | Rôle |
|---|---|
| `id` | identifiant |
| `urlSource` | lien externe lorsque la candidature se fait hors BidWise |
| `lettreMotivationUrl` | lien vers la lettre jointe ou générée |
| `urlCVSoumis` | lien vers le CV soumis |
| `statut` | état de la candidature |
| `contactEmail` | email fourni pour le contact |
| `contactPhone` | téléphone fourni |
| `dateCreation` | date de création ou d'enregistrement |

### Méthodes

| Méthode | Rôle |
|---|---|
| `confirmer()` | confirme une postulation externe ou une étape de suivi |
| `annuler()` | retire ou annule la candidature |

### Relations

```text
ProfilCandidat 1 -- 0..* Candidature
Opportunite 1 -- 0..* Candidature
Candidature 0..* -- 0..1 CVProfil
```

Phrase de défense :

> La candidature fait le lien entre un candidat et une opportunité. Elle
> supporte à la fois les opportunités internes et les opportunités externes,
> grâce aux statuts de suivi.

## 12. Classe Notification

### Rôle

`Notification` représente un message envoyé ou conservé pour informer un
utilisateur.

### Attributs

| Attribut | Rôle |
|---|---|
| `id` | identifiant |
| `type` | type de notification |
| `message` | contenu |
| `lue` | indique si la notification a été lue |
| `dateEnvoi` | date de création ou d'envoi |
| `lien` | lien contextuel éventuel |

### Méthode

| Méthode | Rôle |
|---|---|
| `marquerCommeLue()` | marque la notification comme lue |

### Relation

```text
Utilisateur 1 -- 0..* Notification
```

Cette relation peut être représentée par composition si l'on considère que les
notifications dépendent du compte utilisateur.

Phrase de défense :

> Les notifications sont rattachées à l'utilisateur afin de conserver une trace
> des messages envoyés ou à afficher.

## 13. Énumérations principales

### RoleEnum

Définit les rôles principaux :

- `CANDIDATE` ;
- `ORGANIZATION` ;
- `ADMIN`.

### StatutEnum

Définit l'état général d'un compte :

- `ACTIF` ;
- `SUSPENDU`.

### TypeOppEnum

Définit le type d'opportunité :

- `EMPLOI` ;
- `STAGE` ;
- `APPEL_OFFRE`.

### StatutOpportuniteEnum

Définit le cycle de vie d'une opportunité :

- `ACTIVE` ;
- `EN_ATTENTE` ;
- `REJETEE` ;
- `SUSPENDUE` ;
- `FERMEE` ;
- `ARCHIVEE` ;
- `EXPIREE`.

### StatutCandidatureEnum

Définit le suivi d'une candidature interne ou externe :

- `SOUMISE` ;
- `VUE` ;
- `PRESELECTIONNEE` ;
- `REJETEE` ;
- `RETIREE` ;
- `LIEN_EXTERNE_OUVERT` ;
- `POSTULATION_EXTERNE_CONFIRMEE` ;
- `RAPPEL_EXTERNE_DEMANDE`.

### StatutTraitementBrutEnum

Définit l'état d'une opportunité brute dans le pipeline :

- `NOUVELLE` ;
- `VALIDEE` ;
- `REJETEE` ;
- `MATERIALISEE`.

### TypeNotifEnum

Définit les grandes familles de notifications :

- `RECOMMANDATION` ;
- `CANDIDATURE` ;
- `RAPPEL_ECHEANCE`.

## 14. Pourquoi certaines relations sont des compositions ?

La composition est utilisée lorsque l'objet dépend fortement du cycle de vie de
l'objet principal.

Exemples défendables :

```text
Utilisateur -- ProfilCandidat
Utilisateur -- ProfilOrganisation
Utilisateur -- Notification
ProfilCandidat -- CVProfil
SourceOpportunite -- OpportuniteBrute
```

Phrase de défense :

> J'ai utilisé la composition uniquement pour les entités fortement dépendantes,
> comme les profils d'un utilisateur ou les données brutes d'une source. Pour les
> entités métier plus autonomes, comme Opportunite ou Candidature, j'ai conservé
> des associations simples afin d'éviter une dépendance de cycle de vie trop
> forte.

## 15. Pourquoi certaines relations ne sont pas des compositions ?

### SourceOpportunite - Opportunite

Même si une opportunité garde une source d'origine, elle devient une entité
métier normalisée utilisée par d'autres modules : recherche, recommandation,
candidature et supervision.

La relation est donc une association simple :

```text
SourceOpportunite 1 -- 0..* Opportunite
```

### Opportunite - Candidature

Une candidature dépend à la fois du candidat et de l'opportunité. Pour éviter
une double composition, le diagramme utilise une association simple.

```text
Opportunite 1 -- 0..* Candidature
ProfilCandidat 1 -- 0..* Candidature
```

Phrase de défense :

> J'ai évité la composition lorsqu'une classe dépend de plusieurs entités ou
> possède une valeur métier propre. Cela rend le diagramme plus clair et plus
> fidèle au modèle conceptuel.

## 16. Lecture rapide du diagramme

Script oral :

> Le diagramme commence par l'utilisateur, qui peut posséder un profil candidat
> ou un profil organisation selon son rôle. Le profil candidat contient les
> informations nécessaires à la recommandation et peut importer plusieurs CV.
> Le profil organisation peut publier plusieurs opportunités. Les opportunités
> peuvent aussi provenir de sources externes : elles sont d'abord stockées sous
> forme d'opportunités brutes, puis normalisées en opportunités exploitables. Le
> candidat peut ensuite soumettre une candidature à une opportunité, en utilisant
> éventuellement un CV. Enfin, les notifications permettent d'informer
> l'utilisateur des événements importants.

## 17. Questions probables du jury

### Pourquoi `Candidat` et `Organisation` ne sont pas des sous-classes de `Utilisateur` ?

> Parce que dans le modèle retenu, le compte utilisateur porte le rôle, et les
> informations spécifiques sont placées dans des profils associés. Cela évite de
> dupliquer les champs communs et respecte mieux l'implémentation Django.

### Pourquoi ajouter OpportuniteBrute ?

> Parce que la collecte multi-source est centrale dans BidWise. Les données sont
> d'abord conservées sous forme brute pour assurer la traçabilité, gérer les
> doublons et permettre la normalisation.

### Pourquoi `OpportuniteBrute` est-elle simplifiée ?

> Elle contient plus de champs techniques dans l'implémentation. Dans le
> diagramme global, nous avons gardé seulement les attributs utiles à la
> compréhension du domaine.

### Pourquoi `Favoris` n'apparaît plus ?

> Les favoris sont actuellement gérés côté client. Comme ils ne constituent pas
> une entité persistée principale du backend, ils ne sont pas affichés dans le
> diagramme global.

### Pourquoi garder des méthodes ?

> Les méthodes affichées sont seulement les comportements métier les plus
> représentatifs. Les détails opérationnels sont plutôt décrits dans les
> diagrammes de séquence et les chapitres de réalisation.

## 18. Limites assumées du diagramme

Le diagramme ne montre pas :

- toutes les tables techniques Django ;
- les index et contraintes ;
- les historiques détaillés ;
- les modèles de supervision complets ;
- tous les champs IA et embeddings.

Phrase de défense :

> Ces éléments existent dans l'implémentation, mais ils sont volontairement
> exclus du diagramme global pour garder une vue métier lisible. Ils seront
> présentés dans les sprints concernés lorsque leur rôle devient central.

