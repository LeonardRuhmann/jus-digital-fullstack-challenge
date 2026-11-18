import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Loader2, LogOut } from "lucide-react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import LoginPage from "./pages/LoginPage";

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-1 flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-7 h-7 animate-spin text-brand-green" />
        <p className="text-sm text-slate-11">Carregando sua sessão...</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function TemporaryAuthenticatedPreview() {
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <div className="min-h-screen bg-slate-1 flex items-center justify-center p-6">
      <div className="bg-white border border-slate-6 rounded-[12px] p-6 max-w-md w-full shadow-sm space-y-4">
        <div className="flex items-center gap-3">
          {user.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={user.name}
              referrerPolicy="no-referrer"
              className="w-10 h-10 rounded-[8px] object-cover"
            />
          ) : (
            <div className="w-10 h-10 rounded-[8px] bg-brand-green text-white flex items-center justify-center font-semibold">
              {user.name.charAt(0).toUpperCase()}
            </div>
          )}
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-slate-12 truncate">
              {user.name}
            </p>
            <p className="text-xs text-slate-11 truncate">{user.email}</p>
          </div>
        </div>
        <p className="text-xs text-slate-11">
          Login Google OAuth 2.0 funcionando! No próximo passo (Step 3.3) colocaremos a Sidebar verde oficial do Figma aqui.
        </p>
        <button
          type="button"
          onClick={() => void logout()}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-[8px] bg-slate-3 hover:bg-slate-6/60 text-xs font-medium text-slate-12 transition-colors"
        >
          <LogOut className="w-3.5 h-3.5" />
          Sair da conta
        </button>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/documentos"
            element={
              <ProtectedRoute>
                <TemporaryAuthenticatedPreview />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/documentos" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
