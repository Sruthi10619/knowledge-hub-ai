import { lazy, Suspense, useEffect, useState, type ReactNode } from "react";
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAppStore } from "./stores/useAppStore";

const Auth = lazy(() => import("./pages/Auth"));
const Layout = lazy(() => import("./pages/Layout"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const FolderView = lazy(() => import("./pages/FolderView"));
const AnalyticsView = lazy(() => import("./pages/AnalyticsView"));
const SettingsView = lazy(() => import("./pages/SettingsView"));

/** Route guard — redirects to /login if unauthenticated. */
function ProtectedRoute({ children }: { children: ReactNode }) {
  const { token, user, loading, checkAuth } = useAppStore();
  const navigate = useNavigate();
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    if (!user) {
      checkAuth().then((ok) => {
        setAuthChecked(true);
        if (!ok) navigate("/login", { replace: true });
      });
    } else {
      setAuthChecked(true);
    }
  }, [token, user, checkAuth, navigate]);

  if (!token) return null;
  if (!user && (!authChecked || loading)) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950 text-slate-400">
        <Loader2 className="h-8 w-8 animate-spin text-violet-500" />
      </div>
    );
  }
  if (!user) return null;
  return <>{children}</>;
}

export default function App() {
  const { theme } = useAppStore();

  // Sync HTML class on initial render
  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(theme);
  }, [theme]);

  return (
    <BrowserRouter>
      <Suspense
        fallback={
          <div className="flex h-screen items-center justify-center bg-slate-950 text-slate-400">
            <Loader2 className="h-8 w-8 animate-spin text-violet-500" />
          </div>
        }
      >
        <Routes>
          {/* Public auth route */}
          <Route path="/login" element={<Auth />} />

          {/* Protected app shell */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="folders/:folderId" element={<FolderView />} />
            <Route path="analytics" element={<AnalyticsView />} />
            <Route path="settings" element={<SettingsView />} />
          </Route>

          {/* Catch-all → dashboard */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
