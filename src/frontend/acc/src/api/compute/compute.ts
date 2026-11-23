import { api } from "../base";
import { ApiResponse } from "../types";
import { AdvancedSettings, ComputationConfig } from "./types";

export type CalculationStatus = "CALCULATING" | "COMPLETED" | "FAILED";

/** A method and parameter set whose charges are not available for a file. */
export interface UnavailableCharges {
  method: string;
  methodName: string;
  parameters: string | null;
  parametersName: string | null;
  file: string;
  message: string;
  /** ChargeFW's code of the reason, or one of ACC's own, such as "unexpected_error". */
  kind: string;
  /** Every reason ChargeFW gave. */
  issues: Issue[];
}

/**
 * A problem that ChargeFW reports, with its code in `kind`, such as
 * "unbonded_residue_atoms". `source` says where it comes from: reading the file
 * ("import"), the molecules as calculated ("input"), the charges ("charge"), how the
 * calculation ran ("plan"), why it did not ("rejection", "failure"), or why its charges
 * cannot be written ("output").
 */
export interface Issue {
  kind: string;
  message: string;
  source:
    | "import"
    | "input"
    | "charge"
    | "plan"
    | "rejection"
    | "failure"
    | "output"
    | "acc";
  /** Name of the molecule, when the issue is about one. */
  molecule: string | null;
  /** Positions of the atoms in the molecule. */
  atomIndices: number[];
}

/**
 * A warning about a file or about one of its calculations. The API lists every warning
 * of ChargeFW; the page chooses the kinds it shows.
 */
export interface FileWarning extends Issue {
  file: string;
  /** The calculation, for warnings that are not about reading the file. */
  method?: string;
  parameters?: string | null;
}

/** Whether ChargeFW warns that a molecule has carbon but no hydrogen atoms. */
export const isMissingHydrogens = (warnings: FileWarning[] | undefined) =>
  warnings?.some(({ kind }) => kind === "hydrogens_missing") ?? false;

/** Whether ChargeFW warns that the calculated charges are probably wrong. */
export const isSuspiciousCharges = ({ kind }: FileWarning) =>
  kind === "atoms_too_close" || kind === "charge_out_of_range";

export interface CalculationStatusResponse {
  status: CalculationStatus;
  error?: string;
  unavailable?: UnavailableCharges[];
  warnings?: FileWarning[];
}

export const setup = async (
  fileHashes: string[],
  settings?: AdvancedSettings
): Promise<string> => {
  const response = await api.post<ApiResponse<string>>("/charges/setup", {
    fileHashes,
    ...(settings ? { settings } : {}),
  });

  if (!response.data.success) {
    throw new Error(response.data.message);
  }

  return response.data.data;
};

export const compute = async (
  fileHashes: string[],
  configs: ComputationConfig[],
  computationId?: string,
  settings?: AdvancedSettings
): Promise<string> => {
  const body: Record<string, unknown> = {
    fileHashes,
    configs: configs.map((comp) => ({
      method: comp.method || null,
      parameters: comp.parameters || null,
    })),
    ...(settings ? { settings } : {}),
  };

  if (computationId) {
    body.computation_id = computationId;
  }

  const response = await api.post<ApiResponse<string>>(
    `/charges/calculate`,
    body,
    {
      params: {
        response_format: "none",
      },
    }
  );

  if (!response.data?.success) {
    throw new Error(response.data.message ?? "Something went wrong.");
  }

  return response.data.data;
};

export const getMolecules = async (
  computationId: string
): Promise<string[]> => {
  const response = await api.get<ApiResponse<string[]>>(
    `/charges/${computationId}/molecules`
  );

  if (!response.data.success) {
    throw Error(response.data.message ?? "Something went wrong.");
  }

  return response.data.data;
};

export const getCalculationStatus = async (
  computationId: string
): Promise<CalculationStatusResponse> => {
  const response = await api.get<ApiResponse<CalculationStatusResponse>>(
    `/charges/${computationId}/status`
  );

  if (!response.data.success) {
    throw Error(response.data.message ?? "Something went wrong.");
  }

  return response.data.data;
};
