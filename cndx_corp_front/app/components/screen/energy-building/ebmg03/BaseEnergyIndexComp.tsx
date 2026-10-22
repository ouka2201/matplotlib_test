import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "~/components/ui/accordion";
import React from "react";

type Props = {
  buildingName: string; // 拠点名
  buildingId: string;
  onSelectItem: (key: string) => void; // スクロール処理を呼ぶ関数
};

const BaseEnergyIndexComp: React.FC<Props> = ({
  buildingName,
  buildingId,
  onSelectItem,
}) => {
  // インデックス項目一覧
  const indexItems = [
    "拠点基本情報",
    "電気",
    "都市ガス",
    "熱",
    "エネルギー使用量",
  ];

  return (
    <div>
      <Accordion type="multiple" className="pl-3" defaultValue={["item-1"]}>
        <AccordionItem value="item-1">
          <AccordionTrigger className="flex-row-reverse justify-end gap-2">
            <h3 className="text-[14px] font-bold text-gray-400">
              {buildingName}
            </h3>
          </AccordionTrigger>
          <AccordionContent className="border-none">
            <div>
              {indexItems.map((label) => (
                <div
                  key={label}
                  role="button"
                  tabIndex={0}
                  className="m-5 text-[15px] text-bold text-gray-600 cursor-pointer"
                  onClick={() => onSelectItem(`${label}-${buildingId}`)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelectItem(`${label}-${buildingId}`);
                    }
                  }}
                >
                  {label}
                </div>
              ))}
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  );
};

export default BaseEnergyIndexComp;
