# FloodShield: Android app (APK) and iPhone app

This turns the FloodShield web UI (`../static`) into an installable phone app using Capacitor.

## Read this first: what the app is
The app is the phone **front end**. The AI model, shelters, alerts and SOS run on the Python server (`server.py`),
so the server must be running somewhere the phone can reach. The app asks for the server address on first launch,
or you can bake the address into the APK when you build it (below). Running the whole AI model inside the phone
is not part of this project.

What the app does on the phone itself: opens full-screen with its own icon, uses the phone's GPS for
"Use my location", shows native high-risk notifications, handles the Android back button, makes phone calls
(Call 112 / station numbers), and shows the Emergency Guide even with no internet.

What needs the server to be reachable: everything else (training, prediction, safe houses, alerts, SOS, weather).

## Option A (recommended): build the APK in the cloud. No Android Studio needed
GitHub builds the APK for you for free.

1. **Create a free GitHub account** at github.com and make a new repository (name: `floodshield`; private is fine).
2. **Upload the project.** Unzip `flood_project.zip`. In the new repository click **uploading an existing file** and drag in
   the **contents** of the `flood_project` folder (all the files and folders inside it, not the folder itself).
3. **Make sure the workflow file is there.** It lives in the hidden folder `.github/workflows/`. Finder hides folders that
   start with a dot (press `Cmd + Shift + .` to show them), and a drag-and-drop upload may skip them.
   In the repository open `.github/workflows/`. If it is missing:
   **Add file > Create new file**, type the name `.github/workflows/build-android.yml`, paste the contents of
   `mobile/build-android.workflow.yml`, and click **Commit changes**.
4. **Run the build.** Open the **Actions** tab. If asked, click "I understand my workflows, go ahead and enable them".
   Choose **Build Android APK** on the left, click **Run workflow**, optionally type your server address
   (for example `https://abc123.ngrok-free.app` or `http://192.168.1.5:8000`), and click the green **Run workflow** button.
5. **Wait about 5 to 10 minutes** until the run shows a green tick. Open the run, scroll to **Artifacts**, and download
   **FloodShield-debug-apk**. Unzip it to get `app-debug.apk`.
6. **Install on the phone.** Send the APK to your phone (USB cable, Google Drive, email, or WhatsApp to yourself) and open it.
   Android asks you to allow "Install unknown apps" for the app you opened it from: allow it, then tap Install.
   Google Play Protect may warn about an unknown app (this is a debug build that did not come from the Play Store):
   tap **More details**, then **Install anyway**.
7. **First launch.** If you typed a server address in step 4 the app is already connected. Otherwise it asks for the
   address (you can change it any time: Home > Status > Server).

If the build fails, open the failed step in the run log. Re-running often fixes download hiccups.
Artifacts are kept for a limited time, so download the APK once and keep it.

### Choosing the server address
- **Same Wi-Fi (Android allows plain http):** start the server with `uvicorn server:app --host 0.0.0.0`
  and use `http://<computer-ip>:8000`. Your computer and phone must be on the same network and the computer must stay on.
- **HTTPS tunnel:** `ngrok http 8000` or `cloudflared tunnel --url http://localhost:8000` gives an https address
  that works from any network. Free tunnel addresses change each time, so enter the new one in the app
  (Home > Status > Server) instead of rebuilding. Anyone with the link can open your server and it has no login:
  keep simulation mode on and close the tunnel when you are done.

## Option B: build on your own computer with Android Studio
Requirements: Node.js 22 or newer, JDK 21, Android Studio.
```bash
cd mobile
npm install
FS_SERVER_URL=http://192.168.1.5:8000 npm run web   # optional: bake in the server address (omit to be asked in the app)
npx cap add android
python3 patch_android.py                            # permissions + FloodShield icon
npx cap sync android
npx cap open android                                # Android Studio: Build > Build APK(s), or press Run
```
After changing anything in `../static`, run `npm run web` and `npx cap sync android` again.

## iPhone
Needs a Mac with Xcode (`npx cap add ios`, `npx cap open ios`). iPhone blocks plain http, so use an HTTPS server address.
Add `NSLocationWhenInUseUsageDescription` to `ios/App/App/Info.plist` so "Use my location" can ask for permission.
The simplest iPhone route is the installable web app: open the https address in Safari, Share > Add to Home Screen.

## What was tested, and what was not
Tested while building this: generating the Android project from Capacitor, adding permissions and icons with
`patch_android.py` (also when run twice), registering the three native plugins, baking in the server address,
and the app's native code paths (location, notifications, back button) with simulated plugins.
**Not tested:** the Gradle compile and installing the APK on a real phone, because the Android SDK is not available in
the environment this was prepared in. If a build step fails, send me the error from the Actions log.

## Safety
- The APK is a debug build, signed with a debug key. It is fine for a project demo, not for publishing on the Play Store.
- The server has no login. Do not expose it publicly with live alerts/SOS enabled.
- Keep simulation mode (default) unless you control every contact that can receive messages.
