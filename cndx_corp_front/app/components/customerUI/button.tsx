import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "~/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 font-bold text-sm whitespace-nowrap transition-colors cursor-pointer rounded border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-white text-gray-900 border-gray-400 hover:bg-gray-100 active:bg-gray-200",
        primary: "bg-green-primary text-white border-green-400 hover:bg-teal-700 active:bg-teal-900",
        secondary:
          "bg-white text-teal-700 border-teal-600 hover:bg-green-50 active:bg-green-100 shadow hover:shadow-md",
        destructive:
          "bg-red-600 text-white border-red-600 hover:bg-red-700 active:bg-red-800",
      },
      size: {
        default: "h-9 px-3",
        sm: "h-8 px-2 text-sm",
        lg: "h-[36px] px-[12px] text-base", // ← 元のCSSの設定
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "lg", // 元のCSSは button-height: 36px
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <div className="gap-2 bg-green-primary">
        <Comp
          className={cn(buttonVariants({ variant, size, className }))}
          ref={ref}
          {...props}
        />
      </div>
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
