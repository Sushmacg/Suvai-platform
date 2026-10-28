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
