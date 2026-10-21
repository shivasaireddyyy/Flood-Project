#!/usr/bin/env python3
"""Run after `npx cap add android`. Adds the permissions the app needs and the FloodShield icon.
Safe to run more than once."""
import pathlib
import shutil
import sys

root = pathlib.Path(__file__).parent
main = root / "android" / "app" / "src" / "main"
manifest = main / "AndroidManifest.xml"
if not manifest.exists():
    sys.exit(f"Cannot find {manifest}. Run `npx cap add android` first.")

PERMISSIONS = [
    "android.permission.INTERNET",
    "android.permission.ACCESS_FINE_LOCATION",    # "Use my location"
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.POST_NOTIFICATIONS",      # high-risk notifications (Android 13+)
]
text = manifest.read_text()
add = "".join(f'    <uses-permission android:name="{p}" />\n' for p in PERMISSIONS if p not in text)
if add:
    if "</manifest>" not in text:
        sys.exit("Unexpected AndroidManifest.xml (no </manifest>).")
    manifest.write_text(text.replace("</manifest>", add + "</manifest>"))
    print("Added permissions:", add.count("uses-permission"))
else:
    print("Permissions already present")

icons = root / "android-res"
if icons.exists():
    shutil.copytree(icons, main / "res", dirs_exist_ok=True)
    print("Copied FloodShield icons")
