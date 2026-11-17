import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { FloatingCart } from "../components/FloatingCart";
import { NankhataiArt } from "../components/NankhataiArt";
import { StallNow } from "../components/StallNow";
import { btn } from "../components/ui";
import { Menu } from "./Menu";
import { Stalls } from "./Stalls";

export function Home() {
  const { hash, key } = useLocation();
  // Links like /#menu scroll to that section, from any page.
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: "smooth" });
    else window.scrollTo({ top: 0, behavior: "smooth" });
  }, [hash, key]);

  return (
    <>
      <section className="bg-cream">
        <div className="mx-auto grid max-w-6xl items-center gap-8 px-4 py-14 md:grid-cols-2 md:py-20">
          <div className="space-y-5">
            <p className="text-sm font-semibold uppercase tracking-widest text-terracotta">Suvai · nankhatai street stall</p>
            <h1 className="text-4xl font-bold leading-tight md:text-6xl">Heart-shaped nankhatai, made with love.</h1>
            <p className="max-w-md text-lg text-muted">Pick your favourites, order ahead, and collect them at the stall near you.</p>
            <div className="flex flex-wrap gap-3">
              <Link to="/#menu" className={btn("primary")}>See the menu</Link>
              <Link to="/#stalls" className={btn("ghost")}>Find the stall</Link>
            </div>
          </div>
          <div className="relative mx-auto flex w-full max-w-md items-center justify-center" aria-hidden="true">
            <NankhataiArt name="Elaichi Nankhatai" className="-mr-10 mt-10 w-1/3 -rotate-12" />
            <NankhataiArt name="Classic Nankhatai" className="float z-10 w-1/2" />
            <NankhataiArt name="Dry Fruit Nankhatai" className="-ml-10 mt-10 w-1/3 rotate-12" />
          </div>
        </div>
      </section>

      <StallNow />

      <section id="menu" className="scroll-mt-20"><Menu embedded /></section>
      <section id="stalls" className="scroll-mt-20 bg-surface"><Stalls embedded /></section>
      <FloatingCart />
    </>
  );
}