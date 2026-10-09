import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Alert as NativeAlert, Pressable, RefreshControl, Text, View } from 'react-native';
import { api, errorMessage } from '@/api/client';
import { Card, ErrorState, LoadingState, Page, PageHeading, Pill } from '@/components/ui';
import { colors } from '@/constants/theme';
import { useHousehold } from '@/hooks/useHousehold';
import { Leak, Paginated } from '@/models/types';
import { formatDate, formatNumber } from '@/utils/format';

export default function LeaksScreen() {
  const queryClient = useQueryClient();
  const { household, isLoading: householdsLoading } = useHousehold();
  const [busyId, setBusyId] = useState<number | null>(null);
  const leaks = useQuery({
    queryKey: ['leaks', household?.id],
    enabled: !!household,
    queryFn: async () => (await api.get<Paginated<Leak>>(`/leaks/?household=${household?.id}`)).data.results,
  });
  const action = useMutation({
    mutationFn: async ({ id, name }: { id: number; name: string }) => api.post(`/leaks/${id}/${name}/`, {}),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ['leaks', household?.id] }),
    onError: (error) => NativeAlert.alert('Could not update leak status', errorMessage(error)),
    onSettled: () => setBusyId(null),
  });

  if (householdsLoading || leaks.isLoading) return <LoadingState label="Loading leak history" />;
  if (leaks.isError) return <ErrorState message="Could not load leak detections." onRetry={() => void leaks.refetch()} />;

  return <Page refreshControl={<RefreshControl refreshing={leaks.isRefetching} onRefresh={() => void leaks.refetch()} tintColor={colors.ocean} />}>
    <PageHeading title="Leak detection" subtitle="Sensor-detected anomalies and suggested next steps." eyebrow="WATER SAFETY" />
    {!leaks.data?.length && <Card><Text style={{ color: colors.positive, fontWeight: '800', fontSize: 15 }}>No anomalies recorded</Text><Text style={{ color: colors.muted, marginTop: 5, lineHeight: 20 }}>Your household has no recorded leak events.</Text></Card>}
    {leaks.data?.map((leak) => {
      const tone = leak.stage >= 2 ? 'critical' : leak.stage === 1 ? 'warning' : 'neutral';
      return <Card key={leak.id}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
          <View style={{ flex: 1, gap: 7 }}><Pill label={leak.stage >= 2 ? 'Stage 2 · Critical' : leak.stage === 1 ? 'Stage 1 · Warning' : 'Monitoring'} tone={tone} /><Text style={{ color: colors.ink, fontSize: 17, fontWeight: '800' }}>{leak.classification}</Text></View>
          <Pill label={leak.status.replace('_', ' ')} />
        </View>
        <Text style={{ color: colors.muted, fontSize: 12, lineHeight: 19, marginTop: 12 }}>Detected {formatDate(leak.detected_at)} · {formatNumber(leak.duration_hours, 1)} h · {formatNumber(leak.avg_flow_rate, 2)} L/min</Text>
        {leak.recommended_steps && <View style={{ marginTop: 14, padding: 12, borderRadius: 8, backgroundColor: colors.aquaLight }}>
          <Text style={{ color: colors.ink, fontWeight: '700', lineHeight: 20 }}>{leak.recommended_steps.message}</Text>
          {leak.recommended_steps.checklist.map((step) => <Text key={step.priority} style={{ color: colors.muted, fontSize: 12, lineHeight: 18, marginTop: 7 }}>• {step.item}: {step.how}</Text>)}
        </View>}
        {!leak.resolved_at && <View style={{ gap: 8, marginTop: 14 }}>
          <Pressable disabled={action.isPending} onPress={() => { setBusyId(leak.id); action.mutate({ id: leak.id, name: 'inspect' }); }} style={{ alignItems: 'center', borderRadius: 8, padding: 12, backgroundColor: colors.ocean }}><Text style={{ color: '#fff', fontWeight: '800' }}>{action.isPending && busyId === leak.id ? 'Updating…' : 'Mark inspected'}</Text></Pressable>
          <View style={{ flexDirection: 'row', gap: 8 }}>
            <Pressable disabled={action.isPending} onPress={() => { setBusyId(leak.id); action.mutate({ id: leak.id, name: 'false-alarm' }); }} style={{ flex: 1, alignItems: 'center', borderRadius: 8, padding: 11, borderWidth: 1, borderColor: colors.line }}><Text style={{ color: colors.ink, fontWeight: '700' }}>False alarm</Text></Pressable>
            <Pressable disabled={action.isPending} onPress={() => { setBusyId(leak.id); action.mutate({ id: leak.id, name: 'resolve' }); }} style={{ flex: 1, alignItems: 'center', borderRadius: 8, padding: 11, borderWidth: 1, borderColor: colors.line }}><Text style={{ color: colors.ink, fontWeight: '700' }}>Mark fixed</Text></Pressable>
          </View>
        </View>}
      </Card>;
    })}
  </Page>;
}