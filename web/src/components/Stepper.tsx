export function Stepper({ value, onChange, min = 1, max = 50 }: { value: number; onChange: (v: number) => void; min?: number; max?: number }) {
  return (
    <div className="inline-flex items-center rounded-full border border-line bg-white">
      <button type="button" aria-label="Decrease quantity" className="h-9 w-9 text-lg disabled:opacity-40" disabled={value <= min} onClick={() => onChange(value - 1)}>-</button>
      <span className="w-8 text-center text-sm font-semibold" aria-live="polite">{value}</span>
      <button type="button" aria-label="Increase quantity" className="h-9 w-9 text-lg disabled:opacity-40" disabled={value >= max} onClick={() => onChange(value + 1)}>+</button>
    </div>
  );
}