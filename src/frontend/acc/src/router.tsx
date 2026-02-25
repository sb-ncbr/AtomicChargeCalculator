import { BrowserRouter, Route, Routes } from "react-router";

import { Layout } from "./components/layout/layout";
import { CalculationsPage } from "./pages/calculations";
import { FilesPage } from "./pages/files";
import { HomePage } from "./pages/home";
import { ResultsPage } from "./pages/results";
import { SetupPage } from "./pages/setup";
import { WikiPage } from "./pages/wiki";

export const Router = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="wiki" element={<WikiPage />} />
          <Route path="setup" element={<SetupPage />} />
          <Route path="results" element={<ResultsPage />} />
          <Route path="calculations" element={<CalculationsPage />} />
          <Route path="files" element={<FilesPage />} />
          <Route path="*" element={<HomePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};
