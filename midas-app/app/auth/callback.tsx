import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect } from 'react';
import { Platform, ActivityIndicator, StyleSheet, View } from 'react-native';
import { setAccessToken } from '../../services/api';
import { authService } from '../../services/auth.service';
import { useAuthStore } from '../../store/auth.store';

function readTokenFromCurrentUrl(): string | null {
  if (Platform.OS !== 'web' || typeof window === 'undefined') {
    return null;
  }
  const hash = window.location.hash.startsWith('#')
    ? window.location.hash.slice(1)
    : window.location.hash;
  const hashParams = new URLSearchParams(hash);
  return (
    hashParams.get('access_token') ??
    hashParams.get('token') ??
    hashParams.get('jwt')
  );
}

export default function AuthCallbackScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ access_token?: string; token?: string; jwt?: string }>();
  const setStoreAccessToken = useAuthStore((state) => state.setAccessToken);

  useEffect(() => {
    const bootstrap = async () => {
      const tempToken =
        params.access_token ??
        params.token ??
        params.jwt ??
        readTokenFromCurrentUrl();

      console.log('[callback] temp token found:', tempToken ? `${tempToken.slice(0, 20)}…` : 'NONE');

      if (tempToken) {
        try {
          // Exchange the temporary token for a JWT
          const { accessToken, user } = await authService.exchangeToken(tempToken);
          console.log('[callback] jwt received:', `${accessToken.slice(0, 20)}…`);
          
          await setAccessToken(accessToken);
          setStoreAccessToken(accessToken);
          if (user) {
            setStoreAccessToken(accessToken);
            useAuthStore.getState().setUser(user);
          }
          router.replace('/(tabs)');
        } catch (err) {
          console.error('[callback] exchange failed:', err);
          router.replace('/auth/login');
        }
      } else {
        router.replace('/auth/login');
      }
    };

    void bootstrap();
  }, [params.access_token, params.jwt, params.token, router, setStoreAccessToken]);

  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color="#1B5E3A" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#F7F5F0',
  },
});
