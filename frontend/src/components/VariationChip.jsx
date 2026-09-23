import { ArrowDownRight, ArrowUpRight } from "lucide-react";

/** Chip verde/rojo — exclusivamente para variaciones vs. una evaluación anterior. */
export default function VariationChip({ value, suffix = "%", variant }) {
  if (value === null || value === undefined) return null;
  const up = value >= 0;
  const cls = variant === "on-dark" ? (up ? "chip up" : "chip down") : `chip ${up ? "up" : "down"}`;
  const Icon = up ? ArrowUpRight : ArrowDownRight;
  return (
    <span className={cls}>
      <Icon size={13} strokeWidth={2.6} />
      {Math.abs(value).toFixed(1)}
      {suffix}
    </span>
  );
}
