import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@radix-ui/react-popover";
import { format } from "date-fns";
import { CalendarIcon } from "lucide-react";
import {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
  useState,
} from "react";
import { DateRange, Matcher } from "react-day-picker";
import { Control, FieldError, FieldValues, Path } from "react-hook-form";
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "~/components/ui/form";
import { Input } from "~/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "~/components/ui/select";
import { Messages } from "~/constants/messages/message";
import { cn } from "~/lib/utils";
import { Button } from "../customerUI/button";
import { Calendar } from "../ui/calendar";
import { Textarea } from "../ui/textarea";

interface Option {
  id: string;
  name: string;
}

type HTMLFieldProps =
  | InputHTMLAttributes<HTMLInputElement>
  | SelectHTMLAttributes<HTMLSelectElement>
  | TextareaHTMLAttributes<HTMLTextAreaElement>;

export type CustomFormFieldProps<T extends FieldValues> = {
  control: Control<T>;
  name: Path<T>;
  label: string;
  type?: string;
  placeholder?: string;
  required?: boolean;
  options?: Option[];
  renderCustom?: (field: any) => ReactNode;
  renderUnChange?: (field: any) => ReactNode;
  renderConfirmChange?: (field: any) => ReactNode;
  className?: string;
  triggerValidation?: (name: keyof T) => void;
  isEditing?: boolean;
  isConfirmation?: boolean;
  isInactive?: boolean;
  unit?: string;
  allowFutureDates?: boolean;
  specifiedDate?: Matcher | Matcher[];
  onValueChange?: (value: string) => void;
} & HTMLFieldProps;

export default function MasterFormField<T extends FieldValues>({
  control,
  name,
  label,
  type = "text",
  placeholder = "",
  required = false,
  options = [],
  renderCustom,
  renderUnChange,
  renderConfirmChange,
  className = "",
  triggerValidation,
  isEditing = true,
  isConfirmation = false,
  isInactive = false,
  unit,
  allowFutureDates = true,
  specifiedDate,
  ...props
}: CustomFormFieldProps<T>) {
  const [open, setOpen] = useState(false);
  return (
    <FormField
      control={control}
      name={name}
      render={({ field, fieldState }) => {
        const { error } = fieldState as { error?: FieldError };
        const disableFutureDates = allowFutureDates ? undefined : specifiedDate;
        const renderValue = () => {
          if (renderCustom) return renderCustom(field);

          if (options.length > 0) {
            const selectedOption = options.find(
              (option) => option.id === field.value
            );
            return selectedOption?.name ?? "";
          }

          if (
            typeof field.value === "object" &&
            field.value !== null &&
            "getTime" in field.value
          ) {
            return format(field.value as Date, "yyyy-MM-dd");
          }

          return field.value ?? "";
        };
        return (
          <FormItem
            className={`flex items-start ${isEditing ? "flex-col gap-1 min-h-[70px]" : "flex-row"
              } ${className}`}
          >
            {isEditing ? (
              <>
                <div className="flex items-center gap-2 min-h-[24px]">
                  <FormLabel className="text-left input-item-title">
                    {label}
                  </FormLabel>
                  {isEditing && required && (
                    <span className="required-mark">必須</span>
                  )}
                </div>

                <FormControl className="flex-auto flex w-full min-h-[40px]">
                  <div className="relative">
                    {renderCustom ? (
                      renderCustom(field)
                    ) : type === "number" ? (
                      <Input
                        type="number"
                        placeholder={placeholder}
                        required={required}
                        {...props}
                        {...field}
                        className={error ? "input-text-error" : ""}
                        onChange={(e) => field.onChange(Number(e.target.value))}
                        onBlur={() => {
                          field.onBlur();
                          triggerValidation && triggerValidation(name);
                        }}
                      />
                    ) : type === "calendar" ? (
                      <Popover open={open} onOpenChange={setOpen}>
                        <PopoverTrigger asChild>
                          <Button
                            variant="default"
                            className={cn(
                              "w-full justify-start text-left font-normal",
                              !field.value && "text-muted-foreground",
                              error && "border-red-500"
                            )}
                          >
                            <span className="flex items-center justify-between w-full">
                              {field.value
                                ? format(new Date(field.value), "yyyy/MM/dd")
                                : placeholder}
                              <CalendarIcon className="ml-2 h-4 w-4" />
                            </span>
                          </Button>
                        </PopoverTrigger>
                        <PopoverContent
                          align="start"
                          className="w-[250px] p-0 z-[9999] bg-white pointer-events-auto shadow-md">
                          <Calendar
                            mode="single"
                            selected={field.value ?? undefined} // valueはDate型
                            onSelect={(date: Date | undefined) => {
                              field.onChange(date ?? undefined); // そのまま渡す
                              triggerValidation?.(name);
                              setOpen(false);
                            }}
                            disabled={disableFutureDates}
                            initialFocus
                          />
                        </PopoverContent>
                      </Popover>
                    ) : type === "calendarRange" ? (
                      <Popover>
                        <PopoverTrigger asChild>
                          <Button
                            variant="default"
                            className={cn(
                              "w-full justify-start text-left font-normal",
                              !field.value && "text-muted-foreground",
                              error && "border-red-500"
                            )}
                          >
                            <span className="flex items-center justify-between w-full">
                              {field.value && field.value.from && field.value.to
                                ? `${format(
                                  new Date(field.value.from),
                                  "yyyy-MM-dd"
                                )} ~ ${format(
                                  new Date(field.value.to),
                                  "yyyy-MM-dd"
                                )}`
                                : placeholder}
                              <CalendarIcon className="ml-2 h-4 w-4" />
                            </span>
                          </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-auto p-0 z-5 bg-white pointer-events-auto">
                          <Calendar
                            mode="range"
                            selected={field.value ?? undefined}
                            onSelect={(range: DateRange | undefined) => {
                              field.onChange(range ?? undefined);
                              triggerValidation?.(name);
                            }}
                            initialFocus
                          />
                        </PopoverContent>
                      </Popover>
                    ) : type === "textarea" ? (
                      <Textarea
                        placeholder={placeholder}
                        required={required}
                        {...field}
                        className={cn("resize-none", error && "border-red-500")}
                        onBlur={() => {
                          field.onBlur();
                          triggerValidation?.(name);
                        }}
                      />
                    ) : type === "select" || (options && options.length > 0) ? (
                      <Select
                        value={field.value || ""}
                        onValueChange={(v) => {
                          field.onChange(v);
                          props.onValueChange?.(v);
                        }}
                        //disable={isInactive}
                        {...props}
                      >
                        <SelectTrigger
                          className={cn(
                            isInactive && "opacity-50",
                            error && "input-text-error"
                          )}
                          onBlur={() => {
                            field.onBlur();
                            triggerValidation?.(name);
                          }}
                        >
                          {options.find((option) => option.id === field.value)
                            ?.name || Messages.common.pulldown_default}
                        </SelectTrigger>
                        <SelectContent>
                          {options.map((option) => (
                            <SelectItem key={option.id} value={option.id}>
                              {option.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input
                        type={type}
                        placeholder={placeholder}
                        required={required}
                        {...field}
                        className={error ? "input-text-error" : "w-full"}
                        onBlur={() => {
                          field.onBlur();
                          triggerValidation && triggerValidation(name);
                        }}
                        {...props}
                      />
                    )}
                    {unit && (
                      <div className="absolute bottom-2 right-[-80px] min-w-20 h-[21px]">
                        {unit}
                      </div>
                    )}
                  </div>
                </FormControl>
                <FormMessage className="text-left" />
              </>
            ) : isConfirmation && renderConfirmChange ? (
              <>
                <div
                  className={`flex flex-col items-start gap-1 min-h-[70px] ${className}`}
                >
                  <div className="flex items-center gap-2 min-h-[24px]">
                    <FormLabel className="text-left input-item-title">
                      {label}
                    </FormLabel>
                  </div>
                  <div className="flex-auto flex w-full min-h-[40px]">
                    <div className="relative">{renderConfirmChange(field)}</div>
                  </div>
                </div>
              </>
            ) : renderUnChange ? (
              <>
                <div
                  className={`flex flex-col items-start gap-1 min-h-[70px] ${className}`}
                >
                  <div className="flex items-center gap-2 min-h-[24px]">
                    <FormLabel className="text-left input-item-title">
                      {label}
                    </FormLabel>
                  </div>
                  <div className="flex-auto flex w-full min-h-[40px]">
                    <div className="relative">{renderUnChange(field)}</div>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex min-h-[50px] text-base w-full">
                <div className="flex items-center w-[200px] border border-gray-300 bg-gray-100 text-gray-600 px-3">
                  <span>{label}</span>
                </div>
                <div className="flex flex-1 items-center px-3 border-t border-b border-r border-gray-200 text-gray-700 min-w-[200px]">
                  {renderValue()}
                </div>
              </div>
            )}
          </FormItem>
        );
      }}
    />
  );
}