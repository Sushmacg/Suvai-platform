import { StyleSheet, Text, View } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { api } from "../../api/client";
import type { Product, PublicReview, RatingSummary } from "../../api/models";
import { ProductImage } from "../../components/ProductImage";
import { Screen } from "../../components/Screen";
import { ErrorView, LoadingView } from "../../components/States";
import { useLoad } from "../../hooks/useLoad";
import type { MenuStackParamList } from "../../navigation/MenuStack";
import { rupees } from "../../utils/format";
import { colors, radius, spacing, typography } from "../../theme";

type Props = NativeStackScreenProps<MenuStackParamList, "ProductDetail">;

export function ProductDetailScreen({ route }: Props) {
  const { productId } = route.params;
  const { data, loading, error, reload } = useLoad(async () => {
    const [product, summary, reviews] = await Promise.all([
      api.get<Product>(`/products/${productId}`, { auth: false }),
      api.get<RatingSummary>(`/reviews/product/${productId}/summary`, { auth: false }).catch(() => null),
      api.get<PublicReview[]>(`/reviews/product/${productId}`, { auth: false }).catch(() => [] as PublicReview[]),
    ]);
    return { product, summary, reviews };
  }, [productId]);

  if (loading) return <LoadingView />;
  if (error || !data) return <ErrorView message={error ?? "Could not load this product."} onRetry={reload} />;

  const { product, summary, reviews } = data;
  return (
    <Screen>
      <View style={styles.imageWrap}>
        <ProductImage uri={product.image_url} name={product.name} />
      </View>
      <Text style={typography.title}>{product.name}</Text>
      <Text style={styles.price}>{rupees(product.price)}</Text>
      {summary && summary.count > 0 && summary.average !== null ? (
        <Text style={typography.body}>★ {summary.average.toFixed(1)} ({summary.count} reviews)</Text>
      ) : (
        <Text style={typography.caption}>No reviews yet</Text>
      )}
      {product.description ? <Text style={typography.body}>{product.description}</Text> : null}
      {!product.is_available ? <Text style={styles.unavailable}>Currently unavailable</Text> : null}
      {reviews.length > 0 ? <Text style={typography.heading}>Reviews</Text> : null}
      {reviews.map((r) => (
        <View key={r.id} style={styles.review}>
          <Text style={typography.body}>{"★".repeat(r.rating)}  {r.reviewer_name}</Text>
          {r.comment ? <Text style={typography.caption}>{r.comment}</Text> : null}
        </View>
      ))}
    </Screen>
  );
}

const styles = StyleSheet.create({
  imageWrap: { borderRadius: radius.lg, overflow: "hidden" },
  price: { ...typography.heading, color: colors.terracotta },
  unavailable: { ...typography.body, color: colors.danger },
  review: { backgroundColor: colors.card, borderRadius: radius.md, padding: spacing.md, gap: spacing.xs },
});
