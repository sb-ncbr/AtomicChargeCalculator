import { cn } from "@acc/lib/utils";
import MolstarPartialCharges from "@acc/lib/viewer/viewer";
import { HTMLAttributes, useEffect } from "react";

import { Busy } from "../shared/busy";
import { BusySize } from "../shared/busy-size";
import { MolstarViewer } from "./molstar";

export type MolstarWrapperProps = {
  setMolstar: React.Dispatch<
    React.SetStateAction<MolstarPartialCharges | undefined>
  >;
  molstar: MolstarPartialCharges | undefined;
} & HTMLAttributes<HTMLElement>;

export const MolstarWrapper = ({
  molstar,
  setMolstar,
  className,
}: MolstarWrapperProps) => {
  const setup = async () => {
    const molstar = await MolstarPartialCharges.initialize();

    setMolstar(molstar);
  };

  useEffect(() => {
    void setup();
  }, []);

  return (
    <div className={cn("relative w-[90%] mx-auto h-[700px]", className)}>
      <Busy isBusy={!molstar} size={BusySize.Big} />
      {molstar && <MolstarViewer molstar={molstar} />}
    </div>
  );
};
