import { useQuery } from '@tanstack/react-query';
import { useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { RefreshControl, Text, View } from 'react-native';
import { api } from '@/api/client';
import { Card, ErrorState, LoadingState, Page, PageHeading, Pill, StatCard } from '@/components/ui';
import { colors } from '@/constants/theme';
import { useSessionStore } from '@/store/session';
import { formatDate, formatMoney, formatNumber } from '@/utils/format';

type Household = { id: number; name: string; address: string };
type DashboardData = {
  household: Household;
  current_flow_rate: number | null;
  current_pressure: number | null;
  last_reading_at: string | null;
  today_consumption_liters: number;
  max_daily_consumption_liters: number;
  average_hourly_usage_liters: number;
  projected_bill: number;
  devices: { id: number; name: string; status: string; last_seen: string | null }[];
  active_leak: { stage: number; duration_hours: number; status: string } | null;
};

export default function HomeScreen() {
  const selectedId = useSessionStore((state) => state.householdId);
  const clearSession = useSessionStore((state) => state.clearSession);
  const queryClient = useQueryClient();
  const logout = async () => { queryClient.clear(); await clearSession(); };
  const households = useQuery({ queryKey: ['households'], queryFn: async () => (await api.get('/households/')).data.results as Household[] });
  const household = households.data?.find((item) => item.id === selectedId) ?? households.data?.[0];
  const dashboard = useQuery({
    queryKey: ['dashboard', household?.id],
    enabled: !!household,
    refetchInterval: 30_000,
    queryFn: async () => (await api.get(`/households/${household?.id}/dashboard/`)).data as DashboardData,
  });

  if (households.isLoading) return <LoadingState label="Loading your water overview" />;
  if (households.isError) return <ErrorState message="Could not load your household." onRetry={() => void households.refetch()} />;
  if (!household) return <Page><PageHeading title="Welcome to AquaTrack" subtitle="Your household is not linked to this account yet." action={<Text onPress={() => void logout()}>Log out</Text>} /><Card><Text style={{ color: colors.muted, lineHeight: 22 }}>Ask your AquaTrack administrator to set up your household and connect its sensor.</Text></Card></Page>;
  if (dashboard.isLoading) return <LoadingState label="Loading your water overview" />;
  if (dashboard.isError || !dashboard.data) return <ErrorState message="Could not load your latest readings." onRetry={() => void dashboard.refetch()} />;

  const data = dashboard.data;
  const leak = data.active_leak;
  return <Page refreshControl={<RefreshControl refreshing={dashboard.isRefetching} onRefresh={() => void dashboard.refetch()} tintColor={colors.ocean} />}>
    <PageHeading title={data.household.name} subtitle={`Last sensor update ${formatDate(data.last_reading_at)}`} action={<Text onPress={() => void logout()} style={{ color: colors.ocean, fontWeight: '700' }}>Log out</Text>} eyebrow="AQUATRACK · WATER OVERVIEW" />
    <Card style={{ backgroundColor: leak ? (leak.stage >= 2 ? colors.criticalLight : colors.warningLight) : colors.positiveLight, borderColor: leak ? (leak.stage >= 2 ? '#f0d0ca' : '#efdfb8') : '#cce8d8' }}>
      <View style={{ flexDirection: 'row', gap: 12, alignItems: 'flex-start' }}>
        <MaterialCommunityIcons name={leak ? 'water-alert' : 'check-circle-outline'} size={25} color={leak ? (leak.stage >= 2 ? colors.critical : colors.warning) : colors.positive} />
        <View style={{ flex: 1, gap: 4 }}>
          <Text style={{ color: colors.ink, fontSize: 15, fontWeight: '700' }}>{leak ? (leak.stage >= 2 ? 'Critical leak warning' : 'Possible leak detected') : 'Water use looks normal'}</Text>
          <Text style={{ color: colors.muted, lineHeight: 20 }}>{leak ? `Abnormal flow has continued for ${formatNumber(leak.duration_hours, 0)} hours.` : 'We are monitoring your connected sensor readings.'}</Text>
          {leak && <Text onPress={() => router.push('/(tabs)/leaks')} style={{ color: colors.ocean, fontWeight: '700', marginTop: 5 }}>View leak guidance  ›</Text>}
        </View>
      </View>
    </Card>
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginTop: 4 }}>
      <StatCard label="Flow rate" value={`${formatNumber(data.current_flow_rate, 2)} L/min`} icon="water" highlight />
      <StatCard label="Pipe pressure" value={`${formatNumber(data.current_pressure, 1)} PSI`} icon="gauge" />
      <StatCard label="Used today" value={`${formatNumber(data.today_consumption_liters, 0)} L`} icon="cup-water" />
      <StatCard label="Estimated bill" value={formatMoney(data.projected_bill)} icon="receipt-text-outline" />
    </View>
    <Card style={{ marginTop: 4 }}>
      <Text style={{ color: colors.ink, fontSize: 16, fontWeight: '700', marginBottom: 12 }}>Sensor units</Text>
      {data.devices.length ? data.devices.map((device) => <View key={device.id} style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 9, borderTopWidth: 1, borderTopColor: colors.line }}>
        <View><Text style={{ color: colors.ink, fontWeight: '700' }}>{device.name}</Text><Text style={{ color: colors.muted, fontSize: 12, marginTop: 3 }}>Last seen {formatDate(device.last_seen)}</Text></View>
        <Pill label={device.status} tone={device.status === 'online' ? 'positive' : 'neutral'} />
      </View>) : <Text style={{ color: colors.muted }}>No sensor unit is registered yet.</Text>}
    </Card>
  </Page>;
}
