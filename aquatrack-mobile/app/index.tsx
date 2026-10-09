import { Redirect } from 'expo-router';
import { ActivityIndicator, View } from 'react-native';
import { colors } from '@/constants/theme';
import { useSessionStore } from '@/store/session';

export default function IndexRoute() {
  const hydrated = useSessionStore((state) => state.hydrated);
  const user = useSessionStore((state) => state.user);
  if (!hydrated) return <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.canvas }}><ActivityIndicator color={colors.ocean} /></View>;
  return <Redirect href={user ? '/(tabs)' : '/login'} />;
}