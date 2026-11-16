import { scheduleLoad } from "../../utils/scheduleLoad";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { formatShortDateTime } from "../../utils/datetime";

import {
  AlertTriangle,
  Eye,
  EyeOff,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
  UserCheck,
  UserX,
  X,
} from "lucide-react";

import "./Users.css";
import PasswordRequirements from "../../components/auth/PasswordRequirements";
import { evaluatePassword } from "../../utils/password";

import { API_BASE_URL } from "../../services/config";

interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
  last_login_ip: string | null;
}

interface CreateUserForm {
  username: string;
  email: string;
  password: string;
  role: "VIEWER" | "SOC_ANALYST";
}

function Users() {
  const [users, setUsers] = useState<User[]>([]);

  const [search, setSearch] = useState("");

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");

  const [showCreate, setShowCreate] = useState(false);

  const [creating, setCreating] = useState(false);

  const [createError, setCreateError] = useState("");

  const [createSuccess, setCreateSuccess] = useState("");

  const [showCreatePassword, setShowCreatePassword] = useState(false);

  const [userToDelete, setUserToDelete] = useState<User | null>(null);

  const [deleting, setDeleting] = useState(false);

  const [deleteError, setDeleteError] = useState("");

  const [updatingUserId, setUpdatingUserId] = useState<number | null>(null);

  const [currentUserId] = useState<number | null>(() => {
    try {
      const user = JSON.parse(localStorage.getItem("zuka_user") || "null");
      return typeof user?.id === "number" ? user.id : null;
    } catch {
      return null;
    }
  });

  const [form, setForm] = useState<CreateUserForm>({
    username: "",
    email: "",
    password: "",
    role: "SOC_ANALYST",
  });

  /*
   * Get the currently logged-in user.
   */

  /*
   * Load users from the ADMIN API.
   */
  async function loadUsers() {
    const token = localStorage.getItem("zuka_access_token");

    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/users`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to load users.");
      }

      setUsers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load users.");
    } finally {
      setLoading(false);
    }
  }

  /*
   * Load users when the page opens.
   */
  useEffect(() => {
    return scheduleLoad(loadUsers);
  }, []);

  /*
   * Update create-user form.
   */
  function updateForm(field: keyof CreateUserForm, value: string) {
    setForm((previous) => ({
      ...previous,
      [field]: value,
    }));
  }

  /*
   * Open Create User modal.
   */
  function openCreateModal() {
    setCreateError("");
    setCreateSuccess("");
    setShowCreatePassword(false);

    setForm({
      username: "",
      email: "",
      password: "",
      role: "SOC_ANALYST",
    });

    setShowCreate(true);
  }

  /*
   * Close Create User modal.
   */
  function closeCreateModal() {
    if (!creating) {
      setShowCreate(false);
    }
  }

  /*
   * Create a new user.
   */
  async function handleCreateUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setCreating(true);
    setCreateError("");
    setCreateSuccess("");

    const pwdCheck = evaluatePassword(form.password);
    if (!pwdCheck.isValid) {
      setCreateError(
        pwdCheck.firstError ||
          "Password must meet enterprise complexity conditions (e.g. first letter capital, minimum 8 characters, number, symbol).",
      );
      setCreating(false);
      return;
    }

    const token = localStorage.getItem("zuka_access_token");

    if (!token) {
      setCreateError("Authentication token is missing.");
      setCreating(false);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/users`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(form),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to create user.");
      }

      setCreateSuccess(`User "${data.username}" created successfully.`);

      setForm({
        username: "",
        email: "",
        password: "",
        role: "SOC_ANALYST",
      });

      await loadUsers();

      window.setTimeout(() => {
        setShowCreate(false);
        setCreateSuccess("");
      }, 2000);
    } catch (err) {
      setCreateError(
        err instanceof Error ? err.message : "Unable to create user.",
      );
    } finally {
      setCreating(false);
    }
  }

  /*
   * Change a user's role.
   */
  async function changeUserRole(userId: number, role: string) {
    setError("");
    setUpdatingUserId(userId);

    const token = localStorage.getItem("zuka_access_token");

    if (!token) {
      setError("Authentication token is missing.");
      setUpdatingUserId(null);
      return;
    }

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/admin/users/${userId}/role`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            role,
          }),
        },
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to change user role.");
      }

      await loadUsers();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to change user role.",
      );
    } finally {
      setUpdatingUserId(null);
    }
  }

  /*
   * Activate or deactivate a user.
   */
  async function changeUserStatus(userId: number, isActive: boolean) {
    setError("");
    setUpdatingUserId(userId);

    const token = localStorage.getItem("zuka_access_token");

    if (!token) {
      setError("Authentication token is missing.");
      setUpdatingUserId(null);
      return;
    }

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/admin/users/${userId}/status`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            is_active: isActive,
          }),
        },
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to change user status.");
      }

      await loadUsers();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to change user status.",
      );
    } finally {
      setUpdatingUserId(null);
    }
  }

  /*
   * Open in-website Delete User confirmation modal.
   */
  function openDeleteModal(user: User) {
    setDeleteError("");
    setUserToDelete(user);
  }

  /*
   * Close Delete User confirmation modal.
   */
  function closeDeleteModal() {
    if (!deleting) {
      setUserToDelete(null);
      setDeleteError("");
    }
  }

  /*
   * Confirm and execute user deletion from the in-website modal.
   */
  async function handleConfirmDelete() {
    if (!userToDelete || deleting) {
      return;
    }

    setDeleting(true);
    setDeleteError("");

    const token = localStorage.getItem("zuka_access_token");

    if (!token) {
      setDeleteError("Authentication token is missing.");
      setDeleting(false);
      return;
    }

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/admin/users/${userToDelete.id}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: "application/json",
          },
        },
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to delete user.");
      }

      setUserToDelete(null);
      await loadUsers();
    } catch (err) {
      setDeleteError(
        err instanceof Error ? err.message : "Unable to delete user.",
      );
    } finally {
      setDeleting(false);
    }
  }

  /*
   * Search users.
   */
  const filteredUsers = users.filter((user) => {
    const query = search.toLowerCase().trim();

    if (!query) {
      return true;
    }

    return (
      user.username.toLowerCase().includes(query) ||
      user.email.toLowerCase().includes(query) ||
      user.role.toLowerCase().includes(query)
    );
  });

  /*
   * Format user date/time in IST.
   *
   * Backend timestamps are UTC. The shared ZUKA
   * datetime utility converts them to Asia/Kolkata.
   */
  function formatUserDateTime(value: string | null) {
    if (!value) {
      return "Never";
    }

    const formatted = formatShortDateTime(value);

    return formatted === "—" ? "Unknown" : formatted;
  }

  /*
   * Count users by role.
   */
  const adminCount = users.filter((user) => user.role === "ADMIN").length;

  const analystCount = users.filter(
    (user) => user.role === "SOC_ANALYST",
  ).length;

  const viewerCount = users.filter((user) => user.role === "VIEWER").length;

  const activeCount = users.filter((user) => user.is_active).length;

  return (
    <div className="users-page">
      {/* PAGE HEADER */}
      <div className="users-heading">
        <div>
          <div className="users-eyebrow">ADMINISTRATION / ACCESS CONTROL</div>

          <h1>User Management</h1>

          <p>Manage ZUKA SOC accounts, roles, and access status.</p>
        </div>

        <button
          type="button"
          className="users-create-button"
          onClick={openCreateModal}
        >
          <Plus size={17} />
          Create User
        </button>
      </div>

      {/* SEARCH + REFRESH */}
      <div className="users-toolbar">
        <div className="users-search">
          <Search size={16} />

          <input
            type="text"
            placeholder="Search username, email, or role..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        <button
          type="button"
          className="users-refresh"
          onClick={loadUsers}
          disabled={loading}
          title="Refresh users"
        >
          <RefreshCw size={16} className={loading ? "users-spin" : ""} />
        </button>
      </div>

      {/* ERROR */}
      {error && <div className="users-error">{error}</div>}

      {/* SUMMARY */}
      <div className="users-summary">
        <div>
          <span>Total Users</span>
          <strong>{users.length}</strong>
        </div>

        <div>
          <span>Active Users</span>
          <strong>{activeCount}</strong>
        </div>

        <div>
          <span>SOC Analysts</span>
          <strong>{analystCount}</strong>
        </div>

        <div>
          <span>Viewers</span>
          <strong>{viewerCount}</strong>
        </div>
      </div>

      {/* USERS TABLE */}
      <section className="users-panel">
        <div className="users-panel-header">
          <div>
            <span>IDENTITY & ACCESS</span>

            <h2>Registered Users</h2>
          </div>

          <ShieldCheck size={20} />
        </div>

        {loading ? (
          <div className="users-empty">Loading users...</div>
        ) : filteredUsers.length === 0 ? (
          <div className="users-empty">No users found.</div>
        ) : (
          <div className="users-table-wrapper">
            <table className="users-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Last Login</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {filteredUsers.map((user) => {
                  const isCurrentUser = user.id === currentUserId;

                  const isUpdating = updatingUserId === user.id;

                  return (
                    <tr key={user.id}>
                      {/* USER */}
                      <td>
                        <div className="users-user-cell">
                          <div className="users-avatar">
                            {user.username.charAt(0).toUpperCase()}
                          </div>

                          <div>
                            <strong>{user.username}</strong>

                            <span>
                              ID #{user.id}
                              {isCurrentUser ? " • YOU" : ""}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* EMAIL */}
                      <td>{user.email}</td>

                      {/* ROLE */}
                      <td>
                        <select
                          className="users-role-select"
                          value={user.role}
                          disabled={isUpdating || isCurrentUser}
                          title={
                            isCurrentUser
                              ? "You cannot change your own ADMIN role."
                              : "Change user role"
                          }
                          onChange={(event) =>
                            changeUserRole(user.id, event.target.value)
                          }
                        >
                          <option value="VIEWER">VIEWER</option>

                          <option value="SOC_ANALYST">SOC_ANALYST</option>

                          <option value="ADMIN">ADMIN</option>
                        </select>
                      </td>

                      {/* STATUS */}
                      <td>
                        <button
                          type="button"
                          className={`users-status-button ${
                            user.is_active ? "active" : "inactive"
                          }`}
                          disabled={isUpdating || isCurrentUser}
                          title={
                            isCurrentUser
                              ? "You cannot deactivate your own account."
                              : user.is_active
                                ? "Click to deactivate user immediately"
                                : "Click to activate user immediately"
                          }
                          onClick={() =>
                            changeUserStatus(user.id, !user.is_active)
                          }
                        >
                          {user.is_active ? (
                            <>
                              <UserCheck size={13} />
                              Active
                            </>
                          ) : (
                            <>
                              <UserX size={13} />
                              Inactive
                            </>
                          )}
                        </button>
                      </td>

                      {/* CREATED */}
                      <td>{formatUserDateTime(user.created_at)}</td>

                      {/* LAST LOGIN */}
                      <td>{formatUserDateTime(user.last_login_at)}</td>

                      {/* ACTIONS: IN-WEBSITE MODAL CONFIRMATION DELETE */}
                      <td>
                        {!isCurrentUser ? (
                          <button
                            type="button"
                            className="users-delete-button"
                            disabled={isUpdating}
                            title={`Delete user account ${user.username}`}
                            onClick={() => openDeleteModal(user)}
                          >
                            <Trash2 size={13} />
                            Delete
                          </button>
                        ) : (
                          <span
                            className="users-action-locked"
                            title="You cannot delete your own account"
                          >
                            —
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ROLE STATISTICS */}
      <div className="users-role-statistics">
        <div>
          <span>ADMINISTRATORS</span>
          <strong>{adminCount}</strong>
        </div>

        <div>
          <span>SOC ANALYSTS</span>
          <strong>{analystCount}</strong>
        </div>

        <div>
          <span>VIEWERS</span>
          <strong>{viewerCount}</strong>
        </div>
      </div>

      {/* CREATE USER MODAL */}
      {showCreate && (
        <div className="users-modal-backdrop" onMouseDown={closeCreateModal}>
          <div
            className="users-modal"
            onMouseDown={(event) => event.stopPropagation()}
          >
            {/* MODAL HEADER */}
            <div className="users-modal-header">
              <div>
                <span>ADMINISTRATION</span>

                <h2>Create User</h2>
              </div>

              <button
                type="button"
                className="users-modal-close"
                onClick={closeCreateModal}
                disabled={creating}
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>

            {/* FORM */}
            <form className="users-form" onSubmit={handleCreateUser}>
              <label>
                Username
                <input
                  type="text"
                  required
                  minLength={3}
                  maxLength={50}
                  autoComplete="username"
                  value={form.username}
                  onChange={(event) =>
                    updateForm("username", event.target.value)
                  }
                  placeholder="Enter username"
                />
              </label>

              <label>
                Email
                <input
                  type="email"
                  required
                  autoComplete="email"
                  value={form.email}
                  onChange={(event) => updateForm("email", event.target.value)}
                  placeholder="user@example.com"
                />
              </label>

              <label>
                Password
                <div className="users-password-wrapper">
                  <input
                    type={showCreatePassword ? "text" : "password"}
                    required
                    minLength={8}
                    maxLength={128}
                    autoComplete="new-password"
                    value={form.password}
                    onChange={(event) =>
                      updateForm("password", event.target.value)
                    }
                    placeholder="e.g. SecOps@2026!"
                  />
                  <button
                    type="button"
                    className="users-password-toggle-btn"
                    onClick={() => setShowCreatePassword(!showCreatePassword)}
                    aria-label={
                      showCreatePassword ? "Hide password" : "Show password"
                    }
                    title={
                      showCreatePassword ? "Hide password" : "Show password"
                    }
                    tabIndex={-1}
                  >
                    {showCreatePassword ? (
                      <EyeOff size={16} />
                    ) : (
                      <Eye size={16} />
                    )}
                  </button>
                </div>
                <PasswordRequirements password={form.password} />
              </label>

              <label>
                Role
                <select
                  value={form.role}
                  onChange={(event) =>
                    updateForm(
                      "role",
                      event.target.value as "VIEWER" | "SOC_ANALYST",
                    )
                  }
                >
                  <option value="SOC_ANALYST">SOC_ANALYST</option>

                  <option value="VIEWER">VIEWER</option>
                </select>
              </label>

              {/* FORM ERROR */}
              {createError && (
                <div className="users-form-error">{createError}</div>
              )}

              {/* FORM SUCCESS */}
              {createSuccess && (
                <div className="users-form-success">{createSuccess}</div>
              )}

              {/* SUBMIT */}
              <button
                type="submit"
                className="users-submit-button"
                disabled={creating}
              >
                {creating ? "Creating..." : "Create User"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* IN-WEBSITE USER DELETE CONFIRMATION MODAL */}
      {userToDelete && (
        <div className="users-modal-backdrop" onMouseDown={closeDeleteModal}>
          <div
            className="users-modal users-delete-modal"
            onMouseDown={(event) => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-dialog-title"
          >
            {/* MODAL HEADER */}
            <div className="users-modal-header users-delete-modal-header">
              <div className="users-delete-header-content">
                <div className="users-delete-icon-badge">
                  <AlertTriangle size={20} />
                </div>
                <div>
                  <span className="users-delete-eyebrow">
                    DANGER ZONE / PERMANENT ACTION
                  </span>
                  <h2 id="delete-dialog-title">Delete User Account</h2>
                </div>
              </div>

              <button
                type="button"
                className="users-modal-close"
                onClick={closeDeleteModal}
                disabled={deleting}
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>

            {/* MODAL BODY */}
            <div className="users-delete-modal-body">
              <p className="users-delete-notice-text">
                Are you sure you want to permanently delete this user account
                from the ZUKA SOC platform?
              </p>

              {/* USER DETAILS BOX */}
              <div className="users-delete-user-card">
                <div className="users-delete-card-avatar">
                  {userToDelete.username.charAt(0).toUpperCase()}
                </div>
                <div className="users-delete-card-details">
                  <div className="users-delete-card-top">
                    <strong>{userToDelete.username}</strong>
                    <span className="users-delete-card-id">
                      ID #{userToDelete.id}
                    </span>
                  </div>
                  <div className="users-delete-card-email">
                    {userToDelete.email}
                  </div>
                  <div className="users-delete-card-tags">
                    <span className="users-delete-tag role-tag">
                      Role: {userToDelete.role}
                    </span>
                    <span
                      className={`users-delete-tag status-tag ${userToDelete.is_active ? "active" : "inactive"}`}
                    >
                      Status: {userToDelete.is_active ? "Active" : "Inactive"}
                    </span>
                  </div>
                </div>
              </div>

              {/* SECURITY MATTER & IMPACT */}
              <div className="users-delete-matter-box">
                <h4>Permanent Deletion Impact</h4>
                <ul>
                  <li>
                    <strong>Immediate Access Revocation:</strong> The user will
                    be immediately logged out and blocked from logging in.
                  </li>
                  <li>
                    <strong>Credential Purge:</strong> Account credentials and
                    authorization tokens will be permanently removed.
                  </li>
                  <li>
                    <strong>Audit Trail Retention:</strong> Historical audit log
                    entries generated by this user will be preserved for
                    security compliance.
                  </li>
                </ul>
              </div>

              {deleteError && (
                <div className="users-form-error" style={{ marginTop: 14 }}>
                  {deleteError}
                </div>
              )}

              {/* ACTIONS */}
              <div className="users-delete-actions">
                <button
                  type="button"
                  className="users-delete-cancel-button"
                  onClick={closeDeleteModal}
                  disabled={deleting}
                >
                  Cancel
                </button>

                <button
                  type="button"
                  className="users-delete-confirm-button"
                  onClick={handleConfirmDelete}
                  disabled={deleting}
                >
                  <Trash2 size={15} />
                  {deleting
                    ? "Deleting Account..."
                    : "Yes, Delete User Permanently"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Users;
