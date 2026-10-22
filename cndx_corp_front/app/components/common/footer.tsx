import { Icons } from "../icons";
import Icon from "../icon";
import { Button, buttonVariants } from "../ui/button";
import { VariantProps } from "class-variance-authority";

interface FooterProps {
  buttons: {
    text: string;
    isLoading?: boolean;
    variant?: VariantProps<typeof buttonVariants>["variant"];
    className?: string;
    disabled?: boolean;
    onClick?: () => void;
  }[];
  errorMessage?: string | string[];
  type?: "default" | "confirmation";
  hasSidebar?: boolean;
  onClickError?: () => void;
}

export default function Footer({ buttons, errorMessage, type, hasSidebar = false, onClickError }: FooterProps) {
  const errorMessages: string[] = (() => {
    const error = errorMessage;
    if (!error) return [];
    return Array.isArray(error) ? error : [error];
  })();

  const errorCount = errorMessages.length;

  const leftClass = hasSidebar ? "left-[220px]" : "left-0";
  if (type === "confirmation") {
    return (
      <footer className={`fixed bottom-0 ${leftClass} right-0 bg-gray-700 p-4 text-white flex justify-end gap-2`}>
        {buttons.map((button, index) => (
          <Button
            key={index}
            variant={button.variant ?? "default"}
            className={button.className}
            onClick={button.onClick}
            disabled={button.disabled}
          >
            {button.isLoading && <Icons.spinner className="mr-2 size-4 animate-spin" />}
            {button.text}
          </Button>
        ))}
      </footer>
    );
  }

  return (
    <footer
      className={`fixed bottom-0 ${leftClass} right-0 bg-gray-700 p-4 text-white flex items-center justify-between`}
    >
      {buttons.length === 2 ? (
        <>
          {/* 左側（キャンセルなど） */}
          <div className="flex gap-2">
            <Button
              variant={buttons[0].variant ?? "default"}
              className={buttons[0].className}
              onClick={buttons[0].onClick}
              disabled={buttons[0].disabled}
            >
              {buttons[0].isLoading && <Icons.spinner className="mr-2 size-4 animate-spin" />}
              {buttons[0].text}
            </Button>
          </div>

          {/* 右側（登録 + エラー） */}
          <div className="flex items-center gap-2">
            {errorCount > 0 && (
              <div className="flex">
                <div className="flex items-center gap-2 h-10 px-2 py-1.5 text-sm text-white bg-[#D92D20] rounded-l-[4px]">
                  <Icons.warning className="w-5 h-5" />
                </div>
                <div className="flex items-center gap-1 h-10 px-2 py-1.5 text-sm text-gray-800 border-2 border-[#D92D20] rounded-r-[4px] bg-[#FEF3F2]">
                  <span className="text-[#D92D20] font-bold text-base leading-6 font-['Noto_Sans_JP']">
                    エラー項目: {errorCount}件
                  </span>
                </div>
              </div>
            )}
            <Button
              variant={buttons[1].variant ?? "default"}
              className={buttons[1].className}
              onClick={buttons[1].onClick}
              disabled={buttons[1].disabled}
            >
              {buttons[1].isLoading && <Icons.spinner className="mr-2 size-4 animate-spin" />}
              {buttons[1].text}
            </Button>
          </div>
        </>
      ) : (
        // それ以外（3つ以上 or 1つ以下）は既存処理を継続
        <>
          <div className="flex gap-2">
            {buttons.slice(0, buttons.length - 2).map((button, index) => (
              <Button
                key={index}
                variant={button.variant ?? "default"}
                className={button.className}
                onClick={button.onClick}
                disabled={button.disabled}
              >
                {button.isLoading && <Icons.spinner className="mr-2 size-4 animate-spin" />}
                {button.text}
              </Button>
            ))}
          </div>
          <div className="flex gap-2 items-center">
            {errorCount > 0 && (
              <button
                type="button"
                onClick={() => onClickError?.()}
                className="flex cursor-pointer border-none bg-transparent p-0"
              >
                <div className="flex items-center gap-2 h-10 px-2 py-1.5 text-sm text-white bg-[#D92D20] rounded-l-[4px]">
                  <Icon name="error-pink" className="w-5 h-5" />
                </div>
                <div className="flex items-center gap-1 h-10 px-2 py-1.5 text-sm text-gray-800 border-2 border-[#D92D20] rounded-r-[4px] bg-[#FEF3F2]">
                  <span className="text-[#D92D20] font-bold text-base leading-6 font-['Noto_Sans_JP']">
                    エラー項目: {errorCount}件
                  </span>
                </div>
              </button>
            )}
            {buttons.slice(-2).map((button, index) => (
              <Button
                key={index}
                variant={button.variant ?? "default"}
                className={button.className}
                onClick={button.onClick}
                disabled={button.disabled}
              >
                {button.isLoading && <Icons.spinner className="mr-2 size-4 animate-spin" />}
                {button.text}
              </Button>
            ))}
          </div>
        </>
      )}
    </footer>
  );
}
