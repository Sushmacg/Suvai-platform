import { StyleSheet, Text, TextInput, TextInputProps, View } from "react-native";
import { colors, radius, spacing, typography } from "../theme";

export interface FieldProps extends TextInputProps {
  label: string;
  error?: string | null;
}

export function TextField({ label, error, style, ...rest }: FieldProps) {
  return (
    <View style={styles.wrap}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        placeholderTextColor={colors.muted}
        style={[styles.input, !!error && styles.inputError, style]}
        {...rest}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.xs },
  label: { ...typography.caption, fontWeight: "600" },
  input: {
    minHeight: 50,
    backgroundColor: colors.card,
    borderWidth: 1.5,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.lg,
    fontSize: 16,
    color: colors.text,
  },
  inputError: { borderColor: colors.danger },
  error: { ...typography.caption, color: colors.danger },
});
