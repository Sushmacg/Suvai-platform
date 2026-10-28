import { useEffect, useRef } from "react";
import { Animated, Easing } from "react-native";
import Svg, { Circle, ClipPath, Defs, Ellipse, G, Path, RadialGradient, Rect, Stop } from "react-native-svg";
import { GIFT, HEART, PALETTE, bumps, flavorOf, toppings } from "./cookieShapes";
import type { Shape } from "./cookieShapes";

const EL = { path: Path, circle: Circle, ellipse: Ellipse, rect: Rect };
const SEEDS = { classic: 11, elaichi: 23, jaggery: 37, dryfruit: 41, ajwain: 59 } as const;
const BUMPS = Object.fromEntries(Object.entries(SEEDS).map(([f, s]) => [f, bumps(s, `bump-${f}`)]));

const draw = (shapes: Shape[]) =>
  shapes.map((s, i) => {
    const Tag: any = EL[s.tag];
    return <Tag key={i} {...s.props} />;
  });

export function NankhataiImage({ name, size = 96, animate = true }: { name: string; size?: number; animate?: boolean }) {
  const f = flavorOf(name);
  const t = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!animate) return;
    const d = 1500 + (name.length % 5) * 200;
    const step = (v: number) => Animated.timing(t, { toValue: v, duration: d, easing: Easing.inOut(Easing.sin), useNativeDriver: true });
    const loop = Animated.loop(Animated.sequence([step(1), step(0)]));
    loop.start();
    return () => loop.stop();
  }, [animate, name, t]);

  let content;
  if (f === "gift") {
    content = draw(GIFT);
  } else {
    const [light, base, dark] = PALETTE[f];
    content = (
      <>
        <Defs>
          <RadialGradient id={`body-${f}`} cx="0.32" cy="0.25" r="0.95">
            <Stop offset="0" stopColor={light} />
            <Stop offset="0.55" stopColor={base} />
            <Stop offset="1" stopColor={dark} />
          </RadialGradient>
          <RadialGradient id={`bump-${f}`} cx="0.35" cy="0.3" r="0.75">
            <Stop offset="0" stopColor={light} />
            <Stop offset="0.6" stopColor={base} />
            <Stop offset="1" stopColor={dark} stopOpacity={0.55} />
          </RadialGradient>
          <ClipPath id={`clip-${f}`}>
            <Path d={HEART} />
          </ClipPath>
        </Defs>
        <Ellipse cx={50} cy={92} rx={30} ry={3.6} fill="#00000026" />
        <Path d={HEART} fill={`url(#body-${f})`} stroke={dark} strokeWidth={1.2} />
        <G clipPath={`url(#clip-${f})`} opacity={0.9}>{draw(BUMPS[f])}</G>
        <Path d={HEART} fill="none" stroke="#FFFFFF" strokeOpacity={0.28} strokeWidth={1.4} transform="translate(3.5, 3.4) scale(0.93)" />
        <Ellipse cx={33} cy={22} rx={15} ry={6} fill="#FFFFFF" opacity={0.25} transform="rotate(-28, 33, 22)" />
        {draw(toppings(f))}
      </>
    );
  }

  const lift = t.interpolate({ inputRange: [0, 1], outputRange: [0, -size * 0.06] });
  const tilt = t.interpolate({ inputRange: [0, 1], outputRange: ["-3deg", "3deg"] });
  return (
    <Animated.View style={{ width: size, height: size, transform: [{ translateY: lift }, { rotate: tilt }] }}>
      <Svg width={size} height={size} viewBox="0 0 100 100">{content}</Svg>
    </Animated.View>
  );
}