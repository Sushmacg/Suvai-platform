const p = (n: number) => String(n).padStart(2, "0");
// Local calendar date as YYYY-MM-DD (not UTC, so it is right around midnight in India).
export const isoDate = (d: Date = new Date()) => `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
export const addDays = (n: number) => { const d = new Date(); d.setDate(d.getDate() + n); return isoDate(d); };