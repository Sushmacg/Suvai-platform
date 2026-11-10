import { Link } from "react-router-dom";
import { btn } from "../components/ui";
import { StallNow } from "../components/StallNow";

const HEART = "M50 88 C20 66 6 48 6 30 C6 16 17 8 29 8 C38 8 46 13 50 21 C54 13 62 8 71 8 C83 8 94 16 94 30 C94 48 80 66 50 88 Z";

function HeroHeart() {
  return (
    <svg viewBox="0 0 100 100" className="float w-full max-w-md drop-shadow-xl" role="img" aria-label="A heart-shaped nankhatai">
      <defs>
        <radialGradient id="hh" cx=".32" cy=".25" r=".95">
          <stop offset="0" stopColor="#FFD98E" /><stop offset=".55" stopColor="#E9A94B" /><stop offset="1" stopColor="#A8691F" />
        </radialGradient>
        <clipPath id="hc"><path d={HEART} /></clipPath>
      </defs>
      <path d={HEART} fill="url(#hh)" stroke="#A8691F" strokeWidth="1.2" />
      <g clipPath="url(#hc)" opacity=".5">
        {Array.from({ length: 60 }, (_, i) => (
          <circle key={i} cx={10 + ((i * 37) % 80)} cy={12 + ((i * 53) % 72)} r="2.6" fill="#FFD98E" stroke="#A8691F" strokeOpacity=".35" strokeWidth=".4" />
        ))}
      </g>
      <ellipse cx="33" cy="22" rx="15" ry="6" fill="#fff" opacity=".25" transform="rotate(-28 33 22)" />
      <ellipse cx="50" cy="38" rx="7" ry="2.8" fill="#7FA650" transform="rotate(-20 50 38)" />
      <ellipse cx="43" cy="47" rx="6" ry="2.4" fill="#9BC46B" transform="rotate(35 43 47)" />
      <ellipse cx="58" cy="48" rx="5.5" ry="2.3" fill="#7FA650" transform="rotate(-50 58 48)" />
    </svg>
  );
}

const points = [
  ["Pure butter", "Rich, crumbly and made with natural ingredients."],
  ["Small batches", "Prepared with care in small batches, the time-honoured way."],
  ["Freshly baked", "No artificial colours or preservatives. Baked fresh for the stall."],
];

export function Home() {
  return (
    <>
      <section className="mx-auto grid max-w-6xl items-center gap-8 px-4 py-12 md:grid-cols-2 md:py-20">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-terracotta">Homemade with love</p>
          <h1 className="mt-3 text-5xl font-bold leading-tight md:text-6xl">Traditional <span className="text-terracotta">nankatai</span>, shaped like a heart.</h1>
          <p className="mt-4 max-w-lg text-lg text-muted">Pick your flavour, see where our stall is today, and order ahead. Pay and collect at the stall.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/menu" className={btn("primary", "px-7 py-3 text-base")}>View the menu</Link>
            <Link to="/stalls" className={btn("ghost", "px-7 py-3 text-base")}>Find the stall</Link>
          </div>
        </div>
        <div className="flex justify-center"><HeroHeart /></div>
      </section>

      <StallNow />
      <section className="bg-surface py-14">
        <div className="mx-auto grid max-w-6xl gap-6 px-4 md:grid-cols-3">
          {points.map(([t, d]) => (
            <div key={t} className="rounded-2xl border border-line bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-md">
              <h2 className="text-xl font-bold text-terracotta">{t}</h2>
              <p className="mt-2 text-muted">{d}</p>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}