import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { useAuth } from "../auth/AuthContext";
import { Button } from "../components/Button";
import { LoginScreen } from "../screens/auth/LoginScreen";
import { RegisterScreen } from "../screens/auth/RegisterScreen";
import { PlaceholderScreen } from "../screens/common/PlaceholderScreen";
import { ProfileScreen } from "../screens/common/ProfileScreen";
import { colors, spacing, typography } from "../theme";
import type { AuthStackParamList } from "./types";

const AuthStack = createNativeStackNavigator<AuthStackParamList>();
const Tabs = createBottomTabNavigator();

const tabOptions = {
  headerShown: false,
  tabBarActiveTintColor: colors.terracotta,
  tabBarInactiveTintColor: colors.muted,
  tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border },
  tabBarIconStyle: { display: "none" as const },
  tabBarLabelStyle: { fontSize: 14, fontWeight: "600" as const, paddingBottom: 10 },
};

const Menu = () => <PlaceholderScreen title="Menu" />;
const MyOrders = () => <PlaceholderScreen title="My orders" />;
const Dashboard = () => <PlaceholderScreen title="Dashboard" />;
const AdminOrders = () => <PlaceholderScreen title="Orders" />;

function CustomerTabs() {
  return (
    <Tabs.Navigator screenOptions={tabOptions}>
      <Tabs.Screen name="Menu" component={Menu} />
      <Tabs.Screen name="Orders" component={MyOrders} />
      <Tabs.Screen name="Profile" component={ProfileScreen} />
    </Tabs.Navigator>
  );
}

function AdminTabs() {
  return (
    <Tabs.Navigator screenOptions={tabOptions}>
      <Tabs.Screen name="Dashboard" component={Dashboard} />
      <Tabs.Screen name="Orders" component={AdminOrders} />
      <Tabs.Screen name="Profile" component={ProfileScreen} />
    </Tabs.Navigator>
  );
}

function Message({ text, action }: { text: string; action?: { title: string; onPress: () => void } }) {
  return (
    <View style={styles.center}>
      <Text style={styles.brand}>Suvai</Text>
      <Text style={styles.text}>{text}</Text>
      {action ? <Button title={action.title} onPress={action.onPress} /> : null}
    </View>
  );
}

export function RootNavigator() {
  const { status, user, retry, logout } = useAuth();

  if (status === "loading") {
    return (
      <View style={styles.center}>
        <Text style={styles.brand}>Suvai</Text>
        <ActivityIndicator size="large" color={colors.terracotta} />
      </View>
    );
  }
  if (status === "unreachable") {
    return <Message text="Could not reach the server. Check your Wi-Fi and try again." action={{ title: "Try again", onPress: retry }} />;
  }
  if (status === "signedOut" || !user) {
    return (
      <AuthStack.Navigator screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.cream } }}>
        <AuthStack.Screen name="Login" component={LoginScreen} />
        <AuthStack.Screen name="Register" component={RegisterScreen} />
      </AuthStack.Navigator>
    );
  }
  if (user.role === "admin") return <AdminTabs />;
  if (user.role === "customer") return <CustomerTabs />;
  return <Message text="This account role is not supported in the app." action={{ title: "Log out", onPress: logout }} />;
}

const styles = StyleSheet.create({
  center: { flex: 1, backgroundColor: colors.cream, alignItems: "center", justifyContent: "center", padding: spacing.xl, gap: spacing.lg },
  brand: { ...typography.title, color: colors.terracotta, fontSize: 40 },
  text: { ...typography.body, textAlign: "center" },
});
