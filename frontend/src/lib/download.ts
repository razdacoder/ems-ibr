import { api } from "./api";

function pickFilename(disposition: string | undefined, fallback: string) {
  if (!disposition) return fallback;
  // Look for filename*=UTF-8''<encoded> first, then filename="..."
  const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
  if (utf8) {
    try {
      return decodeURIComponent(utf8[1]);
    } catch {
      // fall through
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(disposition);
  return plain?.[1] ?? fallback;
}

/** Error carrying a parsed JSON body so extractErrorEnvelope can read it. */
class DownloadError extends Error {
  response: { data: unknown };
  constructor(data: unknown) {
    super("Download failed");
    this.response = { data };
  }
}

/**
 * Blob responses hide error bodies: with responseType "blob" a JSON 4xx body
 * arrives as a Blob, so `data.detail` reads as undefined and every failure
 * collapses into "Something went wrong". Decode it back into an object.
 */
async function blobToEnvelope(blob: Blob): Promise<unknown> {
  try {
    return JSON.parse(await blob.text());
  } catch {
    return undefined;
  }
}

export async function downloadAuthenticatedFile(
  url: string,
  fallbackFilename: string,
  params?: Record<string, string | number | undefined>,
): Promise<void> {
  let res;
  try {
    res = await api.get(url, {
      params,
      responseType: "blob",
    });
  } catch (err) {
    const data = (err as { response?: { data?: unknown } })?.response?.data;
    if (data instanceof Blob) {
      const envelope = await blobToEnvelope(data);
      if (envelope) throw new DownloadError(envelope);
    }
    throw err;
  }
  const blob = res.data as Blob;

  // A 2xx carrying JSON or HTML is not the file we asked for — it means the
  // endpoint redirected to a page (axios follows redirects transparently) or
  // returned an error envelope with the wrong status. Saving it would hand the
  // user a .zip/.csv containing a web page, which is how attendance-sheet
  // downloads used to fail silently. Surface it instead.
  const type = blob.type || "";
  if (type.includes("application/json")) {
    const envelope = await blobToEnvelope(blob);
    throw new DownloadError(
      envelope ?? { detail: "The server did not return a file." },
    );
  }
  if (type.includes("text/html")) {
    throw new DownloadError({
      detail: "The server returned a page instead of a file. Please retry.",
    });
  }
  const filename = pickFilename(
    res.headers["content-disposition"] as string | undefined,
    fallbackFilename,
  );
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Revoke after a short delay so the browser can finish the download.
  setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
}
