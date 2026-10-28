import { Alert, Linking } from "react-native";
import type { Location } from "../api/models";

function clock(t: string): string {
  const [h, m] = t.split(":").map(Number);
  return `${h % 12 || 12}:${String(m).padStart(2, "0")} ${h < 12 ? "AM" : "PM"}`;
}

export const timeRange = (start: string, end: string) => `${clock(start)} – ${clock(end)}`;

export function dayLabel(isoDate: string): string {
  const d = new Date(`${isoDate}T00:00:00`);
  return Number.isNaN(d.getTime())
    ? isoDate
    : d.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" });
}

// A plain Google Maps link built from the coordinates. It needs no API key.
export function openInMaps(location: Pick<Location, "latitude" | "longitude">): void {
  Linking.openURL(
    `https://www.google.com/maps/search/?api=1&query=${location.latitude},${location.longitude}`,
  ).catch(() => Alert.alert("Maps unavailable", "No app on this phone could open the map link."));
}