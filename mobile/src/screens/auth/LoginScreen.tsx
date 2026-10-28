import { useState } from "react";
import { StyleSheet, Text } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useAuth } from "../../auth/AuthContext";
import { Button } from "../../components/Button";
import { Screen } from "../../components/Screen";
import { TextField } from "../../components/TextField";
import type { AuthStackParamList } from "../../navigation/types";
import { colors, spacing, typography } from "../../theme";

type Props = NativeStackScreenProps<AuthStackParamList, "Login">;

export function LoginScreen({ navigation }: Props) {
  const { login } = useAuth();
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!phone.trim() || !password) {
      setError("Enter your phone number and password.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await login({ phone: phone.trim(), password });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
      setBusy(false);
    }
  };

  return (
    <Screen>
      <Text style={styles.brand}>Suvai</Text>
      <Text style={styles.subtitle}>Fresh nankhatai, baked with love</Text>
      <TextField
        label="Phone number"
        value={phone}
        onChangeText={setPhone}
        keyboardType="phone-pad"
        autoCapitalize="none"
        placeholder="Your phone number"
      />
      <TextField
        label="Password"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        autoCapitalize="none"
        placeholder="Your password"
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <Button title="Log in" onPress={submit} loading={busy} />
      <Button title="Create an account" variant="secondary" onPress={() => navigation.navigate("Register")} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  brand: { ...typography.title, color: colors.terracotta, fontSize: 40, marginTop: spacing.xxl },
  subtitle: { ...typography.caption, marginBottom: spacing.lg },
  error: { ...typography.body, color: colors.danger },
});
