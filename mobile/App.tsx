import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import { api } from "./src/api/client";
import { API_URL, apiConfigProblem } from "./src/config";
import { colors, radius, spacing, typography } from "./src/theme";

type State = { kind: "loading" } | { kind: "ok" } | { kind: "error"; message: string };

export default function App() {
  const [state, setState] = useState<State>({ kind: "loading" });

  const check = useCallback(async () => {
    const problem = apiConfigProblem();
    if (problem) {
      setState({ kind: "error", message: problem });
      return;
    }
    setState({ kind: "loading" });
    try {
      await api.get("/health", { auth: false });
      setState({ kind: "ok" });
    } catch (e) {
      setState({ kind: "error", message: e instanceof Error ? e.message : "Unknown error" });
    }
  }, []);

  useEffect(() => {
    check();
  }, [check]);

  return (
    <View style={styles.screen}>
      <StatusBar style="dark" />
      <Text style={styles.brand}>Suvai</Text>
      {state.kind === "loading" && <ActivityIndicator size="large" color={colors.terracotta} />}
      {state.kind === "ok" && <Text style={styles.ok}>Connected to the server</Text>}
      {state.kind === "error" && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{state.message}</Text>
          <Pressable style={styles.button} onPress={check}>
            <Text style={typography.button}>Try again</Text>
          </Pressable>
        </View>
      )}
      <Text style={styles.caption}>{API_URL || "No API address set"}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.cream,
    alignItems: "center",
    justifyContent: "center",
    padding: spacing.xl,
    gap: spacing.lg,
  },
  brand: { ...typography.title, color: colors.terracotta, fontSize: 40 },
  ok: { ...typography.heading, color: colors.success },
  errorBox: { alignItems: "center", gap: spacing.md },
  errorText: { ...typography.body, color: colors.danger, textAlign: "center" },
  button: {
    backgroundColor: colors.terracotta,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.xl,
    borderRadius: radius.pill,
  },
  caption: typography.caption,
});