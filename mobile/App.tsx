import { NavigationContainer, DefaultTheme } from "@react-navigation/native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { AuthProvider } from "./src/auth/AuthContext";
import { RootNavigator } from "./src/navigation/RootNavigator";
import { colors } from "./src/theme";

const navTheme = {
  ...DefaultTheme,
  colors: { ...DefaultTheme.colors, background: colors.cream, card: colors.surface, text: colors.text, primary: colors.terracotta, border: colors.border },
};

export default function App() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <NavigationContainer theme={navTheme}>
          <StatusBar style="dark" />
          <RootNavigator />
        </NavigationContainer>
      </AuthProvider>
    </SafeAreaProvider>
  );
}
