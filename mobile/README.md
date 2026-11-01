# ONE CAFE mobile

Expo React Native shell for the live panel at `https://onecafe.beyondex.one`.

## Local development

```powershell
cd mobile
pnpm install
npx expo start
```

The app opens the existing panel in a restricted WebView, with native splash, status, navigation shortcuts, retry screen, and optional device notification registration. It uses the panel's existing login and cookies. External HTTPS links open in the system browser.

## Builds

The Android and iOS binaries are built in EAS cloud; no Android Studio or local Xcode install is needed. Sign in to an Expo account and initialize the project first:

```powershell
npx eas-cli@latest login
npx eas-cli@latest init
npx eas-cli@latest build --platform android --profile preview
npx eas-cli@latest build --platform ios --profile production
```

The Android preview profile produces a directly installable APK. iOS distribution requires an Apple Developer account and an approved distribution path such as TestFlight. The Expo project ID created by `eas init` is required to register push tokens. Android FCM and iOS APNs credentials must be configured in EAS before remote notifications can be delivered. Do not put these credentials in this repository.

The repository includes the server endpoint, device DocType, and a queued notification after new SepandYar orders are imported. Deploy the backend changes and run `bench --site frontend migrate` before the bell button can register a phone. Until deployment, EAS credentials, and a physical-device test are complete, do not present push as live.
