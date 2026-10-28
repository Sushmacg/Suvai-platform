import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { colors, spacing, typography } from "../theme";
import { Button } from "./Button";

export function LoadingView() {
  return (
    <View style={styles.center}>
      <ActivityIndicator size="large" color={colors.terracotta} />
    </View>
  );
}

export function EmptyView({ title, hint }: { title: string; hint?: string }) {
  return (
    <View style={styles.center}>
      <Text style={typography.heading}>{title}</Text>
      {hint ? <Text style={[typography.caption, styles.text]}>{hint}</Text> : null}
    </View>
  );
}

export function ErrorView({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <View style={styles.center}>
      <Text style={[typography.body, styles.error]}>{message}</Text>
      <Button title="Try again" onPress={onRetry} />
    </View>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl, gap: spacing.lg },
  text: { textAlign: "center" },
  error: { color: colors.danger, textAlign: "center" },
});
