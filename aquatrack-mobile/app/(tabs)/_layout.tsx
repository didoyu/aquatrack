import { Redirect, Tabs } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { ActivityIndicator, View } from 'react-native';
import { colors } from '@/constants/theme';
import { useSessionStore } from '@/store/session';

export default function TabLayout() {
  const hydrated = useSessionStore((state) => state.hydrated);
  const user = useSessionStore((state) => state.user);
  if (!hydrated) return <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}><ActivityIndicator color={colors.ocean} /></View>;
  if (!user) return <Redirect href="/login" />;

  return <Tabs screenOptions={{
    headerShown: false,
    tabBarActiveTintColor: colors.ocean,
    tabBarInactiveTintColor: colors.muted,
    tabBarStyle: { height: 68, paddingTop: 7, paddingBottom: 8, borderTopColor: colors.line, backgroundColor: colors.surface },
    tabBarLabelStyle: { fontSize: 10, fontWeight: '600' },
  }}>
    <Tabs.Screen name="index" options={{ title: 'Home', tabBarIcon: ({ color, size }) => <MaterialCommunityIcons name="water-outline" color={color} size={size} /> }} />
    <Tabs.Screen name="usage" options={{ title: 'Usage', tabBarIcon: ({ color, size }) => <MaterialCommunityIcons name="chart-bar" color={color} size={size} /> }} />
    <Tabs.Screen name="leaks" options={{ title: 'Leaks', tabBarIcon: ({ color, size }) => <MaterialCommunityIcons name="water-alert-outline" color={color} size={size} /> }} />
    <Tabs.Screen name="alerts" options={{ title: 'Alerts', tabBarIcon: ({ color, size }) => <MaterialCommunityIcons name="bell-outline" color={color} size={size} /> }} />
    <Tabs.Screen name="billing" options={{ title: 'Bill', tabBarIcon: ({ color, size }) => <MaterialCommunityIcons name="receipt-text-outline" color={color} size={size} /> }} />
  </Tabs>;
}
