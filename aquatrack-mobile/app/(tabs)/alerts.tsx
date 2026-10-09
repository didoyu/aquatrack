import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert as NativeAlert, Pressable, RefreshControl, Text, View } from 'react-native';
import { api, errorMessage } from '@/api/client';
import { Card, ErrorState, LoadingState, Page, PageHeading, Pill } from '@/components/ui';
import { colors } from '@/constants/theme';
import { useHousehold } from '@/hooks/useHousehold';
import { Alert, Paginated } from '@/models/types';
import { formatDate } from '@/utils/format';

export default function AlertsScreen() {
  const queryClient = useQueryClient();
  const { household, isLoading: householdsLoading } = useHousehold();
  const alerts = useQuery({
    queryKey: ['alerts', household?.id],
    enabled: !!household,
    queryFn: async () => (await api.get<Paginated<Alert>>(`/alerts/?household=${household?.id}`)).data.results,
  });
  const markRead = useMutation({
    mutationFn: async (id: number) => api.post(`/alerts/${id}/read/`),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ['alerts', household?.id] }),
    onError: (error) => NativeAlert.alert('Could not update alert', errorMessage(error)),
  });

  if (householdsLoading || alerts.isLoading) return <LoadingState label="Loading alerts" />;
  if (alerts.isError) return <ErrorState message="Could not load alerts." onRetry={() => void alerts.refetch()} />;
  const unread = alerts.data?.filter((alert) => !alert.is_read).length ?? 0;

  return <Page refreshControl={<RefreshControl refreshing={alerts.isRefetching} onRefresh={() => void alerts.refetch()} tintColor={colors.ocean} />}>
    <PageHeading title="Alerts" subtitle={household?.name ?? 'Leak warnings and sensor notices'} eyebrow="NOTIFICATIONS" action={unread > 0 ? <Pill label={`${unread} new`} tone="warning" /> : undefined} />
    {!alerts.data?.length && <Card><Text style={{ color: colors.muted }}>No alerts yet. New leak warnings will appear here.</Text></Card>}
    {alerts.data?.map((alert) => <Card key={alert.id} style={!alert.is_read ? { borderLeftWidth: 3, borderLeftColor: colors.aqua } : undefined}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}><Text style={{ color: colors.ink, flex: 1, fontSize: 15, fontWeight: '800', textTransform: 'capitalize' }}>{alert.alert_type.replaceAll('_', ' ')}</Text><Pill label={alert.severity} tone={alert.severity === 'critical' ? 'critical' : alert.severity === 'warning' ? 'warning' : 'neutral'} /></View>
      <Text style={{ color: colors.muted, fontSize: 11, marginTop: 6 }}>{formatDate(alert.sent_at)}</Text>
      <Text style={{ color: colors.ink, fontSize: 13, lineHeight: 20, marginTop: 10 }}>{alert.message}</Text>
      {!alert.is_read && <Pressable accessibilityRole="button" disabled={markRead.isPending} onPress={() => markRead.mutate(alert.id)} style={{ alignSelf: 'flex-start', marginTop: 12, paddingVertical: 5 }}><Text style={{ color: colors.ocean, fontWeight: '800' }}>Mark as read</Text></Pressable>}
    </Card>)}
  </Page>;
}