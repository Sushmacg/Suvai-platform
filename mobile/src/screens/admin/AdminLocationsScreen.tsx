import { useState } from "react";
import { Alert, ScrollView, StyleSheet, Switch, Text, View } from "react-native";
import { api } from "../../api/client";
import { Button } from "../../components/Button";
import { LabeledInput } from "../../components/LabeledInput";
import { useLoad } from "../../hooks/useLoad";
import { colors, radius, shadow, spacing, typography } from "../../theme";

type Loc = { id: string; name: string; address: string | null; latitude: number; longitude: number; is_active: boolean };

// Reads coordinates from a long Google Maps link: .../@12.9,77.6,... or !3d12.9!4d77.6 or ?q=12.9,77.6
function coordsFromLink(text: string): [number, number] | null {
  const m =
    text.match(/@(-?\d+\.?\d*),(-?\d+\.?\d*)/) ||
    text.match(/!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)/) ||
    text.match(/[?&](?:q|query|ll)=(-?\d+\.?\d*),(-?\d+\.?\d*)/);
  return m ? [parseFloat(m[1]), parseFloat(m[2])] : null;
}

const fail = (e: unknown) => Alert.alert("Could not save", e instanceof Error ? e.message : "Try again");

export function AdminLocationsScreen() {
  const { data, loading, error, reload } = useLoad<Loc[]>(() => api.get<Loc[]>("/stalls/locations/all"), []);
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [link, setLink] = useState("");
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [busy, setBusy] = useState(false);

  const onLink = (t: string) => {
    setLink(t);
    const c = coordsFromLink(t);
    if (c) { setLat(String(c[0])); setLng(String(c[1])); }
    else if (/^https?:\/\//i.test(t.trim())) {
      fetch(t.trim())
        .then((r) => {
          const found = coordsFromLink(decodeURIComponent(r.url));
          if (found) { setLat(String(found[0])); setLng(String(found[1])); }
          else Alert.alert("No coordinates found", "Type latitude and longitude by hand.");
        })
        .catch(() => {});
    }
  };

  const save = async () => {
    if (busy) return;
    const la = parseFloat(lat), lo = parseFloat(lng);
    if (name.trim().length < 2) return Alert.alert("Name needed", "Enter at least 2 characters.");
    if (!(la >= -90 && la <= 90) || !(lo >= -180 && lo <= 180))
      return Alert.alert("Check coordinates", "Paste a long Google Maps link, or type latitude (-90 to 90) and longitude (-180 to 180).");
    setBusy(true);
    try {
      await api.post("/stalls/locations", { name: name.trim(), address: address.trim() || null, latitude: la, longitude: lo });
      setName(""); setAddress(""); setLink(""); setLat(""); setLng("");
      reload();
    } catch (e) { fail(e); } finally { setBusy(false); }
  };

  const toggle = async (l: Loc, v: boolean) => {
    try { await api.patch(`/stalls/locations/${l.id}`, { is_active: v }); reload(); } catch (e) { fail(e); }
  };

  return (
    <ScrollView style={{ backgroundColor: colors.cream }} contentContainerStyle={styles.content}>
      <Text style={typography.title}>Add a location</Text>
      <View style={styles.card}>
        <LabeledInput label="Name" value={name} onChangeText={setName} placeholder="e.g. College Gate" />
        <LabeledInput label="Address (optional)" value={address} onChangeText={setAddress} />
        <LabeledInput label="Google Maps link (optional, long link)" value={link} onChangeText={onLink} autoCapitalize="none" autoCorrect={false} />
        <LabeledInput label="Latitude" value={lat} onChangeText={setLat} keyboardType="numbers-and-punctuation" />
        <LabeledInput label="Longitude" value={lng} onChangeText={setLng} keyboardType="numbers-and-punctuation" />
        <Button title={busy ? "Saving..." : "Add location"} onPress={save} />
      </View>

      <Text style={typography.heading}>All locations</Text>
      {loading && <Text style={typography.caption}>Loading...</Text>}
      {error && <Text style={typography.caption}>Could not load locations.</Text>}
      {data?.map((l) => (
        <View key={l.id} style={[styles.card, styles.row]}>
          <View style={{ flex: 1 }}>
            <Text style={typography.heading}>{l.name}</Text>
            {!!l.address && <Text style={typography.caption}>{l.address}</Text>}
            <Text style={typography.caption}>{l.latitude.toFixed(5)}, {l.longitude.toFixed(5)}</Text>
            <Text style={typography.caption}>{l.is_active ? "Shown to customers" : "Hidden"}</Text>
          </View>
          <Switch value={l.is_active} onValueChange={(v) => toggle(l, v)} />
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md },
  card: { backgroundColor: colors.card, borderRadius: radius.md, padding: spacing.lg, gap: spacing.sm, ...shadow.card },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md },
});