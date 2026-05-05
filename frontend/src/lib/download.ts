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

export async function downloadAuthenticatedFile(
  url: string,
  fallbackFilename: string,
  params?: Record<string, string | number | undefined>,
): Promise<void> {
  const res = await api.get(url, {
    params,
    responseType: "blob",
  });
  const blob = res.data as Blob;
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
