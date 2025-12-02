import { Setup } from "@acc/components/setup/setup";
import { useTitle } from "@acc/lib/hooks/use-title";
import { useNavigate, useSearchParams } from "react-router";

export const SetupPage = () => {
  useTitle("Setup");

  const navigate = useNavigate();
  const [searchParams, _] = useSearchParams();

  const computationId = searchParams.get("comp_id");
  if (!computationId) {
    void navigate("/");
    return null;
  }

  return <Setup computationId={computationId} />;
};
