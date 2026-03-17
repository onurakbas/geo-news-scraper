import { BrowserRouter, Route, Routes } from "react-router-dom";

import MapPage from "../pages/MapPage";

/**
 * Root component – sets up routing.
 * Additional pages (e.g. detail) can be added as new <Route> entries.
 */
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MapPage />} />
      </Routes>
    </BrowserRouter>
  );
}
