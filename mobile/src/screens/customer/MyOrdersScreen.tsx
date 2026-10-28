import { useCallback, useRef, useState } from "react";
import { Alert, FlatList, StyleSheet, Text, View } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { api } from "../../api/client";
import type { Order } from "../../api/models";
import { Button } from "../../components/Button";
import { EmptyView, ErrorView, LoadingView } from "../../components/States";
import { useLoad } from "../../hooks/useLoad";
import { rupees } from "../../utils/format";
import { colors, radius, shadow, spacing, typography } from "../../theme";

const statusColor: Record<string, string> = {
  pending: colors.saffron,
  confirmed: colors.terracotta,
  preparing: colors.terracotta,
  ready: colors.success,
  completed: colors.success,
  cancelled: colors.danger,
};

export function MyOrdersScreen() {
  const { data, loading, refreshing, error, reload, refresh } = useLoad(() => api.get<Order[]>("/orders/me"));
  const [cancelling, setCancelling] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;
  useFocusEffect(
    useCallback(() => {
      refreshRef.current();
    }, []),
  );

  const cancel = (id: string) => {
    Alert.alert("Cancel this order?", "This cannot be undone.", [
      { text: "Keep it", style: "cancel" },
      {
        text: "Cancel order",
        style: "destructive",
        onPress: async () => {
          setCancelling(id);
          setNotice(null);
          try {
            await api.post(`/orders/me/${id}/cancel`);
            await refresh();
          } catch (e) {
            setNotice(e instanceof Error ? e.message : "Could not cancel the order.");
          } finally {
            setCancelling(null);
          }
        },
      },
    ]);
  };

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
      ListEmptyComponent={<EmptyView title="No orders yet" hint="Your orders will show up here." />}
      renderItem={({ item }) => (
        <View style={styles.card}>
          <View style={styles.head}>
            <Text style={[styles.status, { color: statusColor[item.status] ?? colors.muted }]}>{item.status.toUpperCase()}</Text>
            <Text style={typography.caption}>{new Date(item.created_at).toLocaleString()}</Text>
          </View>
          <Text style={typography.caption}>{item.session.location.name} · {item.session.session_date}</Text>
          {item.items.map((i) => (
            <Text key={i.product_id} style={typography.body}>{i.quantity} × {i.product_name}  {rupees(i.line_total)}</Text>
          ))}
          <Text style={styles.total}>Total {rupees(item.total_amount)}</Text>
          {item.status === "pending" ? (
            <Button title="Cancel order" variant="secondary" onPress={() => cancel(item.id)} loading={cancelling === item.id} />
          ) : null}
        </View>
      )}
    />
  );
}

const styles = StyleSheet.create({
  list: { padding: spacing.lg, gap: spacing.md, flexGrow: 1 },
  card: { backgroundColor: colors.card, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.sm, ...shadow.card },
  head: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  status: { fontWeight: "700", fontSize: 13 },
  total: { ...typography.body, fontWeight: "700", color: colors.terracotta },
});
