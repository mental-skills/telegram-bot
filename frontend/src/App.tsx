import { useEffect, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { authenticate } from "./api/client";
import { ErrorPage, LoadingPage, OfflinePage } from "./components/StatusPages";
import { useOnline } from "./hooks/useOnline";
import { AgePage, EntryPage, HomePage, ProfilePage, ProgressPage, SituationsPage } from "./pages/MainPages";
import { TrainingPage } from "./pages/TrainingPage";
import { initializeTelegram } from "./telegram/bridge";

export default function App() {
  const online = useOnline();
  const [authState, setAuthState] = useState<"loading" | "ready" | "error">("loading");
  const [authError, setAuthError] = useState<string>();

  useEffect(() => initializeTelegram(), []);
  useEffect(() => {
    if (!online) return;
    authenticate()
      .then(() => setAuthState("ready"))
      .catch((error: Error) => {
        setAuthError(error.message);
        setAuthState("error");
      });
  }, [online]);

  if (!online) return <OfflinePage retry={() => window.location.reload()} />;
  if (authState === "loading") return <LoadingPage />;
  if (authState === "error") return <ErrorPage message={authError} retry={() => window.location.reload()} />;

  return (
    <Routes>
      <Route path="/" element={<EntryPage />} />
      <Route path="/age" element={<AgePage />} />
      <Route path="/home" element={<HomePage />} />
      <Route path="/situations" element={<SituationsPage />} />
      <Route path="/progress" element={<ProgressPage />} />
      <Route path="/profile" element={<ProfilePage />} />
      <Route path="/training" element={<TrainingPage />} />
      <Route path="*" element={<EntryPage />} />
    </Routes>
  );
}
