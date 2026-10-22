import { ReactNode } from "react";

interface SectionTitleProps {
  children: ReactNode;
  className?: string;
}

export default function SectionTitle({ children, className = "" }: SectionTitleProps) {
  return (
    <h3 className={`flex text-lg font-bold mb-4 ${className}`}>
      {children}
    </h3>
  );
}
