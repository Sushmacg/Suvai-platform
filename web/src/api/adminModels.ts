import type { Order } from "./models";

export type Summary = { from: string; to: string; revenue: number; orders: number; expenses: number; profit: number; stocked: number; sold: number; wasted: number; sell_through: number };
export type SalesDay = { date: string; revenue: number; orders: number };
export type TopProduct = { name: string; units: number; revenue: number };
export type LocationSales = { name: string; revenue: number; orders: number };
export type StockAdmin = { id: string; session_id: string; product_id: string; product_name: string; stocked_qty: number; sold_qty: number; wasted_qty: number; available_qty: number; min_stock: number; is_low_stock: boolean; updated_at: string };
export type Expense = { id: string; amount: string; category: string; description: string | null; expense_date: string; session_id: string | null };
export type ExpenseSummary = { total: string; count: number; by_category: Record<string, string | number> };
export type ForecastItem = { date: string; location_id: string; product_id: string; predicted_units: number };
export type ForecastResponse = { model_version: string; forecast_date: string; items: ForecastItem[] };
export type AdminReview = { id: string; product_id: string; product_name: string; rating: number; comment: string | null; is_hidden: boolean; created_at: string; customer_name: string; customer_phone: string; hidden_reason: string | null };
export type AdminOrder = Order & { customer_id: string; customer_name: string; customer_phone: string };