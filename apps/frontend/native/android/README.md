# Android ML Kit Plugin Template

This directory is intentionally outside the generated Capacitor `android/` folder so `npx cap add android` can still create the project cleanly.

After generating the Android project for the demo app:

1. Copy `MlKitObjectDetectorPlugin.kt` into `android/app/src/main/java/com/lawcompass/mobiletest/`.
2. Add the dependency from `build.gradle.snippet` to `android/app/build.gradle`.
3. Run `npx cap sync android`.

The plugin consumes frame image data from the demo page and returns object candidates only. It must not produce fault ratio, accident type, signal violation, KNIA chart, or legal judgment fields.

