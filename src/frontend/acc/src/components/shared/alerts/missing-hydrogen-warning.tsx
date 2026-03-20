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
      description="At least one of the uploaded structures is missing hydrogen atoms. This may affect the calculation results."
    />
  );
};
