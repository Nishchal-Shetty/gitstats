#!/bin/sh

# Replace placeholder with env var
sed -i "s|__API_URL__|${API_URL}|g" /usr/share/nginx/html/config.js

echo "Injected API_URL=${API_URL}"