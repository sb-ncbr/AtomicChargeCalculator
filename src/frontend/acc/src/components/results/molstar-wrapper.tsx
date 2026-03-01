import MolstarPartialCharges from "@acc/lib/viewer/viewer";
import { HTMLAttributes, useEffect } from "react";

import { Busy, BusySize } from "../shared/busy";
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
}: MolstarWrapperProps) => {
  const setup = async () => {
    const molstar = await MolstarPartialCharges.initialize();

    setMolstar(molstar);
  };

  useEffect(() => {
    void setup();
  }, []);

  return (
    <div className={"relative w-[90%] mx-auto h-[700px]"}>
      <Busy isBusy={!molstar} size={BusySize.Big} />
      {molstar && <MolstarViewer molstar={molstar} />}
    </div>
  );
};
