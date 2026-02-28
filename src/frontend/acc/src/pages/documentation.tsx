import { Documentation } from "@acc/components/documentation/documentation";
import { useTitle } from "@acc/lib/hooks/use-title";

export const DocumentationPage = () => {
  useTitle("Documentation");

  return <Documentation />;
};
