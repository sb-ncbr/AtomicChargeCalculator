export type SetupResponse = {
  computationId: string;
};

export type ComputationConfig = {
  method?: string;
  parameters?: string;
};

// Atoms of PDB/mmCIF files to calculate; each selection adds to the next: polymers
// (with their modified residues), then ligands and ions, then water.
export type Selection = "polymers" | "polymers-and-ligands" | "all";

export type AdvancedSettings = {
  selection: Selection;
  permissiveTypes: boolean;
};
