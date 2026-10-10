# Site + dashboard (TanStack Start on Node via Nitro). Point both the bare
# domain and its app. subdomain at this service.
# Runtime env: API_URL (Django as this server reaches it) and optionally
# PUBLIC_API_URL / APP_URL / SITE_URL (default: api./app./bare of the
# request host). See src/lib/origins.server.ts.

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
