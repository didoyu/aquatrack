import * as SecureStore from 'expo-secure-store';
import { create } from 'zustand';

export type User = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  is_superuser: boolean;
};

type SessionState = {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  householdId: number | null;
  hydrated: boolean;
  hydrate: () => Promise<void>;
  setSession: (accessToken: string, refreshToken: string, user: User) => Promise<void>;
  updateTokens: (accessToken: string, refreshToken?: string) => Promise<void>;
  setHouseholdId: (householdId: number | null) => void;
  clearSession: () => Promise<void>;
};

const ACCESS_KEY = 'aquatrack.access';
const REFRESH_KEY = 'aquatrack.refresh';
const USER_KEY = 'aquatrack.user';

export const useSessionStore = create<SessionState>((set, get) => ({
  accessToken: null,
  refreshToken: null,
  user: null,
  householdId: null,
  hydrated: false,
  hydrate: async () => {
    try {
      const [accessToken, refreshToken, storedUser] = await Promise.all([
        SecureStore.getItemAsync(ACCESS_KEY),
        SecureStore.getItemAsync(REFRESH_KEY),
        SecureStore.getItemAsync(USER_KEY),
      ]);
      set({ accessToken, refreshToken, user: storedUser ? JSON.parse(storedUser) as User : null });
    } catch {
      await get().clearSession();
    } finally {
      set({ hydrated: true });
    }
  },
  setSession: async (accessToken, refreshToken, user) => {
    await Promise.all([
      SecureStore.setItemAsync(ACCESS_KEY, accessToken),
      SecureStore.setItemAsync(REFRESH_KEY, refreshToken),
      SecureStore.setItemAsync(USER_KEY, JSON.stringify(user)),
    ]);
    set({ accessToken, refreshToken, user });
  },
  updateTokens: async (accessToken, refreshToken) => {
    const currentRefresh = refreshToken ?? get().refreshToken;
    await Promise.all([
      SecureStore.setItemAsync(ACCESS_KEY, accessToken),
      ...(currentRefresh ? [SecureStore.setItemAsync(REFRESH_KEY, currentRefresh)] : []),
    ]);
    set({ accessToken, refreshToken: currentRefresh });
  },
  setHouseholdId: (householdId) => set({ householdId }),
  clearSession: async () => {
    await Promise.all([
      SecureStore.deleteItemAsync(ACCESS_KEY),
      SecureStore.deleteItemAsync(REFRESH_KEY),
      SecureStore.deleteItemAsync(USER_KEY),
    ]);
    set({ accessToken: null, refreshToken: null, user: null, householdId: null });
  },
}));