import { format } from "date-fns";
import { Omit } from "lodash";
import { CalendarIcon } from "lucide-react";
import { ReactNode } from "react";
import { Control, FieldError, FieldValues, Path, RegisterOptions } from "react-hook-form";
import { Calendar } from "~/components/ui/calendar";
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "~/components/ui/form";
import { Input } from "~/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "~/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "~/components/ui/select";
import { Slider } from "~/components/ui/slider";
import { Textarea } from "~/components/ui/textarea";
import { Messages } from "~/constants/messages/message";
import { cn } from "~/lib/utils";
import styles from "~/styles/common.module.css";
import { Button } from "../ui/button";

interface Option {
  id: string;
  name: string;
}

interface UnifiedFieldProps<T extends FieldValues> {
  control: Control<T>;
  name: Path<T>;
  label: string;
  type?: "text" | "textarea" | "select" | "number" | "numberRange" | "calendar" | "calendarRange" | "slider";
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  options?: Option[];
  helperText?: string;
  renderCustom?: (field: any) => ReactNode;
  className?: string;
  isEditing?: boolean;
  triggerValidation?: (name: keyof T) => void;
  min?: number;
  max?: number;
  step?: number;
  dateFormat?: string;
  rules?: Omit<RegisterOptions<T, Path<T>>, "disabled" | "valueAsNumber" | "valueAsDate" | "setValueAs">;
}

export default function UnifiedField<T extends FieldValues>({
  control,
  name,
  label,
  type = "text",
  placeholder = "",
  required = false,
  disabled = false,
  options = [],
  helperText,
  renderCustom,
  className = "",
  isEditing = true,
  triggerValidation,
  min,
  max,
  step,
  dateFormat = "yyyy-MM-dd",
  rules
}: UnifiedFieldProps<T>) {
  return (
    <FormField
      control={control}
      name={name}
      rules={rules}
      render={({ field, fieldState }) => {
        const error = (fieldState as { error?: FieldError })?.error;

        // const { onBlur, ...restField } = field;
        const commonProps = {
          ...field,
          disabled,
          required,
          placeholder,
          className: cn("w-fit", error && "input-text-error"),
        };

        let inputComponent: ReactNode = null;

        if (!isEditing) {
          inputComponent = (
            <div className="text-sm text-gray-700">
              {type === "select"
                ? options.find(opt => opt.id === field.value)?.name || "-"
                : type === "calendar" || type === "calendarRange"
                ? field.value
                  ? Array.isArray(field.value)
                    ? `${format(field.value[0], dateFormat)} ~ ${format(field.value[1], dateFormat)}`
                    : format(new Date(field.value), dateFormat)
                  : "-"
                : field.value || "-"}
            </div>
          );
        } else if (renderCustom) {
          inputComponent = renderCustom(field);
        } else {
          switch (type) {
            case "textarea":
              inputComponent = <Textarea {...commonProps} />;
              break;
            case "numberRange":
              inputComponent = <Input type="number" min={min} max={max} step={step} {...commonProps} />;
              break;
            case "number":
                inputComponent = 
                    <Input
                        type="text"
                        inputMode="numeric"
                        pattern="[0-9]*"
                        maxLength={13}
                        placeholder="13桁"
                    />
                break;
            case "select":
              inputComponent = (
                <Select value={field.value || ""} onValueChange={field.onChange}>
                  <SelectTrigger className={cn(error && "border-red-500")}>
                    {options.find(o => o.id === field.value)?.name || Messages.common.pulldown_default}
                  </SelectTrigger>
                  <SelectContent>
                    {options.map(option => (
                      <SelectItem key={option.id} value={option.id}>
                        {option.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              );
              break;
            case "calendar":
              inputComponent = (
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      className={cn("w-full justify-start text-left font-normal", !field.value && "text-muted-foreground", error && "border-red-500")}
                      disabled={disabled}
                    >
                      <span className="flex items-center justify-between w-full">
                        {field.value ? format(new Date(field.value), dateFormat) : placeholder}
                        <CalendarIcon className="ml-2 h-4 w-4" />
                      </span>
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0 z-51 bg-white pointer-events-auto">
                    <Calendar selected={field.value ? new Date(field.value) : undefined}
                      onSelect={(date: Date | undefined) => {
                        field.onChange(date?.toISOString()) // フォームで扱うのが文字列なら ISO 形式に変換
                      }}
                      initialFocus />
                  </PopoverContent>
                </Popover>
              );
              break;
            case "calendarRange":
              inputComponent = (
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      className={cn("w-full justify-start text-left font-normal", !field.value?.[0] && "text-muted-foreground", error && "border-red-500")}
                      disabled={disabled}
                    >
                      <span className="flex items-center justify-between w-full">
                        {field.value?.[0] && field.value?.[1]
                          ? `${format(field.value[0], dateFormat)} ~ ${format(field.value[1], dateFormat)}`
                          : placeholder}
                        <CalendarIcon className="ml-2 h-4 w-4" />
                      </span>
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0">
                    <Calendar
                      mode="range"
                      selected={field.value}
                      onSelect={field.onChange}
                      initialFocus
                    />
                  </PopoverContent>
                </Popover>
              );
              break;
            case "slider":
              inputComponent = (
                <Slider
                  min={min}
                  max={max}
                  step={step}
                  value={[field.value || 0]}
                  onValueChange={([val]) => field.onChange(val)}
                />
              );
              break;
            default:
              inputComponent = <Input type={type} {...commonProps} />;
          }
        }

        return (
          <FormItem className={cn("flex items-center gap-2", className)}>
            <div className="flex flex-col space-y-1">
                <FormLabel className="min-w-[150px] text-left">
                    <span className="flex items-center gap-1">
                    {label}
                    {required && isEditing && (
                        <span className={styles.requiredMark}>必須</span>
                    )}
                    </span>
                </FormLabel>

                <FormControl className="flex-auto flex flex-col">
                    <>
                    {inputComponent}
                    {helperText && (
                        <p className="text-sm text-muted-foreground mt-1">{helperText}</p>
                    )}
                    <FormMessage className="text-left mt-1" />
                    </>
                </FormControl>
            </div>
          </FormItem>
        );
      }}
    />
  );
}
