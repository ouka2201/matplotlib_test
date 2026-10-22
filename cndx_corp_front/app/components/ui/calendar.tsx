import { ChevronLeft, ChevronRight } from "lucide-react";
import * as React from "react";
import { DayPicker } from "react-day-picker";

import { ja } from "date-fns/locale";
import { buttonVariants } from "~/components/ui/button";
import { cn } from "~/lib/utils";

export type CalendarProps = React.ComponentProps<typeof DayPicker>;

function Calendar({
  className,
  classNames,
  showOutsideDays = true,
  fixedWeeks = true,
  ...props
}: CalendarProps) {
  return (
    <DayPicker
      locale={ja}
      showOutsideDays={showOutsideDays}
      fixedWeeks={fixedWeeks}
      className={cn("px-2 py-3 w-full", className)}
      classNames={{
        months: "flex flex-col",
        month: "space-y-4 w-full",

        caption: "flex justify-center items-center relative pt-1",
        caption_label: "text-sm font-medium",

        nav: "flex items-center space-x-1",
        nav_button: cn(
          buttonVariants({ variant: "outline" }),
          "h-8 w-8 bg-transparent p-0 opacity-70 hover:opacity-100 border-none shadow-none"
        ),
        nav_button_previous: "absolute left-1",
        nav_button_next: "absolute right-1",

        table: "w-full border-collapse",
        head_row: "flex w-full",
        head_cell:
          "w-9 h-9 text-[0.8rem] text-muted-foreground font-normal flex items-center justify-center",

        row: "flex w-full mt-1",
        cell: "h-9 w-9 text-center text-sm p-0 relative",

        day: cn(
          buttonVariants({ variant: "ghost" }),
          "h-9 w-9 p-0 font-normal rounded-full transition-colors aria-selected:opacity-100 hover:bg-accent hover:text-accent-foreground"
        ),

        day_selected:
          "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground focus:bg-primary focus:text-primary-foreground",

        day_today:
          "border border-primary text-primary bg-transparent",

        day_outside:
          "text-muted-foreground opacity-35",

        day_disabled:
          "text-muted-foreground opacity-30 cursor-not-allowed",

        day_hidden: "invisible",

        ...classNames,
      }}
      components={{
        IconLeft: ({ className, ...props }) => (
          <ChevronLeft className={cn("h-4 w-4", className)} {...props} />
        ),
        IconRight: ({ className, ...props }) => (
          <ChevronRight className={cn("h-4 w-4", className)} {...props} />
        ),
      }}
      {...props}
    />
  );
}

Calendar.displayName = "Calendar";

export { Calendar };

