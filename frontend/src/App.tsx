import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppProvider } from "./lib/appState";
import { Layout } from "./components/Layout";
import { Overview } from "./pages/Overview";
import { Demo } from "./pages/Demo";
import { Ask } from "./pages/Ask";
import { Capture } from "./pages/Capture";
import { MemoryCenter } from "./pages/MemoryCenter";
import { Evolution } from "./pages/Evolution";
import { Risk } from "./pages/Risk";
import { Governance } from "./pages/Governance";
import { Audit } from "./pages/Audit";

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/demo" element={<Demo />} />
            <Route path="/ask" element={<Ask />} />
            <Route path="/capture" element={<Capture />} />
            <Route path="/memory" element={<MemoryCenter />} />
            <Route path="/evolution" element={<Evolution />} />
            <Route path="/risk" element={<Risk />} />
            <Route path="/governance" element={<Governance />} />
            <Route path="/audit" element={<Audit />} />
            <Route path="*" element={<Overview />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </AppProvider>
  );
}
