#!/bin/sh
# Wraps dashboard/app.html in a full HTML document for GitHub Pages (index.html).
set -e
cd "$(dirname "$0")"
{
  printf '<!doctype html>\n<html lang="en-AU">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n</head>\n<body>\n'
  cat dashboard/app.html
  printf '\n</body>\n</html>\n'
} > index.html
