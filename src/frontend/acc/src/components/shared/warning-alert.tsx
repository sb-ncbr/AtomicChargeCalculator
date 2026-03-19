import { AlertTriangleIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "../ui/alert";

export type WarningAlertProps = {
  title: string;
  description: string;
};

export const WarningAlert = ({ title, description }: WarningAlertProps) => {
  return (
    <Alert className="border-yellow-200 bg-yellow-50 text-yellow-600 my-4">
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
