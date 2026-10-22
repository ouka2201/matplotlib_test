import Icon from "../icon";
import Text from "../text";

type ErrorContent = string | string[] | null | undefined;

interface ErrorHintProps {
  message?: ErrorContent;
  title?: string;
  className?: string;
  bodyClassName?: string;
}

const ErrorHint: React.FC<ErrorHintProps> = ({
  message,
  title = "エラーがあります",
  className = "",
  bodyClassName = "",
}) => {
  if (
    !message ||
    (Array.isArray(message) && message.length === 0)
  ) {
    return null;
  }

  return (
    <div className={`flex flex-col border border-red-500 rounded overflow-hidden ${className}`}>
      <div className="flex flex-row items-center bg-red-500 px-4 py-2 gap-1">
        <Icon name="error-pink" />
        <Text content={title} color="white" weight="bold" />
      </div>
      <div
        className={`flex flex-col items-start bg-[#fee4e2] border border-[#d92d20] px-4 py-6 rounded-b text-[#d92d20] gap-[25px] ${bodyClassName}`}
      >
        {Array.isArray(message) ? (
          <ul className="list-disc list-inside space-y-1">
            {message.map((msg, index) => (
              <li key={index}>{msg}</li>
            ))}
          </ul>
        ) : (
          <div className="text-[14px] font-normal leading-[21px] text-left whitespace-pre-line">
            {message}
          </div>
        )}
      </div>
    </div>
  );
};

export default ErrorHint;
