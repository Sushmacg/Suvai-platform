// Reads latitude/longitude from a full Google Maps link or a "lat, lng" pair. Short links (maps.app.goo.gl) cannot be opened from a browser.
export function parseCoords(text: string): [number, number] | null {
  let t = text.trim();
  try { t = decodeURIComponent(t); } catch { /* keep the raw text */ }
  const pats = [
    /@(-?\d+\.\d+),(-?\d+\.\d+)/,
    /!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)/,
    /[?&](?:q|query|ll|destination)=(-?\d+\.\d+),\s*(-?\d+\.\d+)/,
    /^(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)$/,
  ];
  for (const re of pats) {
    const m = t.match(re);
    if (!m) continue;
    const lat = Number(m[1]), lng = Number(m[2]);
    if (Math.abs(lat) <= 90 && Math.abs(lng) <= 180) return [lat, lng];
  }
  return null;
}