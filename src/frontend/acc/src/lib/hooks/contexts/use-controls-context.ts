import { MolstarColoringType } from "@acc/components/results/controls/coloring-controls";
import { MolstarViewType } from "@acc/components/results/controls/view-controls";
import { ControlsContext } from "@acc/lib/contexts/controls-context";
import MolstarPartialCharges from "@acc/lib/viewer/viewer";
import { useContext } from "react";

export type ControlsContextHookType = {
  get: {
    coloringType: MolstarColoringType;
    maxValue: number;
    viewType: MolstarViewType;
    currentTypeId: number;
    structure: string;
    methodNames: (string | undefined)[];
  };
  set: {
    coloringType: (type: MolstarColoringType) => Promise<void>;
    maxValue: (value: number) => Promise<void>;
    viewType: (type: MolstarViewType) => Promise<void>;
    typeId: (id: number) => void;
    structure: (structure: string) => void;
    methodNames: (names: (string | undefined)[]) => void;
  };
};

export const useControlsContext = (
  molstar: MolstarPartialCharges
): ControlsContextHookType => {
  const context = useContext(ControlsContext);

  if (context === null) {
    throw Error("Busy context is null.");
  }

  const coloringType = async (
    type: MolstarColoringType,
    maxValue: number | null = null
  ) => {
    maxValue ??= context.maxValue;

    switch (type) {
      case "structure":
        await molstar.color.default();
        break;
      case "charges":
        await molstar.color.absolute(maxValue);
        break;
      default:
        console.warn(
          `Invalid Molstar coloring type. ('${type}'), nothing changed.`
        );
    }
    context.setColoringType(type);
  };

  const maxValue = async (value: number): Promise<void> => {
    context.setMaxValue(value);
    await coloringType(context.coloringType, value);
  };

  const viewType = async (type: MolstarViewType) => {
    switch (type) {
      case "ball-and-stick":
        await molstar.type.ballAndStick();
        break;
      case "cartoon":
        await molstar.type.default();
        break;
      case "surface":
        await molstar.type.surface();
        if (context.coloringType === "structure") {
          await coloringType("charges");
        }

        break;
      default:
        console.error(
          `Invalid Molstar view type. ('${type}'), nothing changed.`
        );
        return;
    }

    context.setViewType(type);
  };

  const typeId = async (id: number): Promise<void> => {
    molstar.charges.setTypeId(id);
    await coloringType(context.coloringType);
    context.setCurrentTypeId(id);
  };

  const structure = (structure: string): void => {
    context.setStructure(structure);
  };

  const methodNames = (names: (string | undefined)[]): void => {
    context.setMethodNames(names);
  };

  return {
    get: {
      coloringType: context.coloringType,
      maxValue: context.maxValue,
      currentTypeId: context.currentTypeId,
      viewType: context.viewType,
      structure: context.structure,
      methodNames: context.methodNames,
    },
    set: {
      coloringType,
      maxValue,
      viewType,
      typeId,
      structure,
      methodNames,
    },
  };
};
