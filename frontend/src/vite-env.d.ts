/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** The release id (git short sha), stamped on browser error reports. */
  readonly VITE_RELEASE?: string;
}
