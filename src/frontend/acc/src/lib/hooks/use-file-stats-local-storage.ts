import {
  FileStats,
  FileStatsContextValue,
} from "@acc/lib/contexts/file-stats-context";
import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "acc_file_stats";

export const useFileStatsLocalStorage = (): FileStatsContextValue => {
  const [statsMap, setStatsMap] = useState<Record<string, FileStats>>({});

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        setStatsMap(JSON.parse(stored));
      } catch {
        setStatsMap({});
      }
    }
  }, []);

  const persist = useCallback((map: Record<string, FileStats>) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  }, []);

  const get = useCallback(
    (computationId: string): FileStats | undefined => {
      return statsMap[computationId];
    },
    [statsMap]
  );

  const set = useCallback(
    (computationId: string, stats: FileStats): void => {
      setStatsMap((prev) => {
        const next = { ...prev, [computationId]: stats };
        persist(next);
        return next;
      });
    },
    [persist]
  );

  return { get, set };
};
