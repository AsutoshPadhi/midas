import { useMemo } from 'react';
import { authService } from '../services/auth.service';
import { useAuthStore } from '../store/auth.store';

export function useAuth() {
  const auth = useAuthStore();

  return useMemo(
    () => ({
      ...auth,
      login: authService.login,
      logout: authService.logout,
      getCurrentUser: authService.getCurrentUser,
    }),
    [auth],
  );
}
