import { Navigate, Outlet, useLocation } from "react-router-dom";

interface ProtectedRouteProps {
  allowedRoles?: string[];
}

function ProtectedRoute({ allowedRoles }: ProtectedRouteProps = {}) {
  const location = useLocation();
  const token = localStorage.getItem("zuka_access_token");

  if (!token) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname }}
      />
    );
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
      return (
        <Navigate
          to="/dashboard"
          replace
        />
      );
    }
  }

  return <Outlet />;
}

export default ProtectedRoute;