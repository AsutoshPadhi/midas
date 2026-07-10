import { create } from 'zustand';
import type { User } from '../types/auth';
import type { Transaction } from '../types/transaction';

type AuthState = {
  user: User | null;
  accessToken: string | null;
  transactions: Transaction[];
  setSession: (user: User, accessToken: string) => void;
  setAccessToken: (accessToken: string) => void;
  setUser: (user: User) => void;
  setTransactions: (transactions: Transaction[]) => void;
  clearSession: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  transactions: [],
  setSession: (user, accessToken) => set({ user, accessToken }),
  setAccessToken: (accessToken) => set({ accessToken }),
  setUser: (user) => set({ user }),
  setTransactions: (transactions) => set({ transactions }),
  clearSession: () => set({ user: null, accessToken: null, transactions: [] }),
}));
