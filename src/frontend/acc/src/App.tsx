import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";

import { AuthProvider } from "./lib/contexts/auth-context";
import { FileStatsContextProvider } from "./lib/contexts/file-stats-context";
import { useFileStatsLocalStorage } from "./lib/hooks/use-file-stats-local-storage";
import { Router } from "./router";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
    },
  },
});

export const App = () => {
  const fileStatsLocalStorage = useFileStatsLocalStorage();

  return (
    <QueryClientProvider client={queryClient}>
      <Toaster richColors />
      <AuthProvider>
        <FileStatsContextProvider value={fileStatsLocalStorage}>
          <Router />
        </FileStatsContextProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
};
