import React from "react";
import { Label } from "~/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";

type Option = {
  id: string;
  name: string;
};

type SelectFieldProps = {
  label: string;
  name: string;
  options: Option[];
  value: string;
  placeholder?: string;
  onChange: (value: string) => void;
  required?: boolean;
};

export const SelectField: React.FC<SelectFieldProps> = ({
  label,
  name,
  options,
  value,
  placeholder = "選択してください",
  onChange,
  required = false,
}) => {
  return (
    <div className="flex flex-col space-y-1 w-full">
      <Label htmlFor={name} className="text-sm text-gray-700">
        {label} {required && <span className="text-red-500">*</span>}
      </Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger id={name}>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option.id} value={option.id}>
              {option.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
};
