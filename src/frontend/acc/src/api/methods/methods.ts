import { api } from "../base";
import { ApiResponse } from "../types";
import { Method, SuitableMethods } from "./types";

// we don't want to show 'dummy' method on frontend
const DUMMY_KEY = "dummy";

const FALLBACK_ERROR_MESSAGE = "Something went wrong.";

export const getSuitableMethods = async (
  computationId: string
): Promise<SuitableMethods> => {
  const response = await api.post<ApiResponse<SuitableMethods>>(
    `/charges/${computationId}/methods/suitable`
  );

  if (!response.data.success) {
    throw new Error(response.data.message ?? FALLBACK_ERROR_MESSAGE);
  }

  const data = response.data.data;

  data.methods = data.methods.filter(
    (method) => method.internalName !== DUMMY_KEY
  );
  delete data.parameters[DUMMY_KEY];

  return data;
};

export const getSuitableMethodsForFiles = async (
  fileHashes: string[],
  permissiveTypes: boolean
): Promise<SuitableMethods> => {
  const response = await api.post<ApiResponse<SuitableMethods>>(
    `/charges/methods/suitable`,
    {
      fileHashes,
      permissiveTypes,
    }
  );

  if (!response.data.success) {
    throw new Error(response.data.message ?? FALLBACK_ERROR_MESSAGE);
  }

  return response.data.data;
};

export const getAvailableMethods = async (): Promise<Method[]> => {
  const response = await api.get<ApiResponse<Method[]>>(
    `/charges/methods/available`
  );

  if (!response.data.success) {
    throw new Error(response.data.message ?? FALLBACK_ERROR_MESSAGE);
  }

  const data = response.data.data;
  const methods = data.filter((method) => method.internalName !== DUMMY_KEY);

  return methods;
};
