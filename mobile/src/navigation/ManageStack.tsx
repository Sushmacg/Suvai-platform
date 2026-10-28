import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { AdminExpensesScreen } from "../screens/admin/AdminExpensesScreen";
import { AdminLocationsScreen } from "../screens/admin/AdminLocationsScreen";
import { AdminSessionsScreen } from "../screens/admin/AdminSessionsScreen";
import { AdminStockScreen } from "../screens/admin/AdminStockScreen";
import { ManageHomeScreen } from "../screens/admin/ManageHomeScreen";
import { colors } from "../theme";

export type ManageStackParamList = {
  ManageHome: undefined;
  Sessions: undefined;
  Stock: undefined;
  Expenses: undefined;
  Locations: undefined;
};

const Stack = createNativeStackNavigator<ManageStackParamList>();

export function ManageStack() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.surface },
        headerTintColor: colors.terracotta,
        headerTitleStyle: { color: colors.text },
        contentStyle: { backgroundColor: colors.cream },
      }}
    >
      <Stack.Screen name="ManageHome" component={ManageHomeScreen} options={{ title: "Manage" }} />
      <Stack.Screen name="Sessions" component={AdminSessionsScreen} options={{ title: "Stall sessions" }} />
      <Stack.Screen name="Stock" component={AdminStockScreen} options={{ title: "Stock" }} />
      <Stack.Screen name="Expenses" component={AdminExpensesScreen} options={{ title: "Expenses" }} />
      <Stack.Screen name="Locations" component={AdminLocationsScreen} options={{ title: "Locations" }} />
    </Stack.Navigator>
  );
}