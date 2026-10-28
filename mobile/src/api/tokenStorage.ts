import * as SecureStore from "expo-secure-store";

const ACCESS = "suvai_access_token";
const REFRESH = "suvai_refresh_token";

export interface Tokens {
  access: string;
  refresh: string;
}

export async function loadTokens(): Promise<Tokens | null> {
  try {
    const [access, refresh] = await Promise.all([
      SecureStore.getItemAsync(ACCESS),
      SecureStore.getItemAsync(REFRESH),
    ]);
    return access && refresh ? { access, refresh } : null;
  } catch {
    return null;
  }
}

export async function saveTokens(tokens: Tokens): Promise<void> {
  await Promise.all([
    SecureStore.setItemAsync(ACCESS, tokens.access),
    SecureStore.setItemAsync(REFRESH, tokens.refresh),
  ]);
}

export async function clearTokens(): Promise<void> {
  try {
    await Promise.all([SecureStore.deleteItemAsync(ACCESS), SecureStore.deleteItemAsync(REFRESH)]);
  } catch {
    // nothing to clear
  }
}
