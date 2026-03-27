# BidWise — Documentation Sprint 1

**Projet :** BidWise — Plateforme intelligente de gestion des opportunités  
**Type :** Projet de Fin d'Études (PFE) — TWIN 2026  
**Sprint :** Sprint 1 — Gestion des utilisateurs  
**Date de livraison :** Fin Février 2026  
**Méthodologie :** Agile Scrum

---

## 1. Vue d'ensemble du Sprint

### Objectif du Sprint

L'objectif du Sprint 1 était de mettre en place un **système d'authentification moderne et sécurisé** ainsi qu'une **expérience d'onboarding structurée** pour les candidats sur la plateforme web et mobile BidWise.

### Durée

Sprint 1 couvre la phase de fondation du projet, incluant la conception, le développement et la validation de l'ensemble du module de gestion des utilisateurs.

### Importance stratégique

L'authentification constitue le **socle fondamental** de toute plateforme numérique. Sans un système d'identification fiable et sécurisé, aucune fonctionnalité métier (candidatures, matching, notifications) ne peut être déployée. Ce sprint pose les bases essentielles sur lesquelles tous les sprints suivants s'appuieront.

### Lien avec la vision produit

BidWise ambitionne de connecter intelligemment les candidats avec les meilleures opportunités professionnelles. Pour cela, la plateforme doit d'abord **connaître ses utilisateurs** — leur identité, leurs préférences et leurs objectifs de carrière. Le Sprint 1 répond exactement à ce besoin en offrant une inscription fluide, une connexion sécurisée et un parcours de personnalisation dès la première utilisation.

---

## 2. Rappel de la vision produit

**BidWise** est une plateforme intelligente de gestion des opportunités professionnelles, conçue dans le cadre d'un Projet de Fin d'Études (PFE). Sa mission est de **simplifier et accélérer la mise en relation entre les candidats et les opportunités** (emploi, stage, freelance) grâce à des mécanismes de matching avancés.

À ce stade du développement, la plateforme se concentre exclusivement sur les **candidats** (stratégie « Candidat d'abord »). Ce choix permet de valider l'expérience utilisateur fondamentale avant d'étendre la plateforme aux organisations.

L'authentification est une brique critique car elle conditionne :

- La **sécurité** des données personnelles des utilisateurs
- La **personnalisation** de l'expérience (profil, préférences, recommandations)
- La **confiance** des utilisateurs envers la plateforme
- La **conformité** avec les bonnes pratiques de sécurité moderne

---

## 3. User Stories implémentées (COMPLÉTÉES)

### US-01 — Authentification sans mot de passe par code OTP

| Élément | Description |
|---------|-------------|
| **User Story** | En tant que candidat, je souhaite me connecter en recevant un code à usage unique (OTP) par email, afin de ne pas avoir à mémoriser un mot de passe. |
| **Valeur métier** | Réduction des frictions à l'inscription et à la connexion. Élimination du risque lié aux mots de passe faibles ou réutilisés. Expérience utilisateur moderne et fluide. |
| **Critères d'acceptation** | ✅ L'utilisateur saisit son adresse email sur la page de connexion. ✅ Un code à 6 chiffres est envoyé par email. ✅ Le code expire au bout de 5 minutes. ✅ Le nombre de tentatives de saisie est limité à 5. ✅ Un délai de 60 secondes est imposé entre deux demandes de code. ✅ Un maximum de 10 demandes par heure et par adresse IP est appliqué. |
| **Statut** | ✅ **Terminé** |

---

### US-02 — Authentification via Google

| Élément | Description |
|---------|-------------|
| **User Story** | En tant que candidat, je souhaite me connecter avec mon compte Google, afin de m'authentifier en un clic sans saisir d'informations. |
| **Valeur métier** | Accélération maximale du processus de connexion. Exploitation de la confiance des utilisateurs envers Google. Augmentation du taux de conversion à l'inscription. |
| **Critères d'acceptation** | ✅ Un bouton « Se connecter avec Google » est affiché sur la page de connexion. ✅ L'authentification Google est vérifiée côté serveur. ✅ Le compte utilisateur est automatiquement créé si c'est la première connexion. ✅ Une session sécurisée est délivrée après authentification réussie. |
| **Statut** | ✅ **Terminé** |

---

### US-03 — Création automatique de compte

| Élément | Description |
|---------|-------------|
| **User Story** | En tant que nouveau visiteur, je souhaite que mon compte soit créé automatiquement lors de ma première connexion (OTP ou Google), afin de ne pas passer par un formulaire d'inscription séparé. |
| **Valeur métier** | Suppression de l'étape d'inscription classique. Parcours « zero friction » : un seul flux pour l'inscription et la connexion. Réduction significative du taux d'abandon. |
| **Critères d'acceptation** | ✅ Si l'email n'existe pas en base, un compte est automatiquement créé. ✅ Un profil candidat est associé au nouveau compte. ✅ L'utilisateur est immédiatement authentifié après la création. ✅ L'utilisateur est redirigé vers le parcours d'onboarding. |
| **Statut** | ✅ **Terminé** |

---

### US-04 — Gestion sécurisée des sessions (JWT)

| Élément | Description |
|---------|-------------|
| **User Story** | En tant que candidat connecté, je souhaite que ma session reste active de manière sécurisée, afin de naviguer librement sur la plateforme sans devoir me reconnecter fréquemment. |
| **Valeur métier** | Expérience utilisateur fluide et continue. Sécurité renforcée grâce à des jetons à durée limitée et renouvelables. |
| **Critères d'acceptation** | ✅ Un jeton d'accès est délivré avec une durée de validité de 15 minutes. ✅ Un jeton de rafraîchissement est délivré avec une durée de validité de 1 jour. ✅ Le renouvellement de session se fait automatiquement et de manière transparente. ✅ Les jetons sont stockés de manière sécurisée côté client. |
| **Statut** | ✅ **Terminé** |

---

### US-05 — Envoi d'emails professionnels (SMTP + template HTML)

| Élément | Description |
|---------|-------------|
| **User Story** | En tant que candidat, je souhaite recevoir des emails professionnels et visuellement soignés de la part de BidWise, afin de bénéficier d'une expérience de qualité et de reconnaître facilement l'expéditeur. |
| **Valeur métier** | Renforcement de l'image de marque. Amélioration de la confiance utilisateur. Réduction du risque que les emails soient ignorés ou classés comme spam. |
| **Critères d'acceptation** | ✅ Les emails sont envoyés depuis un expéditeur identifié « BidWise ». ✅ Le template HTML est professionnel, avec en-tête brandé, code OTP mis en avant et pied de page informatif. ✅ Une version texte brut est incluse pour compatibilité maximale. ✅ Le système d'envoi fonctionne en environnement de production (SMTP). |
| **Statut** | ✅ **Terminé** |

---

### US-06 — Parcours d'onboarding en plusieurs étapes

| Élément | Description |
|---------|-------------|
| **User Story** | En tant que nouveau candidat, je souhaite être guidé à travers un parcours de personnalisation structuré après ma première connexion, afin de configurer mon profil et recevoir des opportunités pertinentes. |
| **Valeur métier** | Collecte progressive d'informations de profil sans surcharger l'utilisateur. Meilleure qualité des données pour le matching futur. Engagement renforcé dès la première utilisation. |
| **Critères d'acceptation** | ✅ Le parcours comporte 6 étapes : type d'opportunité, localisation, rémunération, type de contrat, rôles ciblés, visibilité du profil. ✅ Une barre de progression indique l'avancement. ✅ L'utilisateur peut naviguer entre les étapes (précédent/suivant). ✅ L'utilisateur peut ignorer le parcours à tout moment. ✅ Les données sont enregistrées dans le profil à la fin du parcours. |
| **Statut** | ✅ **Terminé** |

---

### US-07 — Reprise du parcours d'onboarding

| Élément | Description |
|---------|-------------|
| **User Story** | En tant que candidat ayant interrompu mon onboarding, je souhaite pouvoir reprendre là où je me suis arrêté, afin de ne pas recommencer depuis le début. |
| **Valeur métier** | Amélioration du taux de complétion de l'onboarding. Respect du temps de l'utilisateur. Expérience fluide même en cas d'interruption. |
| **Critères d'acceptation** | ✅ La progression de l'onboarding est sauvegardée localement (session du navigateur). ✅ À la reprise, l'utilisateur retrouve l'étape où il s'est arrêté. ✅ Les données déjà saisies sont pré-remplies. |
| **Statut** | ✅ **Terminé** |

---

### US-08 — Accès protégé au tableau de bord

| Élément | Description |
|---------|-------------|
| **User Story** | En tant que candidat authentifié, je souhaite accéder à mon tableau de bord personnel, afin de consulter mes opportunités et gérer mon profil. |
| **Valeur métier** | Espace sécurisé et personnalisé pour chaque utilisateur. Protection des données personnelles. Point d'entrée central vers les fonctionnalités de la plateforme. |
| **Critères d'acceptation** | ✅ Le tableau de bord n'est accessible qu'aux utilisateurs authentifiés. ✅ Toute tentative d'accès non authentifié redirige vers la page de connexion. ✅ Les routes protégées vérifient la validité du jeton avant d'afficher le contenu. |
| **Statut** | ✅ **Terminé** |

---

### US-09 — Déconnexion sécurisée

| Élément | Description |
|---------|-------------|
| **User Story** | En tant que candidat, je souhaite pouvoir me déconnecter de manière sécurisée, afin de protéger mon compte sur un appareil partagé. |
| **Valeur métier** | Sécurité et contrôle donnés à l'utilisateur. Conformité avec les bonnes pratiques de sécurité. |
| **Critères d'acceptation** | ✅ Un bouton de déconnexion est accessible depuis l'interface. ✅ La déconnexion supprime les jetons de session côté client. ✅ L'utilisateur est redirigé vers la page d'accueil après déconnexion. ✅ Aucun accès aux pages protégées n'est possible après déconnexion. |
| **Statut** | ✅ **Terminé** |

---

## 4. Décisions techniques (niveau fonctionnel)

### Pourquoi l'authentification sans mot de passe ?

L'approche traditionnelle par mot de passe présente de nombreux inconvénients : mots de passe oubliés, mots de passe faibles, réutilisation entre services, nécessité d'un flux de réinitialisation… En adoptant le **passwordless via code OTP**, BidWise supprime ces problèmes à la source. L'utilisateur n'a besoin que de son adresse email pour se connecter, ce qui simplifie radicalement l'expérience tout en améliorant la sécurité.

### Pourquoi l'authentification Google ?

Google est le fournisseur d'identité le plus répandu. Proposer cette option permet aux candidats de se connecter **en un seul clic**, sans aucune saisie. Cela réduit considérablement les frictions et augmente le taux de conversion à l'inscription, particulièrement sur une plateforme professionnelle où la rapidité d'accès est valorisée.

### Pourquoi la simplification du système de rôles ?

Initialement, la plateforme prévoyait trois types d'utilisateurs (candidat, organisation, administrateur). La décision a été prise de se concentrer exclusivement sur le **profil candidat** dans un premier temps. Cette stratégie « Candidat d'abord » permet de :
- Valider l'expérience fondamentale avant de complexifier
- Livrer plus rapidement une version fonctionnelle
- Recueillir des retours utilisateurs concrets avant d'étendre les fonctionnalités

### Pourquoi un onboarding structuré en étapes ?

Plutôt que de demander à l'utilisateur de remplir un long formulaire unique, le parcours d'onboarding est découpé en **6 étapes progressives**. Chaque étape se concentre sur un aspect spécifique du profil. Cette approche :
- Réduit la charge cognitive de l'utilisateur
- Améliore le taux de complétion du profil
- Permet de collecter des données structurées pour le matching futur
- Offre une expérience moderne et engageante

---

## 5. Mesures de sécurité et de qualité

### Expiration et limitation des codes OTP

Chaque code à usage unique a une **durée de vie de 5 minutes**. Au-delà, il devient invalide. Le nombre de tentatives de saisie est **limité à 5** pour empêcher les attaques par force brute. Un **délai de 60 secondes** entre deux demandes de code empêche le spam. Un plafond de **10 demandes par heure par adresse IP** protège contre les abus automatisés.

### Vérification sécurisée de l'email

Le mécanisme OTP garantit que seul le propriétaire de l'adresse email peut se connecter au compte associé. Il n'est pas possible de créer un compte avec un email fictif puisque la réception du code est nécessaire à la connexion.

### Protection contre les faux comptes

L'absence de formulaire d'inscription classique élimine le risque de création de comptes en masse. Chaque inscription est conditionnée à la vérification effective d'une adresse email valide, que ce soit par code OTP ou par authentification Google.

### Jetons de session sécurisés

Le système utilise des **jetons JWT** (JSON Web Token) à durée limitée. Le jeton d'accès expire après 15 minutes, obligeant un renouvellement régulier. Le jeton de rafraîchissement, valide 1 jour, permet de prolonger la session de manière transparente sans obligation de s'authentifier à nouveau.

### Aucun stockage de mot de passe

BidWise ne stocke **aucun mot de passe utilisateur**. Les codes OTP sont chiffrés en base de données et supprimés après utilisation. L'authentification Google délègue la vérification d'identité à Google. Cette approche élimine totalement le risque de fuite de mots de passe.

### Système d'email prêt pour la production

Les emails transactionnels sont envoyés via un serveur SMTP professionnel, avec un template HTML brandé et une version texte de secours. L'expéditeur est clairement identifié sous le nom **BidWise**, renforçant la confiance et la reconnaissance de marque.

---

## 6. Évolutions du périmètre du Sprint 1 (Transparence Agile)

Dans un souci de transparence conforme aux principes Agile, voici les **adaptations de périmètre** réalisées au cours du Sprint 1 :

### Suppression de l'authentification classique par mot de passe

Le système d'inscription et de connexion par mot de passe, initialement prévu, a été **remplacé** par l'authentification sans mot de passe (OTP + Google). Cette décision a été motivée par des considérations de sécurité, de simplicité et d'expérience utilisateur.

### Report du rôle « Organisation »

Le système de rôles multiples (candidat, organisation, administrateur) a été **simplifié**. Le Sprint 1 se concentre uniquement sur les candidats. Les fonctionnalités pour les organisations (publication d'offres, tableau de bord recruteur) sont reportées à un sprint ultérieur.

### Recentrage sur l'expérience candidat

Le périmètre a été volontairement resserré pour livrer une expérience **complète et de qualité** pour un seul type d'utilisateur, plutôt qu'une expérience partielle pour plusieurs. C'est une application directe du principe Agile : **livrer un incrément de valeur fonctionnel et utilisable**.

### Fonctionnalités déplacées vers les sprints suivants

Certaines fonctionnalités initialement envisagées (changement d'email, paramètres de compte avancés, interface d'administration) ont été **dépriorisées** au profit de la solidité du socle d'authentification et de l'onboarding.

---

## 7. Fonctionnalités hors périmètre du Sprint 1 (Backlog différé)

Les éléments suivants font partie de la vision produit globale mais n'étaient **pas inclus dans le Sprint 1** :

| Fonctionnalité | Raison du report | Sprint estimé |
|---------------|-----------------|---------------|
| **Authentification mobile (React Native)** | ✅ **Livrée dans le Sprint 1** — OTP + Google fonctionnels | ✅ Done |
| **Constructeur de CV (CV Builder)** | Fonctionnalité avancée, dépend du profil de base | Sprint 3 |
| **Générateur de CV par IA** | Nécessite intégration IA, complexité élevée | Sprint 4–5 |
| **Tableau de bord organisation** | Report du rôle organisation | Sprint 3 |
| **Matching avancé de profils** | Nécessite données de profil complètes | Sprint 3–4 |
| **Changement d'email / paramètres de compte** | Fonctionnalité secondaire pour le MVP | Sprint 2–3 |

Ces fonctionnalités restent dans le **Product Backlog** et seront planifiées lors des prochains Sprint Plannings.

---

## 7 bis. Version mobile (Expo / React Native)

### Contexte

En complément de la plateforme web, une **application mobile** a été développée lors du Sprint 1 afin de démontrer la capacité multi-plateforme de BidWise. L'application mobile consomme la **même API backend** que l'application web, validant ainsi l'architecture API-First du projet.

### Technologie

L'application mobile est construite avec **Expo (React Native)**, un framework permettant de développer une application native pour iOS et Android à partir d'une base de code unique en TypeScript.

### Fonctionnalités mobile implémentées

| Fonctionnalité | Description | Statut |
|----------------|-------------|--------|
| **Connexion OTP** | Saisie de l'email, réception du code à 6 chiffres, vérification et accès à la plateforme | ✅ Terminé |
| **Connexion Google** | Authentification via Google OAuth, envoi du jeton au backend, session sécurisée | ✅ Terminé |
| **Stockage sécurisé des jetons** | Les jetons JWT sont stockés dans le coffre-fort sécurisé du téléphone (SecureStore) | ✅ Terminé |
| **Renouvellement automatique de session** | Le jeton d'accès est rafraîchi automatiquement en arrière-plan | ✅ Terminé |
| **Navigation vers onboarding / tableau de bord** | Un nouvel utilisateur est dirigé vers l'onboarding, un utilisateur existant vers son tableau de bord | ✅ Terminé |
| **Déconnexion sécurisée** | Suppression des jetons et retour à l'écran de connexion | ✅ Terminé |
| **Interface d'onboarding** | Parcours 6 étapes avec barre de progression et navigation | ✅ Terminé |

### Architecture

L'application mobile partage exactement les mêmes endpoints que l'application web :

- `POST /api/auth/passwordless/request/` — Demande de code OTP
- `POST /api/auth/passwordless/verify/` — Vérification du code et obtention des jetons
- `POST /api/auth/google/` — Authentification Google
- `POST /api/auth/refresh/` — Renouvellement de jeton
- `GET /api/profile/me/` — Profil utilisateur

Cette approche démontre la **réutilisabilité** de l'API et valide le choix architectural d'un backend unique pour plusieurs clients.

### Validation

- ✅ L'application mobile a été testée sur un appareil physique via Expo Go
- ✅ L'envoi de code OTP et la vérification fonctionnent correctement
- ✅ La connexion Google OAuth redirige vers le navigateur, authentifie et revient dans l'application
- ✅ La navigation conditionnelle (nouvel utilisateur → onboarding, utilisateur existant → dashboard) est opérationnelle
- ✅ La déconnexion fonctionne et protège les routes

---

## 8. Bilan de validation du Sprint

L'ensemble des fonctionnalités livrées dans le Sprint 1 ont été **validées fonctionnellement** :

### Flux d'authentification

- ✅ **Connexion par OTP** : Le candidat saisit son email, reçoit un code à 6 chiffres, le saisit et accède à la plateforme. Testé et validé.
- ✅ **Connexion par Google** : Le candidat clique sur le bouton Google, s'authentifie via son compte Google et accède à la plateforme. Testé et validé.
- ✅ **Création automatique de compte** : Un nouvel email crée automatiquement un compte sans étape supplémentaire. Testé et validé.

### Envoi d'emails

- ✅ **Réception du code OTP** : L'email est reçu avec un template professionnel, le code OTP est clairement visible, l'expéditeur est identifié comme « BidWise ». Testé et validé.
- ✅ **Compatibilité email** : Version HTML pour les clients modernes, version texte brut en secours. Testé et validé.

### Parcours d'onboarding

- ✅ **Navigation 6 étapes** : Chaque étape s'affiche correctement, la barre de progression reflète l'avancement. Testé et validé.
- ✅ **Sauvegarde des préférences** : Les données sont enregistrées dans le profil utilisateur à la fin du parcours. Testé et validé.
- ✅ **Reprise de session** : L'onboarding reprend à la dernière étape en cas d'interruption. Testé et validé.

### Sécurité

- ✅ **Expiration OTP** : Le code expire après 5 minutes. Testé et validé.
- ✅ **Limitation des tentatives** : Le nombre de tentatives et la fréquence de demande sont limités. Testé et validé.
- ✅ **Routes protégées** : L'accès au tableau de bord et au profil est refusé sans authentification active. Testé et validé.
- ✅ **Déconnexion** : La déconnexion supprime les jetons et interdit l'accès aux pages protégées. Testé et validé.

### Stabilité du système

- ✅ L'application web frontend compile sans erreur (1669 modules)
- ✅ L'application mobile compile sans erreur (TypeScript 0 erreurs)
- ✅ Le backend démarre correctement dans l'environnement Docker
- ✅ La base de données PostgreSQL est opérationnelle avec toutes les migrations appliquées
- ✅ L'application mobile a été testée sur appareil physique (APK via EAS Build)
- ✅ **154 tests automatisés backend passent avec succès** (détail ci-dessous)
- ✅ Le système est **stable et prêt pour le Sprint 2**

### Tests automatisés (Backend)

Le Sprint 1 inclut une suite complète de **154 tests automatisés** couvrant l'ensemble des composants backend :

| Module | Tests | Lignes de code | Couverture |
|--------|-------|----------------|------------|
| **users** | 65 tests | 583 lignes | Modèles (Utilisateur, Profil, OTP), Sérialiseurs, Vues (OTP, Google Auth, Profil, Token Refresh), Permissions, Signaux |
| **opportunities** | 52 tests | 466 lignes | Modèles (Opportunite, SourceOpportunite), Sérialiseurs (validation dates), Vues (CRUD, filtres, tri, pagination), Permissions |
| **applications** | 37 tests | 382 lignes | Modèles (Candidature, Document), Sérialiseurs, Vues (CRUD, propriété, duplication), Permissions |
| **Total** | **154 tests** | **1 431 lignes** | **Tous passent ✅** |

Les tests couvrent :
- **Modèles** : Création, valeurs par défaut, contraintes, relations, cascade de suppression
- **Sérialiseurs** : Sérialisation/désérialisation, champs read-only, validation métier
- **Vues/API** : Authentification, autorisation, CRUD complet, filtrage, pagination, tri
- **Permissions** : Propriétaire, lecture seule, accès non authentifié
- **Signaux** : Création automatique de profil à la création d'utilisateur
- **Google OAuth** : Mocking de `google.oauth2.id_token.verify_oauth2_token`, gestion des erreurs réseau, tokens invalides, audience incorrecte

---

## 9. Definition of Done — Sprint 1

Le Sprint 1 est considéré comme **terminé** car les conditions suivantes sont toutes réunies :

- ✅ Toutes les user stories d'authentification planifiées ont été implémentées (US-01 à US-09)
- ✅ Le système d'authentification sans mot de passe est fonctionnel (OTP + Google) sur web et mobile
- ✅ Les exigences de sécurité sont satisfaites (expiration OTP, limitation de tentatives, chiffrement, jetons JWT)
- ✅ Le parcours d'onboarding en 6 étapes est complet et fonctionnel
- ✅ La validation fonctionnelle a été réalisée pour chaque user story
- ✅ Les emails transactionnels sont envoyés avec un template professionnel
- ✅ L'application web et l'application mobile sont stables en environnement de développement
- ✅ L'architecture API-First est validée : un seul backend, deux clients (web + mobile)
- ✅ **Validation mobile sur APK réel** : Application testée via EAS Build (APK) sur appareil Android physique, pas seulement Expo Go
- ✅ **154 tests automatisés passent** : Suite de tests complète couvrant modèles, sérialiseurs, vues, permissions et signaux
- ✅ La documentation du sprint est rédigée et à jour
- ✅ Le code est versionné et un tag de stabilité a été posé (`v1.0.0-sprint1`)

---

## Conclusion — Transition vers le Sprint 2

Le Sprint 1 a permis de poser les **fondations solides** de la plateforme BidWise : un système d'authentification moderne et sécurisé, une expérience d'inscription fluide et un parcours d'onboarding structuré, le tout déployé à la fois sur **web et mobile**.

La livraison de l'application mobile dès le Sprint 1 valide l'**architecture API-First** du projet : un seul backend consommé par deux clients distincts. Cette approche confirme la scalabilité et la réutilisabilité de la solution.

Ces fondations permettent désormais d'aborder le Sprint 2 avec confiance. Les prochaines itérations se concentreront sur l'**enrichissement de l'expérience candidat** : consultation et recherche d'opportunités, gestion du profil détaillé, et début du système de candidature. Chaque sprint suivant s'appuiera sur le socle technique et fonctionnel validé lors de ce premier sprint.

Le projet BidWise avance conformément à la méthode Agile Scrum, avec des incréments de valeur livrés, validés et documentés à chaque itération.

---

*Document rédigé dans le cadre du suivi Agile du projet BidWise — PFE 2026*
