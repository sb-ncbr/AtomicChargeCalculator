import MolstarPartialCharges from "@acc/lib/viewer/viewer";
import { PluginUIContext } from "molstar/lib/commonjs/mol-plugin-ui/context";
import { HTMLAttributes, useEffect, useState } from "react";

import { Busy, BusySize } from "../shared/busy";
import { MolstarViewer } from "./molstar";

export type MolstarWrapperProps = {
  setMolstar: React.Dispatch<
    React.SetStateAction<MolstarPartialCharges | undefined>
  >;
  maxCharge?: number;
} & HTMLAttributes<HTMLElement>;

export const MolstarWrapper = ({
  setMolstar,
  maxCharge,
}: MolstarWrapperProps) => {
  const [plugin, setPlugin] = useState<PluginUIContext | undefined>();

  const setup = async () => {
    const molstar = await MolstarPartialCharges.initialize();

    setMolstar(molstar);
    setPlugin(molstar.plugin);
  };

  useEffect(() => {
    void setup();
  }, []);

  return (
    <div className={"relative w-[90%] mx-auto h-[700px]"}>
      <Busy isBusy={!plugin} size={BusySize.Big} />
      {plugin && <MolstarViewer maxCharge={maxCharge} plugin={plugin} />}
    </div>
  );
};
