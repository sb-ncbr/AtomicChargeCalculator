import { HTMLAttributes, HTMLElementType } from "react";

import { WarningAlert } from "../warning-alert";
import { LearnMore } from "./learn-more";

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
          At least one of the uploaded structures is missing hydrogen atoms.
          Calculated charges might not be usable.{" "}
          <LearnMore entry="Missing hydrogen atoms" />
        </>
      }
    />
  );
};
