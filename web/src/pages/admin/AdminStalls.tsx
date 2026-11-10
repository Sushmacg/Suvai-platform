import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../../api/client";
import type { Location, StallSession } from "../../api/models";
import { Label, inp } from "../../components/inputs";
import { StatusBadge } from "../../components/StatusBadge";
import { Button, Card, Notice, PageSpinner } from "../../components/ui";
import { useLoad } from "../../hooks/useLoad";
import { addDays, isoDate } from "../../utils/dates";
import { dayLabel, mapsLink, timeRange } from "../../utils/format";
import { parseCoords } from "../../utils/maps";

type Msg = { kind: "error" | "success"; text: string };

function LocationForm({ loc, onDone, onCancel }: { loc: Location | null; onDone: (m: string) => void; onCancel: () => void }) {
  const [f, setF] = useState({ name: loc?.name ?? "", address: loc?.address ?? "", lat: loc ? String(loc.latitude) : "", lng: loc ? String(loc.longitude) : "", place: loc?.google_place_id ?? "" });
  const [hint, setHint] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f, v: string) => setF((c) => ({ ...c, [k]: v }));

  function paste(v: string) {
    const c = parseCoords(v);
    if (c) { setF((cur) => ({ ...cur, lat: String(c[0]), lng: String(c[1]) })); setHint(`Coordinates found: ${c[0]}, ${c[1]}`); }
    else setHint(v.trim() ? "No coordinates found. Use the full link from the address bar, or type latitude and longitude." : "");
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    const lat = Number(f.lat), lng = Number(f.lng);
    if (f.name.trim().length < 2) return setErr("Name needs at least 2 characters.");
    if (f.lat === "" || f.lng === "" || Math.abs(lat) > 90 || Math.abs(lng) > 180) return setErr("Enter a valid latitude (-90 to 90) and longitude (-180 to 180).");
    const body = { name: f.name.trim(), address: f.address.trim() || null, latitude: lat, longitude: lng, google_place_id: f.place.trim() || null };
    setBusy(true);
    setErr("");
    try {
      if (loc) await api.patch(`/stalls/locations/${loc.id}`, body); else await api.post("/stalls/locations", body);
      onDone("Location saved.");
    } catch (x) {
      setErr(x instanceof Error ? x.message : "Could not save the location.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <h3 className="mb-4 text-xl font-bold">{loc ? `Edit ${loc.name}` : "New location"}</h3>
      <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
        <Label text="Name"><input className={inp} value={f.name} maxLength={120} onChange={(e) => set("name", e.target.value)} required /></Label>
        <Label text="Address (optional)"><input className={inp} value={f.address} maxLength={300} onChange={(e) => set("address", e.target.value)} /></Label>
        <div className="md:col-span-2">
          <Label text="Paste a Google Maps link to fill the coordinates (optional)"><input className={inp} placeholder="https://www.google.com/maps/..." onChange={(e) => paste(e.target.value)} /></Label>
          {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
        </div>
        <Label text="Latitude"><input className={inp} inputMode="decimal" value={f.lat} onChange={(e) => set("lat", e.target.value)} required /></Label>
        <Label text="Longitude"><input className={inp} inputMode="decimal" value={f.lng} onChange={(e) => set("lng", e.target.value)} required /></Label>
        {err && <div className="md:col-span-2"><Notice>{err}</Notice></div>}
        <div className="flex gap-3 md:col-span-2">
          <Button type="submit" disabled={busy}>{busy ? "Saving..." : "Save"}</Button>
          <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button>
        </div>
      </form>
    </Card>
  );
}

function SessionForm({ locations, onDone }: { locations: Location[]; onDone: (m: string) => void }) {
  const [f, setF] = useState({ location_id: locations[0]?.id ?? "", session_date: isoDate(), start_time: "09:00", end_time: "13:00", notes: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f, v: string) => setF((c) => ({ ...c, [k]: v }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!f.location_id) return setErr("Pick a location.");
    if (f.end_time <= f.start_time) return setErr("End time must be after the start time.");
    setBusy(true);
    setErr("");
    try {
      await api.post("/stalls/sessions", { ...f, notes: f.notes.trim() || null });
      onDone("Session created.");
    } catch (x) {
      setErr(x instanceof Error ? x.message : "Could not create the session.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <h3 className="mb-4 text-xl font-bold">New session</h3>
      {locations.length === 0 ? <p className="text-muted">Add an active location first.</p> : (
        <form onSubmit={submit} className="grid gap-4 md:grid-cols-4">
          <div className="md:col-span-2"><Label text="Location"><select className={inp} value={f.location_id} onChange={(e) => set("location_id", e.target.value)}>{locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}</select></Label></div>
          <Label text="Date"><input type="date" className={inp} value={f.session_date} onChange={(e) => set("session_date", e.target.value)} required /></Label>
          <div className="grid grid-cols-2 gap-2">
            <Label text="Start"><input type="time" className={inp} value={f.start_time} onChange={(e) => set("start_time", e.target.value)} required /></Label>
            <Label text="End"><input type="time" className={inp} value={f.end_time} onChange={(e) => set("end_time", e.target.value)} required /></Label>
          </div>
          <div className="md:col-span-4"><Label text="Notes (optional)"><input className={inp} value={f.notes} onChange={(e) => set("notes", e.target.value)} /></Label></div>
          {err && <div className="md:col-span-4"><Notice>{err}</Notice></div>}
          <div className="md:col-span-4"><Button type="submit" disabled={busy}>{busy ? "Creating..." : "Create session"}</Button></div>
        </form>
      )}
    </Card>
  );
}

export function AdminStalls() {
  const locs = useLoad(() => api.get<Location[]>("/stalls/locations/all"), []);
  const sess = useLoad(() => api.get<StallSession[]>("/stalls/sessions", { start: addDays(-7), end: addDays(30) }), []);
  const [editing, setEditing] = useState<Location | "new" | null>(null);
  const [msg, setMsg] = useState<Msg | null>(null);
  const [busy, setBusy] = useState("");
  const all = locs.data ?? [];
  const sessions = [...(sess.data ?? [])].sort((a, b) => `${a.session_date}${a.start_time}`.localeCompare(`${b.session_date}${b.start_time}`));

  async function act(id: string, fn: () => Promise<unknown>, ok: string) {
    setBusy(id);
    setMsg(null);
    try { await fn(); setMsg({ kind: "success", text: ok }); locs.reload(); sess.reload(); }
    catch (e) { setMsg({ kind: "error", text: e instanceof Error ? e.message : "Request failed." }); }
    finally { setBusy(""); }
  }
  const finished = (m: string) => { setEditing(null); setMsg({ kind: "success", text: m }); locs.reload(); sess.reload(); };
  const setStatus = (s: StallSession, status: string, ok: string) => act(s.id, () => api.patch(`/stalls/sessions/${s.id}/status`, { status }), ok);

  return (
    <div className="space-y-10">
      <h1 className="text-3xl font-bold">Stalls</h1>
      {msg && <Notice kind={msg.kind}>{msg.text}</Notice>}
      {(locs.error || sess.error) && <Notice>{locs.error || sess.error}</Notice>}
      {((locs.loading && !locs.data) || (sess.loading && !sess.data)) && <PageSpinner />}

      <section className="space-y-4">
        <div className="flex items-center justify-between"><h2 className="text-2xl font-bold">Sessions</h2><span className="text-xs text-muted">Last 7 days to next 30</span></div>
        <SessionForm key={all.length} locations={all.filter((l) => l.is_active)} onDone={finished} />
        {sess.data && sessions.length === 0 && <Card className="text-center text-muted">No sessions in this range.</Card>}
        <ul className="space-y-3">
          {sessions.map((s) => (
            <li key={s.id}>
              <Card className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <p className="font-bold">{s.location.name}</p>
                  <p className="text-sm text-muted">{dayLabel(s.session_date)} · {timeRange(s.start_time, s.end_time)}{s.notes ? ` · ${s.notes}` : ""}</p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge status={s.status} />
                  {s.status === "scheduled" && <Button disabled={busy === s.id} onClick={() => setStatus(s, "open", "Session opened.")}>Open</Button>}
                  {s.status === "open" && <Button disabled={busy === s.id} onClick={() => setStatus(s, "closed", "Session closed.")}>Close</Button>}
                  {(s.status === "scheduled" || s.status === "open") && <Button variant="ghost" disabled={busy === s.id} onClick={() => window.confirm("Cancel this session?") && setStatus(s, "cancelled", "Session cancelled.")}>Cancel</Button>}
                </div>
              </Card>
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between"><h2 className="text-2xl font-bold">Locations</h2>{!editing && <Button onClick={() => setEditing("new")}>Add location</Button>}</div>
        {editing && <LocationForm key={editing === "new" ? "new" : editing.id} loc={editing === "new" ? null : editing} onDone={finished} onCancel={() => setEditing(null)} />}
        {locs.data && all.length === 0 && <Card className="text-center text-muted">No locations yet.</Card>}
        <ul className="grid gap-3 md:grid-cols-2">
          {all.map((l) => (
            <li key={l.id}>
              <Card className={`space-y-1 p-4 ${l.is_active ? "" : "opacity-60"}`}>
                <p className="font-bold">{l.name} {!l.is_active && <span className="ml-1 rounded-full bg-line px-2 py-0.5 text-xs font-medium text-muted">Inactive</span>}</p>
                {l.address && <p className="text-sm text-muted">{l.address}</p>}
                <p className="text-xs text-muted">{l.latitude}, {l.longitude} · <a className="font-semibold text-terracotta" href={mapsLink(l.latitude, l.longitude)} target="_blank" rel="noreferrer">Open in Maps</a></p>
                <div className="flex gap-2 pt-2">
                  <Button variant="ghost" onClick={() => setEditing(l)}>Edit</Button>
                  <Button variant="ghost" disabled={busy === l.id} onClick={() => act(l.id, () => api.patch(`/stalls/locations/${l.id}`, { is_active: !l.is_active }), l.is_active ? "Location deactivated." : "Location activated.")}>{l.is_active ? "Deactivate" : "Activate"}</Button>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}