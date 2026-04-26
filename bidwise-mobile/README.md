# BidWise Mobile

Expo Router mobile client for BidWise.

## Architecture

- `app/`: route entry points
- `src/features/`: feature modules (`auth`, `dashboard`, `opportunities`, `profile`)
- `src/shared/`: shared components, hooks, services, and theme utilities

The mobile app consumes the same backend API as the web client and currently includes:
- login with OTP and Google Sign-In,
- onboarding and dashboard entry flows,
- public opportunity browsing,
- authenticated detail actions and recommendation surfaces.

## Run locally

```bash
npm install
npx expo start
```

Optional environment variable:

```env
EXPO_PUBLIC_API_BASE_URL=http://<your-lan-ip>:8000/api
```

If `EXPO_PUBLIC_API_BASE_URL` is not set, the app tries to detect the local development host automatically and falls back to `http://127.0.0.1:8000/api` when needed.
