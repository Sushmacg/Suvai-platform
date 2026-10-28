import { Pressable, ScrollView, StyleSheet, Text } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { ManageStackParamList } from "../../navigation/ManageStack";
import { colors, radius, shadow, spacing, typography } from "../../theme";

type Props = NativeStackScreenProps<ManageStackParamList, "ManageHome">;

const ITEMS = [
  { to: "Sessions", title: "Stall sessions", hint: "Schedule visits, open and close the stall" },
  { to: "Stock", title: "Stock", hint: "Set how many packs each product has per session" },
  { to: "Expenses", title: "Expenses", hint: "Record costs and see the 30-day total" },
  { to: "Locations", title: "Locations", hint: "Add stall places and choose which customers see" },
] as const;

export function ManageHomeScreen({ navigation }: Props) {
  return (
    <ScrollView style={{ backgroundColor: colors.cream }} contentContainerStyle={styles.content}>
      <Text style={typography.title}>Manage</Text>
      {ITEMS.map((item) => (
        <Pressable
          key={item.to}
          onPress={() => navigation.navigate(item.to)}
          accessibilityRole="button"
          style={({ pressed }) => [styles.card, { opacity: pressed ? 0.8 : 1 }]}
        >
          <Text style={typography.heading}>{item.title}</Text>
          <Text style={typography.caption}>{item.hint}</Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md },
  card: { backgroundColor: colors.card, borderRadius: radius.md, padding: spacing.lg, gap: spacing.xs, ...shadow.card },
});