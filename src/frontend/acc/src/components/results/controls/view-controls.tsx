import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@acc/components/ui/select";
import { useControlsContext } from "@acc/lib/hooks/contexts/use-controls-context";
import MolstarPartialCharges from "@acc/lib/viewer/viewer";
import { useEffect } from "react";

// Overriding the default view type for specific examples
const exampleOverrides: Record<string, { viewType: MolstarViewType }> = {
  "examples/pore": {
    viewType: "surface",
  },
  "examples/oseltamivir": {
    viewType: "cartoon",
  },
};

export type MolstarViewControlsProps = {
  molstar: MolstarPartialCharges;
  computationId: string;
};

export type MolstarViewType = "ball-and-stick" | "cartoon" | "surface";

export const MolstarViewControls = ({
  computationId,
  molstar,
}: MolstarViewControlsProps) => {
  const context = useControlsContext(molstar);

  const initializeView = async () => {
    if (!molstar.type.isDefaultApplicable()) {
      // default (cartoon) is unavailable, switch to ball-and-stick
      await context.set.viewType("ball-and-stick");
      return;
    }

    if (exampleOverrides?.[computationId]?.viewType) {
      // hack to allow for surface to load ...
      await new Promise((resolve) => setTimeout(resolve, 200));
      await context.set.viewType(exampleOverrides[computationId].viewType);
    }
  };

  useEffect(() => {
    void initializeView();
  }, []);

  return (
    <div>
      <h3 className="font-bold mb-2">View</h3>
      <Select onValueChange={context.set.viewType} value={context.get.viewType}>
        <SelectTrigger className="md:min-w-[180px] border-2">
          <SelectValue placeholder="Select View" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem
            value="cartoon"
            disabled={!molstar.type.isDefaultApplicable()}
          >
            Cartoon
          </SelectItem>
          <SelectItem value="ball-and-stick">Balls and Sticks</SelectItem>
          <SelectItem value="surface">Surface</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
};
