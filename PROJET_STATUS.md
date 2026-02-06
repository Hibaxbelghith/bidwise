# BidWise — État d'avancement du projet

**Projet :** BidWise — Plateforme intelligente de gestion des opportunités  
**Type :** PFE (Projet de Fin d'Études) — TWIN

---

## Architecture Globale

```
┌─────────────────────────────────────────────────────────┐
│                   CLIENTS (Consommateurs)               │
├─────────────────────────────────────────────────────────┤
│   Application Web           Application Mobile          │
│  (React/Vue/Angular)         (Flutter/React Native)     │
│                                                         │
│  ├─ Pages inscription        ├─ Écrans inscription      │
│  ├─ Login                    ├─ Login                   │
│  ├─ Dashboard                ├─ Navigation              │
│  └─ Profil                   └─ Profil                  │
└──────────────────┬──────────────────┬───────────────────┘
                   │                  │
                   └─────────┬────────┘
                             │
              ┌──────────────▼──────────────┐
              │     API REST (Backend)      │
              │   Django + DRF + JWT        │
              │  PostgreSQL + Docker        │
              │                             │
              │  Endpoints :                │
              │  • /api/auth/register/      │
              │  • /api/auth/login/         │
              │  • /api/auth/refresh/       │
              │  • /api/profile/me/         │
              │  • /api/opportunites/       │
              │  • /api/candidatures/       │
              └─────────────────────────────┘
```

**Architecture API-First :** Une seule API, plusieurs clients (Web + Mobile)

---

## ✅ SPRINT 1 — État : COMPLÉTÉ (Backend uniquement)

### 📦 Livré

| Composant | État | Description |
|-----------|------|-------------|
| **Backend API** | ✅ 100% | Django REST Framework avec JWT |
| **Authentification** | ✅ Complète | Inscription, Login, Password Reset |
| **Permissions** | ✅ Complète | Groupes (CANDIDAT/ORGANISATION/ADMIN) |
| **Base de données** | ✅ PostgreSQL | Migrations appliquées |
| **Docker** | ✅ Configuré | docker-compose prêt |
| **Documentation** | ✅ Complète | AUTHENTICATION.md + TESTS_POSTMAN.md |
| **Tests API** | ✅ 14 tests | Validés avec Postman |
| **Frontend Web** | ⏳ À venir | Sprint 2 |
| **Frontend Mobile** | ⏳ À venir | Sprint 4-5 |

---

## 📋 Sprints Planifiés

### ✅ SPRINT 1 — Authentification (Backend API) [COMPLÉTÉ]
**Durée :** 1 journée  
**Objectif :** API d'authentification complète (inscription, login, JWT, password reset)

**Tâches terminées :**
- [x] ÉTAPE 1 : Modèles utilisateur & rôles
- [x] ÉTAPE 2 : API d'inscription (POST /api/auth/register/)
- [x] ÉTAPE 3 : Email de confirmation
- [x] ÉTAPE 4 : Authentification JWT (login, logout, password reset)
- [x] ÉTAPE 5 : Tests API (14 tests Postman)

**Livrables :**
- ✅ 5 endpoints d'authentification
- ✅ Documentation complète (290 lignes)
- ✅ Guide de tests (380 lignes, 14 tests)
- ✅ Récapitulatif SPRINT1_RECAP.md

---

### ⏳ SPRINT 2 — Frontend Web (Authentification)
**Durée estimée :** 1-2 semaines  
**Objectif :** Interface Web pour inscription et connexion

**Technologies :**
- React/Vue/Angular
- Axios ou Fetch API
- React Router / Vue Router
- localStorage pour tokens

**Tâches prévues :**
- [ ] Page d'inscription (formulaire avec type_compte)
- [ ] Page de login (email + password)
- [ ] Gestion des tokens (localStorage)
- [ ] Routes protégées (vérification token)
- [ ] Page profil utilisateur (GET/PUT /api/profile/me/)
- [ ] Password reset UI
- [ ] Interceptor Axios (auto refresh token)

**Endpoints à consommer :**
- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `POST /api/auth/password-reset/`
- `POST /api/auth/password-reset-confirm/`
- `GET /api/profile/me/`
- `PUT /api/profile/me/`

---

### ⏳ SPRINT 3 — Opportunités & Candidatures
**Durée estimée :** 2-3 semaines  
**Objectif :** CRUD opportunités + système de candidatures

**Backend (déjà partiellement en place) :**
- [ ] CRUD complet opportunités (ORGANISATION seulement)
- [ ] Filtres avancés (type, date, statut)
- [ ] Système de candidatures (CANDIDAT)
- [ ] Upload documents (CV, lettre motivation)
- [ ] Matching AI (scoring candidat/opportunité)

**Frontend Web :**
- [ ] Liste des opportunités (avec filtres)
- [ ] Détail d'une opportunité
- [ ] Créer/modifier opportunité (ORGANISATION)
- [ ] Postuler à une opportunité (CANDIDAT)
- [ ] Mes candidatures (historique)

---

### ⏳ SPRINT 4 — Application Mobile (Flutter/React Native)
**Durée estimée :** 3-4 semaines  
**Objectif :** App mobile avec mêmes fonctionnalités que Web

**Technologies :**
- Flutter (Dart) ou React Native (JavaScript)
- http/dio pour appels API
- SharedPreferences/AsyncStorage pour tokens
- Navigation (MaterialApp/NavigationContainer)

**Tâches prévues :**
- [ ] Écran d'inscription (CANDIDAT/ORGANISATION)
- [ ] Écran de login
- [ ] Navigation (BottomNavigationBar/TabBar)
- [ ] Écran profil
- [ ] Liste opportunités
- [ ] Détail opportunité
- [ ] Postuler (CANDIDAT)
- [ ] Créer opportunité (ORGANISATION)
- [ ] Mes candidatures

**Endpoints à consommer :** Les mêmes que Web ✅ (API unique)

---

### ⏳ SPRINT 5 — Notifications & Tests
**Durée estimée :** 1-2 semaines  
**Objectif :** Notifications + tests complets + déploiement

**Tâches prévues :**
- [ ] Notifications email avancées
- [ ] Notifications push (Firebase/OneSignal)
- [ ] Tests unitaires backend (pytest, coverage 80%+)
- [ ] Tests e2e Web (Cypress/Selenium)
- [ ] Tests e2e Mobile (integration_test/Detox)
- [ ] CI/CD (GitHub Actions)
- [ ] Déploiement (Heroku/AWS/DigitalOcean)

---

## 🌐 Endpoints API Disponibles

### Authentification (tous complétés ✅)

| Endpoint | Méthode | Auth | Description | Status |
|----------|---------|------|-------------|--------|
| `/api/auth/register/` | POST | ❌ | Inscription (CANDIDAT/ORGANISATION) | ✅ |
| `/api/auth/login/` | POST | ❌ | Connexion JWT | ✅ |
| `/api/auth/refresh/` | POST | ❌ | Renouveler access token | ✅ |
| `/api/auth/password-reset/` | POST | ❌ | Demander reset password | ✅ |
| `/api/auth/password-reset-confirm/` | POST | ❌ | Confirmer reset password | ✅ |

### Profil (complété ✅)

| Endpoint | Méthode | Auth | Description | Status |
|----------|---------|------|-------------|--------|
| `/api/profile/me/` | GET | ✅ | Consulter son profil | ✅ |
| `/api/profile/me/` | PUT | ✅ | Modifier son profil | ✅ |

### Opportunités (partiellement en place)

| Endpoint | Méthode | Auth | Description | Status |
|----------|---------|------|-------------|--------|
| `/api/opportunites/` | GET | ✅ | Liste opportunités | ✅ |
| `/api/opportunites/` | POST | ✅ | Créer opportunité (ORG) | ✅ |
| `/api/opportunites/{id}/` | GET | ✅ | Détail opportunité | ✅ |
| `/api/opportunites/{id}/` | PUT | ✅ | Modifier (ORG propriétaire) | ✅ |
| `/api/opportunites/{id}/` | DELETE | ✅ | Supprimer (ORG propriétaire) | ✅ |

### Candidatures (partiellement en place)

| Endpoint | Méthode | Auth | Description | Status |
|----------|---------|------|-------------|--------|
| `/api/candidatures/` | GET | ✅ | Mes candidatures | ✅ |
| `/api/candidatures/` | POST | ✅ | Postuler (CANDIDAT) | ✅ |
| `/api/candidatures/{id}/` | GET | ✅ | Détail candidature | ✅ |
| `/api/candidatures/{id}/` | PUT | ✅ | Modifier statut | ✅ |

---

## 📊 Statistiques du Projet

### Code Backend
- **Lignes de code Python :** ~800 lignes
- **Fichiers créés :** 15+ fichiers
- **Migrations :** 4 migrations appliquées
- **Endpoints API :** 12 endpoints fonctionnels
- **Tests documentés :** 14 tests Postman

### Documentation
- **AUTHENTICATION.md :** 290 lignes
- **TESTS_POSTMAN.md :** 380 lignes
- **SPRINT1_RECAP.md :** 220 lignes
- **Total documentation :** ~900 lignes

### Technologies Backend
- Django 5.0.6
- Django REST Framework 3.15.1
- djangorestframework-simplejwt 5.3.1
- PostgreSQL 16
- Docker + docker-compose
- Python 3.12

---

## 🎯 Objectif Final (PFE)

### Plateforme Complète "BidWise"

**Description :**  
Plateforme intelligente de gestion des opportunités permettant :
- Aux **candidats** : rechercher et postuler à des opportunités
- Aux **organisations** : publier et gérer des opportunités
- Matching AI entre profils et opportunités

**Architecture :**
- **Backend REST API** (Django + DRF)
- **Frontend Web** (React/Vue)
- **Application Mobile** (Flutter/React Native)
- **Base de données** (PostgreSQL)
- **Conteneurisation** (Docker)

**Avancement global actuel :**
- Backend API : 60% (authentification complète, CRUD opportunités/candidatures à finaliser)
- Frontend Web : 0% (Sprint 2)
- Mobile : 0% (Sprint 4)
- Tests : 30% (tests API uniquement)
- Documentation : 80% (backend bien documenté)

---

## 🚀 Pour continuer le développement

### Démarrer le backend (Docker)

```bash
# Démarrer les conteneurs
docker-compose up -d

# Vérifier les logs
docker-compose logs -f backend

# Accéder à l'API
http://localhost:8000/api/

# Admin Django
http://localhost:8000/admin/
```

### Tests Postman

1. Ouvrir Postman
2. Créer un environnement "BidWise Local"
3. Variables : `base_url = http://localhost:8000`
4. Suivre [TESTS_POSTMAN.md](./backend/TESTS_POSTMAN.md)

### Prochaine étape recommandée

**SPRINT 2 — Frontend Web :**
1. Créer un projet React/Vue
2. Installer axios
3. Implémenter page inscription
4. Implémenter page login
5. Gérer les tokens JWT
6. Tester avec l'API backend

---

## 📚 Ressources

- [Documentation Django](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [JWT.io](https://jwt.io/) — Décoder les tokens
- [Postman](https://www.postman.com/) — Tests API
- [Docker Docs](https://docs.docker.com/)
