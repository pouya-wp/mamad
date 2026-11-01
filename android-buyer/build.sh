#!/usr/bin/env bash
# Builds the buyer's APK straight from the Android build tools — no Gradle, no
# wrapper download, no daemon. It fits in a few hundred MB of RAM and finishes in
# seconds, which is the whole point: this app is one activity and one WebView.
#
#   ./build.sh            → build/one-buying.apk  (signed, installable)
set -euo pipefail

SDK="${ANDROID_HOME:-$HOME/AppData/Local/Android/Sdk}"
SDK="${SDK//\\//}"
BUILD_TOOLS="$SDK/build-tools/35.0.0"
PLATFORM="$SDK/platforms/android-35/android.jar"
OUT=build
KEYSTORE=one-buying.jks
STOREPASS=onecafe

[ -x "$BUILD_TOOLS/aapt2.exe" ] || [ -x "$BUILD_TOOLS/aapt2" ] || { echo "build-tools 35.0.0 not found in $SDK"; exit 1; }
[ -f "$PLATFORM" ] || { echo "android-35 platform not found in $SDK"; exit 1; }

rm -rf "$OUT"
mkdir -p "$OUT/res" "$OUT/gen" "$OUT/classes"

echo "1/6 resources"
"$BUILD_TOOLS/aapt2" compile --dir res -o "$OUT/res.zip"
"$BUILD_TOOLS/aapt2" link \
  -o "$OUT/base.apk" \
  -I "$PLATFORM" \
  --manifest AndroidManifest.xml \
  --java "$OUT/gen" \
  --min-sdk-version 24 \
  --target-sdk-version 35 \
  "$OUT/res.zip"

echo "2/6 java"
javac -encoding UTF-8 --release 11 -nowarn \
  -classpath "$PLATFORM" \
  -d "$OUT/classes" \
  $(find src "$OUT/gen" -name '*.java')

echo "3/6 dex"
"$BUILD_TOOLS/d8.bat" --lib "$PLATFORM" --min-api 24 --output "$OUT" $(find "$OUT/classes" -name '*.class')

echo "4/6 package"
python - "$OUT" <<'PY'
import sys, zipfile, shutil, os
out = sys.argv[1]
shutil.copy(os.path.join(out, 'base.apk'), os.path.join(out, 'unsigned.apk'))
with zipfile.ZipFile(os.path.join(out, 'unsigned.apk'), 'a', zipfile.ZIP_DEFLATED) as apk:
    apk.write(os.path.join(out, 'classes.dex'), 'classes.dex')
PY

echo "5/6 align"
"$BUILD_TOOLS/zipalign" -f -p 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"

echo "6/6 sign"
if [ ! -f "$KEYSTORE" ]; then
  # A local signing key: fine for sideloading, and the same key must sign every
  # update or the phone refuses to install over the previous one. Keep this file.
  keytool -genkeypair -keystore "$KEYSTORE" -alias one -storepass "$STOREPASS" -keypass "$STOREPASS" \
    -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=ONE CAFE, O=ONE CAFE, C=IR" >/dev/null
fi
"$BUILD_TOOLS/apksigner.bat" sign --ks "$KEYSTORE" --ks-pass "pass:$STOREPASS" --key-pass "pass:$STOREPASS" \
  --out "$OUT/one-buying.apk" "$OUT/aligned.apk"
"$BUILD_TOOLS/apksigner.bat" verify "$OUT/one-buying.apk"

rm -f "$OUT/res.zip" "$OUT/base.apk" "$OUT/unsigned.apk" "$OUT/aligned.apk" "$OUT/one-buying.apk.idsig"
ls -lh "$OUT/one-buying.apk"
