import {Section} from "../section";

export const Tools = () => {
    return (
        <Section title="Tools">
            <p>
                Find out about our other tools for computing partial atomic charges:{" "}
                <a
                    href="https://pdbcharges.biodata.ceitec.cz"
                    target="_blank"
                    referrerPolicy="no-referrer"
                    className="text-primary hover:underline" rel="noreferrer">
                    PDBCharges</a> {" "}
                optimised for structures from the Protein Data Bank and {" "}
                <a href="https://alphacharges.ncbr.muni.cz" target="_blank" referrerPolicy="no-referrer"
                   className="text-primary hover:underline" rel="noreferrer">AlphaCharges</a> {" "}
                for structures from the AlphaFold DB.

                <br/>
                Interested in other tools from the Structural Bioinformatics group at National Centre for Biomolecular
                Research (NCBR)?
                Check out our <a
                href="https://sb-ncbr-tools.biodata.ceitec.cz"
                target="_blank"
                referrerPolicy="no-referrer"
                className="text-primary hover:underline" rel="noreferrer">
                complete list
            </a> of tools.
            </p>
        </Section>
    );
};
