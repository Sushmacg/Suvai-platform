import { useCallback, useRef, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { api } from "../../api/client";
import type { CurrentStall, StockAdmin } from "../../api/models";
import { Button } from "../../components/Button";
import { Screen } from "../../components/Screen";
import { EmptyView, ErrorView, LoadingView } from "../../components/States";
import { TextField } from "../../components/TextField";
import { useLoad } from "../../hooks/useLoad";
import { colors, radius, shadow, spacing, typography } from "../../theme";

const whole = (v: string): number | null => (/^\d+$/.test(v.trim()) ? Number(v.trim()) : null);

function Row({
  item,
  sessionId,
  onDone,
  onError,
}: {
  item: StockAdmin;
  sessionId: string;
  onDone: () => Promise<void>;
  onError: (message: string) => void;
}) {
  const [stock, setStock] = useState("");
  const [waste, setWaste] = useState("");
  const [busy, setBusy] = useState<"stock" | "waste" | null>(null);

  const run = async (kind: "stock" | "waste", call: () => Promise<unknown>, reset: () => void) => {
    setBusy(kind);
    try {
      await call();
      reset();
      await onDone();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setBusy(null);
    }
  };

  const saveStock = () => {
    const n = whole(stock);
    if (n === null) return onError("Enter a whole number for the stocked quantity.");
    run(
      "stock",
      () => api.put(`/inventory/sessions/${sessionId}/products/${item.product_id}`, { stocked_qty: n, min_stock: item.min_stock }),
      () => setStock(""),
    );
  };

  const saveWaste = () => {
    const n = whole(waste);
    if (n === null || n < 1) return onError("Enter a whole number above 0 for waste.");
    run(
      "waste",
      () => api.post(`/inventory/sessions/${sessionId}/products/${item.product_id}/waste`, { quantity: n }),
      () => setWaste(""),
    );
  };

  return (
    <View style={styles.card}>
      <Text style={typography.heading}>{item.product_name}</Text>
      <Text style={typography.body}>
        Stocked {item.stocked_qty} · Sold {item.sold_qty} · Wasted {item.wasted_qty}
      </Text>
      <Text style={[typography.body, { fontWeight: "700", color: item.is_low_stock ? colors.danger : colors.success }]}>
        {item.available_qty} available{item.is_low_stock ? " (low stock)" : ""}
      </Text>
      <TextField label="Set stocked quantity" value={stock} onChangeText={setStock} keyboardType="number-pad" placeholder={String(item.stocked_qty)} />
      <Button title="Save stock" onPress={saveStock} loading={busy === "stock"} disabled={busy === "waste" || !stock.trim()} />
      <TextField label="Record waste" value={waste} onChangeText={setWaste} keyboardType="number-pad" placeholder="Units wasted" />
      <Button title="Record waste" variant="secondary" onPress={saveWaste} loading={busy === "waste"} disabled={busy === "stock" || !waste.trim()} />
    </View>
  );
}

export function AdminStockScreen() {
  const { data, loading, error, reload, refresh } = useLoad(async () => {
    const current = await api.get<CurrentStall>("/stalls/current", { auth: false });
    const stock = current.session ? await api.get<StockAdmin[]>(`/inventory/sessions/${current.session.id}/admin`) : [];
    return { current, stock };
  });
  const [notice, setNotice] = useState<string | null>(null);

  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;
  useFocusEffect(
    useCallback(() => {
      refreshRef.current();
    }, []),
  );

  if (loading) return <LoadingView />;
  if (error || !data) return <ErrorView message={error ?? "Could not load stock."} onRetry={reload} />;

  const session = data.current.session;
  if (!session) return <EmptyView title="No stall session" hint="Create a session first, then set its stock here." />;

  return (
    <Screen>
      <Text style={typography.title}>Stock</Text>
      <View style={styles.sessionCard}>
        <Text style={typography.heading}>{session.location.name}</Text>
        <Text style={typography.caption}>
          {session.session_date} · {session.start_time.slice(0, 5)}–{session.end_time.slice(0, 5)} · {session.status}
        </Text>
      </View>
      {notice ? <Text style={[typography.body, { color: colors.danger }]}>{notice}</Text> : null}
      {data.stock.length === 0 ? <EmptyView title="No stock set" hint="Set quantities for this session's products." /> : null}
      {data.stock.map((s) => (
        <Row
          key={s.product_id}
          item={s}
          sessionId={session.id}
          onDone={async () => {
            setNotice(null);
            await refresh();
          }}
          onError={setNotice}
        />
      ))}
    </Screen>
  );
}

const styles = StyleSheet.create({
  sessionCard: { backgroundColor: colors.saffronSoft, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.xs },
  card: { backgroundColor: colors.card, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.sm, ...shadow.card },
});
