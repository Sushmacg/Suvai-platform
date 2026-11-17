import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import { imageUrl } from "../utils/format";

export type StoredImage = { id: string; url: string; position: number };
const TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_BYTES = 5 * 1024 * 1024;
const MAX_IMAGES = 10;

type Props = {
  existing: StoredImage[];
  pending: File[];
  onPick: (files: File[]) => void;
  onRemovePending: (index: number) => void;
  onCover: (id: string) => void;
  onRemove: (id: string) => void;
  busy: boolean;
};

const badge = "absolute left-1 top-1 rounded-full px-2 py-0.5 text-[10px] font-semibold text-white";

export function ImageManager({ existing, pending, onPick, onRemovePending, onCover, onRemove, busy }: Props) {
  const [error, setError] = useState("");
  const previews = useMemo(() => pending.map((f) => URL.createObjectURL(f)), [pending]);
  useEffect(() => () => previews.forEach((u) => URL.revokeObjectURL(u)), [previews]);

  function choose(e: ChangeEvent<HTMLInputElement>) {
    const picked = Array.from(e.target.files ?? []);
    e.target.value = "";
    const room = MAX_IMAGES - existing.length - pending.length;
    const ok: File[] = [];
    const problems: string[] = [];
    for (const f of picked) {
      if (!TYPES.includes(f.type)) problems.push(`${f.name}: only JPG, PNG or WebP`);
      else if (f.size > MAX_BYTES) problems.push(`${f.name}: larger than 5 MB`);
      else if (ok.length >= room) problems.push(`${f.name}: limit of ${MAX_IMAGES} images`);
      else ok.push(f);
    }
    setError(problems.join(". "));
    if (ok.length) onPick(ok);
  }

  return (
    <div>
      <p className="mb-2 text-sm font-medium">Photos <span className="font-normal text-muted">(the first is the cover; with none, the illustration is shown)</span></p>
      <ul className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-5">
        {existing.map((img, i) => (
          <li key={img.id} className="relative overflow-hidden rounded-xl border border-line bg-white">
            <img src={imageUrl(img.url) ?? ""} alt={`Product photo ${i + 1}`} className="aspect-square w-full object-cover" />
            {i === 0 && <span className={`${badge} bg-terracotta`}>Cover</span>}
            <div className="flex justify-between gap-1 p-1.5 text-xs">
              {i > 0 ? <button type="button" disabled={busy} className="text-terracotta underline" onClick={() => onCover(img.id)}>Make cover</button> : <span />}
              <button type="button" disabled={busy} className="text-bad underline" onClick={() => onRemove(img.id)}>Remove</button>
            </div>
          </li>
        ))}
        {pending.map((f, i) => (
          <li key={`${f.name}-${i}`} className="relative overflow-hidden rounded-xl border border-saffron bg-white">
            <img src={previews[i]} alt={`New photo ${f.name}`} className="aspect-square w-full object-cover" />
            <span className={`${badge} bg-saffron`}>New</span>
            <div className="flex justify-end p-1.5 text-xs">
              <button type="button" className="text-bad underline" onClick={() => onRemovePending(i)}>Remove</button>
            </div>
          </li>
        ))}
        {existing.length + pending.length < MAX_IMAGES && (
          <li>
            <label className="flex aspect-square cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-line text-sm font-semibold text-terracotta hover:bg-saffron-soft focus-within:ring-2 focus-within:ring-saffron/50">
              <span className="text-3xl leading-none">+</span>
              Add images
              <input type="file" multiple accept="image/jpeg,image/png,image/webp" className="sr-only" onChange={choose} />
            </label>
          </li>
        )}
      </ul>
      {error && <p className="mt-2 text-sm text-bad">{error}</p>}
      {pending.length > 0 && <p className="mt-2 text-xs text-muted">{pending.length} new {pending.length === 1 ? "image" : "images"} will upload when you press Save.</p>}
    </div>
  );
}