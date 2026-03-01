import { Busy } from "@acc/components/shared/busy";
import { Card } from "@acc/components/ui/card";
import MolstarPartialCharges from "@acc/lib/viewer/viewer";
import { HTMLAttributes } from "react";

import { Controls } from "./controls";

export type ControlsWrapperProps = {
  computationId: string;
  molstar: MolstarPartialCharges;
  molecules: string[];
} & HTMLAttributes<HTMLElement>;

export const ControlsWrapper = ({
  computationId,
  molstar,
  molecules,
}: ControlsWrapperProps) => {
  return (
    <Card className="w-[90%] rounded-none mx-auto p-4 max-w-content mt-4 flex flex-col relative">
      <Busy isBusy={!molstar} />
      {molstar && (
        <Controls
          computationId={computationId}
          molstar={molstar}
          molecules={molecules}
        />
      )}
    </Card>
  );
};
