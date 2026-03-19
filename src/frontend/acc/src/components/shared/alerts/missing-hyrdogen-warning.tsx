import { WarningAlert } from "../warning-alert";

export const MissingHydrogensWarning = () => {
  return (
    <WarningAlert
      title="Missing hydrogen atoms"
      description="At least one of the uploaded structures is missing hydrogen atoms. This may affect the calculation results."
    />
  );
};
