import type { FileWarning } from "@acc/api/compute/compute";

import { HTMLAttributes, HTMLElementType } from "react";

import { WarningAlert } from "../warning-alert";
import { LearnMore } from "./learn-more";

export type SuspiciousChargesWarningProps = {
  warnings: FileWarning[];
} & HTMLAttributes<HTMLElementType>;

/**
 * Charges that were calculated and shown but are probably wrong: atoms much closer than
 * bonded atoms are, or charges far from the formal charges.
 */
export const SuspiciousChargesWarning = ({
  warnings,
  className,
}: SuspiciousChargesWarningProps) => {
  // Atoms too close are about the structure, the same for each method, and listed once;
  // charges out of range are about one method.
  const reasons = [
    ...new Set(
      warnings.map(({ file, kind, message, method, parameters }) =>
        kind === "charge_out_of_range" && method
          ? `${file} (${method}${parameters ? `, ${parameters}` : ""}): ${message}`
          : `${file}: ${message}`
      )
    ),
  ];

  return (
    <WarningAlert
      className={className}
      title="Charges may be wrong"
      description={
        <>
          Check the structure, or compare with another method.{" "}
          <LearnMore entry="Charges may be wrong" />
          <ul className="list-disc ml-4 mt-1">
            {reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </>
      }
    />
  );
};
