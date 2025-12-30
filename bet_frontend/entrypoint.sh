#!/bin/sh
# Inject DEFAULT_MODEL environment variable into HTML
# Replace placeholder with actual value from environment

DEFAULT_MODEL=${DEFAULT_MODEL:-llama3.2:1b}

# Inject into HTML as a script tag
sed -i "s|<!-- DEFAULT_MODEL_PLACEHOLDER -->|<script>window.DEFAULT_MODEL = '${DEFAULT_MODEL}';</script>|g" /usr/share/nginx/html/index.html

# Start nginx
exec nginx -g "daemon off;"


