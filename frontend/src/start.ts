import { createCsrfMiddleware, createStart } from "@tanstack/react-start";

// Server functions are only ever called by this app's own pages, so reject
// any server-function request that isn't same-origin (checked via
// Sec-Fetch-Site, falling back to Origin / Referer). Page loads and assets
// aren't affected.
const csrf = createCsrfMiddleware({
  filter: (ctx) => ctx.handlerType === "serverFn",
});

export const startInstance = createStart(() => ({
  requestMiddleware: [csrf],
}));
