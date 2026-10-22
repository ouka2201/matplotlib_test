import React from "react";
import SectionTitle from "~/components/common/section-title";
import {Button} from "~/components/ui/button";
import { Command, CommandInput } from "~/components/ui/command";

// TODO:レポート管理・作成画面共通化対応再作成後、削除予定
interface SearchField {
  id: string;
  label: string;
  type?: "text" | "number" | "select";
  placeholder?: string;
  options?: { value: string; label: string }[]; // select 用
}

interface SearchFormProps {
  searchConditionTitle: string;
  fields: SearchField[];
  values: Record<string, string>;
  onValueChange: (newValues: Partial<Record<string, string>>) => void;
  onSearch: () => void;
  onReset: () => void;
}

export default function SearchForm({
  searchConditionTitle,
  fields,
  values,
  onValueChange,
  onSearch,
  onReset
}: SearchFormProps) {
  return (<>
    <SectionTitle>{searchConditionTitle}</SectionTitle>
    <div className="flex items-center gap-4">
      {fields.map((field) => (
        <div className="space-y-4" key={field.id}>
          <label htmlFor={field.id} className="min-w-[100px] text-left">
            {field.label}
          </label>
          <Command className="flex-1">
            {field.type === "select" && field.options ? (
              <select
                id={field.id}
                value={values[field.id] || ""}
                onChange={(e) => onValueChange({ [field.id]: e.target.value })}
                className="w-full border rounded px-2 py-1"
              >
                <option value="">選択してください</option>
                {field.options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            ) : (
              <CommandInput
                id={field.id}
                placeholder={field.placeholder}
                value={values[field.id] || ""}
                onValueChange={(value) => onValueChange({ [field.id]: value })}
              />
            )}
          </Command>
        </div>
      ))}
    </div>

    <div className="flex justify-center gap-4 mt-4">
      <Button variant="secondary" onClick={onReset}>
        リセット
      </Button>
      <Button variant="default" onClick={onSearch}>
        検索
      </Button>
    </div>
    </>
  );
}
