import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useSessionStore } from '@/store/session';

const baseURL = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.18.38:8000/api';

export const api = axios.create({ baseURL, timeout: 15_000, headers: { Accept: 'application/json' } });

type RetryConfig = InternalAxiosRequestConfig & { _retried?: boolean };

api.interceptors.request.use((config) => {
  const accessToken = useSessionStore.getState().accessToken;
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});

api.interceptors.response.use((response) => response, async (error: AxiosError) => {
  const original = error.config as RetryConfig | undefined;
  const session = useSessionStore.getState();
  if (error.response?.status !== 401 || !original || original._retried || !session.refreshToken || original.url?.includes('/auth/')) {
    return Promise.reject(error);
  }

  original._retried = true;
  try {
    const response = await axios.post(`${baseURL}/auth/refresh/`, { refresh: session.refreshToken }, { timeout: 15_000 });
    await session.updateTokens(response.data.access, response.data.refresh);
    original.headers.Authorization = `Bearer ${response.data.access}`;
    return api(original);
  } catch (refreshError) {
    await useSessionStore.getState().clearSession();
    return Promise.reject(refreshError);
  }
});

export function errorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (!error.response) return 'Cannot reach AquaTrack. Check your Wi-Fi and API address.';
  }
  return 'Something went wrong. Please try again.';
}