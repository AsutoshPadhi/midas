import * as AuthSession from 'expo-auth-session';
import * as WebBrowser from 'expo-web-browser';
import { router } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { APP_CONFIG } from '../../constants/config';
import { setAccessToken } from '../../services/api';
import { useAuthStore } from '../../store/auth.store';

WebBrowser.maybeCompleteAuthSession();

function extractNextUrlFromHtml(html: string, baseUrl: string): string | null {
  const patterns = [
    /window\.location(?:\.href)?\s*=\s*['\"]([^'\"]+)['\"]/i,
    /location(?:\.href)?\s*=\s*['\"]([^'\"]+)['\"]/i,
    /<meta[^>]+http-equiv=['\"]refresh['\"][^>]+content=['\"][^'\"]*url=([^'\">\s]+)[^'\"]*['\"]/i,
    /href=['\"]([^'\"]+)['\"]/i,
    /((?:https?:\/\/|midasapp:\/\/)[^\s'\"<>]+)/i,
  ];

  for (const pattern of patterns) {
    const match = html.match(pattern);
    const candidate = match?.[1] ?? match?.[0];

    if (!candidate) {
      continue;
    }

    try {
      return new URL(candidate, baseUrl).toString();
    } catch {
      // Continue searching if one candidate is not a valid URL.
    }
  }

  return null;
}

async function resolveIntermediateAuthUrl(url: string): Promise<string | null> {
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'text/html,application/xhtml+xml',
      },
    });

    if (!response.ok) {
      return null;
    }

    const html = await response.text();
    return extractNextUrlFromHtml(html, url);
  } catch {
    return null;
  }
}

async function resolveAuthorizationUrl(loginUrl: string): Promise<string | null> {
  try {
    const response = await fetch(loginUrl, {
      method: 'GET',
      headers: {
        Accept: 'application/json,text/html',
      },
    });

    const contentType = response.headers.get('content-type') ?? '';
    if (contentType.includes('application/json')) {
      const data = (await response.json()) as {
        authorization_url?: string;
        auth_url?: string;
        url?: string;
      };

      return data.authorization_url ?? data.auth_url ?? data.url ?? null;
    }

    if (response.ok) {
      const html = await response.text();
      return extractNextUrlFromHtml(html, loginUrl);
    }

    return null;
  } catch {
    return null;
  }
}

function readTokenFromCallback(url: string): string | null {
  const parsed = new URL(url);
  const queryToken =
    parsed.searchParams.get('access_token') ??
    parsed.searchParams.get('token') ??
    parsed.searchParams.get('jwt');

  if (queryToken) {
    return queryToken;
  }

  const hash = parsed.hash.startsWith('#') ? parsed.hash.slice(1) : parsed.hash;
  const hashParams = new URLSearchParams(hash);

  return hashParams.get('access_token') ?? hashParams.get('token') ?? hashParams.get('jwt');
}

export default function LoginScreen() {
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const setStoreAccessToken = useAuthStore((state) => state.setAccessToken);

  const handleOAuthLogin = async () => {
    setLoading(true);
    setErrorMessage(null);

    try {
      const redirectUri =
        Platform.OS === 'web'
          ? AuthSession.makeRedirectUri({ path: 'auth/callback' })
          : AuthSession.makeRedirectUri({
              scheme: 'midasapp',
              path: 'auth/callback',
            });

      const loginUrl = `${APP_CONFIG.oauthLoginUrl}?redirect_uri=${encodeURIComponent(redirectUri)}`;

      // On web, use a direct page redirect instead of a popup (no popup-blocker issues).
      // Fetch the authorization_url from the backend first, then redirect.
      if (Platform.OS === 'web') {
        const resolvedAuthUrl = await resolveAuthorizationUrl(loginUrl);
        window.location.href = resolvedAuthUrl ?? loginUrl;
        return;
      }

      const resolvedAuthUrl = await resolveAuthorizationUrl(loginUrl);
      const authUrl = resolvedAuthUrl ?? loginUrl;

      let result = await WebBrowser.openAuthSessionAsync(authUrl, redirectUri);

      if (result.type === 'success' && result.url) {
        const nextUrl = await resolveIntermediateAuthUrl(result.url);
        if (nextUrl && nextUrl !== result.url) {
          result = await WebBrowser.openAuthSessionAsync(nextUrl, redirectUri);
        }
      }

      if (result.type !== 'success' || !result.url) {
        setErrorMessage('Login was cancelled or did not complete.');
        return;
      }

      const callbackToken = readTokenFromCallback(result.url);

      if (callbackToken) {
        await setAccessToken(callbackToken);
        setStoreAccessToken(callbackToken);
      }

      router.replace('/(tabs)');
    } catch {
      setErrorMessage('Unable to complete login. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Welcome to Midas</Text>
      <Text style={styles.subtitle}>Sign in to continue to your dashboard.</Text>

      <Pressable disabled={loading} onPress={handleOAuthLogin} style={styles.button}>
        {loading ? <ActivityIndicator color="#F7F5F0" /> : <Text style={styles.buttonText}>Continue with OAuth</Text>}
      </Pressable>

      {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
    backgroundColor: '#F7F5F0',
    gap: 12,
  },
  title: {
    fontSize: 26,
    fontWeight: '700',
    color: '#1B5E3A',
  },
  subtitle: {
    fontSize: 16,
    color: '#2E3F34',
    textAlign: 'center',
    marginBottom: 16,
  },
  button: {
    minWidth: 220,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderRadius: 12,
    backgroundColor: '#1B5E3A',
  },
  buttonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#F7F5F0',
  },
  errorText: {
    marginTop: 12,
    color: '#B42318',
    textAlign: 'center',
  },
});
