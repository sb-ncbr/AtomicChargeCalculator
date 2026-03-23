import { cn } from "@acc/lib/utils";
import { AlertTriangleIcon } from "lucide-react";
import { HTMLAttributes, HTMLElementType, ReactNode } from "react";

import { Alert, AlertDescription, AlertTitle } from "../ui/alert";

export type WarningAlertProps = {
  title: string;
  description: ReactNode;
} & HTMLAttributes<HTMLElementType>;

export const WarningAlert = ({
  title,
  description,
  className,
}: WarningAlertProps) => {
  return (
    <Alert
      className={cn(
        "border-yellow-200 bg-yellow-50 text-yellow-600 my-4",
        className
      )}
    >
      <div className="flex gap-2">
        <AlertTriangleIcon size={15} />
        <div>
          <AlertTitle className="font-bold">{title}</AlertTitle>
          <AlertDescription>{description}</AlertDescription>
        </div>
      </div>
    </Alert>
  );
};
