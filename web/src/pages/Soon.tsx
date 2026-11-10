import { Card } from "../components/ui";

// Placeholder for pages built in the next batches. It shows no fake data.
export function Soon({ title }: { title: string }) {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <Card>
        <h1 className="text-3xl font-bold">{title}</h1>
        <p className="mt-2 text-muted">This page is not built yet. It is part of a later batch.</p>
      </Card>
    </div>
  );
}

export function NotFound() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 text-center">
      <h1 className="text-4xl font-bold">Page not found</h1>
      <p className="mt-2 text-muted">Check the address, or go back to the home page.</p>
    </div>
  );
}