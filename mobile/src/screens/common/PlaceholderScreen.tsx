import { Text } from "react-native";
import { Screen } from "../../components/Screen";
import { typography } from "../../theme";

export function PlaceholderScreen({ title }: { title: string }) {
  return (
    <Screen>
      <Text style={typography.title}>{title}</Text>
      <Text style={typography.caption}>This screen arrives in the next batch.</Text>
    </Screen>
  );
}
