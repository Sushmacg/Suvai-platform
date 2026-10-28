export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type?: string;
}

export interface User {
  id: string;
  name: string;
  phone: string;
  email: string | null;
  role: string;
}

export interface LoginRequest {
  phone: string;
  password: string;
}

export interface RegisterRequest {
  name: string;
  phone: string;
  email?: string | null;
  password: string;
}
