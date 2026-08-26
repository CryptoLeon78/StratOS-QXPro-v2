// adapted to StratOS design_tokens.json -- pill radius, translucent
// semantic background per tokens.component.Badge / color.semantic (PARTE
// 11.2: "badges redondeados pequenos con fondo translucido del color
// semantico"). Semaphore states (verde/amarillo/naranja) reuse the same
// success/warning/orange semantic colors -- they are the same values.
import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-pill px-2 py-0.5 text-xs font-semibold transition-colors",
  {
    variants: {
      variant: {
        default: "bg-accent-primaryMuted text-accent-primary",
        success: "bg-semantic-successMuted text-semantic-success",
        warning: "bg-semantic-warningMuted text-semantic-warning",
        orange: "bg-semantic-orangeMuted text-semantic-orange",
        danger: "bg-semantic-dangerMuted text-semantic-danger",
        info: "bg-semantic-infoMuted text-semantic-info",
        outline: "border border-border-subtle text-text-secondary",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
