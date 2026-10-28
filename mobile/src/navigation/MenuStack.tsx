import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { ProductDetailScreen } from "../screens/customer/ProductDetailScreen";
import { MenuScreen } from "../screens/customer/MenuScreen";
import { colors } from "../theme";

export type MenuStackParamList = {
  MenuList: undefined;
  ProductDetail: { productId: string; name: string };
};

const Stack = createNativeStackNavigator<MenuStackParamList>();

export function MenuStack() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.surface },
        headerTintColor: colors.terracotta,
        headerTitleStyle: { color: colors.text },
        contentStyle: { backgroundColor: colors.cream },
      }}
    >
      <Stack.Screen name="MenuList" component={MenuScreen} options={{ title: "Our menu" }} />
      <Stack.Screen name="ProductDetail" component={ProductDetailScreen} options={({ route }) => ({ title: route.params.name })} />
    </Stack.Navigator>
  );
}
