import { cn } from "@acc/lib/utils";
import { HTMLAttributes } from "react";

export type MolstarColorScaleProps = {
  maxCharge: number;
} & HTMLAttributes<HTMLElement>;

export const MolstarColorScale = ({
  maxCharge,
  className,
}: MolstarColorScaleProps) => {
  return (
    <div className={cn(className)}>
      <div className="w-[120px] h-[20px] bg-gradient-to-r from-[#ff0000] via-[#ffffff] to-[#0000ff]"></div>
      <div className="w-[120px] flex items-center justify-between text-sm">
        <span>{-Math.round(Math.abs(maxCharge) * 100) / 100}</span>
        <span>0</span>
        <span>{Math.round(Math.abs(maxCharge) * 100) / 100}</span>
      </div>
    </div>
  );
};
