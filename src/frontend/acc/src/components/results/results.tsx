import { handleApiError } from "@acc/api/base";
import { ScrollArea } from "@acc/components/ui/scroll-area";
import { ControlsContextProvider } from "@acc/lib/contexts/controls-context";
import { MolstarContextProvider } from "@acc/lib/contexts/molstar-context";
import { useComputationMutations } from "@acc/lib/hooks/mutations/use-calculations";
import MolstarPartialCharges from "@acc/lib/viewer/viewer";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { toast } from "sonner";

import { Busy } from "../shared/busy";
import { MolstarColoringType } from "./controls/coloring-controls";
import { ControlsWrapper } from "./controls/controls-wrapper";
import { MolstarViewType } from "./controls/view-controls";
import { MolstarWrapper } from "./molstar-wrapper";

export type ResultsProps = {
  computationId: string;
};

export const Results = ({ computationId }: ResultsProps) => {
  const navigate = useNavigate();
  const { getMoleculesMutation } = useComputationMutations();

  const [molstar, setMolstar] = useState<MolstarPartialCharges>();
  const [molecules, setMolecules] = useState<string[]>([]);

  const [currentTypeId, setCurrentTypeId] = useState<number>(1);
  const [structure, setStructure] = useState<string>(molecules[0]);
  const [coloringType, setColoringType] =
    useState<MolstarColoringType>("charges-relative");
  const [maxValue, setMaxValue] = useState<number>(0);
  const [viewType, setViewType] = useState<MolstarViewType>("cartoon");
  const [methodNames, setMethodNames] = useState<(string | undefined)[]>([]);

  const loadMolecules = async () => {
    // make this a query
    await getMoleculesMutation.mutateAsync(computationId, {
      onError: (error) => {
        toast.error(handleApiError(error));
        void navigate("/");
      },
      onSuccess: (molecules) => setMolecules(molecules),
    });
  };

  useEffect(() => {
    void loadMolecules();
  }, []);

  return (
    <main className="mx-auto w-full selection:text-white selection:bg-primary mb-8 relative">
      <Busy isBusy={getMoleculesMutation.isPending || !molstar} fullscreen />

      <ScrollArea type="auto" className="relative">
        <h2 className="w-[90%] mx-auto max-w-content mt-8 text-3xl text-primary font-bold mb-2 sm:text-5xl">
          Computational Results
        </h2>
        <ControlsContextProvider
          value={{
            currentTypeId,
            setCurrentTypeId,
            coloringType,
            setColoringType,
            maxValue,
            setMaxValue,
            structure,
            setStructure,
            viewType,
            setViewType,
            methodNames,
            setMethodNames,
          }}
        >
          {molstar && molecules.length && (
            <ControlsWrapper
              computationId={computationId}
              molecules={molecules}
              molstar={molstar}
            />
          )}

          <MolstarContextProvider value={{ plugin: molstar?.plugin }}>
            <MolstarWrapper setMolstar={setMolstar} molstar={molstar} />
          </MolstarContextProvider>
        </ControlsContextProvider>
      </ScrollArea>
    </main>
  );
};
