import { api } from "../api/client";
import type { AppNotification } from "../api/models";
import { Button, Card, Notice, PageSpinner } from "../components/ui";
import { useLoad } from "../hooks/useLoad";
import { dateTime } from "../utils/format";

export function Notifications() {
  const { data, loading, error, reload } = useLoad(() => api.get<AppNotification[]>("/notifications/me", { limit: 50 }), []);
  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-4xl font-bold">Notifications</h1>
      {loading && !data && <PageSpinner />}
      {error && <div className="mt-6 space-y-3"><Notice>{error}</Notice><Button variant="ghost" onClick={reload}>Try again</Button></div>}
      {data && data.length === 0 && <Card className="mt-8 text-center text-muted">Nothing here yet. Updates about your orders will show up here.</Card>}
      <ul className="mt-6 space-y-3">
        {(data ?? []).map((n) => (
          <li key={n.id}>
            <Card className="p-4">
              <p className="font-bold">{n.title}</p>
              <p className="text-sm">{n.body}</p>
              <p className="mt-1 text-xs text-muted">{dateTime(n.created_at)}</p>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}