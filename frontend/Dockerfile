# Dashboard (TanStack Start on Node via Nitro), behind Traefik for every
# <slug>.<base> and console.<base> (deploy/traefik/dynamic.yml). Runtime env:
# API_URL (Django as this server reaches it), PLATFORM_BASE_DOMAIN, and
# optionally SITE_URL (the marketing site) and PUBLIC_API_URL (default: the
# request's own origin). See src/lib/origins.server.ts.

# pnpm 11 needs Node >= 22.13; corepack installs the version pinned in
# package.json's "packageManager".
FROM node:22-slim AS build
WORKDIR /frontend
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm run build

FROM node:22-slim AS runtime
WORKDIR /frontend
ENV NODE_ENV=production
# Nitro's node-server output is self-contained — no node_modules needed.
COPY --from=build /frontend/.output ./.output
ENV PORT=3000
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
