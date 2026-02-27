import { Button } from "@acc/components/ui/button";
import { Input } from "@acc/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@acc/components/ui/select";
import { useControlsContext } from "@acc/lib/hooks/contexts/use-controls-context";
import MolstarPartialCharges from "@acc/lib/viewer/viewer";
import { HTMLAttributes, useEffect } from "react";

export const molstarColoringTypes = [
  "structure",
  "charges-relative",
  "charges-absolute",
] as const;

export type MolstarColoringType = (typeof molstarColoringTypes)[number];

export type MolstarColoringControlsProps = {
  molstar: MolstarPartialCharges;
} & HTMLAttributes<HTMLElement>;

export const MolstarColoringControls = ({
  molstar,
}: MolstarColoringControlsProps) => {
  const context = useControlsContext(molstar);

  const onMaxValueChange = async (value: number) => {
    await context.set.maxValue(value);
  };

  const resetMaxValue = async () => {
    const maxValue = molstar.charges.getMaxCharge();
    await context.set.maxValue(maxValue);
  };

  useEffect(() => {
    void context.set.coloringType("charges-relative");
    void context.set.maxValue(molstar.charges.getMaxCharge());
  }, []);

  return (
    <div className="flex gap-4 flex-col sm:flex-row">
      <div className="grow">
        <h3 className="font-bold mb-2">Coloring</h3>
        <Select
          onValueChange={(value) =>
            context.set.coloringType(value as MolstarColoringType)
          }
          value={context.get.coloringType}
          defaultValue="charges-relative"
        >
          <SelectTrigger className="min-w-[180px] border-2">
            <SelectValue placeholder="Select Coloring" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem
              value="structure"
              disabled={
                context.get.viewType !== "ball-and-stick" &&
                context.get.viewType !== "cartoon"
              }
            >
              Structure
            </SelectItem>
            <SelectItem value="charges-relative">Charges (relative)</SelectItem>
            <SelectItem value="charges-absolute">Charges (absolute)</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="w-full col-span-1 sm:w-1/2">
        {context.get.coloringType === "charges-absolute" && (
          <>
            <h3 className="mb-2 w-fit">Max Value</h3>
            <div className="flex gap-4">
              <Input
                value={context.get.maxValue}
                type="number"
                className="border-2 lg:min-w-[120px]"
                onChange={({ target }) =>
                  onMaxValueChange(target.valueAsNumber)
                }
                min={0}
                step={0.01}
              />

              <Button
                type="button"
                variant={"secondary"}
                onClick={resetMaxValue}
              >
                Reset
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
