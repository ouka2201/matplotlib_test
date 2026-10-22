import React from "react";
import { useForm } from "react-hook-form";
import UnifiedField from "~/components/common/commonFileld";
import MasterLayout from "~/components/layout/master-layout";
import { Form } from "~/components/ui/form";

type FormValues = {
  textField: string;
  textareaField: string;
  selectField: string;
  numberRangeField: number;
  numberField: number;
  calendarField: Date | null;
  calendarRangeField: [Date | undefined, Date | undefined];
  sliderField: number;
};

export default function ExampleForm() {
  const form = useForm<FormValues>({
    defaultValues: {
      textField: "",
      textareaField: "",
      selectField: "",
      numberField: 0,
      calendarField: null,
      calendarRangeField: [undefined, undefined],
      sliderField: 0,
    },
  });

  const selectOptions = [
    { id: "option1", name: "選択肢1" },
    { id: "option2", name: "選択肢2" },
  ];

  return (
    <MasterLayout>
    <Form {...form}>
    <form onSubmit={form.handleSubmit(data => console.log(data))} className="space-y-4">
      <UnifiedField
        control={form.control}
        name="textField"
        label="テキスト入力"
        type="text"
        placeholder="テキストを入力"
        required
        rules={{ required: "必須です" }}
      />

      <UnifiedField
        control={form.control}
        name="textareaField"
        label="テキストエリア"
        type="textarea"
        placeholder="複数行テキスト"
      />

      <UnifiedField
        control={form.control}
        name="selectField"
        label="セレクト"
        type="select"
        options={selectOptions}
        placeholder="選択してください"
        required
      />

      <UnifiedField
        control={form.control}
        name="numberRangeField"
        label="数値範囲入力"
        type="numberRange"
        min={0}
        max={100}
        step={1}
      />

    <UnifiedField
        control={form.control}
        name="numberField"
        label="数値入力"
        type="number"
      />

      <UnifiedField
        control={form.control}
        name="calendarField"
        label="カレンダー"
        type="calendar"
        placeholder="日付を選択してください"
        dateFormat="yyyy年MM月dd日"
      />

      <UnifiedField
        control={form.control}
        name="calendarRangeField"
        label="期間選択"
        type="calendarRange"
        placeholder="期間を選択してください"
        dateFormat="yyyy年MM月dd日"
      />

      <UnifiedField
        control={form.control}
        name="sliderField"
        label="スライダー"
        type="slider"
        min={0}
        max={100}
        step={5}
      />

      <button type="submit" className="btn-primary mt-4">送信</button>

      <ul>
        テキストリンクボタン状態確認: 
        <li>
          <button className="textlink">
            テキストリンク
          </button>
        </li>
        <li>
          <button className="textlink" disabled>
          テキストリンク非活性
          </button>
        </li>
      </ul>
    </form>
    </Form>
    </MasterLayout>
  );
}
