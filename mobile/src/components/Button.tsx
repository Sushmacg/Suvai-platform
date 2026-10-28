import { ActivityIndicator, Pressable, StyleSheet, Text } from "react-native";
import { colors, radius, spacing, typography } from "../theme";

interface Props {
  title: string;
  onPress: () => void;
  loading?: boolean;
  disabled?: boolean;
  variant?: "primary" | "secondary";
}

export function Button({ title, onPress, loading = false, disabled = false, variant = "primary" }: Props) {
  const inactive = disabled || loading;
  const primary = variant === "primary";
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: inactive, busy: loading }}
      disabled={inactive}
      onPress={onPress}
      style={({ pressed }) => [
        styles.base,
        primary ? styles.primary : styles.secondary,
        inactive && styles.inactive,
        pressed && styles.pressed,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={primary ? "#FFFFFF" : colors.terracotta} />
      ) : (
        <Text style={[typography.button, !primary && { color: colors.terracotta }]}>{title}</Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    minHeight: 50,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.xl,
  },
  primary: { backgroundColor: colors.terracotta },
  secondary: { backgroundColor: "transparent", borderWidth: 1.5, borderColor: colors.terracotta },
  inactive: { opacity: 0.55 },
  pressed: { transform: [{ scale: 0.98 }], opacity: 0.9 },
});
