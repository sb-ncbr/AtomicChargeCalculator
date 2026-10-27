import { MoleculeSetStats } from "@acc/api/calculations/types";
import { createContext } from "react";

// keys are file hashes
export type FileStats = Record<string, MoleculeSetStats>;

export type FileStatsContextValue = {
  get: (computationId: string) => FileStats | undefined;
  set: (computationId: string, stats: FileStats) => void;
};

export const FileStatsContext = createContext<FileStatsContextValue | null>(
  null
);

export const FileStatsContextProvider = FileStatsContext.Provider;
