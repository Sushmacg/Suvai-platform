import { useState } from "react";
import { RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import * as Location from "expo-location";
import { api } from "../../api/client";
import type { CurrentStall, StallSession } from "../../api/models";
import { Button } from "../../components/Button";
import { SessionCard } from "../../components/SessionCard";
import { ErrorView, LoadingView } from "../../components/States";
import { useLoad } from "../../hooks/useLoad";
import { colors, spacing, typography } from "../../theme";

type Nearest = StallSession & { distance_km: number };

const HEADLINE = {
  open: "The stall is open now",
  upcoming: "Next stall visit",
  none: "No stall is scheduled right now",
} as const;

export function StallScreen() {
  const { data, loading, refreshing, error, reload, refresh } = useLoad(async () => {
    const [current, today, upcoming] = await Promise.all([
      api.get<CurrentStall>("/stalls/current", { auth: false }),
      api.get<StallSession[]>("/stalls/today", { auth: false }),
      api.get<StallSession[]>("/stalls/upcoming", { auth: false, query: { days: 7 } }),
    ]);
    return { current, today, upcoming };
  });
  const [nearest, setNearest] = useState<Nearest[] | null>(null);
  const [nearMessage, setNearMessage] = useState<string | null>(null);
  const [finding, setFinding] = useState(false);

  async function findNearest() {
    if (finding) return;
    setFinding(true);
    setNearMessage(null);
    try {
      const permission = await Location.requestForegroundPermissionsAsync();
      if (permission.status !== "granted") {
        setNearMessage("Location permission was denied. The schedule above still works.");
        return;
      }
      const position = await Location.getCurrentPositionAsync({});
      const list = await api.get<Nearest[]>("/stalls/nearest", {
        auth: false,
        query: { lat: position.coords.latitude, lng: position.coords.longitude, limit: 5 },
      });
      setNearest(list);
      if (list.length === 0) setNearMessage("No upcoming stall visits were found.");
    } catch (e) {
      setNearMessage(e instanceof Error ? e.message : "Could not find your location.");
    } finally {
      setFinding(false);
    }
  }

  if (loading) return <LoadingView />;
  if (error && !data) return <ErrorView message={error} onRetry={reload} />;
  if (!data) return <LoadingView />;

  const { current, today, upcoming } = data;
  const shown = new Set<string>(current.session ? [current.session.id] : []);
  const todayRest = today.filter((s) => !shown.has(s.id));
  todayRest.forEach((s) => shown.add(s.id));
  const later = upcoming.filter((s) => !shown.has(s.id));

  return (
    <ScrollView
      style={{ backgroundColor: colors.cream }}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.terracotta} />}
    >
      <Text style={typography.title}>Find the stall</Text>

      <Text style={typography.heading}>{HEADLINE[current.state]}</Text>
      {current.session ? <SessionCard session={current.session} /> : (
        <Text style={typography.caption}>Pull down to refresh. New visits appear here as soon as they are scheduled.</Text>
      )}

      {todayRest.length > 0 ? <Text style={typography.heading}>Also today</Text> : null}
      {todayRest.map((s) => <SessionCard key={s.id} session={s} />)}

      <Text style={typography.heading}>Coming up this week</Text>
      {later.length === 0 ? <Text style={typography.caption}>No more visits are scheduled this week.</Text> : null}
      {later.map((s) => <SessionCard key={s.id} session={s} />)}

      <View style={styles.nearBox}>
        <Text style={typography.heading}>Closest to you</Text>
        <Button title={finding ? "Finding…" : "Find stalls near me"} onPress={findNearest} />
        {nearMessage ? <Text style={typography.caption}>{nearMessage}</Text> : null}
        {(nearest ?? []).map((s) => <SessionCard key={s.id} session={s} distanceKm={s.distance_km} />)}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxl },
  nearBox: { gap: spacing.md, marginTop: spacing.md },
});