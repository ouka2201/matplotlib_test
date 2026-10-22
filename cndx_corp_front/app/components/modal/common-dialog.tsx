import React from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "~/components/ui/dialog";
import ErrorHint from "../common/error-hint";

interface CustomDialogProps {
  triggerLabel?: string;
  title?: string;
  description?: string;
  children: React.ReactNode;
  headerContent?: React.ReactNode;
  footer?: React.ReactNode;
  onClose?: () => void;
  size?: "default" | "sm" | "lg" | "xl";
  triggerClassName?: string;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  className?: string;
  errorMessage?: string | string[] | null;
  errorTitle?: string;
  errorClassName?: string;
  errorBodyClassName?: string;
}

const sizeClasses = {
  default: "w-4xl h-[70vh]",
  sm: "w-2xl h-[30vh]",
  lg: "w-2xl h-[90vh]",
  xl: "w-4xl h-[100vh]",
};

export default function CustomDialog({
  //   triggerLabel = "開く",
  title,
  description,
  children,
  headerContent,
  footer,
  onClose,
  size = "default",
  //   triggerClassName = "",
  open,
  onOpenChange,
  className,
  errorMessage,
  errorTitle,
  errorClassName = "",
  errorBodyClassName,
}: CustomDialogProps) {
  const handleOpenChange = (isOpen: boolean) => {
    if (!isOpen) {
      requestAnimationFrame(() => {
        document.body.style.pointerEvents = "auto";
      });
    }
    if (!isOpen && onClose) onClose();
    onOpenChange?.(isOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      {/* <DialogTrigger asChild>
        <Button className={triggerClassName}>{triggerLabel}</Button>
      </DialogTrigger> */}
      <DialogContent className={`overflow-y-auto ${sizeClasses[size]} ${className}`}>
        {(title || description || headerContent) && (
          <div className="sticky top-0 z-10 bg-background">
            {(title || description) && (
              <DialogHeader className="px-6 pt-6">
                {title && <DialogTitle>{title}</DialogTitle>}
                {description && <DialogDescription>{description}</DialogDescription>}
              </DialogHeader>
            )}
            {headerContent && <div className="px-6 pb-4">{headerContent}</div>}
          </div>
        )}

        {errorMessage && (
          <div className="px-6">
            <ErrorHint
              title={errorTitle}
              message={errorMessage}
              className={`mb-4 ${errorClassName}`.trim()}
              bodyClassName={errorBodyClassName}
            />
          </div>
        )}

        <div className="overflow-y-auto px-6">{children}</div>

        {footer && <DialogFooter className="px-6 pb-6 pt-4">{footer}</DialogFooter>}
      </DialogContent>
    </Dialog>
  );
}
