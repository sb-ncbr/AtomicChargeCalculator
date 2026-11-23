import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";

import { AuthProvider } from "./lib/contexts/auth-provider";
import { Router } from "./router";

// Former versions kept the element counts of uploaded files here to warn about missing
// hydrogens; ChargeFW's warnings replaced them.
localStorage.removeItem("acc_file_stats");

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
    },
  },
});

export const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <Toaster richColors />
      <AuthProvider>
        <Router />
      </AuthProvider>
    </QueryClientProvider>
  );
};
