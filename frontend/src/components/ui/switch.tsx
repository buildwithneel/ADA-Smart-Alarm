import { forwardRef, ButtonHTMLAttributes } from "react";
import { motion } from "framer-motion";
import { cn } from "@/core/utils/cn";
import { switchThumbVariants } from "@/core/animations/variants";

export interface SwitchProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "onChange"> {
  checked: boolean;
  onCheckedChange?: (checked: boolean) => void;
  label?: string;
  description?: string;
}

export const Switch = forwardRef<HTMLButtonElement, SwitchProps>(
  ({ className, checked, onCheckedChange, label, description, disabled, id, ...props }, ref) => {
    return (
      <div className="flex items-center justify-between gap-4">
        {(label || description) && (
          <div className="text-left cursor-pointer" onClick={() => !disabled && onCheckedChange?.(!checked)}>
            {label && <label htmlFor={id} className="block text-xs font-semibold text-slate-200 select-none cursor-pointer">{label}</label>}
            {description && <p className="text-[11px] text-slate-400 select-none">{description}</p>}
          </div>
        )}
        <button
          id={id}
          ref={ref}
          type="button"
          role="switch"
          aria-checked={checked}
          disabled={disabled}
          onClick={() => onCheckedChange?.(!checked)}
          className={cn(
            "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border border-transparent p-0.5 transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50 disabled:cursor-not-allowed disabled:opacity-50",
            checked ? "bg-brand-600" : "bg-slate-800",
            className
          )}
          {...props}
        >
          <motion.span
            variants={switchThumbVariants}
            animate={checked ? "on" : "off"}
            className="pointer-events-none block h-4 w-4 rounded-full bg-white shadow-md"
          />
        </button>
      </div>
    );
  }
);

Switch.displayName = "Switch";
