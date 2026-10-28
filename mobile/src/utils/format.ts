export function rupees(value: string | number): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  return `₹${Number.isInteger(n) ? n : n.toFixed(2)}`;
}
