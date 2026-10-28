import { useCallback, useRef, useState } from "react";
import { Alert, FlatList, StyleSheet, Text, View } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { api } from "../../api/client";
import type { AdminOrder } from "../../api/models";
import { Button } from "../../components/Button";
import { EmptyView, ErrorView, LoadingView } from "../../components/States";
import { useLoad } from "../../hooks/useLoad";
import { rupees } from "../../utils/format";
import { colors, radius, shadow, spacing, typography } from "../../theme";

const NEXT: Record<string, string> = {
  pending: "confirmed",
  confirmed: "preparing",
  preparing: "ready",
  ready: "completed",
};
const CANCELLABLE = ["pending", "confirmed", "preparing"];

export function AdminOrdersScreen() {
  const { data, loading, refreshing, error, reload, refresh } = useLoad(() => api.get<AdminOrder[]>("/orders"));
  const [busyId, setBusyId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;
  useFocusEffect(
    useCallback(() => {
      refreshRef.current();
    }, []),
  );

  const setStatus = async (id: string, status: string) => {
    setBusyId(id);
    setNotice(null);
    try {
      await api.patch(`/orders/${id}/status`, { status });
      await refresh();
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Could not update the order.");
    } finally {
      setBusyId(null);
    }
  };

  const cancel = (id: string) =>
    Alert.alert("Cancel this order?", "Stock will be returned.", [
      { text: "Keep it", style: "cancel" },
      { text: "Cancel order", style: "destructive", onPress: () => setStatus(id, "cancelled") },
    ]);

  if (loading) return <LoadingView />;
  if (error && !data) return <ErrorView message={error} onRetry={reload} />;

  return (
    <FlatList
      style={{ backgroundColor: colors.cream }}
      data={data ?? []}
      keyExtractor={(o) => o.id}
      contentContainerStyle={styles.list}
      refreshing={refreshing}
      onRefresh={refresh}
      ListHeaderComponent={notice ? <Text style={[typography.body, { color: colors.danger }]}>{notice}</Text> : undefined}
      ListEmptyComponent={<EmptyView title="No orders yet" hint="New orders will appear here." />}
      renderItem={({ item }) => {
        const next = NEXT[item.status];
        return (
          <View style={styles.card}>
            <View style={styles.head}>
              <Text style={styles.status}>{item.status.toUpperCase()}</Text>
              <Text style={typography.caption}>{new Date(item.created_at).toLocaleString()}</Text>
            </View>
            <Text style={typography.body}>{item.customer_name} · {item.customer_phone}</Text>
            <Text style={typography.caption}>{item.session.location.name} · {item.session.session_date}</Text>
            {item.items.map((i) => (
              <Text key={i.product_id} style={typography.body}>{i.quantity} × {i.product_name}</Text>
            ))}
            <Text style={styles.total}>Total {rupees(item.total_amount)}</Text>
            {next ? (
              <Button title={`Mark as ${next}`} onPress={() => setStatus(item.id, next)} loading={busyId === item.id} />
            ) : null}
            {CANCELLABLE.includes(item.status) ? (
              <Button title="Cancel order" variant="secondary" onPress={() => cancel(item.id)} disabled={busyId === item.id} />
            ) : null}
          </View>
        );
      }}
    />
  );
}

const styles = StyleSheet.create({
  list: { padding: spacing.lg, gap: spacing.md, flexGrow: 1 },
  card: { backgroundColor: colors.card, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.sm, ...shadow.card },
  head: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  status: { fontWeight: "700", fontSize: 13, color: colors.terracotta },
  total: { ...typography.body, fontWeight: "700", color: colors.terracotta },
});
