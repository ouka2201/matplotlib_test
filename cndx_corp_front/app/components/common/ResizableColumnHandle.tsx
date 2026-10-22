import React from "react";

interface ResizableColumnHandleProps {
  onResizeStart: (e: React.MouseEvent | React.TouchEvent) => void;
}

export const ResizableColumnHandle: React.FC<ResizableColumnHandleProps> = ({
  onResizeStart,
}) => {
  return (
    <div
      role="presentation"
      tabIndex={-1}
      onMouseDown={onResizeStart}
      onTouchStart={onResizeStart}
      onClick={(e) => e.stopPropagation()} // ソート抑制
      className="w-1 h-full cursor-col-resize bg-gray-300 hover:bg-gray-400 transition"
    />
  );
};
