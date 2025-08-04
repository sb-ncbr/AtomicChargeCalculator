import { useAuth } from "@acc2/lib/hooks/queries/use-auth";
import { NavLink } from "react-router";

export const Footer = () => {
  const { isAuthenticated } = useAuth();

  return (
    <footer className="w-full bg-primary px-8 py-4 text-white h-footer">
      <div className="max-w-content mx-auto">
        <span className="text-center text-xs block">
          © {new Date().getFullYear()} SB NCBR
        </span>
        <div className="flex justify-between">
          <div>
            <ul>
              <li>
                <NavLink className="hover:underline" to={"/"}>
                  Home
                </NavLink>
              </li>
              {isAuthenticated && (
                <>
                  <li>
                    <NavLink className="hover:underline" to={"/calculations"}>
                      Calculations
                    </NavLink>
                  </li>
                  <li>
                    <NavLink className="hover:underline" to={"/files"}>
                      Files
                    </NavLink>
                  </li>
                </>
              )}
            </ul>
          </div>
          <div className="flex flex-col items-start">
            <NavLink
              className="hover:underline"
              to="https://webchem.ncbr.muni.cz/Platform/Home/TermsOfUse"
            >
              Terms of Use & GDPR
            </NavLink>
            <NavLink
              className="hover:underline"
              to="https://github.com/sb-ncbr/AtomicChargeCalculator"
            >
              GitHub
            </NavLink>
            <NavLink className="hover:underline" to="https://sb.ncbr.muni.cz/en">
              SB NCBR
            </NavLink>
          </div>
        </div>
      </div>
    </footer>
  );
};
