import { api } from "../base";
import { ApiResponse } from "../types";
import { AdvancedSettings, ComputationConfig } from "./types";

export type CalculationStatus = "CALCULATING" | "COMPLETED" | "FAILED";

export interface CalculationStatusResponse {
  status: CalculationStatus;
  error?: string;
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
