export const colors = {
  cream: "#FBF4E6",
  surface: "#FFFAF0",
  card: "#FFFFFF",
  border: "#EADBC4",
  terracotta: "#C65D3B",
  terracottaDark: "#A64A2C",
  saffron: "#F4A300",
  saffronSoft: "#FCE9BF",
  text: "#3B2A20",
  muted: "#8A7565",
  success: "#4C8C4A",
  danger: "#B3392F",
  overlay: "rgba(59, 42, 32, 0.45)",
} as const;

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;

export const radius = { sm: 8, md: 14, lg: 22, pill: 999 } as const;

export const typography = {
  title: { fontSize: 28, fontWeight: "700", color: colors.text },
  heading: { fontSize: 20, fontWeight: "700", color: colors.text },
  body: { fontSize: 16, fontWeight: "400", color: colors.text },
  caption: { fontSize: 13, fontWeight: "400", color: colors.muted },
  button: { fontSize: 16, fontWeight: "600", color: "#FFFFFF" },
} as const;

export const shadow = {
  card: {
    shadowColor: "#3B2A20",
    shadowOpacity: 0.08,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 3,
  },
} as const;

export const motion = { fast: 160, normal: 260 } as const;