import { useState } from "react";
import { Image, StyleSheet, View } from "react-native";
import { API_URL } from "../config";
import { colors } from "../theme";
import { NankhataiImage } from "./NankhataiImage";

export function ProductImage({ uri, name }: { uri: string | null; name: string }) {
  const [failed, setFailed] = useState(false);
  const [side, setSide] = useState(0);
  const full = uri ? (uri.startsWith("/") ? `${API_URL}${uri}` : uri) : null;

  if (!full || failed) {
    return (
      <View style={styles.fallback} onLayout={(e) => setSide(e.nativeEvent.layout.width)}>
        {side > 0 && <NankhataiImage name={name} size={side * 0.78} />}
      </View>
    );
  }
  return <Image source={{ uri: full }} style={styles.image} onError={() => setFailed(true)} />;
}

const styles = StyleSheet.create({
  image: { width: "100%", aspectRatio: 1, backgroundColor: colors.saffronSoft },
  fallback: { width: "100%", aspectRatio: 1, backgroundColor: colors.saffronSoft, alignItems: "center", justifyContent: "center" },
  initial: { fontSize: 44, fontWeight: "700", color: colors.terracotta },
});
