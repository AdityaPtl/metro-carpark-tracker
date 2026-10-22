#!/bin/sh
# Builds index.html (the GitHub Pages web app) from dashboard/app.html.
# app.html is the dashboard itself; this wraps it in a full document and adds
# the web-app manifest and service worker so it can be installed like an app.
set -e
cd "$(dirname "$0")"
{
  cat <<'HEAD'
<!doctype html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0d7478">
<meta name="description" content="Which Sydney Metro Northwest Park&amp;Ride car park still has a space when you get there.">
<link rel="manifest" href="app/manifest.webmanifest">
<link rel="icon" href="app/icon-192.png">
<link rel="apple-touch-icon" href="app/icon-192.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Metro Parking">
</head>
<body style="margin:0">
HEAD
  cat dashboard/app.html
  cat <<'FOOT'
<script>
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
</script>
</body>
</html>
FOOT
} > index.html
echo "Built index.html"
