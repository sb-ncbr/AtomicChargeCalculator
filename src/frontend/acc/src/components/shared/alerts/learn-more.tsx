export type LearnMoreProps = {
  // Heading of the entry in the section "Warnings and failures" of the documentation.
  entry: string;
};

/** Link from a warning to what the documentation says about it. */
export const LearnMore = ({ entry }: LearnMoreProps) => {
  return (
    <a
      href={`/docs#${entry.toLocaleLowerCase().replaceAll(/\s+/g, "-")}`}
      target="_blank"
      rel="noopener noreferrer"
      className="underline whitespace-nowrap"
    >
      Learn more
    </a>
  );
};
