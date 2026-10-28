import { useRef, useState } from "react";
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { api } from "../../api/client";
import { colors, radius, shadow, spacing, typography } from "../../theme";

interface Msg {
  id: number;
  role: "user" | "assistant" | "error";
  text: string;
}

const SUGGESTIONS = ["How did we do over the last 7 days?", "What demand do we expect tomorrow?", "Which are our top products?"];

export function AssistantScreen() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scroller = useRef<{ scrollToEnd: (o?: { animated?: boolean }) => void } | null>(null);
  const nextId = useRef(1);

  const add = (role: Msg["role"], text: string) => setMessages((m) => [...m, { id: nextId.current++, role, text }]);

  const send = async () => {
    const question = input.trim();
    if (!question || busy) return;
    setInput("");
    add("user", question);
    setBusy(true);
    try {
      const res = await api.post<{ answer: string }>("/assistant/chat", { question });
      add("assistant", res.answer);
    } catch (e) {
      add("error", e instanceof Error ? e.message : "The assistant is unavailable.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <Text style={styles.title}>Assistant</Text>
        <ScrollView
          ref={(r) => { scroller.current = r as unknown as { scrollToEnd: (o?: { animated?: boolean }) => void } | null; }}
          style={styles.flex}
          contentContainerStyle={styles.list}
          keyboardShouldPersistTaps="handled"
          onContentSizeChange={() => scroller.current?.scrollToEnd({ animated: true })}
        >
          {messages.length === 0 ? (
            <View style={styles.hint}>
              <Text style={typography.body}>Ask about sales, profit, top products, expenses or tomorrow's forecast.</Text>
              {SUGGESTIONS.map((s) => (
                <Pressable key={s} style={styles.suggestion} onPress={() => setInput(s)}>
                  <Text style={styles.suggestionText}>{s}</Text>
                </Pressable>
              ))}
            </View>
          ) : null}
          {messages.map((m) => (
            <View key={m.id} style={[styles.bubble, m.role === "user" ? styles.user : m.role === "error" ? styles.error : styles.bot]}>
              {m.role === "error" ? <Text style={styles.errorTitle}>Assistant unavailable</Text> : null}
              <Text style={[typography.body, m.role === "user" && { color: "#FFFFFF" }]}>{m.text}</Text>
            </View>
          ))}
          {busy ? <Text style={typography.caption}>Thinking…</Text> : null}
        </ScrollView>
        <View style={styles.inputRow}>
          <TextInput
            style={styles.input}
            value={input}
            onChangeText={setInput}
            placeholder="Ask a question"
            placeholderTextColor={colors.muted}
            maxLength={500}
            multiline
          />
          <Pressable style={[styles.send, (busy || !input.trim()) && styles.sendOff]} onPress={send} disabled={busy || !input.trim()}>
            <Text style={typography.button}>Send</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.cream },
  flex: { flex: 1 },
  title: { ...typography.title, paddingHorizontal: spacing.xl, paddingTop: spacing.lg },
  list: { padding: spacing.xl, gap: spacing.md, flexGrow: 1 },
  hint: { gap: spacing.md },
  suggestion: { backgroundColor: colors.saffronSoft, borderRadius: radius.md, padding: spacing.md },
  suggestionText: { ...typography.body, color: colors.terracottaDark },
  bubble: { padding: spacing.md, borderRadius: radius.lg, maxWidth: "88%", gap: spacing.xs, ...shadow.card },
  user: { alignSelf: "flex-end", backgroundColor: colors.terracotta },
  bot: { alignSelf: "flex-start", backgroundColor: colors.card },
  error: { alignSelf: "flex-start", backgroundColor: colors.card, borderWidth: 1.5, borderColor: colors.danger },
  errorTitle: { ...typography.caption, color: colors.danger, fontWeight: "700" },
  inputRow: { flexDirection: "row", alignItems: "flex-end", gap: spacing.sm, padding: spacing.md, backgroundColor: colors.surface, borderTopWidth: 1, borderTopColor: colors.border },
  input: { flex: 1, maxHeight: 120, minHeight: 46, backgroundColor: colors.card, borderRadius: radius.md, borderWidth: 1.5, borderColor: colors.border, paddingHorizontal: spacing.md, paddingVertical: spacing.sm, fontSize: 16, color: colors.text },
  send: { minHeight: 46, paddingHorizontal: spacing.lg, borderRadius: radius.pill, backgroundColor: colors.terracotta, alignItems: "center", justifyContent: "center" },
  sendOff: { opacity: 0.5 },
});
