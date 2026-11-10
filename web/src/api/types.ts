export type User = { id: string; name: string; phone: string; email: string | null; role: string };
export type TokenResponse = { access_token: string; refresh_token: string; token_type?: string };
export type Tokens = { access: string; refresh: string };