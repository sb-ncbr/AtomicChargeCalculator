import { cn } from "@acc/lib/utils";
import { AlertTriangleIcon } from "lucide-react";
import { HTMLAttributes } from "react";

import { Alert, AlertDescription, AlertTitle } from "../ui/alert";

export type ErrorAlertProps = {
  title: string;
  description: string;
} & HTMLAttributes<HTMLElement>;

export const ErrorAlert = ({
  title,
  description,
  className,
}: ErrorAlertProps) => {
  return (
    <Alert
      className={cn("border-red-500 bg-red-50 text-red-600 my-4", className)}
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
