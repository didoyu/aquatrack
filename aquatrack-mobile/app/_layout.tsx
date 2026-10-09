import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { ActivityIndicator, View } from 'react-native';
import 'react-native-reanimated';

import { colors } from '@/constants/theme';
import { useSessionStore } from '@/store/session';

export {
  // Catch any errors thrown by the Layout component.
  ErrorBoundary,
} from 'expo-router';

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
});

export default function RootLayout() {
  const hydrate = useSessionStore((state) => state.hydrate);
  const hydrated = useSessionStore((state) => state.hydrated);

  useEffect(() => { void hydrate(); }, [hydrate]);

  return (
    <QueryClientProvider client={queryClient}>
      <StatusBar style="dark" />
      {!hydrated ? (
        <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.canvas }}>
          <ActivityIndicator color={colors.ocean} size="large" />
        </View>
      ) : (
      <Stack>
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen name="login" options={{ headerShown: false }} />
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      </Stack>
      )}
    </QueryClientProvider>
  );
}
