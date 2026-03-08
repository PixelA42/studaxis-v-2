/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_GATEWAY_URL: string;
  readonly VITE_APPSYNC_ENDPOINT: string;
  readonly VITE_APPSYNC_API_KEY: string;
  readonly VITE_TEACHER_BACKEND_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
