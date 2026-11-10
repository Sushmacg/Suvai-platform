// Backend origin without a path. The client adds /api/v1.
export const API_URL = ((import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000").replace(/\/+$/, "");