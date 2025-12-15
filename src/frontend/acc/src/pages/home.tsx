import { Home } from "@acc/components/home/home";
import { useTitle } from "@acc/lib/hooks/use-title";

export const HomePage = () => {
  useTitle("Home");

  return <Home />;
};
