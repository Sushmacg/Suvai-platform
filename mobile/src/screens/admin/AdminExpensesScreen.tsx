import { useState } from "react";
import { RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { api } from "../../api/client";
import { Button } from "../../components/Button";
import { ChoiceChips } from "../../components/ChoiceChips";
import { LabeledInput } from "../../components/LabeledInput";
import { ErrorView, LoadingView } from "../../components/States";
import { useLoad } from "../../hooks/useLoad";
import { colors, radius, shadow, spacing, typography } from "../../theme";
import { isoDate } from "../../utils/dates";
import { rupees } from "../../utils/format";

const CATEGORIES = ["ingredients", "packaging", "fuel", "transport", "rent", "labour", "utilities", "marketing", "maintenance", "other"] as const;
type Category = (typeof CATEGORIES)[number];

interface Expense { id: string; amount: string; category: string; description: string | null; expense_date: string }
interface Summary { total: string; count: number; by_category: Record<string, string> }

export function AdminExpensesScreen() {
  const { data, loading, refreshing, error, reload, refresh } = useLoad(async () => {
    const from = isoDate(-29);
    const [summary, items] = await Promise.all([
      api.get<Summary>("/expenses/summary", { query: { start: from } }),
      api.get<Expense[]>("/expenses", { query: { start: from, limit: 50 } }),
    ]);
    return { summary, items };
  });
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState<Category | null>("ingredients");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function add() {
    if (busy) return;
    const value = amount.trim();
    if (!/^\d+(\.\d{1,2})?$/.test(value) || Number(value) <= 0) return setMessage("Enter an amount above 0, such as 450 or 450.50.");
    if (!category) return setMessage("Choose a category.");
    setBusy(true);
    setMessage(null);
    try {
      await api.post("/expenses", { amount: value, category, description: description.trim() || null });
      setAmount("");
      setDescription("");
      reload();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Could not save the expense.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingView />;
  if (error && !data) return <ErrorView message={error} onRetry={reload} />;
  if (!data) return <LoadingView />;

  const { summary, items } = data;
  const byCategory = Object.entries(summary.by_category).sort((a, b) => Number(b[1]) - Number(a[1]));

  return (
    <ScrollView
      style={{ backgroundColor: colors.cream }}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.terracotta} />}
    >
      <View style={styles.card}>
        <Text style={typography.caption}>Last 30 days</Text>
        <Text style={typography.title}>{rupees(summary.total)}</Text>
        <Text style={typography.caption}>{summary.count} expense{summary.count === 1 ? "" : "s"}</Text>
        {byCategory.map(([name, total]) => (
          <View key={name} style={styles.line}>
            <Text style={[typography.body, styles.cap]}>{name}</Text>
            <Text style={typography.body}>{rupees(total)}</Text>
          </View>
        ))}
      </View>

      <View style={styles.form}>
        <Text style={typography.heading}>Add expense</Text>
        <LabeledInput label="Amount (₹)" value={amount} onChangeText={setAmount} keyboardType="decimal-pad" />
        <Text style={typography.caption}>Category</Text>
        <ChoiceChips options={CATEGORIES.map((c) => ({ value: c, label: c }))} value={category} onChange={setCategory} />
        <LabeledInput label="Description (optional)" value={description} onChangeText={setDescription} maxLength={500} />
        {message ? <Text style={[typography.caption, { color: colors.danger }]}>{message}</Text> : null}
        <Button title={busy ? "Saving…" : "Save expense"} onPress={add} />
      </View>

      <Text style={typography.heading}>Recent expenses</Text>
      {items.length === 0 ? <Text style={typography.caption}>No expenses in the last 30 days.</Text> : null}
      {items.map((e) => (
        <View key={e.id} style={styles.line}>
          <View style={{ flex: 1 }}>
            <Text style={[typography.body, styles.cap]}>{e.category}</Text>
            <Text style={typography.caption}>{e.expense_date}{e.description ? ` · ${e.description}` : ""}</Text>
          </View>
          <Text style={typography.body}>{rupees(e.amount)}</Text>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxl },
  card: { backgroundColor: colors.card, borderRadius: radius.md, padding: spacing.lg, gap: spacing.xs, ...shadow.card },
  form: { backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
  line: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: spacing.md, paddingVertical: spacing.xs },
  cap: { textTransform: "capitalize" },
});