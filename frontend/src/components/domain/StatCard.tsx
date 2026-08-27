import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

// PARTE 11.3: AppHeader, 6 StatCard. Padding/radius/tamanos de
// tokens.component.StatCard resueltos a clases Tailwind del theme
// generado (p-3.5/py-3.5 ~= 0.875rem, rounded-md, text-xs label,
// text-stat valor).
interface StatCardProps {
  label: string;
  value: ReactNode;
  valueClassName?: string;
  subtext?: ReactNode;
}

export function StatCard({ label, value, valueClassName, subtext }: StatCardProps) {
  return (
    <div className="flex flex-col gap-1 rounded-md border border-border-subtle bg-bg-surface px-4 py-3.5">
      <span className="text-xs font-medium text-text-secondary">{label}</span>
      <span className={cn("text-stat font-semibold tabular-nums text-text-primary", valueClassName)}>
        {value}
      </span>
      {subtext && <span className="text-xs text-text-secondary">{subtext}</span>}
    </div>
  );
}
