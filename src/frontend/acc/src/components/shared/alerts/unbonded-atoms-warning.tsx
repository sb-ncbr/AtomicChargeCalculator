import type { FileWarning } from "@acc/api/compute/compute";

import { unbondedAtomsMessage } from "@acc/api/compute/compute";
import { HTMLAttributes, HTMLElementType } from "react";

import { WarningAlert } from "../warning-alert";
import { LearnMore } from "./learn-more";

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
          Some atoms of ligands or modified residues have no bonds, so their
          charges and the charges of their neighbours are probably wrong. This
          happens when the file does not contain the bonds of a ligand and the
          ligand is unknown, or its atoms, often added hydrogens, have other
          names than usual. <LearnMore entry="Atoms without bonds" />
          <ul className="list-disc ml-4 mt-1">
            {warnings.map((warning, index) => (
              <li key={index}>
                {warning.file}: {unbondedAtomsMessage(warning)}
              </li>
            ))}
          </ul>
        </>
      }
    />
  );
};
