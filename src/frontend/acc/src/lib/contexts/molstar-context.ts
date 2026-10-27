import { PluginUIContext } from "molstar/lib/commonjs/mol-plugin-ui/context";
import { createContext } from "react";

export type MolstarContextType = {
  plugin?: PluginUIContext;
};

export const MolstarContext = createContext<MolstarContextType | null>(null);

export const MolstarContextProvider = MolstarContext.Provider;
