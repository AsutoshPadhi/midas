import { Asset } from 'expo-asset';
import { router } from 'expo-router';
import { useEffect, useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { SvgUri } from 'react-native-svg';
import { useAuthStore } from '../store/auth.store';

const STARTUP_DELAY_MS = 1400;

export default function StartupScreen() {
  const logoUri = useMemo(() => Asset.fromModule(require('../assets/exports/icon-master.svg')).uri, []);
  const accessToken = useAuthStore((state) => state.accessToken);

  useEffect(() => {
    const timeout = setTimeout(() => {
      router.replace(accessToken ? '/(tabs)' : '/auth/login');
    }, STARTUP_DELAY_MS);

    return () => clearTimeout(timeout);
  }, [accessToken]);

  return (
    <View style={styles.container}>
      <SvgUri uri={logoUri} width={192} height={192} />
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
