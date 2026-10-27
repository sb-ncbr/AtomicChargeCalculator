import { PropsWithChildren } from "react";

import { useAuthQuery } from "../hooks/queries/use-auth";
import { AuthContext } from "./auth-context";

type AuthProviderProps = PropsWithChildren;

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const verifyQuery = useAuthQuery();
  const isAuthenticated = verifyQuery.data?.isAuthenticated ?? null;
  const isLoading = verifyQuery.isLoading || verifyQuery.isFetching;

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};
