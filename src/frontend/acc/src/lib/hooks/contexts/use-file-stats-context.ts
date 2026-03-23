import {
  FileStats,
  FileStatsContext,
  FileStatsContextValue,
} from "@acc/lib/contexts/file-stats-context";
import { useContext } from "react";

export type FileStatsContextHookType = {
  isMissingHydrogens: (compId: string) => boolean;
} & FileStatsContextValue;

export const useFileStatsContext = () => {
  const context = useContext(FileStatsContext);

  if (context === null) {
    throw Error("File stats context is null.");
  }

  const isMissingHydrogens = (compId: string) => {
    return Object.values(context.get(compId) ?? {}).some(
      (stat) =>
        (stat.atomTypeCounts.find(({ symbol }) => symbol === "H")?.count ??
          0) === 0
    );
  };

  return {
    get: (computationId: string) => context.get(computationId),
    set: (computationId: string, fileStats: FileStats) =>
      context.set(computationId, fileStats),
    isMissingHydrogens: isMissingHydrogens,
  };
};
