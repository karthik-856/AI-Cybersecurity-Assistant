// Same-origin requests use Vite's development proxy or Nginx in production.
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
