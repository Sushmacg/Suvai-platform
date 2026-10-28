export interface Product {
  id: string;
  name: string;
  description: string | null;
  category: string;
  price: string;
  image_url: string | null;
  is_available: boolean;
  is_active: boolean;
}

export interface RatingSummary {
  product_id: string;
  average: number | null;
  count: number;
}

export interface PublicReview {
  id: string;
  reviewer_name: string;
  rating: number;
  comment: string | null;
  created_at: string;
}

export interface Location {
  id: string;
  name: string;
  address: string | null;
  latitude: number;
  longitude: number;
}

export interface StallSession {
  id: string;
  session_date: string;
  start_time: string;
  end_time: string;
  status: string;
  notes: string | null;
  location: Location;
}

export interface CurrentStall {
  state: "open" | "upcoming" | "none";
  session: StallSession | null;
}

export interface StockItem {
  product_id: string;
  product_name: string;
  price: string;
  available_qty: number;
  in_stock: boolean;
}

export interface OrderItem {
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: string;
  line_total: string;
}

export interface Order {
  id: string;
  status: string;
  total_amount: string;
  notes: string | null;
  created_at: string;
  items: OrderItem[];
  session: StallSession;
}

export interface AdminOrder extends Order {
  customer_id: string;
  customer_name: string;
  customer_phone: string;
}

export interface AnalyticsSummary {
  from: string;
  to: string;
  revenue: number;
  orders: number;
  expenses: number;
  profit: number;
  stocked: number;
  sold: number;
  wasted: number;
  sell_through: number;
}

export interface StockAdmin {
  id: string;
  session_id: string;
  product_id: string;
  product_name: string;
  stocked_qty: number;
  sold_qty: number;
  wasted_qty: number;
  available_qty: number;
  min_stock: number;
  is_low_stock: boolean;
}

export interface SalesDay {
  date: string;
  revenue: number;
  orders: number;
}

export interface TopProduct {
  name: string;
  units: number;
  revenue: number;
}

export interface LocationSales {
  name: string;
  revenue: number;
  orders: number;
}

export interface ForecastItem {
  date: string;
  location_id: string;
  product_id: string;
  predicted_units: number;
}

export interface ForecastResponse {
  model_version: string;
  forecast_date: string;
  items: ForecastItem[];
}
