import { useEffect, useRef } from "react";
import { Animated, Pressable, StyleSheet, Text, View } from "react-native";
import type { Product } from "../api/models";
import { rupees } from "../utils/format";
import { colors, motion, radius, shadow, spacing, typography } from "../theme";
import { ProductImage } from "./ProductImage";

export function ProductCard({ product, onPress }: { product: Product; onPress: () => void }) {
  const fade = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.timing(fade, { toValue: 1, duration: motion.normal, useNativeDriver: true }).start();
  }, [fade]);

  return (
    <Animated.View style={[styles.wrap, { opacity: fade }]}>
      <Pressable onPress={onPress} style={({ pressed }) => [styles.card, pressed && styles.pressed]}>
        <ProductImage uri={product.image_url} name={product.name} />
        <View style={styles.body}>
          <Text style={styles.name} numberOfLines={2}>{product.name}</Text>
          <Text style={styles.price}>{rupees(product.price)}</Text>
          {!product.is_available ? <Text style={styles.soldOut}>Currently unavailable</Text> : null}
        </View>
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1 },
  card: { backgroundColor: colors.card, borderRadius: radius.lg, overflow: "hidden", ...shadow.card },
  pressed: { transform: [{ scale: 0.98 }] },
  body: { padding: spacing.md, gap: spacing.xs },
  name: { ...typography.body, fontWeight: "600" },
  price: { ...typography.body, color: colors.terracotta, fontWeight: "700" },
  soldOut: { ...typography.caption, color: colors.danger },
});
