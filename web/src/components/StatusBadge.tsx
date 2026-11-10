import { statusStyle } from "../utils/format";

export const StatusBadge = ({ status }: { status: string }) => (
  <span className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${statusStyle[status] ?? "bg-line text-muted"}`}>{status}</span>
);