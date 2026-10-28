import { api } from "../../api/client";
import type { LocationSales, SalesDay, TopProduct } from "../../api/models";
import { BarList } from "../../components/BarList";
import { ErrorView, LoadingView } from "../../components/States";
import { useLoad } from "../../hooks/useLoad";
import { rupees } from "../../utils/format";

export function Breakdown({ days }: { days: number }) {
  const { data, loading, error, reload } = useLoad(async () => {
    const [sales, products, locations] = await Promise.all([
      api.get<SalesDay[]>("/analytics/sales", { query: { days } }),
      api.get<TopProduct[]>("/analytics/products", { query: { days, limit: 5 } }),
      api.get<LocationSales[]>("/analytics/locations", { query: { days } }),
    ]);
    return { sales, products, locations };
  }, [days]);

  if (loading) return <LoadingView />;
  if (error || !data) return <ErrorView message={error ?? "Could not load the breakdown."} onRetry={reload} />;

  return (
    <>
      <BarList
        title="Revenue by day"
        bars={data.sales.slice(-14).map((d) => ({ label: d.date.slice(5), value: d.revenue, text: rupees(d.revenue) }))}
      />
      <BarList
        title="Top products"
        bars={data.products.map((p) => ({ label: p.name, value: p.units, text: `${p.units} sold` }))}
      />
      <BarList
        title="Revenue by location"
        bars={data.locations.map((l) => ({ label: l.name, value: l.revenue, text: rupees(l.revenue) }))}
      />
    </>
  );
}
