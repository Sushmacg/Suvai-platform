import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { api } from "../../api/client";
import type { ForecastItem, ForecastResponse, Location, Product } from "../../api/models";
import { Screen } from "../../components/Screen";
import { EmptyView, ErrorView, LoadingView } from "../../components/States";
import { useLoad } from "../../hooks/useLoad";
import { colors, radius, shadow, spacing, typography } from "../../theme";

const OPTIONS = [
  { label: "Today", offset: 0 },
  { label: "Tomorrow", offset: 1 },
  { label: "In 2 days", offset: 2 },
  { label: "In 3 days", offset: 3 },
];

function isoDay(offset: number): string {
  const d = new Date();
  d.setDate(d.getDate() + offset);
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

export function ForecastScreen() {
  const [offset, setOffset] = useState(1);
  const { data, loading, error, reload } = useLoad(async () => {
    const [forecast, products, locations] = await Promise.all([
      api.get<ForecastResponse>("/forecasts", { query: { date: isoDay(offset) } }),
      api.get<Product[]>("/products/admin/all"),
      api.get<Location[]>("/stalls/locations/all"),
    ]);
    const productName = new Map(products.map((p) => [p.id, p.name]));
    const locationName = new Map(locations.map((l) => [l.id, l.name]));
    const groups = new Map<string, ForecastItem[]>();
    for (const item of forecast.items) {
      const list = groups.get(item.location_id) ?? [];
      list.push(item);
      groups.set(item.location_id, list);
    }
    const cards = [...groups.entries()].map(([id, items]) => ({
      id,
      name: locationName.get(id) ?? "Unknown location",
      total: items.reduce((s, i) => s + i.predicted_units, 0),
      rows: [...items]
        .sort((a, b) => b.predicted_units - a.predicted_units)
        .map((i) => ({ key: i.product_id, name: productName.get(i.product_id) ?? "Unknown product", units: i.predicted_units })),
    }));
    return { forecast, cards };
  }, [offset]);

  return (
    <Screen>
      <Text style={typography.title}>Forecast</Text>
      <View style={styles.chips}>
        {OPTIONS.map((o) => (
          <Pressable key={o.offset} onPress={() => setOffset(o.offset)} style={[styles.chip, offset === o.offset && styles.chipOn]}>
            <Text style={[styles.chipText, offset === o.offset && styles.chipTextOn]}>{o.label}</Text>
          </Pressable>
        ))}
      </View>
      {loading ? (
        <LoadingView />
      ) : error || !data ? (
        <ErrorView message={error ?? "Could not load the forecast."} onRetry={reload} />
      ) : data.cards.length === 0 ? (
        <EmptyView title="No forecast available" hint="There are no active locations or products to forecast." />
      ) : (
        <>
          <Text style={typography.caption}>
            {data.forecast.forecast_date} · model {data.forecast.model_version}
          </Text>
          {data.cards.map((c) => (
            <View key={c.id} style={styles.card}>
              <View style={styles.head}>
                <Text style={typography.heading}>{c.name}</Text>
                <Text style={styles.total}>{c.total.toFixed(0)} units</Text>
              </View>
              {c.rows.map((r) => (
                <View key={r.key} style={styles.row}>
                  <Text style={typography.body}>{r.name}</Text>
                  <Text style={styles.units}>{r.units.toFixed(1)}</Text>
                </View>
              ))}
            </View>
          ))}
          <Text style={typography.caption}>
            Units expected to sell. Sales are capped by stock, so demand may be higher for products that sell out.
          </Text>
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  chip: { paddingVertical: spacing.sm, paddingHorizontal: spacing.lg, borderRadius: radius.pill, borderWidth: 1.5, borderColor: colors.terracotta },
  chipOn: { backgroundColor: colors.terracotta },
  chipText: { ...typography.body, color: colors.terracotta, fontWeight: "600" },
  chipTextOn: { color: "#FFFFFF" },
  card: { backgroundColor: colors.card, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.sm, ...shadow.card },
  head: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  total: { ...typography.body, color: colors.terracotta, fontWeight: "700" },
  row: { flexDirection: "row", justifyContent: "space-between" },
  units: { ...typography.body, fontWeight: "700" },
});
