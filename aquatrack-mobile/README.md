# AquaTrack Mobile

React Native app for AquaTrack, built with Expo SDK 57 and Expo Router. It uses the existing Django REST API; it does not create a second backend.

## Stack

- Expo SDK 57 / React Native 0.86
- Expo Router for navigation
- Axios for API requests and JWT refresh
- Zustand for the local authentication session and household selection
- TanStack Query for server data caching and refetching
- Expo SecureStore for access and refresh tokens

## Connect to the backend

The checked-in example URL is for this development machine. For a physical phone, set `EXPO_PUBLIC_API_URL` in `.env.local` to the computer's LAN IP and keep the phone and computer on the same Wi-Fi. Do not use `localhost` from Expo Go on a physical phone.

For this workspace, the current LAN URL is:

```text
http://192.168.18.38:8000/api
```

For the Android Studio emulator, use `http://10.0.2.2:8000/api` instead. `.env.local` is ignored by Git.

## Run on Expo Go

1. Start the backend so it listens on the LAN interface. In PowerShell:

```powershell
cd aquatrack-backend
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1,192.168.18.38"
.\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

If your `.env` sets `DJANGO_ALLOWED_HOSTS`, include the computer's LAN IP there too. Allow Python through Windows Firewall on the private network if the phone cannot connect.

2. In another terminal, start Expo:

```powershell
cd aquatrack-mobile
npm start -- --lan
```

3. Open Expo Go and scan the QR code. The phone and development computer must be on the same network. Press `a` in the Expo terminal to open an Android emulator if one is installed.

Create a homeowner account in the app or sign in with an existing account. Public registration always creates a homeowner account. The superuser admin console remains in the web app.

## Mobile features

- Login and homeowner registration
- Securely persisted JWT session and access-token refresh
- Household dashboard with periodic refresh and pull-to-refresh
- Daily, weekly, and monthly usage summaries plus recent readings
- Leak warnings, recommended checklists, and inspect/resolve/false-alarm actions
- Household alerts with mark-as-read
- Monthly bill forecast and rate-tier breakdown

Push-token storage exists in the API, but the backend does not yet deliver Expo push notifications. Mobile alerts currently appear in the in-app Alerts tab.
