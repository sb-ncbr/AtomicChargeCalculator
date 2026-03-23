import type { CalculationStatus } from "@acc/api/compute/compute";

import { handleApiError } from "@acc/api/base";
import { getCalculationStatus } from "@acc/api/compute/compute";
import { ScrollArea } from "@acc/components/ui/scroll-area";
import { ControlsContextProvider } from "@acc/lib/contexts/controls-context";
import { MolstarContextProvider } from "@acc/lib/contexts/molstar-context";
import { useFileStatsContext } from "@acc/lib/hooks/contexts/use-file-stats-context";
import { useComputationMutations } from "@acc/lib/hooks/mutations/use-calculations";
import MolstarPartialCharges from "@acc/lib/viewer/viewer";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { toast } from "sonner";

import { MissingHydrogensWarning } from "../shared/alerts/missing-hydrogen-warning";
import { Busy } from "../shared/busy";
import { ErrorAlert } from "../shared/error-alert";
import { MolstarColoringType } from "./controls/coloring-controls";
import { ControlsWrapper } from "./controls/controls-wrapper";
import { MolstarViewType } from "./controls/view-controls";
import { MolstarWrapper } from "./molstar-wrapper";

export type ResultsProps = {
  computationId: string;
};

const STATUS_POLLING_INTERVAL_MS = 2 * 1000;

export const Results = ({ computationId }: ResultsProps) => {
  const navigate = useNavigate();
  const { getMoleculesMutation } = useComputationMutations();
  const statsContext = useFileStatsContext();

  const [molstar, setMolstar] = useState<MolstarPartialCharges>();
  const [molecules, setMolecules] = useState<string[]>([]);
  const [calculationStatus, setCalculationStatus] =
    useState<CalculationStatus>("CALCULATING");
  const [calculationError, setCalculationError] = useState<string | null>(null);

  const [currentTypeId, setCurrentTypeId] = useState<number>(1);
  const [structure, setStructure] = useState<string>(molecules[0]);
  const [coloringType, setColoringType] =
    useState<MolstarColoringType>("charges");
  const [maxValue, setMaxValue] = useState<number>(0);
  const [viewType, setViewType] = useState<MolstarViewType>("cartoon");
  const [methodNames, setMethodNames] = useState<(string | undefined)[]>([]);

  const pollIntervalRef = useRef<number | null>(null);

  const loadMolecules = async () => {
    await getMoleculesMutation.mutateAsync(computationId, {
      onError: (error) => {
        toast.error(handleApiError(error));
        void navigate("/");
      },
      onSuccess: (molecules) => setMolecules(molecules),
    });
  };

  useEffect(() => {
    if (computationId.startsWith("examples/")) {
      setCalculationStatus("COMPLETED");
      void loadMolecules();
      return;
    }

    let cancelled = false;

    const checkStatus = async () => {
      try {
        const status = await getCalculationStatus(computationId);

        if (cancelled) {
          return;
        }

        setCalculationStatus(status.status);

        if (status.status !== "CALCULATING") {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
        }

        if (status.status === "FAILED" && status.error) {
          setCalculationError(status.error);
        }

        if (status.status === "COMPLETED") {
          void loadMolecules();
        }

        return status.status;
      } catch {
        // ignore polling errors, will retry
      }
    };

    void checkStatus().then((status) => {
      // schedule interval only after the first status check is done and the calculation is in progress
      if (status === "CALCULATING" && !cancelled) {
        pollIntervalRef.current = window.setInterval(
          checkStatus,
          STATUS_POLLING_INTERVAL_MS
        );
      }
    });

    return () => {
      cancelled = true;
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [computationId]);

  const isCalculating =
    calculationStatus === "CALCULATING" ||
    (calculationStatus === "FAILED" && !calculationError);
  const showBusy = isCalculating || getMoleculesMutation.isPending || !molstar;

  return (
    <main className="mx-auto w-full selection:text-white selection:bg-primary mb-8 relative">
      <Busy isBusy={showBusy} fullscreen />

      <ScrollArea type="auto" className="relative">
        <h2 className="w-[90%] mx-auto max-w-content mt-8 text-3xl text-primary font-bold mb-2 sm:text-5xl">
          {calculationStatus === "CALCULATING"
            ? "Calculating Charges..."
            : "Computational Results"}
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
          {calculationStatus !== "CALCULATING" && (
            <>
              {!!molstar && !!molecules.length && (
                <ControlsWrapper
                  computationId={computationId}
                  molecules={molecules}
                  molstar={molstar}
                />
              )}
              {statsContext.isMissingHydrogens(computationId) && (
                <MissingHydrogensWarning className="w-[90%] max-w-content mx-auto" />
              )}

              {calculationStatus === "FAILED" && !!calculationError && (
                <ErrorAlert
                  title="Calculation Failed"
                  description={calculationError}
                  className="w-[90%] max-w-content mx-auto"
                />
              )}
              <MolstarContextProvider value={{ plugin: molstar?.plugin }}>
                <MolstarWrapper setMolstar={setMolstar} molstar={molstar} />
              </MolstarContextProvider>
            </>
          )}
        </ControlsContextProvider>
      </ScrollArea>
    </main>
  );
};
