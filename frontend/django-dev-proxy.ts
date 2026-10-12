import { request } from "node:http";
import type { IncomingMessage } from "node:http";
import type { Duplex } from "node:stream";
import type { Plugin } from "vite";

/**
 * Dev only stand in for Traefik: /api, /ws and /media on any
 * <slug>.localhost:3000 go to Django with the browser's Host untouched, so
 * Django resolves the same school the page is on (spec 0003, child 0002).
 *
 * Not Vite's server.proxy: Nitro's dev middleware answers every path before
 * that runs, but it steps aside for middleware mounted on a route prefix.
 */
export function djangoDevProxy(target: string, prefixes: string[]): Plugin {
  const { hostname, port } = new URL(target);

  function forward(req: IncomingMessage) {
    return request({
      hostname,
      port,
      method: req.method,
      // Connect strips the mount prefix from req.url; originalUrl keeps it.
      path: (req as IncomingMessage & { originalUrl?: string }).originalUrl ?? req.url,
      headers: req.headers,
    });
  }

  return {
    name: "ordo:django-dev-proxy",
    apply: "serve",
    configureServer(server) {
      for (const prefix of prefixes) {
        server.middlewares.use(prefix, (req, res) => {
          const upstream = forward(req);
          upstream.on("response", (answer) => {
            res.writeHead(answer.statusCode ?? 502, answer.headers);
            // Django restarting mid response resets the socket; unhandled,
            // that ECONNRESET lands in Vite's error overlay.
            answer.on("error", () => res.destroy());
            answer.pipe(res);
          });
          upstream.on("error", () => {
            if (res.headersSent) return void res.destroy();
            res.statusCode = 502;
            res.end("Django isn't running on " + target);
          });
          // The browser aborting a request (navigation, refetch) resets too.
          req.on("error", () => upstream.destroy());
          res.on("error", () => upstream.destroy());
          req.pipe(upstream);
        });
      }

      server.httpServer?.on("upgrade", (req, socket: Duplex, head) => {
        if (!prefixes.some((p) => req.url?.startsWith(p + "/"))) return;
        const upstream = forward(req);
        socket.on("error", () => upstream.destroy());
        upstream.on("upgrade", (answer, upSocket, upHead) => {
          const lines = [`HTTP/1.1 ${answer.statusCode} ${answer.statusMessage}`];
          for (let i = 0; i < answer.rawHeaders.length; i += 2) {
            lines.push(`${answer.rawHeaders[i]}: ${answer.rawHeaders[i + 1]}`);
          }
          socket.write(lines.join("\r\n") + "\r\n\r\n");
          if (upHead.length) socket.write(upHead);
          upSocket.pipe(socket).pipe(upSocket);
          socket.on("error", () => upSocket.destroy());
          socket.on("close", () => upSocket.destroy());
          upSocket.on("error", () => socket.destroy());
        });
        upstream.on("response", () => socket.destroy());
        upstream.on("error", () => socket.destroy());
        if (head.length) upstream.write(head);
        upstream.end();
      });
    },
  };
}
