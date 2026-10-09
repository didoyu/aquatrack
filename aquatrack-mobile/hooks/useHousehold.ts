import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { Household, Paginated } from '@/models/types';
import { useSessionStore } from '@/store/session';

export function useHousehold() {
  const selectedId = useSessionStore((state) => state.householdId);
  const query = useQuery({
    queryKey: ['households'],
    queryFn: async () => {
      const { data } = await api.get<Paginated<Household> | Household[]>('/households/');
      if (Array.isArray(data)) return data;
      return Array.isArray(data?.results) ? data.results : [];
    },
  });
  const household = query.data?.find((item) => item.id === selectedId) ?? query.data?.[0] ?? null;
  return { ...query, household };
}