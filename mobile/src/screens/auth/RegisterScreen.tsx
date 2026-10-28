import { useState } from "react";
import { StyleSheet, Text } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useAuth } from "../../auth/AuthContext";
import { Button } from "../../components/Button";
import { Screen } from "../../components/Screen";
import { TextField } from "../../components/TextField";
import type { AuthStackParamList } from "../../navigation/types";
import { colors, spacing, typography } from "../../theme";

type Props = NativeStackScreenProps<AuthStackParamList, "Register">;

export function RegisterScreen({ navigation }: Props) {
  const { register } = useAuth();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!name.trim() || !phone.trim() || !password) {
      setError("Name, phone number and password are required.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await register({ name: name.trim(), phone: phone.trim(), email: email.trim() || null, password });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
      setBusy(false);
    }
  };

  return (
    <Screen>
      <Text style={styles.title}>Create your account</Text>
      <TextField label="Name" value={name} onChangeText={setName} placeholder="Your name" />
      <TextField
        label="Phone number"
        value={phone}
        onChangeText={setPhone}
        keyboardType="phone-pad"
        autoCapitalize="none"
        placeholder="Your phone number"
      />
      <TextField
        label="Email (optional)"
        value={email}
        onChangeText={setEmail}
        keyboardType="email-address"
        autoCapitalize="none"
        placeholder="you@example.com"
      />
      <TextField
        label="Password"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        autoCapitalize="none"
        placeholder="Choose a password"
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <Button title="Sign up" onPress={submit} loading={busy} />
      <Button title="I already have an account" variant="secondary" onPress={() => navigation.goBack()} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { ...typography.title, marginTop: spacing.lg },
  error: { ...typography.body, color: colors.danger },
});
