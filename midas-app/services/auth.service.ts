import { api, clearAccessToken, setAccessToken } from './api';
import { APP_CONFIG } from '../constants/config';
import type { LoginRequest, LoginResponse, User } from '../types/auth';
import { useAuthStore } from '../store/auth.store';

type ExchangeResponse = {
  access_token: string;
  user?: User;
  token_type?: string;
  expires_in?: number;
};

async function exchangeToken(tempToken: string): Promise<{ accessToken: string; user?: User }> {
  const { data } = await api.get<ExchangeResponse>(
    `/api/v1/auth/exchange?token=${encodeURIComponent(tempToken)}`,
    { baseURL: APP_CONFIG.backendApiUrl }
  );
  return { accessToken: data.access_token, user: data.user };
}

async function login(payload: LoginRequest) {
  const { data } = await api.post<LoginResponse>('/auth/login', payload);

  await setAccessToken(data.accessToken);
  useAuthStore.getState().setSession(data.user, data.accessToken);

  return data;
}

async function logout() {
  await clearAccessToken();
  useAuthStore.getState().clearSession();
}

async function getCurrentUser() {
  const { data } = await api.get<User>('/auth/me');
  useAuthStore.getState().setUser(data);
  return data;
}

export const authService = {
  exchangeToken,
  login,
  logout,
  getCurrentUser,
};
