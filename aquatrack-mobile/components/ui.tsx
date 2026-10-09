import { ReactNode } from 'react';
import { ActivityIndicator, Pressable, RefreshControlProps, ScrollView, StyleProp, StyleSheet, Text, View, ViewStyle } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors } from '@/constants/theme';

export function Page({ children, refreshControl }: { children: ReactNode; refreshControl?: React.ReactElement<RefreshControlProps> }) {
  return <SafeAreaView style={styles.safe} edges={['top']}><ScrollView contentContainerStyle={styles.page} refreshControl={refreshControl} keyboardShouldPersistTaps="handled">{children}</ScrollView></SafeAreaView>;
}

export function PageHeading({ title, subtitle, eyebrow, action }: { title: string; subtitle?: string; eyebrow?: string; action?: ReactNode }) {
  return <View style={styles.heading}><View style={{ flex: 1 }}>{eyebrow && <Text style={styles.eyebrow}>{eyebrow}</Text>}<Text style={styles.title}>{title}</Text>{subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}</View>{action}</View>;
}

export function Card({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) { return <View style={[styles.card, style]}>{children}</View>; }

export function StatCard({ label, value, icon, highlight = false }: { label: string; value: string; icon: keyof typeof MaterialCommunityIcons.glyphMap; highlight?: boolean }) {
  return <View style={[styles.stat, highlight && styles.statHighlight]}><MaterialCommunityIcons name={icon} size={20} color={highlight ? '#d6faff' : colors.ocean} /><Text style={[styles.statLabel, highlight && { color: '#d6faff' }]}>{label}</Text><Text adjustsFontSizeToFit numberOfLines={1} style={[styles.statValue, highlight && { color: '#ffffff' }]}>{value}</Text></View>;
}

export function Pill({ label, tone = 'neutral' }: { label: string; tone?: 'neutral' | 'positive' | 'warning' | 'critical' }) {
  const toneStyle = tone === 'positive' ? styles.positivePill : tone === 'warning' ? styles.warningPill : tone === 'critical' ? styles.criticalPill : styles.neutralPill;
  const textColor = tone === 'positive' ? colors.positive : tone === 'warning' ? colors.warning : tone === 'critical' ? colors.critical : colors.muted;
  return <View style={[styles.pill, toneStyle]}><Text style={[styles.pillText, { color: textColor }]}>{label}</Text></View>;
}

export function PrimaryButton({ label, onPress, disabled = false }: { label: string; onPress: () => void; disabled?: boolean }) {
  return <Pressable accessibilityRole="button" onPress={onPress} disabled={disabled} style={({ pressed }) => [styles.primaryButton, (pressed || disabled) && { opacity: .75 }]}><Text style={styles.primaryButtonText}>{label}</Text></Pressable>;
}

export function LoadingState({ label }: { label: string }) { return <SafeAreaView style={styles.loading}><ActivityIndicator color={colors.ocean} size="large" /><Text style={styles.subtitle}>{label}</Text></SafeAreaView>; }
export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) { return <SafeAreaView style={styles.loading}><MaterialCommunityIcons name="cloud-alert-outline" size={32} color={colors.critical} /><Text style={styles.errorText}>{message}</Text><Pressable accessibilityRole="button" onPress={onRetry}><Text style={{ color: colors.ocean, fontWeight: '700' }}>Try again</Text></Pressable></SafeAreaView>; }

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.canvas },
  page: { paddingHorizontal: 18, paddingTop: 18, paddingBottom: 28, gap: 14 },
  heading: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginBottom: 3 },
  eyebrow: { color: colors.ocean, fontSize: 10, fontWeight: '800', letterSpacing: 1.1, marginBottom: 6 },
  title: { color: colors.ink, fontSize: 25, fontWeight: '800' },
  subtitle: { color: colors.muted, fontSize: 13, lineHeight: 19, marginTop: 4 },
  card: { padding: 16, borderRadius: 10, borderWidth: 1, borderColor: colors.line, backgroundColor: colors.surface },
  stat: { flexGrow: 1, flexBasis: '47%', minWidth: 145, minHeight: 120, padding: 14, borderRadius: 10, borderWidth: 1, borderColor: colors.line, backgroundColor: colors.surface, justifyContent: 'space-between' },
  statHighlight: { borderColor: colors.ocean, backgroundColor: colors.ocean },
  statLabel: { color: colors.muted, fontSize: 12, fontWeight: '600', marginTop: 8 },
  statValue: { color: colors.ink, fontSize: 19, fontWeight: '800', marginTop: 3 },
  pill: { alignSelf: 'flex-start', borderRadius: 99, paddingHorizontal: 9, paddingVertical: 5 },
  neutralPill: { backgroundColor: '#edf2f4' }, positivePill: { backgroundColor: colors.positiveLight }, warningPill: { backgroundColor: colors.warningLight }, criticalPill: { backgroundColor: colors.criticalLight },
  pillText: { fontSize: 11, fontWeight: '700', textTransform: 'capitalize' },
  primaryButton: { minHeight: 44, alignItems: 'center', justifyContent: 'center', borderRadius: 8, backgroundColor: colors.ocean, paddingHorizontal: 16 },
  primaryButtonText: { color: '#ffffff', fontWeight: '800', fontSize: 14 },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12, backgroundColor: colors.canvas, padding: 24 },
  errorText: { color: colors.critical, textAlign: 'center', fontSize: 14 },
});