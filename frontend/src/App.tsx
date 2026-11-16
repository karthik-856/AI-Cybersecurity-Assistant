import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import SocLayout from "./layouts/SocLayout";
import ProtectedRoute from "./components/ProtectedRoute";

const Login = lazy(() => import("./pages/auth/Login"));
const Register = lazy(() => import("./pages/auth/Register"));
const Dashboard = lazy(() => import("./pages/dashboard/Dashboard"));
const Users = lazy(() => import("./pages/users/Users"));
const NetworkMonitor = lazy(() => import("./pages/network/NetworkMonitor"));
const Databases = lazy(() => import("./pages/database/Databases"));
const AlertsPage = lazy(() => import("./pages/alerts/Alerts"));
const IncidentsPage = lazy(() => import("./pages/incidents/Incidents"));
const InvestigationPage = lazy(() => import("./pages/investigation/Investigation"));
const ReportsPage = lazy(() => import("./pages/reports/Reports"));
const Settings = lazy(() => import("./pages/settings/Settings"));
const DefenseDepartment = lazy(() => import("./pages/defense/DefenseDepartment"));


function App() {
  return (
    <Suspense fallback={<div role="status" aria-live="polite" style={{ padding: 24 }}>Loading page…</div>}>
    <Routes>
      {/* =================================================
          PUBLIC ROUTES
      ================================================= */}

      <Route
        path="/login"
        element={<Login />}
      />

      <Route
        path="/register"
        element={<Register />}
      />

      {/* =================================================
          PROTECTED SOC ROUTES
      ================================================= */}

      <Route element={<ProtectedRoute />}>
        <Route element={<SocLayout />}>
          {/* Accessible to VIEWER, SOC_ANALYST, and ADMIN */}
          <Route
            path="/dashboard"
            element={<Dashboard />}
          />

          <Route
            path="/network-monitor"
            element={<NetworkMonitor />}
          />

          {/* Operational routes: ADMIN and SOC_ANALYST only */}
          <Route element={<ProtectedRoute allowedRoles={["ADMIN", "SOC_ANALYST"]} />}>
            <Route
              path="/alerts"
              element={<AlertsPage />}
            />
            <Route
              path="/incidents"
              element={<IncidentsPage />}
            />
            <Route
              path="/defense"
              element={<DefenseDepartment />}
            />
            <Route
              path="/investigation"
              element={<InvestigationPage />}
            />
            <Route
              path="/reports"
              element={<ReportsPage />}
            />
            <Route
              path="/settings"
              element={<Settings />}
            />
          </Route>

          {/* Admin only: User Management and Database Center */}
          <Route element={<ProtectedRoute allowedRoles={["ADMIN"]} />}>
            <Route
              path="/databases"
              element={<Databases />}
            />
            <Route
              path="/users"
              element={<Users />}
            />
          </Route>
        </Route>
      </Route>

      {/* =================================================
          DEFAULT ROUTE
      ================================================= */}

      <Route
        path="/"
        element={
          <Navigate
            to="/dashboard"
            replace
          />
        }
      />

      {/* =================================================
          UNKNOWN ROUTES
      ================================================= */}

      <Route
        path="*"
        element={
          <Navigate
            to="/dashboard"
            replace
          />
        }
      />
    </Routes>
    </Suspense>
  );
}

export default App;
