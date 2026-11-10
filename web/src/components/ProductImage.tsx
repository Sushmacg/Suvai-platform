import { useState } from "react";
import type { Product } from "../api/models";
import { imageUrl } from "../utils/format";
import { NankhataiArt } from "./NankhataiArt";

// Shows the product photo from the backend when there is one, otherwise the flavour illustration.
export function ProductImage({ product, className = "" }: { product: Product; className?: string }) {
  const [failed, setFailed] = useState(false);
  const src = imageUrl(product.image_url);
  if (!src || failed) return <NankhataiArt name={product.name} className={className} />;
  return <img src={src} alt={product.name} className={`${className} object-cover`} onError={() => setFailed(true)} loading="lazy" />;
}