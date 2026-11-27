import { request as httpRequest } from "node:http";
import { request as httpsRequest } from "node:https";

/*
 * Server side calls to Django on behalf of a browser request. API_URL is
 * Django as this server reaches it (often a private address), so the
 * browser's own Host goes along explicitly: that's how Django knows which
 * school is asking. WHATWG fetch drops a custom Host, hence node:http.
 */

export interface DjangoResponse<T> {
  status: number;
  body: T | null;
}

export function getFromDjango<T>(
  path: string,
  { host, proto }: { host: string; proto: string },
): Promise<DjangoResponse<T>> {
  const base = (process.env.API_URL ?? "http://localhost:8000").replace(/\/+$/, "");
  const url = new URL(`${base}/api${path}`);
  const send = url.protocol === "https:" ? httpsRequest : httpRequest;

  return new Promise((resolve, reject) => {
    const req = send(
      url,
      {
        headers: {
          Accept: "application/json",
          Host: host,
          // So absolute URLs Django builds (the logo) match the browser's scheme.
          "X-Forwarded-Proto": proto,
        },
        timeout: 5000,
      },
      (res) => {
        let raw = "";
        res.setEncoding("utf8");
        res.on("data", (chunk: string) => (raw += chunk));
        res.on("end", () => {
          let body: T | null = null;
          try {
            body = raw ? (JSON.parse(raw) as T) : null;
          } catch {
            // Not JSON (an HTML error page): the status says enough.
          }
          resolve({ status: res.statusCode ?? 0, body });
        });
      },
    );
    req.on("timeout", () => req.destroy(new Error(`GET ${path} timed out`)));
    req.on("error", reject);
    req.end();
  });
}
