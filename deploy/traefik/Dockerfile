# Traefik for the Render test environment (spec 0003, child 0002). Render
# terminates TLS for staging.ordo.app and *.staging.ordo.app, so this listens
# on plain HTTP and only routes. Build context: the repo root.
#
# Runtime env: PORT (set by Render), PLATFORM_BASE_DOMAIN, API_UPSTREAM and
# DASHBOARD_UPSTREAM (the private services' internal URLs), SITE_URL.
# Render health check path: /ping
FROM traefik:v3.5

COPY deploy/traefik/dynamic.yml /etc/traefik/dynamic.yml

# forwardedHeaders.insecure: Render's own proxy sits in front and sets
# X-Forwarded-Proto and X-Forwarded-For. Only ever on Render, never the VPS.
ENTRYPOINT ["/bin/sh", "-c", "exec traefik \
  --entryPoints.web.address=:${PORT:-8080} \
  --entryPoints.web.forwardedHeaders.insecure=true \
  --providers.file.filename=/etc/traefik/dynamic.yml \
  --ping=true --ping.entryPoint=web \
  --accessLog=true --log.level=INFO"]
