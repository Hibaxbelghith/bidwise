# 🧪 Guide de Tests Postman - BidWise API

## 📋 Objectif
Valider l'ensemble du système d'authentification et des ressources protégées de BidWise.

---

## ⚙️ Configuration Postman

### Variables d'environnement (recommandé)
Créer un environnement "BidWise Local" avec :

```
base_url = http://localhost:8000
access_token = (vide au départ)
refresh_token = (vide au départ)
```

---

## 🧪 TESTS À EFFECTUER

### ✅ TEST 1 : Inscription d'un CANDIDAT

**Request:**
```
POST {{base_url}}/api/auth/register/
Content-Type: application/json

{
  "email": "candidat.test@bidwise.fr",
  "password": "SecurePass123",
  "password2": "SecurePass123",
  "first_name": "Jean",
  "last_name": "Candidat",
  "account_type": "CANDIDAT"
}
```

**Validation attendue:**
- ✅ Status: `201 Created`
- ✅ Response contient : `id`, `username`, `email`, `message`
- ✅ Email de bienvenue dans logs Docker : `docker-compose logs backend`
- ✅ Groupe "CANDIDAT" assigné

**Tests Postman:**
```javascript
pm.test("Status code is 201", function () {
    pm.response.to.have.status(201);
});

pm.test("Response has id and email", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('id');
    pm.expect(jsonData).to.have.property('email');
    pm.expect(jsonData.email).to.eql('candidat.test@bidwise.fr');
});
```

---

### ✅ TEST 2 : Inscription d'une ORGANISATION

**Request:**
```
POST {{base_url}}/api/auth/register/
Content-Type: application/json

{
  "email": "organisation.test@bidwise.fr",
  "password": "SecurePass123",
  "password2": "SecurePass123",
  "first_name": "Entreprise",
  "last_name": "TechCorp",
  "account_type": "ORGANISATION"
}
```

**Validation attendue:**
- ✅ Status: `201 Created`
- ✅ Groupe "ORGANISATION" assigné
- ✅ Email de bienvenue reçu

---

### ✅ TEST 3 : Validation des erreurs d'inscription

#### A. Email déjà utilisé
```
POST {{base_url}}/api/auth/register/

{
  "email": "candidat.test@bidwise.fr",  // Déjà inscrit
  "password": "SecurePass123",
  "password2": "SecurePass123",
  "first_name": "Autre",
  "last_name": "User",
  "account_type": "CANDIDAT"
}
```

**Validation :**
- ✅ Status: `400 Bad Request`
- ✅ Message : "Un utilisateur avec cet email existe déjà."

#### B. Mots de passe ne correspondent pas
```json
{
  "email": "new@bidwise.fr",
  "password": "SecurePass123",
  "password2": "DifferentPass456",  // Différent !
  "first_name": "Test",
  "last_name": "User",
  "account_type": "CANDIDAT"
}
```

**Validation :**
- ✅ Status: `400 Bad Request`
- ✅ Message : "Les mots de passe ne correspondent pas."

---

### ✅ TEST 4 : Login avec email

**Request:**
```
POST {{base_url}}/api/auth/login/
Content-Type: application/json

{
  "username": "candidat.test@bidwise.fr",
  "password": "SecurePass123"
}
```

**Validation attendue:**
- ✅ Status: `200 OK`
- ✅ Response contient : `access` et `refresh` tokens

**Tests Postman (sauvegarder les tokens):**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Response has tokens", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('access');
    pm.expect(jsonData).to.have.property('refresh');
    
    // Sauvegarder dans les variables d'environnement
    pm.environment.set("access_token", jsonData.access);
    pm.environment.set("refresh_token", jsonData.refresh);
});
```

---

### ✅ TEST 5 : Accès au profil (avec token)

**Request:**
```
GET {{base_url}}/api/profile/me/
Authorization: Bearer {{access_token}}
```

**Validation attendue:**
- ✅ Status: `200 OK`
- ✅ Response contient : `nom`, `prenom`, `competences`, `domaines_interet`, `niveau_experience`

**Tests Postman:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Profile has required fields", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('nom');
    pm.expect(jsonData).to.have.property('prenom');
    pm.expect(jsonData.prenom).to.eql('Jean');
});
```

---

### ✅ TEST 6 : Mise à jour du profil

**Request:**
```
PUT {{base_url}}/api/profile/me/
Authorization: Bearer {{access_token}}
Content-Type: application/json

{
  "competences": "Python, Django, React",
  "domaines_interet": "IA, Data Science",
  "niveau_experience": "CONFIRME",
  "annees_experience": 5
}
```

**Validation attendue:**
- ✅ Status: `200 OK`
- ✅ Les champs sont mis à jour

---

### ✅ TEST 7 : Accès sans token (401)

**Request:**
```
GET {{base_url}}/api/profile/me/
# SANS Authorization header !
```

**Validation attendue:**
- ✅ Status: `401 Unauthorized`
- ✅ Message : "Authentication credentials were not provided."

---

### ✅ TEST 8 : Refresh Token

**Request:**
```
POST {{base_url}}/api/auth/refresh/
Content-Type: application/json

{
  "refresh": "{{refresh_token}}"
}
```

**Validation attendue:**
- ✅ Status: `200 OK`
- ✅ Nouveau `access` token généré

**Tests Postman:**
```javascript
pm.test("New access token generated", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('access');
    pm.environment.set("access_token", jsonData.access);
});
```

---

### ✅ TEST 9 : Password Reset (Demande)

**Request:**
```
POST {{base_url}}/api/auth/password-reset/
Content-Type: application/json

{
  "email": "candidat.test@bidwise.fr"
}
```

**Validation attendue:**
- ✅ Status: `200 OK`
- ✅ Message : "Un email de réinitialisation a été envoyé"
- ✅ Email visible dans logs Docker avec `uid` et `token`

**Action manuelle :**
- Copier `uid` et `token` depuis les logs

---

### ✅ TEST 10 : Password Reset (Confirmation)

**Request:**
```
POST {{base_url}}/api/auth/password-reset-confirm/
Content-Type: application/json

{
  "uid": "MQ",  // Depuis l'email
  "token": "d4ohzo-44a36174df34a0c41d6e0071834e7188",  // Depuis l'email
  "new_password": "NewSecurePass456",
  "new_password2": "NewSecurePass456"
}
```

**Validation attendue:**
- ✅ Status: `200 OK`
- ✅ Message : "Votre mot de passe a été réinitialisé avec succès"

---

### ✅ TEST 11 : Login avec nouveau mot de passe

**Request:**
```
POST {{base_url}}/api/auth/login/
Content-Type: application/json

{
  "username": "candidat.test@bidwise.fr",
  "password": "NewSecurePass456"  // Nouveau mot de passe
}
```

**Validation attendue:**
- ✅ Status: `200 OK`
- ✅ Tokens générés correctement

---

### ✅ TEST 12 : Accès aux opportunités (GET)

**Request:**
```
GET {{base_url}}/api/opportunites/
Authorization: Bearer {{access_token}}
```

**Validation attendue:**
- ✅ Status: `200 OK`
- ✅ Liste paginée des opportunités (peut être vide)
- ✅ Structure : `count`, `next`, `previous`, `results`

---

### ✅ TEST 13 : Créer une opportunité (ORGANISATION uniquement)

**Pré-requis :** Se connecter avec un compte ORGANISATION

**Request:**
```
POST {{base_url}}/api/opportunites/
Authorization: Bearer {{access_token}}  // Token d'ORGANISATION
Content-Type: application/json

{
  "titre": "Développeur Django Senior",
  "description": "Nous recherchons un développeur Django expérimenté",
  "type_opportunite": "OFFRE_EMPLOI",
  "date_limite": "2026-03-15",
  "budget": 60000,
  "competences_requises": "Python, Django, PostgreSQL, Docker"
}
```

**Validation attendue:**
- ✅ Status: `201 Created` (si ORGANISATION)
- ✅ Status: `403 Forbidden` (si CANDIDAT essaye)

---

### ✅ TEST 14 : Permissions refusées (CANDIDAT crée opportunité)

**Request:**
```
POST {{base_url}}/api/opportunites/
Authorization: Bearer {{access_token}}  // Token de CANDIDAT
Content-Type: application/json

{
  "titre": "Test",
  "description": "Test",
  "type_opportunite": "OFFRE_EMPLOI"
}
```

**Validation attendue:**
- ✅ Status: `403 Forbidden`
- ✅ Message : Permission refusée

---

## 📊 RÉCAPITULATIF DES TESTS

| # | Test | Endpoint | Méthode | Status attendu |
|---|------|----------|---------|----------------|
| 1 | Inscription CANDIDAT | `/api/auth/register/` | POST | 201 |
| 2 | Inscription ORGANISATION | `/api/auth/register/` | POST | 201 |
| 3 | Email déjà utilisé | `/api/auth/register/` | POST | 400 |
| 4 | Login avec email | `/api/auth/login/` | POST | 200 |
| 5 | Récupérer profil | `/api/profile/me/` | GET | 200 |
| 6 | Modifier profil | `/api/profile/me/` | PUT | 200 |
| 7 | Accès sans token | `/api/profile/me/` | GET | 401 |
| 8 | Refresh token | `/api/auth/refresh/` | POST | 200 |
| 9 | Password reset (demande) | `/api/auth/password-reset/` | POST | 200 |
| 10 | Password reset (confirm) | `/api/auth/password-reset-confirm/` | POST | 200 |
| 11 | Login nouveau password | `/api/auth/login/` | POST | 200 |
| 12 | Liste opportunités | `/api/opportunites/` | GET | 200 |
| 13 | Créer opportunité (ORG) | `/api/opportunites/` | POST | 201 |
| 14 | Créer opportunité (CAND) | `/api/opportunites/` | POST | 403 |

---

## 🚀 EXÉCUTION DES TESTS

### Option 1 : Tests manuels dans Postman
1. Créer une collection "BidWise Auth"
2. Ajouter les 14 requêtes ci-dessus
3. Exécuter dans l'ordre (1 → 14)
4. Valider chaque status code et response

### Option 2 : Collection Runner Postman
1. Importer toutes les requêtes
2. Cliquer sur "Run Collection"
3. Observer les résultats automatisés

### Option 3 : Tests automatisés (futur)
```bash
# Avec Newman (CLI Postman)
newman run BidWise_Collection.json -e BidWise_Environment.json
```

---

## 📝 CHECKLIST DE VALIDATION

### Authentification
- [ ] Inscription CANDIDAT fonctionne
- [ ] Inscription ORGANISATION fonctionne
- [ ] Email de bienvenue reçu
- [ ] Login avec email/username fonctionne
- [ ] Tokens JWT générés correctement
- [ ] Refresh token fonctionne
- [ ] Password reset (demande + confirmation) fonctionne
- [ ] Login avec nouveau mot de passe fonctionne

### Profil
- [ ] GET /api/profile/me/ retourne le profil
- [ ] PUT /api/profile/me/ met à jour le profil
- [ ] Accès protégé sans token → 401

### Permissions
- [ ] CANDIDAT peut lire opportunités
- [ ] CANDIDAT ne peut PAS créer opportunités (403)
- [ ] ORGANISATION peut créer opportunités (201)
- [ ] ADMIN a tous les accès

### Sécurité
- [ ] Mots de passe hashés en base
- [ ] Tokens expirés → 401
- [ ] Email unique validé
- [ ] Password reset token expire (24h)

---

## 🎯 RÉSULTAT ATTENDU

**✅ Tous les tests passent = SPRINT 1 complété avec succès !**

Le backend est prêt pour :
- 📱 Intégration mobile (Flutter/React Native)
- 🌐 Intégration web (React/Vue/Angular)
- 🔌 Consommation API par n'importe quel client

---

**Dernière mise à jour :** 6 février 2026
