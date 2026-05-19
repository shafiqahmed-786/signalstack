import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "ghost";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-lg text-sm font-medium transition-colors focus:outline-none disabled:opacity-50 disabled:pointer-events-none",
          {
            "bg-ai text-black hover:opacity-90 px-4 py-2":
              variant === "default",

            "border border-border bg-card hover:bg-card-hover text-ink px-4 py-2":
              variant === "outline",

            "hover:bg-card text-ink px-3 py-2":
              variant === "ghost",
          },
          className
        )}
        {...props}
      />
    );
  }
);

Button.displayName = "Button";