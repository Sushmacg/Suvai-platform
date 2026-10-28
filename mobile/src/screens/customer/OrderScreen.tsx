import { useCallback, useRef, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { api } from "../../api/client";
import type { CurrentStall, Order, StockItem } from "../../api/models";
import { Button } from "../../components/Button";
import { Screen } from "../../components/Screen";
import { EmptyView, ErrorView, LoadingView } from "../../components/States";
import { TextField } from "../../components/TextField";
import { useLoad } from "../../hooks/useLoad";
import { rupees } from "../../utils/format";
import { colors, radius, shadow, spacing, typography } from "../../theme";

function Stepper({ value, max, onChange }: { value: number; max: number; onChange: (n: number) => void }) {
  return (
    <View style={styles.stepper}>
      <Pressable style={styles.stepBtn} disabled={value <= 0} onPress={() => onChange(value - 1)}>
        <Text style={[styles.stepText, value <= 0 && styles.dim]}>−</Text>
      </Pressable>
      <Text style={styles.qty}>{value}</Text>
      <Pressable style={styles.stepBtn} disabled={value >= max} onPress={() => onChange(value + 1)}>
        <Text style={[styles.stepText, value >= max && styles.dim]}>+</Text>
      </Pressable>
    </View>
  );
}

export function OrderScreen() {
  const { data, loading, error, reload, refresh } = useLoad(async () => {
    const current = await api.get<CurrentStall>("/stalls/current", { auth: false });
    const stock = current.session
      ? await api.get<StockItem[]>(`/inventory/sessions/${current.session.id}`, { auth: false })
      : [];
    return { current, stock };
  });
  const [qty, setQty] = useState<Record<string, number>>({});
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;
  useFocusEffect(
    useCallback(() => {
      refreshRef.current();
    }, []),
  );

  if (loading) return <LoadingView />;
  if (error || !data) return <ErrorView message={error ?? "Could not load the stall."} onRetry={reload} />;

  const session = data.current.session;
  if (!session) {
    return <EmptyView title="No stall session right now" hint="Check back when the next session is scheduled." />;
  }

  const lines = data.stock.filter((s) => (qty[s.product_id] ?? 0) > 0);
  const total = lines.reduce((sum, s) => sum + Number(s.price) * (qty[s.product_id] ?? 0), 0);

  const place = async () => {
    setBusy(true);
    setMessage(null);
    try {
      await api.post<Order>("/orders", {
        session_id: session.id,
        items: lines.map((s) => ({ product_id: s.product_id, quantity: qty[s.product_id] })),
        notes: notes.trim() || null,
      });
      setQty({});
      setNotes("");
      setMessage({ ok: true, text: "Order placed! Track it in the Orders tab." });
      await reload();
    } catch (e) {
      setMessage({ ok: false, text: e instanceof Error ? e.message : "Could not place the order." });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen>
      <View style={styles.sessionCard}>
        <Text style={typography.heading}>{session.location.name}</Text>
        <Text style={typography.caption}>
          {session.session_date} · {session.start_time.slice(0, 5)}–{session.end_time.slice(0, 5)} · {session.status}
        </Text>
      </View>
      {data.stock.length === 0 ? <EmptyView title="Nothing to order yet" hint="Stock has not been set for this session." /> : null}
      {data.stock.map((s) => (
        <View key={s.product_id} style={styles.row}>
          <View style={styles.rowInfo}>
            <Text style={typography.body}>{s.product_name}</Text>
            <Text style={styles.price}>{rupees(s.price)}</Text>
            <Text style={typography.caption}>{s.in_stock ? `${s.available_qty} left` : "Sold out"}</Text>
          </View>
          <Stepper
            value={qty[s.product_id] ?? 0}
            max={s.in_stock ? s.available_qty : 0}
            onChange={(n) => setQty((q) => ({ ...q, [s.product_id]: n }))}
          />
        </View>
      ))}
      {lines.length > 0 ? (
        <>
          <TextField label="Note for the stall (optional)" value={notes} onChangeText={setNotes} placeholder="Anything we should know?" />
          <Text style={typography.heading}>Total {rupees(total)}</Text>
        </>
      ) : null}
      {message ? <Text style={[typography.body, { color: message.ok ? colors.success : colors.danger }]}>{message.text}</Text> : null}
      <Button title="Place order" onPress={place} loading={busy} disabled={lines.length === 0} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  sessionCard: { backgroundColor: colors.saffronSoft, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.xs },
  row: { flexDirection: "row", alignItems: "center", backgroundColor: colors.card, borderRadius: radius.md, padding: spacing.md, ...shadow.card },
  rowInfo: { flex: 1, gap: 2 },
  price: { ...typography.body, color: colors.terracotta, fontWeight: "700" },
  stepper: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  stepBtn: { width: 40, height: 40, borderRadius: radius.pill, backgroundColor: colors.cream, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.border },
  stepText: { fontSize: 22, color: colors.terracotta, fontWeight: "700" },
  dim: { opacity: 0.3 },
  qty: { ...typography.body, minWidth: 24, textAlign: "center", fontWeight: "700" },
});
