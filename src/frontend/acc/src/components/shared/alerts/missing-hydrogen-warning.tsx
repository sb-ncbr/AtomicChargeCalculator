import { HTMLAttributes, HTMLElementType } from "react";

import { WarningAlert } from "../warning-alert";

export type MissingHydrogensWarningProps = {} & HTMLAttributes<HTMLElementType>;

export const MissingHydrogensWarning = ({
  className,
}: MissingHydrogensWarningProps) => {
  return (
    <WarningAlert
      className={className}
      title="Missing hydrogen atoms"
      description={
        <>
          At least one of the uploaded structures is missing hydrogen atoms. Calculated charges might not be usable.
          See{" "}
          <a href="/docs#protonation"
             target="_blank"
             rel="noopener noreferrer"
             className="underline">
            the Documentation
          </a>{" "}
          for details.
        </>
      }
    />
  );
};
