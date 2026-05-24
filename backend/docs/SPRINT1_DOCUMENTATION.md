# BidWise — Documentation Sprint 1

**Projet :** BidWise — Plateforme intelligente de gestion des opportunités  
**Type :** Projet de Fin d'Études (PFE) — TWIN 2026  
**Sprint :** Sprint 1 — Authentification & onboarding candidat  
**Statut :** Validé fonctionnellement sur backend, web et mobile

---

## 1. Objectif du sprint

Le Sprint 1 pose le socle d'identité de BidWise.

L'objectif était de livrer un système d'authentification moderne, simple et sécurisé, utilisable sur :
- le backend Django/DRF
- le frontend web React
- l'application mobile Expo / React Native

Le périmètre final du sprint couvre :
- l'authentification passwordless par OTP email
- l'authentification Google
- la création automatique de compte
- la gestion de session JWT
- l'onboarding candidat en plusieurs étapes
- les routes protégées candidat, organisation et admin
- la déconnexion sécurisée
- la détection de connexion suspecte

---

## 2. Vue d'ensemble fonctionnelle

### Flux d'authentification livrés

1. **OTP passwordless**
- l'utilisateur saisit son email
- le backend envoie un code OTP à 6 chiffres
- le code est vérifié côté serveur
- le compte est créé automatiquement si nécessaire
- une paire `access` / `refresh` est délivrée

2. **Google Sign-In**
- le client obtient un `id_token` Google
- le backend vérifie ce jeton côté serveur
- le compte est créé automatiquement si nécessaire
- une paire `access` / `refresh` est délivrée

3. **Onboarding candidat**
- après la première connexion, l'utilisateur est redirigé vers l'onboarding si son profil n'est pas encore complété
- sinon il accède directement au dashboard

---

## 3. Architecture livrée

### Backend

Le backend repose sur :
- Django 5
- Django REST Framework
- SimpleJWT
- PostgreSQL
- Docker Compose

Endpoints auth exposés :
- `POST /api/auth/passwordless/request/`
- `POST /api/auth/passwordless/verify/`
- `POST /api/auth/google/`
- `POST /api/auth/refresh/`
- `POST /api/auth/logout/`
- `GET /api/profile/me/`
- `PUT /api/profile/me/`

### Frontend web

Le frontend web repose sur :
- React
- React Router
- Axios
- `AuthContext`
- `ProtectedRoute`
- `OrganizationRoute`

### Mobile

L'application mobile repose sur :
- Expo
- React Native
- Expo Router
- Axios
- SecureStore
- Google Sign-In natif

---

## 4. Implémentation actuelle des sessions

### Backend JWT

Le backend délivre :
- un **access token** valable 30 minutes
- un **refresh token** valable 14 jours

Configuration active :
- rotation des refresh tokens activée
- blacklist des refresh tokens après logout activée

### Web

L'implémentation web actuelle est la suivante :
- **access token stocké en mémoire uniquement**
- **refresh token stocké dans `sessionStorage`**
- rafraîchissement automatique via **intercepteur Axios sur 401**
- plus de `setInterval` de refresh
- suppression des tokens au logout ou si le refresh échoue
- bootstrap d'authentification avec état `loading`, afin d'éviter l'affichage temporaire d'une UI invitée pendant la restauration de session
- routes organisation protégées par `OrganizationRoute`

### Mobile

L'implémentation mobile actuelle est la suivante :
- **access token stocké dans SecureStore**
- **refresh token stocké dans SecureStore**
- rafraîchissement automatique via intercepteur Axios
- prise en charge correcte de la rotation du refresh token
- persistance du nouveau refresh token retourné par le backend après rotation

---

## 5. Mesures de sécurité en place

### OTP

Le système OTP applique les contrôles suivants :
- code OTP à 6 chiffres
- expiration après 5 minutes
- maximum de 5 tentatives par challenge
- cooldown de 60 secondes entre deux demandes pour le même email
- throttle IP sur `/request/` : 10 requêtes/heure
- throttle IP sur `/verify/` : 20 requêtes/heure
- throttle email sur `/verify/` : 10 requêtes/heure
- OTP hashé en base
- vérification sécurisée avec limitation des tentatives

### Sessions

Le système JWT applique :
- access token court
- refresh token rotatif
- blacklist côté serveur au logout
- routes protégées via `IsAuthenticated`
- routes organisation limitées aux comptes `organization`
- routes admin limitées aux comptes administrateurs
- authentification DRF explicite via `JWTAuthentication`

### Création de compte

Le système ne stocke aucun mot de passe exploitable pour les comptes OTP/Google :
- les utilisateurs créés automatiquement reçoivent un mot de passe inutilisable
- l'identité est portée par la possession de l'email ou par Google

---

## 6. Détection de connexion suspecte

### Règle actuelle

Une connexion est considérée comme suspecte si :
- ce n'est pas la toute première connexion du compte
- et qu'on observe une **nouvelle IP** ou un **nouveau User-Agent**

Cette logique est utilisée après :
- une connexion OTP réussie
- une connexion Google réussie

### Contenu de l'email d'alerte

L'email de sécurité contient :
- le type d'appareil détecté (`Desktop`, `Mobile`, `Tablet`)
- l'adresse IP vue par le backend
- une localisation approximative si elle peut être résolue
- la date/heure de la connexion

### Important en environnement local

En développement local, l'email peut être correct sur la logique métier mais imparfait sur les métadonnées réseau :
- l'IP affichée peut être une IP locale, Docker ou LAN
- la localisation peut rester à `Unknown`
- derrière un proxy inverse, l'IP réelle n'est correctement remontée que si `TRUSTED_PROXIES` est configuré

Autrement dit :
- **si l'email part bien lors d'une connexion depuis un nouvel appareil ou un nouveau navigateur, la fonctionnalité est valide**
- **en local, l'IP et la géolocalisation ne sont pas des indicateurs fiables de production**

---

## 7. Mobile : mode de lancement et limites actuelles

### Pré-requis

- backend lancé en Docker
- téléphone Android sur le même réseau local que la machine de développement, ou émulateur Android
- URL backend correcte via `EXPO_PUBLIC_API_BASE_URL` ou résolution automatique de l'hôte Expo

### Point important sur l'URL backend

L'application mobile résout l'URL API depuis :
- `EXPO_PUBLIC_API_BASE_URL` si la variable est définie
- l'hôte Expo détecté en développement
- `10.0.2.2` pour l'émulateur Android

Avant un déploiement multi-environnements, il faut conserver cette configuration externalisée et alignée avec `DJANGO_ALLOWED_HOSTS`.

### Test OTP mobile via Expo Go

Le flux OTP mobile peut être testé rapidement avec Expo Go :

```bash
cd bidwise-mobile
npm install
npm run start
```

Puis :
- scanner le QR code avec Expo Go
- ouvrir l'écran de login
- tester l'envoi OTP
- tester la vérification OTP

### Test Google mobile

**Google Sign-In ne fonctionne pas dans Expo Go** dans cette implémentation, car il dépend du module natif `RNGoogleSignin`.

Pour tester Google sur mobile, il faut utiliser :
- soit un **development build**
- soit un **APK généré avec EAS**

Pré-requis Google côté projet :
- le package Android doit rester `com.bidwise.mobile`
- le projet Google Cloud / Firebase doit autoriser cette application Android
- les empreintes SHA du build utilisé doivent être configurées si nécessaire

### Option A — Development build Android

Commande typique :

```bash
cd bidwise-mobile
npx expo run:android
```

À utiliser si :
- Android SDK est configuré
- un appareil Android ou un émulateur est disponible

### Option B — APK EAS

Le projet contient déjà `eas.json` avec des profils `development` et `preview`.

Commande recommandée pour un APK testable :

```bash
cd bidwise-mobile
npx eas build -p android --profile preview
```

Puis :
- installer l'APK sur un appareil Android réel
- tester OTP
- tester Google Sign-In
- tester logout, refresh et reprise de session

### Recommandation pratique

Pour Sprint 1, le chemin le plus simple est :
- **Expo Go pour OTP et navigation générale**
- **APK EAS ou development build pour Google Sign-In**

---

## 8. Validation fonctionnelle actuelle

Validation déjà réalisée :
- tests Postman backend exécutés avec succès
- flow web OTP validé
- flow web refresh validé
- flow web logout validé
- restauration de session web avec état de bootstrap stable validée
- protection des routes organisation validée
- flow web Google validé
- flow mobile refresh avec rotation validé
- backend Docker lancé sans erreur après correction de la configuration d'environnement

Le guide de test détaillé est disponible dans :
- [SPRINT1_TESTING_GUIDE.md](./SPRINT1_TESTING_GUIDE.md)

---

## 9. Points à garder en tête avant vraie production

Le système est sérieux et stable pour un Sprint 1, mais certains choix sont encore des compromis d'architecture.

### 1. Web : refresh token dans `sessionStorage`

Aujourd'hui :
- l'access token n'est plus stocké dans `localStorage`
- le refresh token reste lisible par JavaScript via `sessionStorage`

C'est un compromis raisonnable pour l'architecture actuelle web + mobile, mais ce n'est pas encore le niveau maximal de protection XSS.

### 2. Pas de `HttpOnly cookie` pour le refresh token web

Le passage vers des cookies `HttpOnly` n'a pas été implémenté dans Sprint 1 car cela casserait le flow actuel :
- les tokens sont aujourd'hui retournés dans le body des endpoints auth
- le mobile dépend de ce modèle
- le endpoint standard `/api/auth/refresh/` attend actuellement un refresh token dans le body

Donc :
- **ne pas présenter Sprint 1 comme un système cookie-based**
- **présenter `HttpOnly cookies` comme une perspective d'évolution Sprint futur / hardening prod**

### 3. Mobile : configuration d'URL backend

L'URL API mobile est configurable, mais devra rester explicitement contrôlée par environnement avant déploiement multi-environnements.

En pratique pour la démonstration :
- il faut conserver un réseau stable entre le téléphone et le backend
- si l'adresse IP de la machine change, vérifier `EXPO_PUBLIC_API_BASE_URL` ou l'hôte Expo détecté
- si l'IP change aussi côté backend, `DJANGO_ALLOWED_HOSTS` doit rester aligné puis le conteneur backend doit être recréé

### 4. Alerte de connexion suspecte

La logique de détection fonctionne, mais en local :
- l'IP peut être privée
- la géolocalisation peut être absente

En production, cette fonctionnalité sera plus fiable derrière un proxy correctement configuré.

### 5. Email OTP en développement

En environnement de développement, le backend email peut être volontairement basculé sur `django.core.mail.backends.console.EmailBackend` :
- les OTP sont alors visibles dans les logs du conteneur backend
- ce mode est adapté au développement sur réseau restreint
- pour une démonstration avec réception réelle par email, il faut réactiver un SMTP fonctionnel

---

## 10. Conclusion

Le Sprint 1 livre un socle d'authentification moderne, cohérent et déjà multi-plateforme :
- backend Django/DRF sécurisé
- frontend web fonctionnel
- mobile OTP fonctionnel
- mobile Google testable via build natif

Le système est prêt pour le Sprint 2, avec une base suffisamment propre pour supporter les fonctionnalités métier suivantes.
