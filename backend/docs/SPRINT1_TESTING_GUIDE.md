# BidWise — Sprint 1 Testing Guide

**Scope:** Authentication module  
**Platforms:** Backend API, Web app, Mobile app  
**Sprint:** Sprint 1

---

## 1. Test scope

This guide covers the final validation of Sprint 1 authentication features:
- OTP passwordless login
- Google authentication
- JWT session handling
- logout and refresh
- onboarding redirection
- organization route protection
- suspicious login detection
- token storage behavior
- OTP security limits

---

## 2. Prerequisites

### Backend

The backend must be running:

```bash
docker compose up -d backend
```

Recommended checks:

```bash
docker compose ps
docker compose logs backend --tail 100
```

Expected:
- `bidwise_backend` is `Up`
- `bidwise_db` is `healthy`
- no startup traceback in backend logs

### Web app

The web app must point to the backend API through `VITE_API_URL`.

### Mobile app

Before running mobile tests, verify the API base URL in:
- [api.ts](d:/Documents/BidWise/bidwise-mobile/src/shared/services/api.ts)

The mobile app uses `EXPO_PUBLIC_API_BASE_URL` when provided, otherwise it resolves the development host from Expo. For Android emulator testing, the fallback host is `10.0.2.2`.

---

## 3. Backend API tests (Postman)

### Environment variables

Create a Postman environment with:
- `base_url = http://localhost:8000/api`
- `access_token`
- `refresh_token`

### Test API-01 — Request OTP with valid email

**Request**
- `POST {{base_url}}/auth/passwordless/request/`

```json
{
  "email": "qa.test@example.com"
}
```

**Expected result**
- HTTP `200`
- generic success message
- OTP sent by email or visible through the configured mail backend

### Test API-02 — Request OTP with invalid email

**Request**
- `POST {{base_url}}/auth/passwordless/request/`

```json
{
  "email": "not-an-email"
}
```

**Expected result**
- HTTP `400`
- validation error on email format

### Test API-03 — OTP cooldown

**Steps**
1. Send a valid OTP request
2. Immediately send the same request again

**Expected result**
- second response stays generic
- no crash
- cooldown behavior prevents OTP spam

### Test API-04 — Verify OTP with correct code

**Request**
- `POST {{base_url}}/auth/passwordless/verify/`

```json
{
  "email": "qa.test@example.com",
  "otp": "123456"
}
```

**Expected result**
- HTTP `200`
- response contains `access`
- response contains `refresh`
- response contains `is_new_user`

**Postman action**
- save `access` into `access_token`
- save `refresh` into `refresh_token`

### Test API-05 — Verify OTP with wrong code

**Request**
- same endpoint with wrong `otp`

**Expected result**
- HTTP `400`
- generic invalid or expired code message
- no account enumeration leak

### Test API-06 — OTP attempts limit

**Steps**
1. Request a fresh OTP
2. Submit a wrong code 5 times
3. Submit again

**Expected result**
- challenge becomes locked
- backend returns an explicit too-many-attempts style message

### Test API-07 — Access protected profile

**Request**
- `GET {{base_url}}/profile/me/`
- Header: `Authorization: Bearer {{access_token}}`

**Expected result**
- HTTP `200`
- full authenticated profile payload returned

### Test API-08 — Protected route without token

**Request**
- `GET {{base_url}}/profile/me/`
- no auth header

**Expected result**
- HTTP `401`

### Test API-09 — Refresh token

**Request**
- `POST {{base_url}}/auth/refresh/`

```json
{
  "refresh": "{{refresh_token}}"
}
```

**Expected result**
- HTTP `200`
- response contains new `access`
- may also contain new `refresh` because rotation is enabled

### Test API-10 — Logout

**Request**
- `POST {{base_url}}/auth/logout/`
- Header: `Authorization: Bearer {{access_token}}`

```json
{
  "refresh": "{{refresh_token}}"
}
```

**Expected result**
- HTTP `200`
- refresh token is blacklisted server-side

### Test API-11 — Refresh after logout

**Request**
- reuse the same refresh token on `/auth/refresh/`

**Expected result**
- token rejected
- HTTP `400` or `401` depending on SimpleJWT response shape

### Test API-12 — Google auth invalid token

**Request**
- `POST {{base_url}}/auth/google/`

```json
{
  "id_token": "fake-token"
}
```

**Expected result**
- request rejected cleanly
- no server crash
- no internal stack trace leaked

---

## 4. Web app manual tests

Files involved:
- [AuthContext.jsx](d:/Documents/BidWise/frontend/src/features/auth/AuthContext.jsx)
- [authService.js](d:/Documents/BidWise/frontend/src/features/auth/authService.js)
- [api.js](d:/Documents/BidWise/frontend/src/lib/api.js)
- [tokenManager.js](d:/Documents/BidWise/frontend/src/lib/tokenManager.js)
- [App.jsx](d:/Documents/BidWise/frontend/src/App.jsx)
- [AppLayout.jsx](d:/Documents/BidWise/frontend/src/components/layout/AppLayout.jsx)
- [OrganizationRoute.jsx](d:/Documents/BidWise/frontend/src/features/organization/OrganizationRoute.jsx)

### Test WEB-01 — OTP login

**Steps**
1. Open `/login`
2. Enter a valid email
3. Request OTP
4. Enter the received code

**Expected result**
- login succeeds
- user is redirected to onboarding if profile is incomplete
- otherwise redirected to dashboard

### Test WEB-02 — Google login

**Steps**
1. Open `/login`
2. Click Google login
3. Complete Google authentication

**Expected result**
- login succeeds
- new user is created automatically if needed
- redirect logic matches onboarding completion state

### Test WEB-03 — Protected routes

**Steps**
1. Open `/dashboard` without an active session

**Expected result**
- user is redirected to `/login`

### Test WEB-04 — Session restore after browser refresh

**Steps**
1. Log in
2. Refresh the page

**Expected result**
- session is restored through the existing refresh mechanism
- protected pages remain accessible if refresh token is still valid
- navbar remains in a neutral bootstrap state until authentication is resolved
- route content is not redirected before auth bootstrap finishes

### Test WEB-05 — Access token storage behavior

**Steps**
1. Log in
2. Open browser DevTools
3. Inspect `localStorage` and `sessionStorage`

**Expected result**
- `bidwise_access_token` is **not** stored in `localStorage`
- access token is in memory only
- refresh token is stored in `sessionStorage`

### Test WEB-06 — Silent refresh on expired access token

**Steps**
1. Log in
2. Wait for access token expiry or simulate a 401 on a protected request
3. Trigger a protected API call

**Expected result**
- interceptor requests a new access token automatically
- original request is retried successfully
- user is not logged out if refresh token is valid

### Test WEB-07 — Logout

**Steps**
1. Log in
2. Click logout
3. Try to access a protected route again

**Expected result**
- local tokens removed
- refresh token blacklisted server-side
- user redirected out of protected area with a short, controlled visual delay
- dashboard no longer accessible

### Test WEB-08 — Organization route protection

**Steps**
1. Log in as a candidate account
2. Open `/organization/dashboard` directly
3. Complete organization profile creation, or log in as an existing organization account
4. Open `/organization/dashboard` again

**Expected result**
- candidate account is redirected to `/organization/create-account`
- organization account with a complete organization profile can access the dashboard
- no redirect loop occurs between organization setup and dashboard

### Test WEB-09 — Refresh failure

**Steps**
1. Log in
2. Invalidate the refresh token
3. Trigger a protected request

**Expected result**
- session is cleared
- user is redirected to `/login`

---

## 5. Mobile app tests

Files involved:
- [login.tsx](d:/Documents/BidWise/bidwise-mobile/app/login.tsx)
- [otp.tsx](d:/Documents/BidWise/bidwise-mobile/app/otp.tsx)
- [AuthContext.tsx](d:/Documents/BidWise/bidwise-mobile/src/features/auth/context/AuthContext.tsx)
- [authService.ts](d:/Documents/BidWise/bidwise-mobile/src/features/auth/services/authService.ts)
- [api.ts](d:/Documents/BidWise/bidwise-mobile/src/shared/services/api.ts)
- [tokenStorage.ts](d:/Documents/BidWise/bidwise-mobile/src/shared/services/tokenStorage.ts)
- [useGoogleAuth.ts](d:/Documents/BidWise/bidwise-mobile/src/features/auth/hooks/useGoogleAuth.ts)
- [DashboardScreen.tsx](d:/Documents/BidWise/bidwise-mobile/src/features/dashboard/components/DashboardScreen.tsx)

### Mobile run options

### Option A — OTP tests with Expo Go

```bash
cd bidwise-mobile
npm install
npm run start
```

Then:
- scan the QR code with Expo Go
- test OTP flow and navigation

### Option B — Google tests with Android dev build

```bash
cd bidwise-mobile
npx expo run:android
```

Use this if Android SDK and a device or emulator are ready.

### Option C — Google tests with APK

```bash
cd bidwise-mobile
npx eas build -p android --profile preview
```

Install the generated APK on a real Android device.

### Important note

**Google Sign-In is not available in Expo Go in this project.**
The app explicitly detects this and shows an error if the native Google module is unavailable.

Google mobile prerequisites:
- Android package name must match `com.bidwise.mobile`
- the corresponding Android app must be configured in Google Cloud / Firebase
- SHA fingerprints for the tested build may be required for native Google auth

### Test MOB-01 — OTP request

**Steps**
1. Open mobile login screen
2. Enter email
3. Tap `Send login code`

**Expected result**
- request succeeds
- app navigates to OTP screen

### Test MOB-02 — OTP verification

**Steps**
1. Enter the 6-digit code

**Expected result**
- successful login
- user redirected to onboarding or dashboard

### Test MOB-03 — Wrong OTP

**Steps**
1. Enter an invalid code

**Expected result**
- clear error message shown
- app does not crash
- code input is reset

### Test MOB-04 — Resend code

**Steps**
1. On OTP screen, tap resend

**Expected result**
- resend request succeeds
- loading state is visible
- no crash or navigation issue

### Test MOB-05 — Google login

**Precondition**
- run through dev build or APK, not Expo Go

**Steps**
1. Tap `Continue with Google`
2. Choose account
3. Complete Google auth

**Expected result**
- Google returns an `id_token`
- backend authentication succeeds
- user redirected correctly

### Test MOB-06 — Token persistence

**Steps**
1. Log in on mobile
2. Close the app fully
3. Reopen the app

**Expected result**
- session is restored if tokens are still valid
- profile loads correctly

### Test MOB-07 — Automatic refresh

**Steps**
1. Log in
2. Force access token expiry or wait for it
3. Trigger a protected request

**Expected result**
- mobile interceptor refreshes token automatically
- if backend returns a rotated refresh token, it is saved correctly
- a second refresh still works after the first rotation
- original request continues successfully

### Test MOB-08 — Logout

**Steps**
1. Log in
2. Trigger logout
3. Reopen protected area

**Expected result**
- SecureStore tokens are removed
- refresh token is blacklisted server-side
- navigation to login uses a short, controlled visual delay
- protected content is no longer accessible

---

## 6. Security checks

### Security-01 — Request throttle

**Goal**
- verify `/auth/passwordless/request/` is rate-limited per IP

**Expected result**
- repeated abuse eventually triggers throttle protection

### Security-02 — Verify throttle per IP and per email

**Goal**
- verify `/auth/passwordless/verify/` is protected against brute-force attempts

**Expected result**
- IP limit applies
- email-scoped throttle applies
- challenge attempt limit applies

### Security-03 — OTP expiry

**Goal**
- verify that an expired OTP cannot be reused

**Expected result**
- backend rejects expired OTP with a controlled error

### Security-04 — Atomic verify

**Goal**
- verify the same OTP cannot be reused successfully from concurrent attempts

**Expected result**
- only one successful verification is possible

### Security-05 — Refresh token rotation

**Goal**
- verify that refresh produces a new access token and supports rotated refresh tokens

**Expected result**
- refresh flow continues cleanly on web and mobile
- mobile stores `data.refresh ?? refresh`
- repeated mobile refreshes keep working after rotation

### Security-06 — Logout blacklist

**Goal**
- verify a logged-out refresh token cannot be reused

**Expected result**
- old refresh token is rejected after logout

### Security-07 — Suspicious login alert

**Goal**
- verify that a second login from a new device or a new browser sends a security alert email

**Recommended test**
1. Log in once from web browser A
2. Log in again with the same account from:
- another browser, or
- another device, or
- Postman with a different User-Agent

**Expected result**
- first login does **not** trigger a suspicious alert
- second login with new IP or new User-Agent **does** trigger an email
- email contains device type and observed IP

**Important note in local development**
- IP may be local or Docker-related
- location may appear as `Unknown`
- this is acceptable in local QA

---

## 7. Final acceptance criteria for Sprint 1

Sprint 1 can be considered fully validated if all of the following are true:
- backend auth endpoints respond correctly
- OTP request and verify work end-to-end
- Google auth works on web and on mobile native build / APK
- protected routes are actually protected
- organization dashboard is restricted to organization accounts
- refresh flow works on web and mobile
- logout invalidates the session correctly
- web session restore keeps navbar state stable during authentication bootstrap
- suspicious login alert is triggered on a new device or browser
- access token is not persisted in web localStorage
- mobile tokens persist securely in SecureStore

---

## 8. Notes for future production hardening

These are known next-step improvements, not Sprint 1 blockers:
- move web refresh token from `sessionStorage` to a stronger cookie-based model when architecture allows it
- formalize environment-based mobile API configuration for staging/production builds
- improve reverse proxy and trusted proxy configuration for more accurate suspicious-login IP reporting
- optionally move toward HttpOnly cookies in a future auth redesign
