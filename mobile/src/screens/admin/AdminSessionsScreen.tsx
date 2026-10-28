import { useState } from "react";
import { Alert, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { api } from "../../api/client";
import type { Location, StallSession } from "../../api/models";
import { Button } from "../../components/Button";
import { ChoiceChips } from "../../components/ChoiceChips";
import { LabeledInput } from "../../components/LabeledInput";
import { SessionCard } from "../../components/SessionCard";
import { ErrorView, LoadingView } from "../../components/States";
import { useLoad } from "../../hooks/useLoad";
import { colors, radius, spacing, typography } from "../../theme";
import { isoDate } from "../../utils/dates";

type NewStatus = "open" | "closed" | "cancelled";
const ACTIONS: Record<string, { label: string; status: NewStatus }[]> = {
  scheduled: [
    { label: "Open stall", status: "open" },
    { label: "Cancel visit", status: "cancelled" },
  ],
  open: [{ label: "Close stall", status: "closed" }],
};
const TIME = /^([01]\d|2[0-3]):[0-5]\d$/;

export function AdminSessionsScreen() {
  const { data, loading, refreshing, error, reload, refresh } = useLoad(async () => {
    const [sessions, locations] = await Promise.all([
      api.get<StallSession[]>("/stalls/sessions", { query: { start: isoDate(-1), end: isoDate(30) } }),
      api.get<Location[]>("/stalls/locations", { auth: false }),
    ]);
    return { sessions, locations };
  });
  const [show, setShow] = useState(false);
  const [locationId, setLocationId] = useState<string | null>(null);
  const [date, setDate] = useState(isoDate(0));
  const [start, setStart] = useState("09:00");
  const [end, setEnd] = useState("14:00");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function create() {
    if (busy) return;
    if (!locationId) return setMessage("Choose a location.");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return setMessage("Date must look like 2026-11-02.");
    if (!TIME.test(start) || !TIME.test(end)) return setMessage("Times must look like 09:00 (24-hour).");
    setBusy(true);
    setMessage(null);
    try {
      await api.post("/stalls/sessions", {
        location_id: locationId,
        session_date: date,
        start_time: `${start}:00`,
        end_time: `${end}:00`,
        notes: notes.trim() || null,
      });
      setShow(false);
      setNotes("");
      reload();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Could not create the session.");
    } finally {
      setBusy(false);
    }
  }

  function changeStatus(s: StallSession, status: NewStatus) {
    const go = async () => {
      try {
        await api.patch(`/stalls/sessions/${s.id}/status`, { status });
        reload();
      } catch (e) {
        Alert.alert("Could not update", e instanceof Error ? e.message : "Please try again.");
      }
    };
    if (status === "open") {
      go();
      return;
    }
    Alert.alert(status === "closed" ? "Close this stall?" : "Cancel this visit?", `${s.location.name}, ${s.session_date}`, [
      { text: "Back", style: "cancel" },
      { text: "Yes", style: status === "cancelled" ? "destructive" : "default", onPress: go },
    ]);
  }

  if (loading) return <LoadingView />;
  if (error && !data) return <ErrorView message={error} onRetry={reload} />;
  if (!data) return <LoadingView />;

  return (
    <ScrollView
      style={{ backgroundColor: colors.cream }}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.terracotta} />}
    >
      <Button title={show ? "Hide form" : "New session"} onPress={() => setShow(!show)} />

      {show ? (
        <View style={styles.form}>
          <Text style={typography.heading}>New session</Text>
          <Text style={typography.caption}>Location</Text>
          {data.locations.length === 0 ? <Text style={typography.caption}>No locations exist yet. Add one in Swagger first.</Text> : null}
          <ChoiceChips options={data.locations.map((l) => ({ value: l.id, label: l.name }))} value={locationId} onChange={setLocationId} />
          <LabeledInput label="Date (YYYY-MM-DD)" value={date} onChangeText={setDate} autoCapitalize="none" />
          <LabeledInput label="Start (24-hour, HH:MM)" value={start} onChangeText={setStart} autoCapitalize="none" />
          <LabeledInput label="End (24-hour, HH:MM)" value={end} onChangeText={setEnd} autoCapitalize="none" />
          <LabeledInput label="Notes (optional)" value={notes} onChangeText={setNotes} maxLength={500} />
          {message ? <Text style={[typography.caption, { color: colors.danger }]}>{message}</Text> : null}
          <Button title={busy ? "Saving…" : "Create session"} onPress={create} />
        </View>
      ) : null}

      <Text style={typography.heading}>Yesterday to the next 30 days</Text>
      {data.sessions.length === 0 ? <Text style={typography.caption}>No sessions yet. Create one above.</Text> : null}
      {data.sessions.map((s) => (
        <SessionCard key={s.id} session={s}>
          {(ACTIONS[s.status] ?? []).map((a) => (
            <Button key={a.status} title={a.label} onPress={() => changeStatus(s, a.status)} />
          ))}
        </SessionCard>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxl },
  form: { backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
});