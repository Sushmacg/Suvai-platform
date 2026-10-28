import { Text } from "react-native";
import { useAuth } from "../../auth/AuthContext";
import { Button } from "../../components/Button";
import { Screen } from "../../components/Screen";
import { typography } from "../../theme";

export function ProfileScreen() {
  const { user, logout } = useAuth();
  return (
    <Screen>
      <Text style={typography.title}>{user?.name ?? "Profile"}</Text>
      <Text style={typography.body}>{user?.phone}</Text>
      <Text style={typography.caption}>Signed in as {user?.role}</Text>
      <Button title="Log out" variant="secondary" onPress={logout} />
    </Screen>
  );
}
