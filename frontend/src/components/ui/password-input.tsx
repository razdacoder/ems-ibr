import * as React from "react";
import { Eye, EyeOff } from "lucide-react";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

/**
 * Password field with a show/hide toggle. Forwards every native input prop
 * (so it drops straight into react-hook-form `field` spreads); the `type` is
 * managed internally and any incoming `type` is ignored.
 */
function PasswordInput({
  className,
  type: _ignored,
  ...props
}: React.ComponentProps<"input">) {
  const [visible, setVisible] = React.useState(false);

  return (
    <div className="relative">
      <Input
        type={visible ? "text" : "password"}
        className={cn("pr-10", className)}
        {...props}
      />
      <button
        type="button"
        onClick={() => setVisible((v) => !v)}
        tabIndex={-1}
        aria-label={visible ? "Hide password" : "Show password"}
        aria-pressed={visible}
        className="absolute right-0 top-0 grid h-full w-10 place-items-center text-muted-foreground transition-colors hover:text-foreground focus-visible:text-foreground focus-visible:outline-none"
      >
        {visible ? (
          <EyeOff className="size-4" strokeWidth={2} />
        ) : (
          <Eye className="size-4" strokeWidth={2} />
        )}
      </button>
    </div>
  );
}

export { PasswordInput };
