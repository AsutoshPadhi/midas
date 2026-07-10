import axios from 'axios';
import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

const BASE_URL = 'http://localhost:3000';
const ACCESS_TOKEN_KEY = 'access_token';

async function getToken(): Promise<string | null> {
  if (Platform.OS === 'web') {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  }
  return SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
}

async function saveToken(token: string): Promise<void> {
  if (Platform.OS === 'web') {
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
    return;
  }
  await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, token);
}

async function deleteToken(): Promise<void> {
  if (Platform.OS === 'web') {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    return;
  }
  await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
}

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
});

api.interceptors.request.use(async (config) => {
  const token = await getToken();
  console.log('[api] token from storage:', token ? `${token.slice(0, 20)}…` : 'NONE');

  if (token) {
    config.headers = {
      ...(config.headers ?? {}),
      Authorization: `Bearer ${token}`,
    } as typeof config.headers;
  }

  return config;
});

export async function setAccessToken(token: string) {
  await saveToken(token);
}

export async function clearAccessToken() {
  await deleteToken();
}
