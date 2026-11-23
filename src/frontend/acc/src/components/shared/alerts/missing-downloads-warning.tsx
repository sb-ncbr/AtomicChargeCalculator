import type { FileWarning } from "@acc/api/compute/compute";

import { HTMLAttributes, HTMLElementType } from "react";

import { WarningAlert } from "../warning-alert";
import { LearnMore } from "./learn-more";

export type MissingDownloadsWarningProps = {
  warnings: FileWarning[];
} & HTMLAttributes<HTMLElementType>;

/**
 * PQR or MOL2 files that ChargeFW cannot write, such as PQR for chain IDs like "AA".
 * The charges are calculated; only these files are not in the download.
 */
export const MissingDownloadsWarning = ({
  warnings,
  className,
}: MissingDownloadsWarningProps) => {
  // Each method gives the same reason for a file; it is listed once.
  const reasons = [
    ...new Set(warnings.map(({ file, message }) => `${file}: ${message}`)),
  ];

  return (
    <WarningAlert
      className={className}
      title="Files not available for download"
      description={
        <>
          The charges are calculated, but these files cannot be written and are
          not in the download.{" "}
          <LearnMore entry="Files not available for download" />
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
