import { addMonths, format, parse, subMonths } from "date-fns";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ZodSchema } from "zod";

type PeriodForm = {
  startYear: string;
  startMonth: string;
  endYear: string;
  endMonth: string;
};

type Touched = Record<keyof PeriodForm, boolean>;

type Options = {
  schema: ZodSchema<any>;                 // baseSchema を渡す
  duplicateCheck?: (startYM: string, endYM: string) => boolean; // 画面ごとに差し替え
  duplicateErrorMessage?: string;         // period重複の文言
};

export function usePeriod12Months(options: Options) {
  const { schema, duplicateCheck, duplicateErrorMessage } = options;

  const [formData, setFormData] = useState<PeriodForm>({
    startYear: "",
    startMonth: "",
    endYear: "",
    endMonth: "",
  });

  const [touched, setTouched] = useState<Touched>({
    startYear: false,
    startMonth: false,
    endYear: false,
    endMonth: false,
  });

  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  const handleBlur = useCallback((field: keyof PeriodForm) => {
    setTouched((prev) => ({ ...prev, [field]: true }));
  }, []);

  const handleStartChange = useCallback((field: "year" | "month", value: string) => {
    const name = field === "year" ? "startYear" : "startMonth";
    setTouched((prev) => ({ ...prev, [name]: true }));

    setFormData((prev) => {
      const updated = { ...prev, [name]: value };
      const y = updated.startYear;
      const m = updated.startMonth;

      if (/^\d{4}$/.test(y) && /^\d{1,2}$/.test(m)) {
        const paddedMonth = m.padStart(2, "0");
        const parsedDate = parse(`${y}-${paddedMonth}`, "yyyy-MM", new Date());
        if (!isNaN(parsedDate.getTime())) {
          const newEnd = addMonths(parsedDate, 11);
          updated.endYear = format(newEnd, "yyyy");
          updated.endMonth = format(newEnd, "MM");
        }
      }
      return updated;
    });
  }, []);

  const handleEndChange = useCallback((field: "year" | "month", value: string) => {
    const name = field === "year" ? "endYear" : "endMonth";
    setTouched((prev) => ({ ...prev, [name]: true }));

    setFormData((prev) => {
      const updated = { ...prev, [name]: value };
      const y = updated.endYear;
      const m = updated.endMonth;

      if (/^\d{4}$/.test(y) && /^\d{1,2}$/.test(m)) {
        const paddedMonth = m.padStart(2, "0");
        const parsedDate = parse(`${y}-${paddedMonth}`, "yyyy-MM", new Date());
        if (!isNaN(parsedDate.getTime())) {
          const newStart = subMonths(parsedDate, 11);
          updated.startYear = format(newStart, "yyyy");
          updated.startMonth = format(newStart, "MM");
        }
      }
      return updated;
    });
  }, []);

  const isValidRange = useMemo(() => schema.safeParse(formData).success, [schema, formData]);

  const isDuplicatePeriod = useMemo(() => {
    if (!duplicateCheck) return false;
    if (!isValidRange) return false;
    if (!formData.startYear || !formData.startMonth || !formData.endYear || !formData.endMonth) return false;

    const startYM = `${formData.startYear}${formData.startMonth.padStart(2, "0")}`;
    const endYM = `${formData.endYear}${formData.endMonth.padStart(2, "0")}`;
    return duplicateCheck(startYM, endYM);
  }, [duplicateCheck, formData, isValidRange]);

  useEffect(() => {
    const result = schema.safeParse(formData);
    const newErrors: Record<string, string> = {};

    if (!result.success) {
      const formatted = result.error.format() as Record<string, any>;
      for (const key in formatted) {
        if (key !== "_errors" && formatted[key]?._errors?.[0]) {
          newErrors[key] = formatted[key]._errors[0];
        }
      }
    }

    if (isValidRange && duplicateCheck && duplicateErrorMessage) {
      const startYM = `${formData.startYear}${formData.startMonth.padStart(2, "0")}`;
      const endYM = `${formData.endYear}${formData.endMonth.padStart(2, "0")}`;
      if (duplicateCheck(startYM, endYM)) {
        newErrors.period = duplicateErrorMessage;
      }
    }

    setFormErrors(newErrors);
  }, [schema, formData, isValidRange, duplicateCheck, duplicateErrorMessage]);

  const reset = useCallback(() => {
    setFormErrors({});
    setTouched({ startYear: false, startMonth: false, endYear: false, endMonth: false });
    setFormData({ startYear: "", startMonth: "", endYear: "", endMonth: "" });
  }, []);

  return {
    formData,
    setFormData,
    touched,
    formErrors,
    isValidRange,
    isDuplicatePeriod,
    handleBlur,
    handleStartChange,
    handleEndChange,
    reset,
  };
}
