import type { ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";
import type { StallSession } from "../api/models";
import { colors, radius, shadow, spacing, typography } from "../theme";
import { dayLabel, openInMaps, timeRange } from "../utils/stall";
import { Button } from "./Button";

const STATUS_COLOR: Record<string, string> = {
  open: colors.success,
  scheduled: colors.saffron,
  closed: colors.muted,
  cancelled: colors.danger,
};

interface Props {
  session: StallSession;
  distanceKm?: number;
  children?: ReactNode;
}

export function SessionCard({ session, distanceKm, children }: Props) {
  const { location } = session;
  return (
    <View style={styles.card}>
      <View style={styles.top}>
        <Text style={[typography.heading, styles.name]}>{location.name}</Text>
        <View style={[styles.badge, { backgroundColor: STATUS_COLOR[session.status] ?? colors.muted }]}>
          <Text style={styles.badgeText}>{session.status}</Text>
        </View>
      </View>
      {location.address ? <Text style={typography.caption}>{location.address}</Text> : null}
      <Text style={typography.body}>
        {dayLabel(session.session_date)} · {timeRange(session.start_time, session.end_time)}
      </Text>
      {distanceKm !== undefined ? <Text style={typography.caption}>{distanceKm.toFixed(1)} km away</Text> : null}
      {session.notes ? <Text style={typography.caption}>{session.notes}</Text> : null}
      <Button title="Open in Maps" onPress={() => openInMaps(location)} />
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: colors.card, borderRadius: radius.md, padding: spacing.lg, gap: spacing.sm, ...shadow.card },
  top: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: spacing.sm },
  name: { flex: 1 },
  badge: { borderRadius: radius.pill, paddingHorizontal: spacing.md, paddingVertical: spacing.xs },
  badgeText: { color: "#FFFFFF", fontSize: 12, fontWeight: "600", textTransform: "capitalize" },
});