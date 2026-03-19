import { AlertTriangleIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "../ui/alert";

export type WarningAlertProps = {
  title: string;
  description: string;
};

export const ErrorAlert = ({ title, description }: WarningAlertProps) => {
  return (
    <Alert className="border-red-500 bg-red-50 text-red-600 my-4">
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
