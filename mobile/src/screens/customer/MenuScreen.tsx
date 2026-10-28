import { FlatList, StyleSheet } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { api } from "../../api/client";
import type { Product } from "../../api/models";
import { EmptyView, ErrorView, LoadingView } from "../../components/States";
import { ProductCard } from "../../components/ProductCard";
import { useLoad } from "../../hooks/useLoad";
import type { MenuStackParamList } from "../../navigation/MenuStack";
import { colors, spacing } from "../../theme";

type Props = NativeStackScreenProps<MenuStackParamList, "MenuList">;

export function MenuScreen({ navigation }: Props) {
  const { data, loading, refreshing, error, reload, refresh } = useLoad(
    () => api.get<Product[]>("/products", { auth: false }),
  );

  if (loading) return <LoadingView />;
  if (error && !data) return <ErrorView message={error} onRetry={reload} />;

  return (
    <FlatList
      style={{ backgroundColor: colors.cream }}
      data={data ?? []}
      keyExtractor={(p) => p.id}
      numColumns={2}
      columnWrapperStyle={styles.row}
      contentContainerStyle={styles.list}
      refreshing={refreshing}
      onRefresh={refresh}
      ListEmptyComponent={<EmptyView title="The menu is empty" hint="Please check back soon." />}
      renderItem={({ item }) => (
        <ProductCard product={item} onPress={() => navigation.navigate("ProductDetail", { productId: item.id, name: item.name })} />
      )}
    />
  );
}

const styles = StyleSheet.create({
  list: { padding: spacing.lg, gap: spacing.md, flexGrow: 1 },
  row: { gap: spacing.md },
});
