import type { UnavailableCharges } from "@acc/api/compute/compute";

import { HTMLAttributes, HTMLElementType } from "react";

import { WarningAlert } from "../warning-alert";
import { LearnMore } from "./learn-more";

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
        <>
          These calculations failed; the others are shown.{" "}
          <LearnMore entry="Charges not available" />
          <ul className="list-disc ml-4 mt-1">
            {unavailable.map((item, index) => (
              <li key={index}>
                {item.methodName}
                {item.parametersName
                  ? ` (${item.parametersName})`
                  : ""} for {item.file}: {item.message}
              </li>
            ))}
          </ul>
        </>
      }
    />
  );
};
