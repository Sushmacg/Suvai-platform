import { useCallback, useRef, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { api } from "../../api/client";
import type { AnalyticsSummary } from "../../api/models";
import { Screen } from "../../components/Screen";
import { ErrorView, LoadingView } from "../../components/States";
import { useLoad } from "../../hooks/useLoad";
import { rupees } from "../../utils/format";
import { colors, radius, shadow, spacing, typography } from "../../theme";

const RANGES = [7, 30, 90];

function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <View style={styles.stat}>
      <Text style={typography.caption}>{label}</Text>
      <Text style={[styles.statValue, tone ? { color: tone } : null]}>{value}</Text>
    </View>
  );
}

export function DashboardScreen() {
  const [days, setDays] = useState(7);
  const { data, loading, error, reload, refresh } = useLoad(
    () => api.get<AnalyticsSummary>("/analytics/summary", { query: { days } }),
    [days],
  );

  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;
  useFocusEffect(
    useCallback(() => {
      refreshRef.current();
    }, []),
  );

  return (
    <Screen>
      <Text style={typography.title}>Dashboard</Text>
      <View style={styles.chips}>
        {RANGES.map((d) => (
          <Pressable key={d} onPress={() => setDays(d)} style={[styles.chip, days === d && styles.chipOn]}>
            <Text style={[styles.chipText, days === d && styles.chipTextOn]}>{d} days</Text>
          </Pressable>
        ))}
      </View>
      {loading ? <LoadingView /> : error || !data ? (
        <ErrorView message={error ?? "Could not load analytics."} onRetry={reload} />
      ) : (
        <>
          <Text style={typography.caption}>{data.from} to {data.to}</Text>
          <View style={styles.grid}>
            <Stat label="Revenue" value={rupees(data.revenue)} />
            <Stat label="Profit" value={rupees(data.profit)} tone={data.profit < 0 ? colors.danger : colors.success} />
            <Stat label="Expenses" value={rupees(data.expenses)} />
            <Stat label="Orders" value={String(data.orders)} />
            <Stat label="Sold" value={`${data.sold} / ${data.stocked}`} />
            <Stat label="Wasted" value={String(data.wasted)} />
            <Stat label="Sell-through" value={`${Math.round(data.sell_through * 100)}%`} />
          </View>
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  chips: { flexDirection: "row", gap: spacing.sm },
  chip: { paddingVertical: spacing.sm, paddingHorizontal: spacing.lg, borderRadius: radius.pill, borderWidth: 1.5, borderColor: colors.terracotta },
  chipOn: { backgroundColor: colors.terracotta },
  chipText: { ...typography.body, color: colors.terracotta, fontWeight: "600" },
  chipTextOn: { color: "#FFFFFF" },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: spacing.md },
  stat: { width: "47%", backgroundColor: colors.card, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.xs, ...shadow.card },
  statValue: { fontSize: 22, fontWeight: "700", color: colors.text },
});
