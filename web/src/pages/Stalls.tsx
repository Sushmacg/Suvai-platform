import { useState } from "react";
import { api } from "../api/client";
import type { CurrentStall, StallSession } from "../api/models";
import { SessionCard } from "../components/SessionCard";
import { Button, Notice, PageSpinner } from "../components/ui";
import { useLoad } from "../hooks/useLoad";

export function Stalls() {
  const cur = useLoad(() => api.get<CurrentStall>("/stalls/current", undefined, false), []);
  const today = useLoad(() => api.get<StallSession[]>("/stalls/today", undefined, false), []);
  const up = useLoad(() => api.get<StallSession[]>("/stalls/upcoming", { days: 14 }, false), []);
  const [near, setNear] = useState<StallSession[] | null>(null);
  const [nearErr, setNearErr] = useState("");
  const [locating, setLocating] = useState(false);

  function findNear() {
    if (!navigator.geolocation) { setNearErr("Your browser cannot share its location."); return; }
    setLocating(true);
    setNearErr("");
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          setNear(await api.get<StallSession[]>("/stalls/nearest", { lat: pos.coords.latitude, lng: pos.coords.longitude, limit: 5 }, false));
        } catch (e) {
          setNearErr(e instanceof Error ? e.message : "Could not load nearby stalls.");
        } finally {
          setLocating(false);
        }
      },
      () => { setNearErr("Location permission was denied. You can still use the lists on this page."); setLocating(false); },
    );
  }

  const loading = (cur.loading && !cur.data) || (today.loading && !today.data) || (up.loading && !up.data);
  const error = cur.error || today.error || up.error;
  const session = cur.data?.session;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-4xl font-bold">Find the stall</h1>
      <p className="mt-1 text-muted">Where we are, and when. Times are the stall opening hours.</p>

      {loading && <PageSpinner />}
      {error && <div className="mt-6"><Notice>{error}</Notice></div>}

      {!loading && !error && (
        <div className="mt-8 space-y-10">
          <section>
            <h2 className="mb-3 text-2xl font-bold">{cur.data?.state === "open" ? "Open right now" : "Next stall"}</h2>
            {session && cur.data?.state !== "none" ? <div className="max-w-xl"><SessionCard s={session} /></div> : <p className="text-muted">No stall is scheduled right now. Check the upcoming list below.</p>}
          </section>

          <section>
            <h2 className="mb-3 text-2xl font-bold">Today</h2>
            {(today.data ?? []).length === 0 ? <p className="text-muted">No stall today.</p> : (
              <div className="grid gap-4 md:grid-cols-2">{(today.data ?? []).map((s) => <SessionCard key={s.id} s={s} />)}</div>
            )}
          </section>

          <section>
            <h2 className="mb-3 text-2xl font-bold">Coming up (14 days)</h2>
            {(up.data ?? []).length === 0 ? <p className="text-muted">Nothing scheduled yet.</p> : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">{(up.data ?? []).map((s) => <SessionCard key={s.id} s={s} />)}</div>
            )}
          </section>

          <section>
            <h2 className="mb-3 text-2xl font-bold">Stalls near me</h2>
            <Button variant="ghost" onClick={findNear} disabled={locating}>{locating ? "Finding..." : "Use my location"}</Button>
            {nearErr && <div className="mt-3 max-w-xl"><Notice>{nearErr}</Notice></div>}
            {near && near.length === 0 && <p className="mt-3 text-muted">No upcoming stalls found near you.</p>}
            {near && near.length > 0 && <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">{near.map((s) => <SessionCard key={s.id} s={s} />)}</div>}
          </section>
        </div>
      )}
    </div>
  );
}