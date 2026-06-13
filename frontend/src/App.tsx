import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./store/auth";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import ListingFormPage from "./pages/ListingFormPage";
import ListingDetailPage from "./pages/ListingDetailPage";
import VideoStudioPage from "./pages/VideoStudioPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore();
  return isAuthenticated() ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/listings/new"
        element={
          <ProtectedRoute>
            <ListingFormPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/listings/:id"
        element={
          <ProtectedRoute>
            <ListingDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/listings/:id/video"
        element={
          <ProtectedRoute>
            <VideoStudioPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
