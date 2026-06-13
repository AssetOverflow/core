import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "../../lib";

const buttonVariants = cva(
  "inline-flex h-[var(--density-button-height)] items-center justify-center gap-[var(--density-control-gap)] rounded-md border px-[var(--density-control-padding-x)] text-sm font-medium transition-colors motion-standard focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary:
          "border-[var(--color-border-strong)] bg-[var(--color-surface-overlay)] text-[var(--color-text-primary)] hover:bg-[var(--color-surface-raised)]",
        quiet:
          "border-[var(--color-border-subtle)] bg-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]",
      },
    },
    defaultVariants: { variant: "primary" },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant, asChild, ...props },
  ref,
) {
  const Comp = asChild ? Slot : "button";
  return <Comp ref={ref} className={cn(buttonVariants({ variant }), className)} {...props} />;
});
