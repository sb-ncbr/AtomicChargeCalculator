import { Section } from "../section";

export const Citing = () => {
  return (
    <Section title="Citing">
      <p>
        If you found Atomic Charge Calculator III helpful, please cite:{" "}
        <i>
          Raček T., Pilát M., Schindler O., Bučeková G., Tichý D., Berka K., Svobodová R. (2026).{" "}
          <a
            href="https://doi.org/10.1093/nar/gkag379"
            target="_blank"
            referrerPolicy="no-referrer"
            className="text-primary hover:underline" rel="noreferrer"
          >
            Atomic Charge Calculator III: a modern platform for calculating partial atomic charges
          </a>
          . Nucleic Acids Research.
        </i>{" "}
        Are you interested in a research collaboration? Feel free to{" "}
        <a
          href="mailto:tomas.racek@muni.cz"
          target="_blank"
          referrerPolicy="no-referrer"
          className="text-primary hover:underline" rel="noreferrer"
        >
          contact us
        </a>
        .
      </p>
    </Section>
  );
};
