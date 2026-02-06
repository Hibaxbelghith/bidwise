# 🔐 Documentation d'Authentification - BidWise

## Vue d'ensemble
BidWise utilise **JWT (JSON Web Tokens)** via `djangorestframework-simplejwt` pour l'authentification. Tous les endpoints sauf `/register/` et `/login/` sont protégés.

---

## 1️⃣ INSCRIPTION (ÉTAPE 2)

### Endpoint
```
POST /api/auth/register/
Content-Type: application/json
```

### Request Body
```json
{
  "email": "alice@bidwise.fr",
  "password": "SecurePass123",
  "password2": "SecurePass123",
  "first_name": "Alice",
  "last_name": "Dupont",
  "account_type": "CANDIDAT"
}
```

**Champs obligatoires :**
- `email` : Email unique (sera aussi le username)
- `password` : Mot de passe (min 8 caractères recommandé)
- `password2` : Confirmation du mot de passe
- `first_name` : Prénom
- `last_name` : Nom de famille
- `account_type` : `CANDIDAT` ou `ORGANISATION`

### Response (201 Created)
```json
{
  "id": 1,
  "username": "alice@bidwise.fr",
  "email": "alice@bidwise.fr",
  "message": "Inscription réussie ! Vous pouvez maintenant vous connecter."
}
```

**Automatiquement créé :**
- ✅ Profil utilisateur (profil.nom, profil.prenom)
- ✅ Assignation au groupe Django (CANDIDAT ou ORGANISATION)
- ✅ Email de bienvenue envoyé

**Erreurs possibles :**
- `400` : Email déjà utilisé, mots de passe ne correspondent pas
- `400` : Champ manquant ou invalid

---

## 2️⃣ LOGIN (ÉTAPE 4.1)

### Endpoint
```
POST /api/auth/login/
Content-Type: application/json
```

### Request Body
```json
{
  "username": "alice@bidwise.fr",
  "password": "SecurePass123"
}
```

**Notes :**
- Le champ `username` accepte **email OU username** (dans ce cas, ils sont identiques)
- L'API cherche d'abord par email, puis par username

### Response (200 OK)
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Tokens :**
- `access` : Token d'accès (valide 15 minutes) → Pour accéder aux ressources protégées
- `refresh` : Token de rafraîchissement (valide 1 jour) → Pour obtenir un nouveau token d'accès

---

## 3️⃣ REFRESH TOKEN (RENOUVELER L'ACCÈS)

### Endpoint
```
POST /api/auth/refresh/
Content-Type: application/json
```

### Request Body
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Response (200 OK)
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Utilisation :** Quand le token d'accès expire (15 min), utilise le refresh token pour en obtenir un nouveau **sans re-entrâmer les credentials**.

---

## 4️⃣ **PASSWORD RESET (ÉTAPE 4.3)**

### Étape 1️⃣ : Demander une réinitialisation

**Endpoint**
```
POST /api/auth/password-reset/
Content-Type: application/json
```

**Request Body**
```json
{
  "email": "alice@bidwise.fr"
}
```

**Response (200 OK)**
```json
{
  "message": "Un email de réinitialisation a été envoyé à votre adresse."
}
```

📧 **Email reçu avec lien** :
```
Sujet: Réinitialisation de votre mot de passe BidWise

Bonjour Alice Dupont,

Vous avez demandé une réinitialisation de votre mot de passe BidWise.

Cliquez sur le lien ci-dessous pour réinitialiser votre mot de passe :
http://localhost:3000/password-reset-confirm/?uid=MQ==&token=...

Ce lien expire dans 24 heures.
```

---

### Étape 2️⃣ : Confirmer la réinitialisation

**Endpoint**
```
POST /api/auth/password-reset-confirm/
Content-Type: application/json
```

**Request Body**
```json
{
  "uid": 1,
  "token": "...",
  "new_password": "NewSecurePass123",
  "new_password2": "NewSecurePass123"
}
```

**Récupération de uid et token** :
- Le lien d'email contient les paramètres : `?uid=<uid>&token=<token>`
- Extraire depuis l'URL et envoyer comme JSON au backend

**Response (200 OK)**
```json
{
  "message": "Votre mot de passe a été réinitialisé avec succès. Vous pouvez maintenant vous connecter."
}
```

**Erreurs possibles** :
- `400` : Token invalide ou expiré (+ de 24h)
- `404` : Utilisateur non trouvé
- `400` : Mots de passe ne correspondent pas

---

## 5️⃣ **LOGOUT (⭐ IMPORTANT)

### ❌ Pas d'endpoint serveur pour le logout !

**Le logout JWT est gérée côté CLIENT.** Il n'y a pas de route `/api/auth/logout/` car :

1. ✅ Les tokens JWT sont **stateless** (pas stockés côté serveur)
2. ✅ Il n'y a rien à supprimer sur le serveur
3. ✅ Le client contrôle entièrement sa session

### ✅ Comment implémenter le logout côté client

#### **JavaScript / React / Vue / Angular :**

```javascript
// 1. Supprimer les tokens du stockage
localStorage.removeItem('access_token');
localStorage.removeItem('refresh_token');
sessionStorage.removeItem('access_token');
sessionStorage.removeItem('refresh_token');

// 2. Rediriger vers la page de login
window.location.href = '/login';
```

#### **React (Example):**

```javascript
const logout = () => {
  // Supprimer les tokens
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  
  // Mettre à jour l'état de l'utilisateur
  setUser(null);
  
  // Rediriger
  navigate('/login');
};
```

#### **Flutter / React Native :**

```dart
// Dart/Flutter
Future<void> logout() async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.remove('access_token');
  await prefs.remove('refresh_token');
  
  // Rediriger vers login
  navigateTo('/login');
}
```

### 🔒 Avancement du logout en production

Pour une sécurité accrue, tu peux aussi :

1. **Blacklister les tokens** (optionnel) : Ajouter une table `TokenBlacklist` et vérifier avant chaque requête
2. **Ajouter un endpoint `/api/auth/logout/`** qui log simplement l'action (optionnel pour audit)
3. **Ajouter une expiration plus courte** du refresh token

---

## 6️⃣ ACCÉDER AUX RESSOURCES PROTÉGÉES

### Utiliser le token d'accès

**Header requis :**
```
Authorization: Bearer <access_token>
```

### Exemple : Récupérer son profil
```
GET /api/profile/me/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

### Réponse (200 OK)
```json
{
  "nom": "Dupont",
  "prenom": "Alice",
  "competences": "",
  "domaines_interet": "",
  "niveau_experience": null,
  "annees_experience": null
}
```

### Erreurs possibles
- `401 Unauthorized` : Token manquant ou expiré → Utilise le refresh token
- `403 Forbidden` : Permissions insuffisantes (rôle non autorisé)
- `404 Not Found` : Ressource inexistante

---

## 📋 CONFIGURATION DJANGO

**settings.py :**
```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),      # Expire en 15 min
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),         # Expire en 1 jour
    'AUTH_HEADER_TYPES': ('Bearer',),
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',    # Protégé par défaut
    ),
}
```

---

## 🧪 FLOW COMPLET DE TEST

### 1. Inscription
```bash
POST /api/auth/register/
→ 201 Created (user + groupe + email)
```

### 2. Login
```bash
POST /api/auth/login/
→ 200 OK (access + refresh tokens)
```

### 3. Utiliser le token
```bash
GET /api/profile/me/
Header: Authorization: Bearer <access_token>
→ 200 OK (données utilisateur)
```

### 4. Password Reset (optionnel)
```bash
POST /api/auth/password-reset/
Body: {"email": "alice@bidwise.fr"}
→ 200 OK (email envoyé)

POST /api/auth/password-reset-confirm/
Body: {"uid": 1, "token": "...", "new_password": "...", "new_password2": "..."}
→ 200 OK (mot de passe changé)
```

### 5. Logout (CLIENT SIDE)
```javascript
localStorage.removeItem('access_token');
localStorage.removeItem('refresh_token');
// Token supprimé du client, session fermée
```

### 6. Rafraîchir le token (si besoin)
```bash
POST /api/auth/refresh/
Body: {"refresh": "<refresh_token>"}
→ 200 OK (nouveau access_token)
```

---

## ⚙️ RÔLES & PERMISSIONS

Chaque utilisateur est assigné à un groupe lors de l'inscription :

| Groupe | Account Type | Permissions |
|--------|-------------|------------|
| **CANDIDAT** | `CANDIDAT` | Peut consulter opportunités, postuler, voir son profil |
| **ORGANISATION** | `ORGANISATION` | Peut créer opportunités, consulter candidatures |
| **ADMIN** | Admin Django | Accès complet |

Pour vérifier le rôle de l'utilisateur connecté :
```python
request.user.groups.filter(name='CANDIDAT').exists()  # True/False
```

---

## 🛠️ TROUBLESHOOTING

### ❌ "Token is invalid or expired" (401)
→ Utilise le refresh token pour en obtenir un nouveau

### ❌ "This field is required" (400) lors du login
→ Vérifie que tu envoies `username` et `password` en JSON

### ❌ Email non reçu
→ Vérifiez les logs Docker : `docker-compose logs backend | grep -A 10 "Subject: Bienvenue"`

### ❌ Email déjà utilisé
→ Utilise un nouvel email ou réinitialise la BD : `docker-compose down -v && docker-compose up`

---

## 📚 Ressources

- [djangorestframework-simplejwt](https://django-rest-framework-simplejwt.readthedocs.io/)
- [JWT.io](https://jwt.io/) - Décoder les tokens pour déboguer
- [Django Groups & Permissions](https://docs.djangoproject.com/en/5.0/topics/auth/default/)

---

**Dernière mise à jour :** 6 février 2026
