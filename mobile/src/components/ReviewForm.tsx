import { useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { api } from "../api/client";
import { colors, radius, spacing, typography } from "../theme";
import { Button } from "./Button";

// The backend decides who may review (a buyer with a completed order, once per product)
// and its message is shown as it is.
export function ReviewForm({ productId }: { productId: string }) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (busy) return;
    if (rating === 0) {
      setError("Please choose a star rating.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.post("/reviews", { product_id: productId, rating, comment: comment.trim() || null });
      setDone(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save your review.");
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <View style={styles.box}>
        <Text style={typography.body}>Thank you! Your review was saved. It shows the next time you open this page.</Text>
      </View>
    );
  }

  return (
    <View style={styles.box}>
      <Text style={typography.heading}>Write a review</Text>
      <View style={styles.stars}>
        {[1, 2, 3, 4, 5].map((n) => (
          <Pressable
            key={n}
            onPress={() => setRating(n)}
            accessibilityRole="button"
            accessibilityLabel={`${n} star${n > 1 ? "s" : ""}`}
            style={({ pressed }) => [{ opacity: pressed ? 0.6 : 1 }]}
          >
            <Text style={[styles.star, { color: n <= rating ? colors.saffron : colors.border }]}>★</Text>
          </Pressable>
        ))}
      </View>
      <TextInput
        style={styles.input}
        value={comment}
        onChangeText={setComment}
        placeholder="Tell others what you thought (optional)"
        placeholderTextColor={colors.muted}
        multiline
        maxLength={1000}
      />
      {error ? <Text style={[typography.caption, { color: colors.danger }]}>{error}</Text> : null}
      <Button title={busy ? "Saving…" : "Submit review"} onPress={submit} />
    </View>
  );
}

const styles = StyleSheet.create({
  box: { backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
  stars: { flexDirection: "row", gap: spacing.sm },
  star: { fontSize: 34 },
  input: { minHeight: 80, backgroundColor: colors.card, borderRadius: radius.sm, borderWidth: 1, borderColor: colors.border, padding: spacing.md, color: colors.text, fontSize: 16, textAlignVertical: "top" },
});