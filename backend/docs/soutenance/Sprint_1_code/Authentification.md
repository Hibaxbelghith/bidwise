# Sprint 1 - Authentification Web et Mobile par email OTP

## Objectif

Le module d'authentification de BidWise a ete concu pour offrir une entree rapide, securisee et fluide a la plateforme. Au lieu d'un formulaire d'inscription classique avec mot de passe, l'utilisateur peut se connecter par email via un code OTP a usage unique. Cette approche est inspiree des parcours modernes utilises par des plateformes comme Indeed : l'utilisateur saisit son email, recoit un code, puis accede a son espace sans creer ni memoriser de mot de passe.

L'objectif technique est double :
- simplifier l'experience utilisateur au premier acces ;
- conserver un niveau de securite solide grace aux OTP, JWT, Turnstile, throttling, blacklist et traitements asynchrones.

## Defense du choix passwordless

Le choix `passwordless` ne signifie pas une authentification faible. Il signifie que la preuve d'identite ne repose pas sur un mot de passe memorise par l'utilisateur, mais sur un code OTP temporaire envoye a une adresse email que l'utilisateur controle.

Ce choix a ete retenu pour plusieurs raisons :
- reduire la friction d'entree sur web et mobile ;
- eviter les problemes classiques des mots de passe : oubli, reutilisation, faiblesse, reset ;
- permettre une creation de compte automatique des la premiere authentification reussie ;
- accelerer l'acces a la plateforme, ce qui est important pour BidWise ou l'utilisateur veut consulter rapidement des opportunites ;
- garder un parcours coherent entre application web et application mobile.

Ce choix reste defendable sur le plan securite car il est complete par plusieurs garde-fous :
- OTP a usage unique ;
- duree de vie courte ;
- hash du code en base ;
- nombre de tentatives limite ;
- cooldown entre deux demandes ;
- throttling anti-abus ;
- Turnstile sur le web avant l'envoi du code ;
- JWT avec refresh token rotatif et blacklist au logout.

L'idee importante a expliquer au jury est la suivante :
la securite ne disparait pas, elle se deplace du mot de passe vers la possession de la boite mail et vers la robustesse du flux OTP.

Dans le contexte BidWise, ce compromis est pertinent :
- la plateforme n'est pas un systeme bancaire ;
- l'objectif principal est de proposer un acces rapide, moderne et fluide ;
- les protections ajoutees rendent le mecanisme suffisamment solide pour une plateforme de gestion d'opportunites.

Limite assumee :
si la boite mail de l'utilisateur est compromise, l'acces BidWise peut l'etre aussi. Ce risque existe, mais il est acceptable ici et compense par la simplicite UX et les mecanismes anti-abus mis en place.

## Pourquoi JWT avec passwordless

L'OTP sert uniquement a prouver l'identite au moment de la connexion. Une fois l'utilisateur verifie, BidWise delivre des JWT pour gerer la session applicative.

Cette combinaison est adaptee a une architecture multi-clients :
- OTP pour l'authentification initiale ;
- JWT pour les appels API REST web et mobile ;
- refresh token pour maintenir une session fluide ;
- rotation et blacklist pour mieux controler la revocation.

Autrement dit :
`OTP` repond a la question "qui entre ?"
`JWT` repond a la question "comment garder la session active de facon stateless et compatible web/mobile ?"

## Flux fonctionnel web

1. L'utilisateur ouvre la page de connexion web.
2. Il saisit son adresse email.
3. Au clic sur `Send Code`, le frontend affiche une modal `Humans only`.
4. La modal execute Cloudflare Turnstile pour verifier que la demande provient d'un utilisateur reel.
5. Si Turnstile reussit, le frontend appelle `POST /api/auth/passwordless/request/` avec l'email, `client_type="web"` et `turnstile_token`.
6. Le backend valide l'email, verifie Turnstile cote serveur, applique les protections anti-abus, puis cree un challenge OTP.
7. L'OTP est stocke sous forme hashee en base et l'email est envoye via Celery.
8. L'utilisateur saisit le code recu.
9. Le frontend appelle `POST /api/auth/passwordless/verify/`.
10. Le backend verifie le code, cree le compte automatiquement si necessaire, puis delivre les tokens JWT.
11. Le frontend charge `/api/profile/me/` pour recuperer le profil complet.
12. Selon l'etat du profil, l'utilisateur est redirige vers l'onboarding ou vers l'espace principal.

## Fichiers principaux

Backend :
- `backend/config/urls.py` : expose les routes d'authentification.
- `backend/users/views.py` : contient `request_otp`, `verify_otp` et `logout_view`.
- `backend/users/models.py` : contient `Utilisateur` et `OTPChallenge`.
- `backend/users/serializers.py` : valide les payloads OTP.
- `backend/users/otp_service.py` : construit et envoie le contenu email OTP.
- `backend/users/tasks.py` : contient la tache Celery d'envoi OTP.
- `backend/opportunities/turnstile.py` : service reutilise pour verifier les tokens Turnstile.
- `backend/config/settings.py` : configure SimpleJWT, throttling, Turnstile et Celery.

Frontend web :
- `frontend/src/features/auth/LoginPage.jsx` : interface login, modal Turnstile et saisie OTP.
- `frontend/src/features/auth/AuthContext.jsx` : etat global d'authentification.
- `frontend/src/features/auth/authService.js` : appels API OTP, Google, refresh et logout.
- `frontend/src/lib/api.js` : intercepteurs Axios, ajout Bearer token et refresh silencieux.
- `frontend/src/lib/tokenManager.js` : stockage des tokens cote web.
- `frontend/src/features/organization/components/TurnstileChallenge.jsx` : composant Turnstile reutilise.

Mobile, pour comparaison :
- `bidwise-mobile/src/features/auth/components/LoginScreen.tsx` : saisie email, demande OTP et Google Sign-In.
- `bidwise-mobile/src/features/auth/components/OtpScreen.tsx` : saisie et verification du code OTP.
- `bidwise-mobile/src/features/auth/services/authService.ts` : appels API auth mobile.
- `bidwise-mobile/src/features/auth/context/AuthContext.tsx` : etat global, login, logout et chargement profil.
- `bidwise-mobile/src/shared/services/api.ts` : client Axios mobile, Bearer token et refresh silencieux.
- `bidwise-mobile/src/shared/services/tokenStorage.ts` : stockage securise des tokens avec Expo SecureStore.
- `bidwise-mobile/src/features/auth/hooks/useGoogleAuth.ts` : integration Google Sign-In native.
- `bidwise-mobile/src/shared/components/AppLaunchSplash.tsx` : animation de demarrage de l'application.

## Endpoints d'authentification

`POST /api/auth/passwordless/request/`

Demande l'envoi d'un OTP. Pour le web, le backend exige un `turnstile_token` si `TURNSTILE_SECRET_KEY` est configure.

Exemple payload web :

```json
{
  "email": "user@example.com",
  "client_type": "web",
  "turnstile_token": "token-navigateur"
}
```

`POST /api/auth/passwordless/verify/`

Verifie le code OTP et retourne les JWT.

```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

Reponse :

```json
{
  "access": "...",
  "refresh": "...",
  "is_new_user": true
}
```

`POST /api/auth/refresh/`

Renouvelle l'access token a partir du refresh token.

`POST /api/auth/logout/`

Blackliste le refresh token et termine la session.

`GET /api/profile/me/`

Recupere le profil complet apres authentification.

## Creation automatique du compte

Le compte n'est pas cree au moment de la demande OTP. Il est cree uniquement apres verification reussie du code OTP.

Dans `verify_otp`, le backend utilise `Utilisateur.objects.get_or_create(email=email, ...)`. Si l'utilisateur n'existe pas encore :
- un compte est cree automatiquement ;
- un mot de passe inutilisable est defini ;
- le profil candidat est cree via le signal Django `post_save`.

Ce choix evite un formulaire d'inscription long et reduit la friction d'entree.

## Onboarding candidat apres authentification

L'onboarding est la deuxieme phase du parcours d'authentification. Apres la verification OTP ou Google, BidWise ne demande pas a l'utilisateur de remplir un long formulaire classique. La plateforme cree d'abord le compte, puis guide le candidat a travers quelques etapes courtes pour construire un profil exploitable par la recommandation.

Objectif fonctionnel :
- comprendre ce que l'utilisateur cherche ;
- collecter les preferences principales du candidat ;
- alimenter le profil utilise ensuite par le moteur de recommandation ;
- laisser la possibilite de reporter l'onboarding et de completer le profil plus tard.

Ce choix est important a defendre : l'onboarding n'est pas seulement une interface d'inscription. C'est le point d'entree de la personnalisation BidWise.

## Flux onboarding web

1. Apres login, le frontend appelle `GET /api/profile/me/`.
2. Si `profil.onboarding_completed=false`, l'utilisateur est dirige vers `/onboarding`.
3. L'onboarding charge les donnees deja connues depuis le profil backend, `localStorage` et `sessionStorage`.
4. L'utilisateur avance etape par etape avec une validation locale.
5. Au clic sur `Finish`, le frontend envoie un profil complet avec `onboarding_completed=true`.
6. Le backend valide et normalise les champs dans `ProfilUpdateSerializer`.
7. Le profil est sauvegarde et l'utilisateur est redirige vers les opportunites.
8. Au clic sur `Skip`, le frontend envoie seulement les champs deja renseignes, avec `onboarding_completed=false`.
9. Le skip redirige vers `/opportunities?tab=explore`, et l'utilisateur peut completer son profil plus tard depuis la page profil.

Ce comportement est volontaire : `Finish` exige les informations minimales, alors que `Skip` sauvegarde uniquement une progression partielle.

## Etapes de l'onboarding candidat

L'onboarding candidat est compose de 8 etapes :

1. Type d'opportunite recherchee : emploi, stage, appel d'offre.
2. Mode de travail et localisation : remote, hybrid, on-site, avec localisation obligatoire pour hybrid/on-site.
3. Competences principales : utilisees pour la similarite profil-opportunite.
4. Domaines d'interet : secteurs professionnels controles.
5. Pretentions salariales : optionnelles, avec controle de coherence.
6. Types de contrat : CDI, CDD, SIVP, Freelance, et Internship seulement si l'utilisateur a choisi Internship comme type d'opportunite.
7. Roles cibles : postes recherches par le candidat.
8. Visibilite du profil : permet d'activer ou desactiver la visibilite du profil.

Les champs vraiment structurants pour la recommandation sont : `opportunity_types`, `competences`, `domaines_interet`, `preferred_locations`, `work_mode_preferences`, `employment_types` et `target_roles`.

## Fichiers onboarding web

Frontend web :
- `frontend/src/features/onboarding/OnboardingPage.jsx` : page principale, navigation entre les etapes, validation, finish et skip.
- `frontend/src/features/onboarding/steps/StepOpportunityIntent.jsx` : choix du type d'opportunite.
- `frontend/src/features/onboarding/steps/StepLocation.jsx` : localisation et mode de travail.
- `frontend/src/features/onboarding/steps/StepSkills.jsx` : competences.
- `frontend/src/features/onboarding/steps/StepSectors.jsx` : secteurs/domaines d'interet.
- `frontend/src/features/onboarding/steps/StepSalary.jsx` : salaire min/max.
- `frontend/src/features/onboarding/steps/StepEmploymentType.jsx` : types de contrat.
- `frontend/src/features/onboarding/steps/StepTargetRoles.jsx` : roles cibles.
- `frontend/src/features/onboarding/steps/StepVisibility.jsx` : visibilite du profil.
- `frontend/src/features/profile/profilePreferences.js` : options canoniques, normalisation et alignement des valeurs profil/onboarding.
- `frontend/src/features/profile/profileValidation.js` : validation salaire, detection d'entrees faibles, normalisation des termes.
- `frontend/src/features/profile/components/ProfileAutocompleteInput.jsx` : composant d'autocompletion pour competences, secteurs et roles.

Backend :
- `backend/users/models.py` : modele `Profil` et champs onboarding.
- `backend/users/serializers.py` : `ProfilUpdateSerializer`, normalisation et validation des valeurs envoyees.
- `backend/users/views.py` : endpoints profil et endpoints de suggestions.
- `backend/users/urls.py` : routes `skills/suggest/`, `roles/suggest/`, `interests/suggest/`.
- `backend/opportunities/autocomplete/service.py` : logique de recherche des suggestions.
- `backend/opportunities/extraction/profile_terms.py` : dictionnaires, alias et garde-fous metier pour les termes profil.

## Fonctionnement des suggestions

Les suggestions ne sont pas seulement des listes statiques cote frontend. Le frontend interroge le backend via :

- `GET /api/profile/skills/suggest/?q=...`
- `GET /api/profile/roles/suggest/?q=...`
- `GET /api/profile/interests/suggest/?q=...`

Le backend utilise `suggest_profile_terms()` dans `opportunities/autocomplete/service.py`.

La recherche combine :
- des termes extraits et consolides en base dans `ProfileSuggestion` ;
- des alias metier pour reconnaitre plusieurs ecritures d'un meme terme ;
- un score base sur exact match, prefix match, contains, fuzzy match, frequence et confiance ;
- un cache pour eviter de recalculer les memes suggestions a chaque frappe ;
- un throttle `ProfileSuggestionThrottle` pour limiter les abus.

Pour les secteurs, BidWise ajoute aussi un dictionnaire metier afin d'eviter qu'un utilisateur saisisse une competence comme secteur. Exemple : `React` doit etre compris comme competence, pas comme domaine d'interet.

Le frontend applique ensuite une validation UX :
- suppression des doublons ;
- limite du nombre d'elements ;
- refus des termes trop vagues ;
- messages explicites si une competence est saisie dans le champ role ou secteur.

## Controle de saisie

La validation est faite a deux niveaux.

Cote frontend :
- chaque etape a un controle local avant de passer a la suivante ;
- les messages d'erreur apparaissent directement dans l'interface ;
- le salaire min/max est controle avant l'envoi ;
- les types de contrat visibles dependent du type d'opportunite choisi ;
- le bouton `Skip` ne force pas la validation complete.

Cote backend :
- `ProfilUpdateSerializer` reste l'autorite finale ;
- les listes sont nettoyees, dedupliquees et limitees ;
- les secteurs sont normalises vers des familles controlees ;
- les localisations sont comparees a une liste de localisations tunisiennes ;
- les salaires incoherents sont refuses ;
- les valeurs non supportees pour contrats, modes de travail ou types d'opportunite sont rejetees.

Cette double validation est defendable : le frontend ameliore l'experience utilisateur, mais le backend protege la coherence des donnees.

## Skip et completion du profil

Le skip est autorise parce que BidWise veut reduire la friction au premier acces. Un utilisateur peut explorer les opportunites rapidement, puis completer son profil plus tard.

Techniquement :
- `Finish` envoie un payload complet et passe `onboarding_completed=true`.
- `Skip` envoie un payload partiel et passe `onboarding_completed=false`.
- Les listes vides ne sont pas envoyees pendant le skip, afin de ne pas declencher les validations obligatoires du backend.
- `last_onboarding_step` permet de savoir ou l'utilisateur s'est arrete.

Point a expliquer au jury : le score de completion peut rester faible apres onboarding. C'est normal, car le profil complet inclut aussi des informations plus avancees comme CV, experience, informations personnelles et enrichissement du profil.

## Onboarding mobile

Le mobile reprend la meme logique metier que le web, avec une interface React Native.

Fichiers principaux :
- `bidwise-mobile/src/features/profile/components/OnboardingScreen.tsx` : orchestration de l'onboarding mobile.
- `bidwise-mobile/src/features/profile/onboarding/onboardingConfig.ts` : definition des etapes et donnees initiales.
- `bidwise-mobile/src/features/profile/onboarding/onboardingValidation.ts` : validations par etape.
- `bidwise-mobile/src/features/profile/components/onboarding/OnboardingStepContent.tsx` : rendu des etapes.
- `bidwise-mobile/src/features/profile/components/ProfileAutocompleteInput.tsx` : suggestions mobile.
- `bidwise-mobile/src/features/profile/hooks/useProfileAutocomplete.ts` : appel aux endpoints de suggestions.
- `bidwise-mobile/src/features/profile/constants/profileOptions.ts` : options canoniques partagees cote mobile.
- `bidwise-mobile/src/features/profile/services/profileService.ts` : appels API profil.

La version mobile est volontairement moins detaillee visuellement que le web, mais elle respecte les memes regles : validation par etape, suggestions backend, normalisation des preferences et sauvegarde du profil.

## Questions possibles du jury sur l'onboarding

### Pourquoi onboarding apres authentification et pas avant ?

Parce que l'email doit d'abord etre verifie. Une fois l'utilisateur authentifie, les preferences peuvent etre associees a un vrai profil candidat et sauvegardees de maniere fiable.

### Pourquoi autoriser Skip ?

Pour ne pas bloquer l'acces a la plateforme. BidWise permet d'explorer les opportunites immediatement, tout en incitant l'utilisateur a completer son profil pour ameliorer ses recommandations.

### Les suggestions viennent-elles d'une liste statique ?

Non. Elles viennent principalement du backend, via les endpoints de suggestions. Le systeme s'appuie sur la table `ProfileSuggestion`, des alias metier, un ranking et un cache. Certaines listes de controle existent aussi pour securiser la saisie, par exemple les localisations et les familles de secteurs.

### Pourquoi controler les secteurs plus fortement que les competences ?

Les competences peuvent etre tres variees et evolutives. Les secteurs doivent rester plus structures, car ils servent a categoriser le profil et a eviter des donnees incoherentes comme mettre `React` ou `Python` dans les domaines d'interet.

### Pourquoi Internship depend du type d'opportunite ?

Pour garder une coherence metier. Si l'utilisateur cherche seulement des emplois, les contrats proposes restent CDI, CDD, SIVP et Freelance. Si l'utilisateur choisit Internship, le type Internship devient disponible.

### Pourquoi le score de profil n'est pas 100% apres onboarding ?

Parce que l'onboarding collecte les preferences de base. Le profil complet inclut aussi d'autres dimensions comme le CV, les informations personnelles, l'experience et les donnees enrichies. Le score pousse donc l'utilisateur a completer son profil progressivement.

## Securite OTP

La classe `OTPChallenge` applique plusieurs protections :
- OTP a 6 chiffres ;
- stockage hash en base, jamais en clair ;
- expiration apres 5 minutes ;
- maximum 5 tentatives par challenge ;
- usage unique via `is_used` ;
- suppression des anciens challenges pour le meme email ;
- cooldown de 60 secondes entre deux demandes ;
- throttling DRF par IP sur la demande OTP ;
- throttling DRF par IP et par email sur la verification OTP.

Ces protections limitent le bruteforce, le spam et l'enumeration de comptes.

## Turnstile

Turnstile est place avant la creation de l'OTP, pas apres la saisie du code.

Raison :
- l'etape couteuse est l'envoi email ;
- un bot pourrait automatiser `/auth/passwordless/request/` pour spammer des adresses ;
- la verification OTP est deja protegee par expiration, tentatives et throttling.

Le frontend affiche Turnstile dans une modal sur la meme page de login. Cela evite de rediriger l'utilisateur vers une page separee et explique le temps d'attente.

Si `TURNSTILE_SECRET_KEY` n'est pas configure cote backend, la verification est desactivee. Si `VITE_TURNSTILE_SITE_KEY` n'est pas configure cote frontend, la modal n'est pas affichee.

Le mobile ne force pas Turnstile actuellement. Ce choix est volontaire : Turnstile est naturellement adapte au navigateur web, alors que React Native demanderait une integration WebView ou native plus fragile. Le mobile reste protege par les limites backend communes.

## Flux fonctionnel mobile

Le mobile reprend le meme principe fonctionnel que le web, mais avec une experience adaptee a React Native :

1. Au lancement, l'application affiche une animation de demarrage avec le logo BidWise.
2. `AuthContext` verifie si des tokens existent dans `SecureStore`.
3. Si un access token existe, l'application appelle `GET /api/profile/me/`.
4. Si l'access token est expire, l'intercepteur mobile tente automatiquement `/api/auth/refresh/`.
5. Si la session est valide, l'utilisateur est dirige vers `/explore` ou `/onboarding` selon son profil.
6. Si aucune session valide n'existe, l'utilisateur reste en mode invite et peut ouvrir l'ecran de login.
7. Dans `LoginScreen.tsx`, l'utilisateur saisit son email.
8. Le mobile appelle `POST /api/auth/passwordless/request/` avec `client_type="mobile"`.
9. Le backend cree un OTP avec les memes regles de securite que le web.
10. L'utilisateur saisit le code dans `OtpScreen.tsx`.
11. Le mobile appelle `POST /api/auth/passwordless/verify/`.
12. Les tokens JWT sont stockes dans `SecureStore`, puis le profil est charge.

Payload mobile de demande OTP :

```json
{
  "email": "user@example.com",
  "client_type": "mobile"
}
```

Le parametre `client_type="mobile"` est important : il permet au backend d'appliquer un comportement adapte au mobile, notamment sans exiger Turnstile.

## Stockage des tokens mobile

Cote mobile, les tokens ne sont pas stockes dans `AsyncStorage`. Ils sont stockes dans Expo SecureStore :

- `bidwise_access_token` : access token JWT ;
- `bidwise_refresh_token` : refresh token JWT.

SecureStore s'appuie sur le stockage securise natif de la plateforme mobile. C'est plus approprie qu'un stockage texte simple pour des credentials.

Au logout, `AuthContext.logout()` :
1. recupere le refresh token ;
2. appelle `/api/auth/logout/` pour le blacklister cote backend ;
3. supprime les tokens de `SecureStore` ;
4. remet l'utilisateur local a `null`.

Meme si l'appel serveur echoue, les tokens sont supprimes localement. C'est un choix UX/securite correct : l'utilisateur est bien deconnecte de l'appareil.

## Refresh silencieux mobile

Le refresh mobile est gere dans `bidwise-mobile/src/shared/services/api.ts`.

Le fonctionnement est similaire au web :
- chaque requete ajoute automatiquement `Authorization: Bearer <access>`;
- si une reponse `401` arrive, l'intercepteur lit le refresh token depuis `SecureStore`;
- il appelle `/api/auth/refresh/`;
- il sauvegarde le nouvel access token ;
- il relance la requete initiale.

Le fichier gere aussi une file d'attente (`pendingQueue`) pour eviter plusieurs refresh paralleles lorsque plusieurs requetes echouent au meme moment.

Si le refresh echoue, les tokens sont supprimes localement. L'utilisateur devra se reconnecter.

## Google Sign-In mobile

Le mobile utilise `@react-native-google-signin/google-signin`.

Le hook `useGoogleAuth.ts` :
- configure le `webClientId` ;
- verifie la disponibilite des Google Play Services ;
- lance le selecteur de compte Google ;
- recupere un `idToken` ;
- transmet ce token au backend via `POST /api/auth/google/`.

Le backend reste responsable de la securite :
- verification du token Google ;
- verification de l'audience ;
- refus des emails non verifies ;
- refus des comptes inactifs ou suspendus ;
- generation des JWT.

Le mobile ne stocke pas le token Google. Il stocke uniquement les JWT BidWise apres validation serveur.

## JWT et session

BidWise utilise SimpleJWT.

Configuration actuelle :
- access token : 30 minutes ;
- refresh token : 14 jours ;
- rotation des refresh tokens activee ;
- blacklist apres rotation et logout.

Le backend delivre les tokens apres :
- verification OTP reussie ;
- verification Google OAuth reussie ;
- login administrateur reussi.

Les comptes suspendus ne peuvent plus obtenir de nouveaux tokens via OTP, Google ou admin login.

## Stockage des tokens web

Cote web :
- access token conserve en memoire uniquement ;
- refresh token conserve dans `sessionStorage` ;
- anciens tokens en `localStorage` nettoyes/migres ;
- suppression des tokens au logout ou en cas d'echec refresh.

Ce choix limite la persistance de l'access token et reste compatible avec une SPA React.

Limite assumee :
- un cookie HttpOnly Secure SameSite serait un durcissement production pertinent pour le web ;
- le choix actuel est un compromis pragmatique entre React web, React Native et delai projet.

## Refresh silencieux

Le refresh est gere dans `frontend/src/lib/api.js`.

Scenario :
1. Une requete protegee part avec un access token expire ou absent.
2. L'intercepteur Axios detecte le probleme.
3. Si un refresh token existe, il appelle `/auth/refresh/`.
4. Le nouveau token est sauvegarde.
5. La requete initiale est relancee automatiquement.
6. Si plusieurs requetes echouent en meme temps, elles sont mises en file d'attente pour eviter plusieurs refresh paralleles.
7. Si le refresh echoue, les tokens sont supprimes et l'utilisateur est redirige vers `/login`.

Ce mecanisme rend l'expiration de l'access token transparente pour l'utilisateur.

## Deconnexion

Au logout :
1. Le frontend envoie le refresh token a `/api/auth/logout/`.
2. Le backend le blackliste via SimpleJWT.
3. Le frontend supprime les tokens locaux.

Apres logout, le refresh token ne peut plus etre reutilise pour obtenir un nouvel access token.

## Celery et performance

Les emails d'authentification sont traites en arriere-plan :
- `users.send_otp_email` envoie le code OTP.

Ces taches sont routees vers la file Celery `notifications`, deja utilisee par les notifications applicatives.

Valeur ajoutee :
- l'endpoint OTP repond plus rapidement ;
- l'envoi SMTP ne bloque pas la requete HTTP ;
- la logique reste robuste grace a un fallback synchrone si l'enqueue OTP echoue immediatement.

Attention en demo :
- si `AUTH_OTP_EMAIL_ASYNC=true`, le worker `celery_notifications` doit etre lance ;
- sinon, mettre `AUTH_OTP_EMAIL_ASYNC=false` pour envoyer l'OTP directement pendant les tests manuels.

## Google OAuth

Le login Google utilise `POST /api/auth/google/`.

Le backend :
- verifie le `id_token` avec Google ;
- controle l'audience (`GOOGLE_CLIENT_ID`) ;
- exige un email Google verifie ;
- cree le compte si necessaire ;
- refuse les comptes inactifs ou suspendus ;
- retourne les JWT.

Aucun token Google n'est stocke.

## Admin login

L'espace administrateur dispose d'un login dedie via `/api/admin/login/`.

Il utilise email + mot de passe administrateur, puis delivre des JWT. Le backend verifie :
- credentials valides ;
- utilisateur actif ;
- role administrateur ;
- compte non suspendu.

Il faut donc distinguer :
- authentification utilisateur : passwordless OTP / Google ;
- authentification administrateur : login dedie admin.

## Tests a mentionner en soutenance

Les tests d'authentification sont principalement dans `backend/users/tests.py`.

Classes importantes :
- `RequestOTPViewTests` : demande OTP, Turnstile, cooldown, email async, mobile.
- `VerifyOTPViewTests` : verification OTP, auto-creation compte, expiration, tentative max, single-use.
- `GoogleAuthViewTests` : Google OAuth, token invalide, audience, email non verifie, compte suspendu.
- `TokenRefreshViewTests` : refresh token valide/invalide.
- `LogoutViewTests` : blacklist du refresh token.
- `AdminLoginEndpointTests` : login admin, refus non-admin, refus compte suspendu.

Commande de validation ciblee :

```bash
docker compose run --rm backend python manage.py test users.tests.RequestOTPViewTests users.tests.VerifyOTPViewTests users.tests.GoogleAuthViewTests users.tests.TokenRefreshViewTests users.tests.LogoutViewTests users.tests.AdminLoginEndpointTests --keepdb
```

Resultat obtenu apres les ameliorations :

Les tests ciblés passent avec succès.

Verification generale Django :

```bash
docker compose run --rm backend python manage.py check
```

Resultat :

```text
System check identified no issues
```

## Questions possibles du jury

### Pourquoi passwordless au lieu d'un formulaire d'inscription ?

Pour reduire la friction utilisateur. L'utilisateur n'a pas besoin de creer un mot de passe au premier acces. Le compte est cree automatiquement apres preuve de possession de l'email. Cela accelere l'onboarding et correspond aux parcours modernes de plateformes d'emploi.

### Pourquoi JWT ?

BidWise est une plateforme multi-client : React web et React Native mobile consomment les memes API REST. JWT permet une authentification stateless, compatible web/mobile, avec refresh token rotatif et blacklist.

### Pourquoi pas cookie HttpOnly ?

C'est une amelioration production pertinente pour le web. Dans ce projet, nous avons choisi un modele commun web/mobile base sur Bearer token. Pour reduire le risque cote web, l'access token est garde en memoire et le refresh token en `sessionStorage`. Une version production avancee pourrait utiliser un refresh token en cookie HttpOnly pour le web, tout en conservant SecureStore pour mobile.

### Que se passe-t-il si l'access token expire pendant la navigation ?

L'intercepteur Axios tente automatiquement un refresh silencieux. Si le refresh reussit, la requete initiale est relancee. Si le refresh echoue, les tokens sont supprimes et l'utilisateur est redirige vers la page de connexion.

### Pourquoi Turnstile seulement sur web ?

Turnstile s'integre naturellement dans le navigateur. Sur mobile, l'integration demande une WebView ou une approche native plus fragile. Le mobile reste protege par les controles backend : cooldown, expiration OTP, limite de tentatives et throttling.

### Pourquoi Celery pour les emails ?

L'envoi SMTP peut ralentir une requete HTTP. Le deplacer vers Celery ameliore la reactivite de l'authentification et isole cette operation lente dans une file dediee.

### Que se passe-t-il si Celery est arrete ?

En mode async, l'OTP peut etre enqueued mais l'email partira seulement quand le worker sera disponible. Pour les tests ou demos sans worker, le flag `AUTH_OTP_EMAIL_ASYNC=false` permet de revenir a un envoi synchrone. Si l'enqueue echoue immediatement, un fallback synchrone est prevu.

## Valeur ajoutee

Le module d'authentification apporte :
- une experience utilisateur rapide et moderne ;
- une inscription implicite sans formulaire long ;
- une securite OTP robuste ;
- une protection anti-bot via Turnstile ;
- une session fluide grace au refresh silencieux ;
- une meilleure performance grace a Celery ;
- une compatibilite web et mobile ;
- une gestion des comptes suspendus coherente sur OTP, Google et admin.
