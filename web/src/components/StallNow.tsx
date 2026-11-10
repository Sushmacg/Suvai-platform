import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { CurrentStall } from "../api/models";
import { useLoad } from "../hooks/useLoad";
import { dayLabel, timeRange } from "../utils/format";

// Home page strip. Shows nothing when there is no stall or the request fails.
export function StallNow() {
  const { data } = useLoad(() => api.get<CurrentStall>("/stalls/current", undefined, false), []);
  if (!data || data.state === "none" || !data.session) return null;
  const s = data.session;
  const open = data.state === "open";
  return (
    <section className="mx-auto max-w-6xl px-4">
      <Link to="/stalls" className={`flex flex-wrap items-center justify-between gap-2 rounded-2xl px-5 py-4 ${open ? "bg-ok/15 text-ok" : "bg-saffron-soft text-terracotta-dark"}`}>
        <span className="font-semibold">{open ? "The stall is open now" : "Next stall"}: {s.location.name}</span>
        <span className="text-sm">{dayLabel(s.session_date)} · {timeRange(s.start_time, s.end_time)}</span>
      </Link>
    </section>
  );
}