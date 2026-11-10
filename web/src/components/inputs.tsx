import type { ReactNode } from "react";

export const inp = "w-full rounded-xl border border-line bg-white px-3 py-2.5 outline-none focus:border-terracotta focus:ring-2 focus:ring-saffron/40";

export const Label = ({ text, children }: { text: string; children: ReactNode }) => (
  <label className="block text-sm"><span className="mb-1 block font-medium">{text}</span>{children}</label>
);