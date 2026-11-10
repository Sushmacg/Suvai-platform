export type Flavor = "classic" | "elaichi" | "jaggery" | "dryfruit" | "ajwain" | "gift";
export type Shape = { tag: "path" | "circle" | "ellipse" | "rect"; props: Record<string, string | number> };

export const HEART =
  "M50 88 C20 66 6 48 6 30 C6 16 17 8 29 8 C38 8 46 13 50 21 C54 13 62 8 71 8 C83 8 94 16 94 30 C94 48 80 66 50 88 Z";

// [light, base, dark]
export const PALETTE: Record<Exclude<Flavor, "gift">, [string, string, string]> = {
  classic: ["#FFD98E", "#E9A94B", "#A8691F"],
  elaichi: ["#FBE7B0", "#E8C378", "#A98238"],
  jaggery: ["#E0A66A", "#B87636", "#6E4018"],
  dryfruit: ["#FFD58A", "#E3A049", "#9E651C"],
  ajwain: ["#F6DDA6", "#DDB268", "#9A7634"],
};

export function flavorOf(name: string): Flavor {
  const n = name.toLowerCase();
  if (/gift|box|hamper/.test(n)) return "gift";
  if (/elaichi|cardamom/.test(n)) return "elaichi";
  if (/jaggery|gud/.test(n)) return "jaggery";
  if (/dry ?fruit|nut/.test(n)) return "dryfruit";
  if (/ajwain|carom/.test(n)) return "ajwain";
  return "classic";
}

const e = (cx: number, cy: number, rx: number, ry: number, fill: string, rot = 0, extra = {}): Shape => ({
  tag: "ellipse",
  props: { cx, cy, rx, ry, fill, ...(rot ? { transform: `rotate(${rot}, ${cx}, ${cy})` } : {}), ...extra },
});

const inHeart = (x: number, y: number) =>
  Math.hypot(x - 29, y - 30) <= 24 || Math.hypot(x - 71, y - 30) <= 24 ||
  (y >= 28 && y <= 88 && Math.abs(x - 50) <= ((88 - y) * 44) / 52);

// Fixed pseudo-random bumps so every render looks the same (the textured nankhatai surface).
export function bumps(seed: number, gradientId: string): Shape[] {
  let s = seed;
  const rnd = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  const pts: [number, number][] = [];
  for (let i = 0; i < 900 && pts.length < 150; i++) {
    const x = 6 + rnd() * 88, y = 8 + rnd() * 80;
    if (inHeart(x, y) && pts.every(([a, b]) => Math.hypot(a - x, b - y) > 5.2)) pts.push([x, y]);
  }
  return pts.map(([x, y]) => ({ tag: "circle", props: { cx: x, cy: y, r: 2.9 + rnd() * 0.9, fill: `url(#${gradientId})` } }));
}

const PIST = "#7FA650", PIST2 = "#9BC46B", ALM = "#F8E7C4";
const dots = (pts: number[][], rx: number, fill: string): Shape[] =>
  pts.map(([x, y, a = 0]) => e(x, y, rx, rx * 0.6, fill, a));

export function toppings(f: Exclude<Flavor, "gift">): Shape[] {
  switch (f) {
    case "classic":
      return [e(50, 36, 7, 2.8, PIST, -20), e(43, 45, 6, 2.4, PIST2, 35), e(58, 46, 5.5, 2.3, PIST, -50)];
    case "elaichi":
      return [
        ...[[40, 33, -30], [60, 35, 25], [50, 48, 70]].flatMap(([x, y, a]) => [
          e(x, y, 5.2, 2.4, "#8DB36A", a, { stroke: "#4B6B2A", strokeWidth: 0.5 }),
          e(x, y, 1.2, 0.8, "#2F4A18", a),
        ]),
      ];
    case "jaggery":
      return dots([[28, 28], [40, 22], [60, 24], [72, 30], [50, 40], [36, 44], [64, 46], [50, 58], [42, 32], [58, 32]], 1.6, "#4A2A10AA");
    case "dryfruit":
      return [
        ...[[34, 31, -30], [63, 33, 30], [50, 47, 80]].map(([x, y, a]) => e(x, y, 6.2, 2.8, ALM, a, { stroke: "#C9A56A", strokeWidth: 0.6 })),
        e(44, 38, 4.5, 2, PIST, 10), e(57, 49, 4.5, 2, PIST2, -40), e(70, 40, 4, 1.8, PIST, 50),
      ];
    default:
      return dots([[30, 26, 20], [42, 20, -30], [60, 22, 40], [72, 28, -10], [36, 38, 60], [50, 32], [64, 40, 30], [46, 48, -45], [56, 56, 20], [40, 30, 70], [52, 44, -20]], 1.8, "#5E4E1ECC");
  }
}

// Gift box: front, lid, ribbon, bow and a heart peeking out.
export const GIFT: Shape[] = [
  e(50, 92, 34, 3.6, "#00000026"),
  { tag: "path", props: { d: HEART, fill: "#E9A94B", stroke: "#A8691F", strokeWidth: 1.2, transform: "translate(25, 6) scale(0.5) rotate(-12, 50, 50)" } },
  { tag: "rect", props: { x: 12, y: 46, width: 76, height: 42, rx: 5, fill: "#C4572E", stroke: "#8E3A1B", strokeWidth: 1.5 } },
  { tag: "rect", props: { x: 12, y: 46, width: 76, height: 10, rx: 4, fill: "#00000022" } },
  { tag: "rect", props: { x: 8, y: 36, width: 84, height: 14, rx: 4, fill: "#E0714A", stroke: "#8E3A1B", strokeWidth: 1.5 } },
  { tag: "rect", props: { x: 8, y: 37, width: 84, height: 4, rx: 2, fill: "#FFFFFF44" } },
  { tag: "rect", props: { x: 45, y: 36, width: 10, height: 52, fill: "#F2B632" } },
  { tag: "path", props: { d: "M50 36 C38 20 26 28 36 36 Z", fill: "#F7C948", stroke: "#B8860B", strokeWidth: 1 } },
  { tag: "path", props: { d: "M50 36 C62 20 74 28 64 36 Z", fill: "#F7C948", stroke: "#B8860B", strokeWidth: 1 } },
];