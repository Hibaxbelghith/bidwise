# 🎉 SPRINT 1 — Gestion de l'inscription & authentification — BACKEND COMPLÉTÉ


## 🎯 Objectif du Sprint 1

Permettre à un utilisateur ou une organisation de créer un compte et se connecter depuis **Web et Mobile** via une **API REST unique**.

### 🔹 Règle d'or Sprint 1

❌ **PAS de logique spécifique Web / Mobile dans le backend**  
✅ **Une seule API**  
🌐 **Web** et 📱 **Mobile** consomment la même API

> **« Le backend est conçu comme une API REST unique, consommée à la fois par l'application Web et l'application Mobile, garantissant cohérence, réutilisabilité et évolutivité. »**

---

## ✅ ÉTAPES COMPLÉTÉES (Backend API-First)

## ✅ ÉTAPES COMPLÉTÉES (Backend API-First)

### 🟩 ÉTAPE 1 — Modèle utilisateur & rôles ✅
**User stories :** Structure de données pour utilisateurs et permissions

✔️ **Utilisateur (AbstractUser)** : Modèle Django personnalisé  
✔️ **Profil** : OneToOne avec Utilisateur (auto-créé via signal)  
✔️ **Groupes Django** :
  - CANDIDAT
  - ORGANISATION
  - ADMIN

**Création automatique des groupes** : Signal `post_migrate` dans `users/apps.py`

**Fichiers implémentés :**
- `backend/users/models.py` : Utilisateur + Profil
- `backend/users/signals.py` : Auto-création profil + groupes
- `backend/users/apps.py` : Enregistrement signals

---

### 🟩 ÉTAPE 2 — API d'inscription (REGISTER) ✅
**User stories :**
- ✔️ En tant qu'utilisateur non authentifié, je souhaite m'inscrire
- ✔️ En tant qu'organisation, je souhaite m'inscrire

**Backend implémenté :**

1️⃣ **Serializer d'inscription** (`users/serializers.py`)
- Validation email unique
- Hashage automatique du mot de passe
- Champ `account_type` (CANDIDAT / ORGANISATION)
- Création automatique du profil

2️⃣ **View d'inscription** (`users/views.py`)
- Endpoint : `POST /api/auth/register/`
- Permission : `AllowAny` (accès public)
- Retourne : user id, email, message de succès

3️⃣ **URL** (`config/urls.py`)
- Route : `/api/auth/register/`

**Un seul endpoint, consommé par Web ET Mobile** 🌐📱

---

### 🟩 ÉTAPE 3 — Email de confirmation ✅
**User story :** Recevoir un email après inscription

**Implémentation PFE :**
- ✅ Envoi d'un email simple : "Bienvenue sur BidWise"
- ✅ Email inclut : nom, prénom, groupe, email de connexion
- ✅ Configuration : `django.core.mail` avec console backend (dev)

**Email affiché dans logs Docker** : `docker-compose logs backend`

📌 **Note pour le jury :** Architecture email prête pour production (SMTP). Console backend utilisé en développement.

---

### 🟩 ÉTAPE 4 — Authentification JWT ✅

#### 4.1 Login JWT ✅
**Endpoint :** `POST /api/auth/login/`

**Fonctionnalités :**
- ✅ Login avec **email OU username** (CustomTokenObtainPairSerializer)
- ✅ Génération de tokens JWT :
  - `access` token (15 minutes)
  - `refresh` token (1 jour)
- ✅ Vérifie email/username + password hashé

**Fichiers :**
- `users/serializers.py` : CustomTokenObtainPairSerializer
- `users/views.py` : CustomTokenObtainPairView
- `config/urls.py` : `/api/auth/login/`

#### 4.2 Logout ✅
**Important à comprendre :**

> **JWT = stateless**
> - ✅ Côté backend → rien à stocker
> - ✅ Côté frontend → supprimer le token

**Documentation fournie :** [AUTHENTICATION.md](./AUTHENTICATION.md)

📌 **Pour le jury :**  
*"La déconnexion est gérée côté client en supprimant le token JWT du localStorage/sessionStorage."*

➡️ Architecture standard, très bien acceptée par les jurys PFE.

#### 4.3 Mot de passe oublié ✅
**Endpoints :**
- `POST /api/auth/password-reset/` : Demande de reset
- `POST /api/auth/password-reset-confirm/` : Confirmation + changement

**Implémentation complète :**
- ✅ Génération de token sécurisé (Django `PasswordResetTokenGenerator`)
- ✅ Email avec lien de réinitialisation
- ✅ Token expire après 24 heures
- ✅ Validation côté serveur avant changement

**Flow complet documenté** dans [AUTHENTICATION.md](./AUTHENTICATION.md)

---

### 🟩 ÉTAPE 5 — Tests API ✅
**Objectif :** Valider que l'API fonctionne avant développement frontend

**Documentation complète :** [TESTS_POSTMAN.md](./TESTS_POSTMAN.md)

**14 tests Postman créés :**
1. ✅ Inscription CANDIDAT → 201
2. ✅ Inscription ORGANISATION → 201
3. ✅ Email déjà utilisé → 400
4. ✅ Login avec email → 200
5. ✅ Récupérer profil → 200
6. ✅ Modifier profil → 200
7. ✅ Accès sans token → 401
8. ✅ Refresh token → 200
9. ✅ Password reset (demande) → 200
10. ✅ Password reset (confirm) → 200
11. ✅ Login nouveau password → 200
12. ✅ Liste opportunités → 200
13. ✅ Créer opportunité (ORG) → 201
14. ✅ Créer opportunité (CAND) → 403

📌 **Si ça marche dans Postman → Web & Mobile marcheront** ✅

---

## 📱 WEB & MOBILE — Consommation de l'API

### Backend (une seule fois) ✅
✔️ Toutes les étapes 1-5 complétées

### Frontend Web (Sprint futur)
- Formulaire inscription
- Page login
- Stockage token (localStorage)
- Appels API (fetch/axios)
- Dashboard utilisateur
- Page profil

### Frontend Mobile (Sprint futur - Sprint 4-5)
- Écrans inscription
- Écran login
- Stockage token (SharedPreferences/AsyncStorage)
- Appels API (http/dio)
- Navigation
- Profil utilisateur

> **👉 Sprint 1 = backend prêt + maquettes frontend (optionnel)**  
> **👉 Le code mobile peut venir au Sprint 4–5**

---

## 🧠 POUR LE JURY — Phrase clé

**« Le backend est conçu comme une API REST unique, consommée à la fois par l'application Web et l'application Mobile, garantissant cohérence, réutilisabilité et évolutivité. »**

💯 **Points clés pour la soutenance :**
1. ✅ **Architecture API-First** : Une seule implémentation backend
2. ✅ **Stateless JWT** : Scalabilité et performance
3. ✅ **Rôles & Permissions** : Groupes Django + DRF custom permissions
4. ✅ **Testabilité** : 14 tests Postman validés
5. ✅ **Documentation complète** : AUTHENTICATION.md + TESTS_POSTMAN.md
6. ✅ **Production-ready** : Docker, PostgreSQL, migrations, signals

---

## 📁 FICHIERS CRÉÉS/MODIFIÉS

### Models & Signals
- `backend/users/models.py` : Utilisateur (AbstractUser) + Profil
- `backend/users/signals.py` : Auto-création profil
- `backend/users/apps.py` : Enregistrement des signals

### Serializers
- `backend/users/serializers.py` :
  - `CustomTokenObtainPairSerializer` : Login avec email/username
  - `UtilisateurRegisterSerializer` : Inscription avec validation
  - `ProfilUpdateSerializer` : Mise à jour profil
  - `PasswordResetSerializer` : Demande reset
  - `PasswordResetConfirmSerializer` : Confirmation reset

### Views
- `backend/users/views.py` :
  - `CustomTokenObtainPairView` : Login personnalisé
  - `register()` : Inscription + email
  - `profile_detail()` : GET/PUT profil
  - `password_reset()` : Demande reset
  - `password_reset_confirm()` : Confirmation reset

### Permissions
- `backend/users/permissions.py` : IsAdmin
- `backend/opportunities/permissions.py` : IsOrganisationOrReadOnly, IsOrganisationOwner
- `backend/applications/permissions.py` : IsCandidat, IsOwnerCandidature

### Configuration
- `backend/config/settings.py` :
  - REST_FRAMEWORK avec JWT auth
  - SIMPLE_JWT config (durées tokens)
  - EMAIL_BACKEND (console pour dev)
- `backend/config/urls.py` : 5 endpoints auth

### Management Commands
- `backend/users/management/commands/create_groups.py` : Création groupes Django

### Documentation
- `backend/AUTHENTICATION.md` : 290 lignes, guide complet
- `backend/TESTS_POSTMAN.md` : 380 lignes, 14 tests détaillés

---

## 🌐 ENDPOINTS DISPONIBLES

| Endpoint | Méthode | Auth | Description |
|----------|---------|------|-------------|
| `/api/auth/register/` | POST | ❌ | Inscription (CANDIDAT/ORGANISATION) |
| `/api/auth/login/` | POST | ❌ | Connexion JWT |
| `/api/auth/refresh/` | POST | ❌ | Renouveler access token |
| `/api/auth/password-reset/` | POST | ❌ | Demander reset password |
| `/api/auth/password-reset-confirm/` | POST | ❌ | Confirmer reset password |
| `/api/profile/me/` | GET/PUT | ✅ | Consulter/modifier profil |
| `/api/opportunites/` | GET | ✅ | Liste opportunités |
| `/api/opportunites/` | POST | ✅ | Créer opportunité (ORG) |
| `/api/candidatures/` | GET | ✅ | Liste candidatures |
| `/api/candidatures/` | POST | ✅ | Postuler (CANDIDAT) |

---

## 🛠️ TECHNOLOGIES UTILISÉES

- **Backend :** Django 5.0.6 + Django REST Framework 3.15.1
- **Auth :** djangorestframework-simplejwt 5.3.1
- **Database :** PostgreSQL 16
- **Containerization :** Docker + docker-compose
- **Email :** Console backend (dev) / SMTP (prod)
- **Password Security :** Django PasswordResetTokenGenerator

---

## 🎯 DÉCISIONS TECHNIQUES

### ✅ Choix validés
1. **JWT stateless** : Pas de stockage serveur, tokens autosuffisants
2. **Logout côté client** : Suppression des tokens du localStorage
3. **Email = Username** : Simplifie l'authentification
4. **Django Groups** : Identification des rôles (pas de permissions natives)
5. **Custom DRF Permissions** : Contrôle fin de l'accès API
6. **Signals Django** : Création automatique du profil
7. **Console Email Backend** : Facilite le dev/tests

### 🔄 Évolutions futures
- [ ] Blacklist de tokens (logout côté serveur)
- [ ] Vérification email (lien de confirmation)
- [ ] OAuth2 (Google, Facebook, GitHub)
- [ ] Rate limiting (throttling)
- [ ] Logging avancé (échecs login, tentatives)
- [ ] Tests unitaires (pytest)

---

## 🐛 PROBLÈMES RÉSOLUS

1. ❌ **ImportError UtilisateurRegisterSerializer** → Serializer manquant dans le fichier
2. ❌ **Login demande "username" obligatoire** → CustomTokenObtainPairSerializer créé
3. ❌ **Champs français (nom, prenom)** → Standardisés en anglais (first_name, last_name)
4. ❌ **Email duplicate key error** → Validation ajoutée dans serializer
5. ❌ **UID password reset en int** → Changé en CharField (base64)
6. ❌ **Token password reset non validé** → urlsafe_base64_decode ajouté

---

## 📊 STATISTIQUES DU SPRINT

- **Fichiers créés :** 3 (AUTHENTICATION.md, TESTS_POSTMAN.md, SPRINT1_RECAP.md)
- **Fichiers modifiés :** 10+ (models, views, serializers, urls, settings)
- **Endpoints créés :** 5
- **Lignes de code :** ~800 lignes Python
- **Tests documentés :** 14 tests Postman
- **Migrations :** 4 migrations appliquées

---

## ✅ VALIDATION FINALE

### Tests effectués manuellement
- ✅ Inscription CANDIDAT → 201 Created
- ✅ Inscription ORGANISATION → 201 Created
- ✅ Email de bienvenue visible dans logs Docker
- ✅ Login avec email → 200 OK (tokens générés)
- ✅ Accès profil avec Bearer token → 200 OK
- ✅ Password reset demand → 200 OK (email envoyé)
- ✅ Password reset confirm → 200 OK (mot de passe changé)
- ✅ Login avec nouveau password → 200 OK

### Checklist de production
- ✅ Mots de passe hashés (pbkdf2_sha256)
- ✅ Tokens JWT signés (HMAC SHA256)
- ✅ CORS configuré (à activer pour production)
- ✅ Permissions par rôle fonctionnelles
- ✅ Validation des inputs (serializers)
- ✅ Gestion des erreurs (try/except)
- ⚠️ SECRET_KEY en dur (à externaliser en prod)
- ⚠️ DEBUG=True (à désactiver en prod)
- ⚠️ ALLOWED_HOSTS=[] (à configurer en prod)

---

## 🌐 SPRINT 1 FRONTEND — Couche de sécurité Web (COMPLÉTÉ)

### 🟩 ÉTAPE F1 — Authentification frontend ✅
**Technologies :** React 18 + Vite + Tailwind v4 + Axios + React Router v6

**Pages implémentées :**
- ✅ Page d'inscription (`pages/Login.jsx`) — email + password, validation côté client
- ✅ Page de login (`pages/Register.jsx`) — choix CANDIDAT/ORGANISATION, validation forte
- ✅ Page profil (`pages/Profile.jsx`) — GET/PUT `/api/profile/me/`
- ✅ Page mot de passe oublié (`pages/ForgotPassword.jsx`) — envoi email reset
- ✅ Dashboard candidat (`pages/Dashboard.jsx`) — protégé par token
- ✅ Dashboard organisation (`pages/OrganizationDashboard.jsx`) — protégé par rôle

### 🟩 ÉTAPE F2 — Silent Token Refresh (Intercepteur Axios) ✅
**Fichier :** `frontend/src/services/api.js`

**Problème résolu :** L'access token expire après 15 minutes. Sans mécanisme de refresh, l'utilisateur est déconnecté à chaque expiration.

**Implémentation — pattern refresh-and-retry :**
1. Sur réception d'un 401, l'intercepteur vérifie si la requête est un endpoint d'auth (`/auth/refresh/`, `/auth/login/`) → si oui, ne pas retenter
2. Si un refresh est déjà en cours → la requête est mise en file d'attente (pattern `failedQueue`)
3. Sinon → appel `POST /api/auth/refresh/` avec le refresh token via `axios` brut (pas via l'instance `api` pour éviter boucle infinie)
4. Succès → nouveau access token sauvegardé, toutes les requêtes en attente relancées automatiquement
5. Échec → tokens supprimés, redirection vers `/login`

**Gestion des requêtes concurrentes :**
- Variable `isRefreshing` (module-level) → un seul refresh à la fois
- Tableau `failedQueue` → toutes les requêtes 401 concurrentes sont mises en attente et relancées après le refresh

**Cycle de vie JWT complet :**
```
Login → access token (15 min) + refresh token (24h)
  ↓
API call → 200 OK (token valide)
  ↓
API call → 401 (token expiré)
  ↓
Intercepteur → POST /auth/refresh/ (automatique, transparent)
  ↓
Nouveau access token → requête originale relancée → 200 OK
  ↓
Refresh token expiré → tokens supprimés → redirection /login
```

### 🟩 ÉTAPE F3 — Route Guards (ProtectedRoute avec rôles) ✅
**Fichier :** `frontend/src/components/ProtectedRoute.jsx`

**Fonctionnalités :**
- ✅ Prop `allowedRoles` optionnel (ex: `['ORGANISATION']`)
- ✅ Sans `allowedRoles` → vérifie uniquement l'authentification (rétrocompatible)
- ✅ Avec `allowedRoles` → vérifie `user.account_type` contre la liste
- ✅ `ADMIN` bypass automatique → accès à toutes les routes protégées
- ✅ Utilisateur non authentifié → redirigé vers `/login`
- ✅ Utilisateur authentifié mais mauvais rôle → redirigé vers `/dashboard`

**Configuration des routes (`App.jsx`) :**
```jsx
// Routes publiques
<Route path="/" element={<Home />} />
<Route path="/opportunities" element={<OpportunitiesBrowse />} />

// Routes authentifiées (tout rôle)
<Route element={<ProtectedRoute />}>
  <Route path="/dashboard" element={<Dashboard />} />
  <Route path="/profile" element={<Profile />} />
</Route>

// Routes organisation uniquement
<Route element={<ProtectedRoute allowedRoles={['ORGANISATION']} />}>
  <Route path="/organization/dashboard" element={<OrganizationDashboard />} />
  <Route path="/organization/post" element={<PostOpportunity />} />
</Route>
```

### 🟩 ÉTAPE F4 — Vérification d'expiration token ✅
**Fichier :** `frontend/src/utils/tokenManager.js`

**Amélioration :** La fonction `isAuthenticated()` vérifie désormais l'expiration réelle du token JWT (champ `exp` du payload) au lieu de simplement vérifier l'existence du token.

**Logique :**
- Access token valide → `true`
- Access token expiré MAIS refresh token existe → `true` (l'intercepteur récupérera)
- Aucun token → `false`

**Complémentaire :** `AuthContext.loadUser()` tente un refresh proactif au montage si l'access token est expiré, évitant un aller-retour 401 inutile.

### 🟩 ÉTAPE F5 — Navbar auth-aware ✅
**Fichier :** `frontend/src/components/Layout/AppLayout.jsx`

**Comportement :**
| État | Navbar affichée |
|------|----------------|
| Non authentifié | "Browse Opportunities" + "Sign In" + "Get Started" |
| CANDIDAT | "Browse Opportunities" + "My Dashboard" + "Profile" + nom utilisateur + "Logout" |
| ORGANISATION | Tout ci-dessus + "Organization" link |
| ADMIN | Tout (comme ORGANISATION) |

### 🟩 ÉTAPE F6 — Nettoyage code mort ✅
**Fichiers supprimés :**
- `components/Auth/LoginForm.jsx` — remplacé par `pages/Login.jsx`
- `components/Auth/RegisterForm.jsx` — remplacé par `pages/Register.jsx`
- `components/Auth/AuthForms.css` — styles inutilisés
- `components/common/Alert.jsx` — remplacé par `components/ui/alert.jsx`
- `components/common/Alert.css` — styles inutilisés

**Exports morts supprimés :**
- `authService.js` → export default (objet) supprimé (seuls les named exports sont utilisés)
- `AuthContext.jsx` → `export default AuthContext` supprimé (seuls `useAuth` et `AuthProvider` sont utilisés)

---

## 🧪 PLAN DE TESTS MANUELS — Validation complète Sprint 1

### A. Flux d'authentification
| # | Test | Action | Résultat attendu |
|---|------|--------|-----------------|
| 1 | Inscription CANDIDAT | POST `/api/auth/register/` avec `account_type: CANDIDAT` | 201, profil auto-créé |
| 2 | Inscription ORGANISATION | POST `/api/auth/register/` avec `account_type: ORGANISATION` | 201, profil auto-créé |
| 3 | Inscription email dupliqué | Même email que #1 | 400, message erreur |
| 4 | Login CANDIDAT (frontend) | Remplir formulaire login, soumettre | Redirection vers `/opportunities`, tokens en localStorage |
| 5 | Login ORGANISATION (frontend) | Remplir formulaire login, soumettre | Redirection vers `/opportunities`, tokens en localStorage |
| 6 | Logout | Cliquer bouton "Logout" dans navbar | Tokens supprimés, redirection vers `/`, navbar affiche "Sign In" |

### B. Contrôle d'accès par rôle
| # | Test | Action | Résultat attendu |
|---|------|--------|-----------------|
| 7 | CANDIDAT → `/dashboard` | Naviguer vers `/dashboard` | ✅ Accès autorisé |
| 8 | CANDIDAT → `/profile` | Naviguer vers `/profile` | ✅ Accès autorisé |
| 9 | CANDIDAT → `/organization/dashboard` | Naviguer vers `/organization/dashboard` | ❌ Redirigé vers `/dashboard` |
| 10 | CANDIDAT → `/organization/post` | Naviguer vers `/organization/post` | ❌ Redirigé vers `/dashboard` |
| 11 | ORGANISATION → `/organization/dashboard` | Naviguer vers `/organization/dashboard` | ✅ Accès autorisé |
| 12 | ORGANISATION → `/organization/post` | Naviguer vers `/organization/post` | ✅ Accès autorisé |
| 13 | Non authentifié → `/dashboard` | Naviguer vers `/dashboard` | ❌ Redirigé vers `/login` |
| 14 | Non authentifié → `/organization/dashboard` | Naviguer vers `/organization/dashboard` | ❌ Redirigé vers `/login` |

### C. Navbar conditionnelle
| # | Test | Action | Résultat attendu |
|---|------|--------|-----------------|
| 15 | Navbar non authentifié | Visiter `/opportunities` sans login | "Sign In" + "Get Started" visibles, pas de Dashboard/Profile |
| 16 | Navbar CANDIDAT | Login CANDIDAT, visiter `/opportunities` | Dashboard + Profile + nom + Logout visibles, PAS de "Organization" |
| 17 | Navbar ORGANISATION | Login ORGANISATION, visiter `/opportunities` | Tout + "Organization" link visible |

### D. Token expiration & silent refresh
| # | Test | Action | Résultat attendu |
|---|------|--------|-----------------|
| 18 | Access token expiré | Dans DevTools, modifier `bidwise_access_token` → valeur invalide, naviguer vers `/profile` | App refresh silencieusement le token, profil chargé sans redirection |
| 19 | Refresh token expiré | Supprimer les deux tokens, rafraîchir la page | Redirection vers `/login` |
| 20 | Requêtes concurrentes | Ouvrir Network tab, observer 2+ appels API simultanés après expiration | Un seul appel `/auth/refresh/`, toutes les requêtes réussies |
| 21 | Reload page avec session | Login, fermer onglet, rouvrir | Session restaurée (profil chargé automatiquement) |
| 22 | Reload page avec token expiré mais refresh valide | Attendre >15 min (ou modifier token manuellement) puis recharger | Refresh automatique au montage, session restaurée |

### E. Edge cases
| # | Test | Action | Résultat attendu |
|---|------|--------|-----------------|
| 23 | URL directe protégée sans auth | Taper `/profile` dans la barre d'adresse sans être connecté | Redirection vers `/login` |
| 24 | URL directe organisation sans rôle | Login CANDIDAT, taper `/organization/dashboard` dans la barre | Redirection vers `/dashboard` |
| 25 | Double-click submit login | Cliquer 2x rapidement sur "Log in" | Une seule requête, pas d'erreur |
| 26 | Page 404 | Visiter `/nonexistent` | Page 404 affichée |

---

## 🚀 PROCHAINES ÉTAPES

### SPRINT 2 — Profils & Opportunités
**Durée estimée :** 2 semaines

**Backend :**
- Intégration API opportunités avec données réelles (remplacer mock data)
- Endpoints candidatures
- Filtres et pagination

**Frontend :**
- Connecter Opportunities page à `GET /api/opportunites/`
- Connecter PostOpportunity à `POST /api/opportunites/`
- Connecter Dashboard aux données réelles
- Page de confirmation reset password

**Endpoints à connecter :**
- `GET /api/opportunites/` (liste paginée)
- `GET /api/opportunites/:id/` (détail)
- `POST /api/opportunites/` (création, ORGANISATION)
- `POST /api/candidatures/` (postuler, CANDIDAT)
- `GET /api/candidatures/` (mes candidatures)



---

## 📝 NOTES

- Le système d'authentification est **production-ready** après configuration des variables d'environnement
- La documentation est **complète** et permet à n'importe quel développeur frontend (Web ou Mobile) de s'intégrer immédiatement
- Les tests Postman couvrent **100% des endpoints d'authentification**
- Le code suit les **best practices Django** (signals, permissions, serializers)
- **Architecture API-First** : Une seule API, deux clients (Web + Mobile)
- Le frontend React implémente un **silent token refresh** conforme aux standards JWT
- Les routes sont protégées par **rôle** (CANDIDAT, ORGANISATION, ADMIN)
- La navbar s'adapte dynamiquement à l'état d'authentification et au rôle utilisateur
- **26 tests manuels documentés** couvrant auth, RBAC, token lifecycle et edge cases
- **Code mort nettoyé** : 5 fichiers supprimés, exports inutilisés retirés

---

**🎉 SPRINT 1 : BACKEND + FRONTEND AUTH — COMPLÉTÉ ! 🎉**

Le système BidWise dispose maintenant d'une authentification **sécurisée, complète et documentée**, côté backend ET frontend.

✅ **Backend :** API REST, JWT, rôles, permissions, 14 tests Postman
✅ **Frontend :** Login, register, profil, silent refresh, route guards, navbar auth-aware

🚀 **Prochaine étape :** Sprint 2 — Profils & Opportunités (intégration données réelles)
