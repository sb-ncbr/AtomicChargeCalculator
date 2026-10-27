import { createContext } from "react";

export type AuthContextType = {
  isAuthenticated: boolean | null;
  isLoading: boolean;
};

export const AuthContext = createContext<AuthContextType>({
  isAuthenticated: null,
  isLoading: false,
});
