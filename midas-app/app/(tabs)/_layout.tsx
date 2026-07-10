import { Tabs } from 'expo-router';
import { Text } from 'react-native';
import Ionicons from '@expo/vector-icons/Ionicons';
import { useAuthStore } from '../../store/auth.store';

function HeaderTitle() {
  const user = useAuthStore((state) => state.user);
  const name = user?.name?.split(' ')[0] || 'there';
  return (
    <Text style={{ fontSize: 18, fontWeight: '700', color: '#1B5E3A' }}>
      Hi {name}
    </Text>
  );
}

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: true,
        headerTitle: () => <HeaderTitle />,
        headerShadowVisible: false,
        headerStyle: { backgroundColor: '#F7F5F0' },
        tabBarActiveTintColor: '#1B5E3A',
        tabBarInactiveTintColor: '#95A39A',
        tabBarShowLabel: false,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="pie-chart" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="expenses"
        options={{
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="wallet" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="settings" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
