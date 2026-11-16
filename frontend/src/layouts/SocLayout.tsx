import {
  AlertTriangle,
  ChevronDown,
  Database,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  Network,
  PanelLeft,
  Search,
  Settings,
  Shield,
  ShieldAlert,
  User,
  Users,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import {
  NavLink,
  Outlet,
  useNavigate,
} from "react-router-dom";
import NotificationCenter from "../components/notifications/NotificationCenter";
import ZukaAssistant from "../components/zuka_assistant/ZukaAssistant";
import "./SocLayout.css";

interface StoredUser {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
}

interface NavigationItem {
  label: string;
  path: string;
  icon: typeof LayoutDashboard;
  roles: string[];
}

interface NavigationGroup {
  section: string;
  items: NavigationItem[];
}

const navGroups: NavigationGroup[] = [
  {
    section: "OVERVIEW",
    items: [
      {
        label: "Dashboard",
        path: "/dashboard",
        icon: LayoutDashboard,
        roles: ["ADMIN", "SOC_ANALYST", "VIEWER"],
      },
    ],
  },
  {
    section: "MONITORING",
    items: [
      {
        label: "Network Monitor",
        path: "/network-monitor",
        icon: Network,
        roles: ["ADMIN", "SOC_ANALYST", "VIEWER"],
      },
    ],
  },
  {
    section: "SOC OPERATIONS",
    items: [
      {
        label: "Alert Center",
        path: "/alerts",
        icon: AlertTriangle,
        roles: ["ADMIN", "SOC_ANALYST"],
      },
      {
        label: "Incident Management",
        path: "/incidents",
        icon: Shield,
        roles: ["ADMIN", "SOC_ANALYST"],
      },
      {
        label: "Defense Department",
        path: "/defense",
        icon: ShieldAlert,
        roles: ["ADMIN", "SOC_ANALYST"],
      },
      {
        label: "Investigation",
        path: "/investigation",
        icon: Search,
        roles: ["ADMIN", "SOC_ANALYST"],
      },
    ],
  },
  {
    section: "REPORTS",
    items: [
      {
        label: "Reports",
        path: "/reports",
        icon: FileText,
        roles: ["ADMIN", "SOC_ANALYST"],
      },
    ],
  },
  {
    section: "ADMINISTRATION",
    items: [
      {
        label: "Database Center",
        path: "/databases",
        icon: Database,
        roles: ["ADMIN"],
      },
      {
        label: "User Management",
        path: "/users",
        icon: Users,
        roles: ["ADMIN"],
      },
    ],
  },
  {
    section: "PREFERENCES",
    items: [
      {
        label: "Settings",
        path: "/settings",
        icon: Settings,
        roles: ["ADMIN", "SOC_ANALYST"],
      },
    ],
  },
];

function getStoredUser(): StoredUser | null {
  const rawUser = localStorage.getItem("zuka_user");
  if (!rawUser) {
    return null;
  }
  try {
    return JSON.parse(rawUser) as StoredUser;
  } catch {
    return null;
  }
}

function SocLayout() {
  const navigate = useNavigate();

  // Desktop/Laptop/TV sidebar collapse state (persisted)
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(() => {
    return localStorage.getItem("zuka_sidebar_collapsed") === "true";
  });

  // Mobile drawer state
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Profile menu dropdown state
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const profileDropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    localStorage.setItem("zuka_sidebar_collapsed", String(sidebarCollapsed));
  }, [sidebarCollapsed]);

  // Synchronize global density and reduced motion preferences across the application
  useEffect(() => {
    function applyGlobalPreferences() {
      try {
        const raw = localStorage.getItem("zuka_settings_preferences_v2");
        if (raw) {
          const parsed = JSON.parse(raw);
          if (parsed.density) {
            document.documentElement.dataset.zukaDensity = parsed.density;
          }
          if (parsed.reducedMotion !== undefined) {
            document.documentElement.dataset.zukaReducedMotion = String(parsed.reducedMotion);
          }
        }
      } catch {
        // ignore
      }
    }
    applyGlobalPreferences();
    window.addEventListener("zuka_preferences_updated", applyGlobalPreferences);
    window.addEventListener("storage", applyGlobalPreferences);
    return () => {
      window.removeEventListener("zuka_preferences_updated", applyGlobalPreferences);
      window.removeEventListener("storage", applyGlobalPreferences);
    };
  }, []);

  // Click outside to close profile dropdown
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        profileDropdownRef.current &&
        !profileDropdownRef.current.contains(event.target as Node)
      ) {
        setProfileMenuOpen(false);
      }
    }
    if (profileMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [profileMenuOpen]);

  const user = getStoredUser();
  const username = user?.username || "Operator";
  const role = user?.role || "VIEWER";
  const initials = username.charAt(0).toUpperCase();

  function handleLogout() {
    localStorage.removeItem("zuka_access_token");
    localStorage.removeItem("zuka_user");
    navigate("/login", {
      replace: true,
    });
  }

  return (
    <div className={`soc-shell ${sidebarCollapsed ? "is-collapsed" : ""}`}>
      {/* MOBILE BACKDROP OVERLAY */}
      <div
        className={`soc-sidebar-backdrop ${mobileMenuOpen ? "active" : ""}`}
        onClick={() => setMobileMenuOpen(false)}
      />

      {/* =================================================
          SIDEBAR
      ================================================= */}
      <aside
        className={`soc-sidebar ${
          sidebarCollapsed ? "desktop-collapsed" : ""
        } ${mobileMenuOpen ? "mobile-open" : ""}`}
      >
        <div className="soc-brand">
          <div className="soc-brand-mark">
            <Shield size={22} />
          </div>

          <div className="soc-brand-text">
            <div className="soc-brand-name">ZUKA</div>
            <div className="soc-brand-subtitle">SECURITY OPERATIONS</div>
          </div>
        </div>

        <div className="soc-sidebar-content">
          <nav className="soc-navigation">
            {navGroups.map((group) => {
              const visibleInGroup = group.items.filter((item) =>
                item.roles.includes(role)
              );

              if (visibleInGroup.length === 0) {
                return null;
              }

              return (
                <div key={group.section} className="soc-navigation-group">
                  <div className="soc-section-label">{group.section}</div>

                  <div className="soc-navigation-items">
                    {visibleInGroup.map((item) => {
                      const Icon = item.icon;

                      return (
                        <NavLink
                          key={item.path}
                          to={item.path}
                          onClick={() => setMobileMenuOpen(false)}
                          className={({ isActive }) =>
                            `soc-nav-item ${isActive ? "active" : ""}`
                          }
                        >
                          <Icon size={17} />
                          <span>{item.label}</span>
                        </NavLink>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </nav>
        </div>

        <div className="soc-sidebar-footer">
          <div className="soc-system-status">
            <span className="soc-status-dot" />
            <span>Platform Operational</span>
          </div>

          <div className="soc-footer-line" />

          <div className="soc-footer-copy">© 2026 ZUKA SOC</div>
          <div className="soc-footer-copy">All rights reserved.</div>
        </div>
      </aside>

      {/* =================================================
          MAIN PLATFORM AREA
      ================================================= */}
      <div className="soc-main">
        <header className="soc-topbar">
          <div className="soc-topbar-left">
            {/* MOBILE ONLY: THREE-LINE HAMBURGER BUTTON */}
            <button
              type="button"
              className="soc-mobile-menu-btn"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle Mobile Navigation"
              title="Open Navigation"
            >
              <Menu size={19} />
            </button>

            {/* LAPTOP, DESKTOP, TV: TOGGLE SIDEBAR TOOL (IMAGE 3 LOGO) */}
            <button
              type="button"
              className={`soc-desktop-sidebar-toggle ${
                sidebarCollapsed ? "collapsed-active" : ""
              }`}
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              aria-label={
                sidebarCollapsed
                  ? "Expand Sidebar"
                  : "Collapse Sidebar"
              }
              title={
                sidebarCollapsed
                  ? "Expand Sidebar"
                  : "Collapse Sidebar"
              }
            >
              <PanelLeft size={19} />
            </button>

            <div className="soc-topbar-title">ZUKA SOC</div>

            <div className="soc-live-badge">
              <span className="soc-live-dot" />
              LIVE
            </div>
          </div>

          <div className="soc-topbar-right">
            <NotificationCenter />

            <div className="soc-user-wrapper" ref={profileDropdownRef}>
              <button
                type="button"
                className={`soc-user ${profileMenuOpen ? "active" : ""}`}
                onClick={() => setProfileMenuOpen(!profileMenuOpen)}
                aria-expanded={profileMenuOpen}
                aria-label="User profile and options menu"
                title="View Account Profile & Menu"
              >
                <div className="soc-user-avatar">{initials}</div>

                <div className="soc-user-info">
                  <div className="soc-user-name">{username}</div>
                  <div className="soc-user-role">{role}</div>
                </div>

                <ChevronDown
                  size={14}
                  className={`soc-user-chevron ${profileMenuOpen ? "rotate" : ""}`}
                />
              </button>

              {profileMenuOpen && (
                <div className="soc-profile-dropdown">
                  <div className="soc-profile-dropdown-header">
                    <div className="soc-dropdown-avatar">{initials}</div>
                    <div className="soc-dropdown-details">
                      <div className="soc-dropdown-name">{username}</div>
                      <div className="soc-dropdown-email">
                        {user?.email || `${username.toLowerCase()}@zuka.soc`}
                      </div>
                      <span className="soc-dropdown-badge">{role}</span>
                    </div>
                  </div>

                  <div className="soc-dropdown-divider" />

                  <div className="soc-dropdown-items">
                    {["ADMIN", "SOC_ANALYST"].includes(role) && (
                      <button
                        type="button"
                        className="soc-dropdown-item"
                        onClick={() => {
                          setProfileMenuOpen(false);
                          navigate("/settings");
                        }}
                      >
                        <User size={15} />
                        <span>Profile & Credentials</span>
                      </button>
                    )}

                    {role === "ADMIN" && (
                      <button
                        type="button"
                        className="soc-dropdown-item"
                        onClick={() => {
                          setProfileMenuOpen(false);
                          navigate("/users");
                        }}
                      >
                        <Users size={15} />
                        <span>User Access Control</span>
                      </button>
                    )}

                    {["ADMIN", "SOC_ANALYST"].includes(role) && (
                      <button
                        type="button"
                        className="soc-dropdown-item"
                        onClick={() => {
                          setProfileMenuOpen(false);
                          navigate("/databases");
                        }}
                      >
                        <Database size={15} />
                        <span>Database Operations</span>
                      </button>
                    )}

                    <div className="soc-dropdown-divider" />

                    <button
                      type="button"
                      className="soc-dropdown-item soc-dropdown-logout"
                      onClick={() => {
                        setProfileMenuOpen(false);
                        handleLogout();
                      }}
                    >
                      <LogOut size={15} />
                      <span>Logout</span>
                    </button>
                  </div>
                </div>
              )}
            </div>

            <button
              type="button"
              className="soc-logout"
              onClick={handleLogout}
              title="Logout from SOC"
            >
              <LogOut size={16} />
              <span>Logout</span>
            </button>
          </div>
        </header>

        <main className="soc-content">
          <div className="soc-content-inner">
            <Outlet />
          </div>
        </main>

        {/* Global Instant AI Assistant Widget (SOC Analyst & Admin only) */}
        {["ADMIN", "SOC_ANALYST"].includes(role) && <ZukaAssistant />}
      </div>
    </div>
  );
}

export default SocLayout;