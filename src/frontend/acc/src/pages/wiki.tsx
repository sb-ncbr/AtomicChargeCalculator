import { Wiki } from "@acc/components/wiki/wiki";
import { useTitle } from "@acc/lib/hooks/use-title";

export const WikiPage = () => {
  useTitle("Wiki");

  return <Wiki />;
};
