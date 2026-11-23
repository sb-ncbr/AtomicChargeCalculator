import { Selection } from "@acc/api/compute/types";

export type CalculationPreview = {
  id: string;
  files: { [filename: string]: MoleculeSetStats };
  configs: {
    method: string;
    parameters: string;
  }[];
  settings: {
    // "without-hetatm": made by ACC before ChargeFW 3, which left out HETATM records.
    // Such computations are shown, but not calculated again.
    selection: Selection | "without-hetatm";
    permissiveTypes: boolean;
  };
  createdAt: string;
};

export type MoleculeSetStats = {
  totalMolecules: number;
  totalAtoms: number;
  atomTypeCounts: {
    symbol: string;
    count: number;
  }[];
};
