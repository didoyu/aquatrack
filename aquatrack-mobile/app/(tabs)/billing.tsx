import { useQuery } from '@tanstack/react-query';
import { RefreshControl, Text, View } from 'react-native';
import { api } from '@/api/client';
import { Card, ErrorState, LoadingState, Page, PageHeading, StatCard } from '@/components/ui';
import { colors } from '@/constants/theme';
import { useHousehold } from '@/hooks/useHousehold';
import { Forecast } from '@/models/types';
import { formatMoney, formatNumber } from '@/utils/format';

export default function BillingScreen() {
  const { household, isLoading: householdsLoading } = useHousehold();
  const forecast = useQuery({
    queryKey: ['forecast', household?.id],
    enabled: !!household,
    queryFn: async () => (await api.get<Forecast>(`/billing/forecast/?household=${household?.id}`)).data,
  });

  if (householdsLoading || forecast.isLoading) return <LoadingState label="Calculating your bill estimate" />;
  if (forecast.isError || !forecast.data) return <ErrorState message="Could not load your bill forecast." onRetry={() => void forecast.refetch()} />;
  const data = forecast.data;

  return <Page refreshControl={<RefreshControl refreshing={forecast.isRefetching} onRefresh={() => void forecast.refetch()} tintColor={colors.ocean} />}>
    <PageHeading title="Bill forecast" subtitle={data.schedule} eyebrow="MONTHLY ESTIMATE" />
    <Card style={{ backgroundColor: colors.ocean, borderColor: colors.ocean }}>
      <Text style={{ color: '#d9f7fa', fontSize: 12, fontWeight: '700' }}>Estimated bill this month</Text>
      <Text style={{ color: '#fff', fontSize: 34, fontWeight: '900', marginTop: 8 }}>{formatMoney(data.predicted_bill)}</Text>
      <Text style={{ color: '#d9f7fa', fontSize: 12, marginTop: 6 }}>Projection method: {data.method.replace('_', ' ')}</Text>
    </Card>
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10 }}>
      <StatCard label="Used so far" value={`${formatNumber(data.consumed_to_date, 2)} cu.m`} icon="water-check-outline" />
      <StatCard label="Projected use" value={`${formatNumber(data.predicted_consumption, 2)} cu.m`} icon="chart-line" />
    </View>
    <Card>
      <Text style={{ color: colors.ink, fontWeight: '800', fontSize: 16, marginBottom: 12 }}>Estimate breakdown</Text>
      {data.breakdown.map((item, index) => <View key={`${item.label}-${index}`} style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 12, paddingVertical: 11, borderTopWidth: 1, borderTopColor: colors.line }}>
        <View style={{ flex: 1 }}><Text style={{ color: colors.ink, fontWeight: '700', fontSize: 13 }}>{item.label}</Text><Text style={{ color: colors.muted, fontSize: 11, marginTop: 3 }}>{formatNumber(item.cubic_meters, 2)} cu.m{item.rate ? ` · ${formatMoney(item.rate)}/cu.m` : ''}</Text></View>
        <Text style={{ color: colors.ink, fontWeight: '800' }}>{formatMoney(item.amount)}</Text>
      </View>)}
    </Card>
    <Text style={{ color: colors.muted, fontSize: 11, lineHeight: 17 }}>This is an estimate based on recent sensor readings and the active rate schedule. Your final bill may differ.</Text>
  </Page>;
}