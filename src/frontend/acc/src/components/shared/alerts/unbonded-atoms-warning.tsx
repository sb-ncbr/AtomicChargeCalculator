import type { FileWarning } from "@acc/api/compute/compute";

import { HTMLAttributes, HTMLElementType } from "react";

import { WarningAlert } from "../warning-alert";

export type UnbondedAtomsWarningProps = {
  warnings: FileWarning[];
} & HTMLAttributes<HTMLElementType>;

export const UnbondedAtomsWarning = ({
  warnings,
  className,
}: UnbondedAtomsWarningProps) => {
  return (
    <WarningAlert
      className={className}
      title="Atoms without bonds"
      description={
        <>
          Charges of these atoms and their neighbours are probably wrong. Bonds
          of ligands and modified residues come from the file or from the wwPDB
          Chemical Component Dictionary. A ligand that is not in the dictionary
          needs its bonds in the file, as CONECT records in PDB or
          _chem_comp_bond in mmCIF; SDF and MOL2 files always have them.
          <ul className="list-disc ml-4 mt-1">
            {warnings.map((warning, index) => (
              <li key={index}>
                {warning.file}: {warning.message}
              </li>
            ))}
          </ul>
        </>
      }
    />
  );
};
