import type { UnavailableCharges } from "@acc/api/compute/compute";

import { HTMLAttributes, HTMLElementType } from "react";

import { WarningAlert } from "../warning-alert";

export type UnavailableChargesWarningProps = {
  unavailable: UnavailableCharges[];
} & HTMLAttributes<HTMLElementType>;

export const UnavailableChargesWarning = ({
  unavailable,
  className,
}: UnavailableChargesWarningProps) => {
  return (
    <WarningAlert
      className={className}
      title="Charges not available"
      description={
        <ul className="list-disc ml-4">
          {unavailable.map((item, index) => (
            <li key={index}>
              {item.methodName}
              {item.parametersName ? ` (${item.parametersName})` : ""} for{" "}
              {item.file}: {item.message}
            </li>
          ))}
        </ul>
      }
    />
  );
};
