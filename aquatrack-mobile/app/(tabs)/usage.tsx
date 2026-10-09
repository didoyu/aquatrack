import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Pressable, RefreshControl, Text, View } from 'react-native';
import { api } from '@/api/client';
import { Card, ErrorState, LoadingState, Page, PageHeading } from '@/components/ui';
import { colors } from '@/constants/theme';
import { useHousehold } from '@/hooks/useHousehold';
import { Reading, UsageSummary, Paginated } from '@/models/types';
import { formatDate, formatNumber } from '@/utils/format';

const periods = ['daily', 'weekly', 'monthly'] as const;
type Period = typeof periods[number];

export default function UsageScreen() {
  const [period, setPeriod] = useState<Period>('daily');
  const { household, isLoading: householdsLoading } = useHousehold();
  const usage = useQuery({
    queryKey: ['usage', household?.id, period],
    enabled: !!household,
    queryFn: async () => (await api.get<UsageSummary[]>(`/households/${household?.id}/usage/?period=${period}`)).data,
  });
  const readings = useQuery({
    queryKey: ['readings', household?.id],
    enabled: !!household,
    queryFn: async () => (await api.get<Paginated<Reading>>(`/readings/?household=${household?.id}&page_size=12`)).data.results,
  });

  if (householdsLoading || usage.isLoading) return <LoadingState label="Loading water usage" />;
  if (usage.isError) return <ErrorState message="Could not load water usage." onRetry={() => void usage.refetch()} />;
  const max = Math.max(...(usage.data ?? []).map((item) => item.total_consumption), 1);

  return <Page refreshControl={<RefreshControl refreshing={usage.isRefetching || readings.isRefetching} onRefresh={() => { void usage.refetch(); void readings.refetch(); }} tintColor={colors.ocean} />}>
    <PageHeading title="Usage history" subtitle={household?.name ?? 'Water consumption over time'} eyebrow="CONSUMPTION" />
    <View style={{ flexDirection: 'row', padding: 4, borderRadius: 9, backgroundColor: '#e7f1f3', gap: 4 }}>
      {periods.map((value) => <Pressable key={value} onPress={() => setPeriod(value)} style={{ flex: 1, alignItems: 'center', paddingVertical: 9, borderRadius: 7, backgroundColor: period === value ? colors.surface : 'transparent' }}><Text style={{ color: period === value ? colors.ocean : colors.muted, fontWeight: '700', textTransform: 'capitalize' }}>{value}</Text></Pressable>)}
    </View>
    <Card>
      <Text style={{ color: colors.ink, fontWeight: '800', fontSize: 15 }}>Liters used · {period}</Text>
      {!usage.data?.length ? <Text style={{ color: colors.muted, marginTop: 18 }}>No usage summaries for this period yet.</Text> : <View style={{ minHeight: 215, flexDirection: 'row', alignItems: 'flex-end', gap: 7, paddingTop: 20 }}>
        {usage.data.map((item) => {
          const height = Math.max(4, item.total_consumption / max * 132);
          const date = new Date(item.period_start);
          const label = period === 'monthly' ? date.toLocaleString(undefined, { month: 'short' }) : `${date.getMonth() + 1}/${date.getDate()}`;
          return <View key={item.id} style={{ flex: 1, height: 185, alignItems: 'center', justifyContent: 'flex-end', gap: 7 }}>
            <Text numberOfLines={1} style={{ color: colors.ink, fontSize: 10, fontWeight: '700' }}>{formatNumber(item.total_consumption, 0)}</Text>
            <View style={{ width: '75%', maxWidth: 34, height, borderRadius: 5, backgroundColor: colors.aqua }} />
            <Text style={{ color: colors.muted, fontSize: 10 }}>{label}</Text>
          </View>;
        })}
      </View>}
      <Text style={{ color: colors.muted, fontSize: 11, marginTop: 8 }}>Volume in liters</Text>
    </Card>
    <Card>
      <Text style={{ color: colors.ink, fontWeight: '800', fontSize: 15, marginBottom: 5 }}>Recent readings</Text>
      {readings.isError && <Text style={{ color: colors.critical, fontSize: 12 }}>Readings are temporarily unavailable.</Text>}
      {!readings.data?.length ? <Text style={{ color: colors.muted, marginTop: 10 }}>No sensor readings yet.</Text> : readings.data.map((reading) => <View key={reading.id} style={{ paddingVertical: 11, borderTopWidth: 1, borderTopColor: colors.line }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}><Text style={{ color: colors.ink, fontWeight: '700', fontSize: 13 }}>{formatDate(reading.timestamp)}</Text><Text style={{ color: reading.is_anomalous ? colors.critical : colors.positive, fontSize: 11, fontWeight: '800' }}>{reading.is_anomalous ? 'ABNORMAL' : 'NORMAL'}</Text></View>
        <Text style={{ color: colors.muted, fontSize: 12, marginTop: 5 }}>{formatNumber(reading.flow_rate, 2)} L/min  ·  {formatNumber(reading.pressure_level, 1)} PSI</Text>
      </View>)}
    </Card>
  </Page>;
}