import { HTMLAttributes, forwardRef } from "react";
import { cn } from "@/core/utils/cn";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  glass?: boolean;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, glass = true, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "rounded-2xl p-5 transition-all duration-300",
          glass
            ? "glass-card border border-white/10 dark:border-white/5 shadow-2xl"
            : "bg-slate-900 border border-slate-800",
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = "Card";
