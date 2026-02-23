import { handleApiError } from "@acc/api/base";
import { ScrollArea } from "@acc/components/ui/scroll-area";
import { ControlsContextProvider } from "@acc/lib/contexts/controls-context";
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

// Overriding the default view type for specific examples
const exampleOverrides: Record<string, { viewType: MolstarViewType }> = {
  "examples/pore": {
    viewType: "surface",
  },
  "examples/oseltamivir": {
    viewType: "cartoon",
  },
};

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
  const [viewType, setViewType] = useState<MolstarViewType>(() => {
    if (exampleOverrides?.[computationId]?.viewType) {
      return exampleOverrides[computationId].viewType;
    }
    return molstar?.type.isDefaultApplicable() ? "cartoon" : "balls-and-sticks";
  });
  const [methodNames, setMethodNames] = useState<(string | undefined)[]>([]);
  const [maxCharge, setMaxCharge] = useState(0);

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

  useEffect(() => {
    if (molstar) {
      setMaxCharge(molstar.charges.getMaxCharge());
    }
  }, [molstar?.plugin.managers.structure.hierarchy.current.structures[0]]);

  return (
    <main className="mx-auto w-full selection:text-white selection:bg-primary mb-8 relative">
      <Busy isBusy={getMoleculesMutation.isPending || !molstar} fullscreen />

      <ScrollArea type="auto" className="relative">
        <h2 className="w-4/5 mx-auto max-w-content mt-8 text-3xl text-primary font-bold mb-2 sm:text-5xl">
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
          {molstar && (
            <ControlsWrapper
              computationId={computationId}
              molecules={molecules}
              molstar={molstar}
            />
          )}
          <MolstarWrapper
            maxCharge={
              coloringType === "charges-absolute"
                ? maxValue
                : coloringType === "charges-relative"
                  ? maxCharge
                  : undefined
            }
            setMolstar={setMolstar}
          />
        </ControlsContextProvider>
      </ScrollArea>
    </main>
  );
};
