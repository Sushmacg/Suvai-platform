import { GIFT, HEART, PALETTE, bumps, flavorOf, toppings } from "./cookieShapes";
import type { Shape } from "./cookieShapes";

const SEEDS = { classic: 11, elaichi: 23, jaggery: 37, dryfruit: 41, ajwain: 59 } as const;
const BUMPS = Object.fromEntries(Object.entries(SEEDS).map(([f, s]) => [f, bumps(s, `bump-${f}`)]));

function Draw({ shapes }: { shapes: Shape[] }) {
  return (
    <>
      {shapes.map((s, i) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const p = s.props as any;
        if (s.tag === "path") return <path key={i} {...p} />;
        if (s.tag === "circle") return <circle key={i} {...p} />;
        if (s.tag === "ellipse") return <ellipse key={i} {...p} />;
        return <rect key={i} {...p} />;
      })}
    </>
  );
}

// Original illustration of a heart-shaped nankhatai, chosen by flavour from the product name.
export function NankhataiArt({ name, className = "" }: { name: string; className?: string }) {
  const f = flavorOf(name);
  if (f === "gift") {
    return <svg viewBox="0 0 100 100" className={className} role="img" aria-label={name}><Draw shapes={GIFT} /></svg>;
  }
  const [light, base, dark] = PALETTE[f];
  return (
    <svg viewBox="0 0 100 100" className={className} role="img" aria-label={name}>
      <defs>
        <radialGradient id={`body-${f}`} cx=".32" cy=".25" r=".95">
          <stop offset="0" stopColor={light} /><stop offset=".55" stopColor={base} /><stop offset="1" stopColor={dark} />
        </radialGradient>
        <radialGradient id={`bump-${f}`} cx=".35" cy=".3" r=".75">
          <stop offset="0" stopColor={light} /><stop offset=".6" stopColor={base} /><stop offset="1" stopColor={dark} stopOpacity=".55" />
        </radialGradient>
        <clipPath id={`clip-${f}`}><path d={HEART} /></clipPath>
      </defs>
      <ellipse cx="50" cy="92" rx="30" ry="3.6" fill="#00000026" />
      <path d={HEART} fill={`url(#body-${f})`} stroke={dark} strokeWidth="1.2" />
      <g clipPath={`url(#clip-${f})`} opacity=".9"><Draw shapes={BUMPS[f]} /></g>
      <path d={HEART} fill="none" stroke="#FFFFFF" strokeOpacity=".28" strokeWidth="1.4" transform="translate(3.5, 3.4) scale(0.93)" />
      <ellipse cx="33" cy="22" rx="15" ry="6" fill="#FFFFFF" opacity=".25" transform="rotate(-28, 33, 22)" />
      <Draw shapes={toppings(f)} />
    </svg>
  );
}