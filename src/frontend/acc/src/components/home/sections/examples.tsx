import Dinitrophenol from "@acc/assets/images/dinitrophenol.png";
import Oseltamivir from "@acc/assets/images/oseltamivir.png";
import Pore from "@acc/assets/images/pore.png";
import { createSearchParams, useNavigate } from "react-router";

import { Example } from "../example";
import { Section } from "../section";

export const Examples = () => {
  const navigate = useNavigate();

  const goToExample = async (exampleId: string) => {
    void navigate({
      pathname: "/results",
      search: createSearchParams({
        example_id: exampleId,
      }).toString(),
    });
  };

  return (
    <Section title="Examples">
      <div className="grid grid-cols-1 gap-8 h-full xl:grid-cols-3">
        <Example
            title="Pore complex"
            image={{src: Pore, alt: "Pore Complex"}}
            actions={[
              {name: "Pore complex", action: () => goToExample("pore")},
            ]}
        >
          <p>
            The SARS-CoV-2 pore complex (PDB ID{" "}
            <a
                href="https://www.ebi.ac.uk/pdbe/entry/pdb/8yax"
                target="_blank"
                referrerPolicy="no-referrer"
                className="text-primary hover:underline"
                rel="noreferrer"
            >
              8yax
            </a>
            ) forming double-membrane vesicles to accommodate viral RNA synthesis and modifications [
            <a
                href="https://doi.org/10.1038/s41586-024-07817-y"
                target="_blank"
                referrerPolicy="no-referrer"
                className="text-primary hover:underline"
                rel="noreferrer"
            >
              source
            </a>
            ]. Visualisation of partial charges on the surface highlights the difference between the nonpolar
            transmembrane part (mostly
            white due to charge around zero) and the polar surface of extracellular and cytoplasmic parts (with a mosaic
            of blue positive and red negative charges).
          </p>
        </Example>
        <Example
            title="Neuraminidase in complex with oseltamivir"
            image={{src: Oseltamivir, alt: "Oseltamivir"}}
            actions={[
              {name: "Oseltamivir", action: () => goToExample("oseltamivir")},
            ]}
        >
          <p>
            Oseltamivir, an antiviral drug known as TAMIFLU, binds to N1 neuraminidase from Influenza A virus
            (PDB ID{" "}
            <a
                href="https://www.ebi.ac.uk/pdbe/entry/pdb/2hu4"
                target="_blank"
                referrerPolicy="no-referrer"
                className="text-primary hover:underline"
                rel="noreferrer"
            >
              2hu4</a>) [
            <a
                href="https://doi.org/10.1038/nature05114"
                target="_blank"
                referrerPolicy="no-referrer"
                className="text-primary hover:underline"
                rel="noreferrer"
            >
              source
            </a>
            ]. Oseltamivir has a negatively charged carboxylate group that interacts electrostatically with positively
            charged arginines of the protein. Other functional groups of oseltamivir form additional electrostatic
            interactions, which further strengthen the bond between the drug and the protein.
          </p>
        </Example>
        <Example
          title="Dissociating hydrogens"
          image={{ src: Dinitrophenol, alt: "2,4-Dinitrophenol" }}
          actions={[{ name: "Phenols", action: () => goToExample("phenols") }]}
        >
          <p>
            This example focuses on acid dissociation of seven phenolic drugs,
            described in{" "}
            <a
              href="https://www.drugbank.ca/"
              target="_blank"
              referrerPolicy="no-referrer"
              className="text-primary hover:underline"
              rel="noreferrer"
            >
              DrugBank
            </a>
            . Their structures were obtained from{" "}
            <a
              href="https://pubchem.ncbi.nlm.nih.gov/"
              target="_blank"
              referrerPolicy="no-referrer"
              className="text-primary hover:underline"
              rel="noreferrer"
            >
              PubChem
            </a>
            . During the acid dissociation, these compounds release a hydrogen
            from the phenolic OH group. Using ACC II, we can examine a relation
            between pKa and a charge on the dissociating hydrogen. We found that
            the higher is pKa, the lower charge the hydrogen has (see{" "}
            <a
              href="pka.pdf"
              target="_blank"
              referrerPolicy="no-referrer"
              className="text-primary hover:underline"
            >
              table
            </a>
            ). This finding agrees with results published in{" "}
            <a
              href="https://pubs.acs.org/doi/full/10.1021/ci200133w"
              target="_blank"
              referrerPolicy="no-referrer"
              className="text-primary hover:underline"
              rel="noreferrer"
            >
              literature
            </a>
            .
          </p>
        </Example>
      </div>
    </Section>
  );
};
