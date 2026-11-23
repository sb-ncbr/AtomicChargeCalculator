import { FileWarning } from "@acc/api/compute/compute";

import { Parameters } from "../parameters/types";

export const MethodTypes = {
  "2D": "2D",
  "3D": "3D",
  OTHER: "other",
} as const;

export type MethodType = (typeof MethodTypes)[keyof typeof MethodTypes];

export type Method = {
  name: string;
  internalName: string;
  fullName: string;
  publication: string | null;
  type: MethodType;
  hasParameters: boolean;
  notes?: string | null;
};

export type SuitableMethods = {
  methods: Method[];
  parameters: Record<Method["internalName"], Parameters[]>;
  // Everything ChargeFW warns about in the files as they will be calculated.
  warnings: FileWarning[];
};

export type MostSuitableMethod = {
  method: Method;
  parameters?: Parameters;
};
