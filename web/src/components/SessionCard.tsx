import type { ReactNode } from "react";
import type { StallSession } from "../api/models";
import { dayLabel, directionsLink, mapsLink, statusStyle, timeRange } from "../utils/format";
import { Card } from "./ui";

export function SessionCard({ s, footer }: { s: StallSession; footer?: ReactNode }) {
  const l = s.location;
  return (
    <Card className="flex flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-xl font-bold">{l.name}</h3>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${statusStyle[s.status] ?? "bg-line text-muted"}`}>{s.status}</span>
      </div>
      {l.address && <p className="text-sm text-muted">{l.address}</p>}
      <p className="font-medium">{dayLabel(s.session_date)} · {timeRange(s.start_time, s.end_time)}</p>
      {s.distance_km !== undefined && <p className="text-sm text-muted">{s.distance_km.toFixed(1)} km away</p>}
      {s.notes && <p className="text-sm">{s.notes}</p>}
      <div className="mt-1 flex flex-wrap gap-4 text-sm font-semibold text-terracotta">
        <a href={mapsLink(l.latitude, l.longitude)} target="_blank" rel="noreferrer">Open in Maps</a>
        <a href={directionsLink(l.latitude, l.longitude)} target="_blank" rel="noreferrer">Directions</a>
      </div>
      {footer}
    </Card>
  );
}