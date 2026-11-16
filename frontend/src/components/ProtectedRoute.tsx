import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useSyncExternalStore } from "react";
import { SESSION_EXPIRED_EVENT } from "../services/sessionFetch";

function subscribeToSession(listener: () => void) {
  window.addEventListener(SESSION_EXPIRED_EVENT, listener);
  window.addEventListener("storage", listener);
  return () => {
    window.removeEventListener(SESSION_EXPIRED_EVENT, listener);
    window.removeEventListener("storage", listener);
  };
}

function getSessionToken() {
  return localStorage.getItem("zuka_access_token");
}

interface ProtectedRouteProps {
  allowedRoles?: string[];
}

function ProtectedRoute({ allowedRoles }: ProtectedRouteProps = {}) {
  const location = useLocation();
  const token = useSyncExternalStore(subscribeToSession, getSessionToken);

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (allowedRoles && allowedRoles.length > 0) {
    const rawUser = localStorage.getItem("zuka_user");
    let role = "VIEWER";
    if (rawUser) {
      try {
        const parsed = JSON.parse(rawUser);
        role = parsed.role || "VIEWER";
      } catch {
        role = "VIEWER";
      }
    }

    if (!allowedRoles.includes(role)) {
      return <Navigate to="/dashboard" replace />;
    }
  }

  return <Outlet />;
}

export default ProtectedRoute;
