import { StyleSheet, Text, View } from "react-native";
import { colors, radius, shadow, spacing, typography } from "../theme";

export interface Bar {
  label: string;
  value: number;
  text: string;
}

export function BarList({ title, bars }: { title: string; bars: Bar[] }) {
  const max = Math.max(1, ...bars.map((b) => b.value));
  return (
    <View style={styles.card}>
      <Text style={typography.heading}>{title}</Text>
      {bars.length === 0 ? <Text style={typography.caption}>No data for this period.</Text> : null}
      {bars.map((b) => (
        <View key={b.label} style={styles.row}>
          <View style={styles.labels}>
            <Text style={typography.body} numberOfLines={1}>{b.label}</Text>
            <Text style={styles.value}>{b.text}</Text>
          </View>
          <View style={styles.track}>
            <View style={[styles.fill, { width: `${Math.max(2, Math.round((b.value / max) * 100))}%` as `${number}%` }]} />
          </View>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: colors.card, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.md, ...shadow.card },
  row: { gap: spacing.xs },
  labels: { flexDirection: "row", justifyContent: "space-between", gap: spacing.md },
  value: { ...typography.body, color: colors.terracotta, fontWeight: "700" },
  track: { height: 8, borderRadius: radius.pill, backgroundColor: colors.saffronSoft, overflow: "hidden" },
  fill: { height: 8, borderRadius: radius.pill, backgroundColor: colors.terracotta },
});
