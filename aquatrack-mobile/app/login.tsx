import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Redirect, router } from 'expo-router';
import { Image, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { api, errorMessage } from '@/api/client';
import { PrimaryButton } from '@/components/ui';
import { colors } from '@/constants/theme';
import { useSessionStore, User } from '@/store/session';

type AuthResponse = { access: string; refresh: string; user: User };

export default function LoginScreen() {
  const hydrated = useSessionStore((state) => state.hydrated);
  const user = useSessionStore((state) => state.user);
  const setSession = useSessionStore((state) => state.setSession);
  const queryClient = useQueryClient();
  const [register, setRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [householdName, setHouseholdName] = useState('My Home');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  if (hydrated && user) return <Redirect href="/(tabs)" />;

  async function submit() {
    setError('');
    setBusy(true);
    try {
      const response = await api.post<AuthResponse>(register ? '/auth/register/' : '/auth/login/', register
        ? { email: email.trim(), password, first_name: firstName.trim(), last_name: lastName.trim(), household_name: householdName.trim() || 'My Home' }
        : { email: email.trim(), password });
      queryClient.clear();
      await setSession(response.data.access, response.data.refresh, response.data.user);
      router.replace('/(tabs)');
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  return <SafeAreaView style={styles.safe}><KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
    <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <Image source={require('../assets/images/aquatrack-logo.png')} style={styles.logo} resizeMode="contain" accessibilityLabel="AquaTrack water logo" />
      <Text style={styles.brand}>AquaTrack</Text>
      <Text style={styles.subtitle}>Your home water, in view.</Text>
      <View style={styles.form}>
        <Text style={styles.title}>{register ? 'Create your account' : 'Welcome back'}</Text>
        <Text style={styles.helper}>{register ? 'Set up your household monitoring.' : 'Sign in to see your latest water readings.'}</Text>
        {register && <>
          <TextInput style={styles.input} placeholder="First name" placeholderTextColor={colors.muted} value={firstName} onChangeText={setFirstName} autoCapitalize="words" />
          <TextInput style={styles.input} placeholder="Last name" placeholderTextColor={colors.muted} value={lastName} onChangeText={setLastName} autoCapitalize="words" />
          <TextInput style={styles.input} placeholder="Household name" placeholderTextColor={colors.muted} value={householdName} onChangeText={setHouseholdName} />
        </>}
        <TextInput style={styles.input} placeholder="Email address" placeholderTextColor={colors.muted} value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" autoComplete="email" />
        <TextInput style={styles.input} placeholder="Password" placeholderTextColor={colors.muted} value={password} onChangeText={setPassword} secureTextEntry autoComplete={register ? 'new-password' : 'current-password'} />
        {!!error && <Text accessibilityRole="alert" style={styles.error}>{error}</Text>}
        <PrimaryButton label={busy ? 'Please wait…' : register ? 'Create account' : 'Sign in'} onPress={() => void submit()} disabled={busy || !email || !password || (register && (!firstName || !lastName))} />
        <Pressable onPress={() => { setRegister(!register); setError(''); }} style={styles.switchMode}><Text style={styles.switchText}>{register ? 'Already have an account? ' : 'New to AquaTrack? '}<Text style={{ color: colors.ocean, fontWeight: '800' }}>{register ? 'Sign in' : 'Create account'}</Text></Text></Pressable>
      </View>
      <Text style={styles.footer}>AquaTrack · Water monitoring for your household</Text>
    </ScrollView>
  </KeyboardAvoidingView></SafeAreaView>;
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.canvas },
  content: { flexGrow: 1, justifyContent: 'center', padding: 22 },
  logo: { width: 58, height: 64, marginBottom: 13 },
  brand: { color: colors.ink, fontSize: 29, fontWeight: '900' },
  subtitle: { color: colors.muted, fontSize: 15, marginTop: 4, marginBottom: 26 },
  form: { gap: 12, padding: 18, borderRadius: 12, borderWidth: 1, borderColor: colors.line, backgroundColor: colors.surface },
  title: { color: colors.ink, fontSize: 21, fontWeight: '800' },
  helper: { color: colors.muted, fontSize: 13, marginTop: -7, marginBottom: 4 },
  input: { minHeight: 48, paddingHorizontal: 13, borderWidth: 1, borderColor: colors.line, borderRadius: 8, backgroundColor: '#fbfefe', color: colors.ink, fontSize: 15 },
  error: { color: colors.critical, fontSize: 13 },
  switchMode: { alignItems: 'center', paddingVertical: 7 },
  switchText: { color: colors.muted, fontSize: 13 },
  footer: { marginTop: 22, color: colors.muted, textAlign: 'center', fontSize: 11 },
});