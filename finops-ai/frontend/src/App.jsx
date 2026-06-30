import { useEffect, useState } from "react";
import seamlessLogo from "./assets/seamless-logo.jpg";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  getAnomalyFindings,
  getAnomalySummary,
  getChatHistory,
  getCostByService,
  getCostSummary,
  getDailyForecast,
  getForecastSummary,
  getProviderBreakdown,
  getServiceCost,
  getWarehouseHealth,
  getWasteFindings,
  getWasteSummary,
  refreshWarehouse,
  runAnomalyScan,
  runForecast,
  runWasteScan,
  askChatbot,
  login,
  signup,
  forgotPassword,
  resetPassword,
  saveAuth,
  getSavedUser,
  logout,
  getUsers,
  createUser,
  updateUser,
  deleteUser,
  getAppSettings,
  saveAppSettings,
} from "./api";

import "./App.css";

function formatCurrency(value) {
  return `$${Number(value || 0).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("en-US");
}

function normalizeProvider(provider) {
  const value = String(provider || "").toLowerCase();

  if (value.includes("aws") || value.includes("amazon")) {
    return "aws";
  }

  if (value.includes("azure") || value.includes("microsoft")) {
    return "azure";
  }

  if (value.includes("gcp") || value.includes("google")) {
    return "gcp";
  }

  return "other";
}

function getUserInitials(user) {
  if (!user?.full_name) {
    return "U";
  }

  return user.full_name
    .split(" ")
    .map((item) => item[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function StatCard({ title, value, subtitle, color = "blue" }) {
  return (
    <div className={`metric-card metric-${color}`}>
      <div className="metric-glow" />
      <p>{title}</p>
      <h2>{value}</h2>
      <span>{subtitle}</span>
    </div>
  );
}

function ProviderCard({ item }) {
  const providerClass = normalizeProvider(item.provider);

  return (
    <div className={`provider-card provider-${providerClass}`}>
      <div>
        <p>{item.provider}</p>
        <h3>{formatCurrency(item.total_cost)}</h3>
      </div>

      <span>
        {formatNumber(item.account_count)} account
        {item.account_count === 1 ? "" : "s"} ·{" "}
        {formatNumber(item.service_count)} services
      </span>
    </div>
  );
}

function App() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [currentUser, setCurrentUser] = useState(getSavedUser());

  const [profileOpen, setProfileOpen] = useState(false);

  const [authMode, setAuthMode] = useState("login");

  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [loginError, setLoginError] = useState("");

  const [signupName, setSignupName] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupPassword, setSignupPassword] = useState("");
  const [signupRole, setSignupRole] = useState("viewer");
  const [signupMessage, setSignupMessage] = useState("");

  const [forgotEmail, setForgotEmail] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");

  const [filterStartDate, setFilterStartDate] = useState("");
  const [filterEndDate, setFilterEndDate] = useState("");

  const [users, setUsers] = useState([]);
  const [appSettings, setAppSettings] = useState(null);

  const [newUser, setNewUser] = useState({
    email: "",
    full_name: "",
    password: "",
    role: "viewer",
    allowed_modules: ["dashboard"],
  });

  const [costSummary, setCostSummary] = useState(null);
  const [providerBreakdown, setProviderBreakdown] = useState([]);
  const [dashboardServiceCost, setDashboardServiceCost] = useState([]);

  const [wasteSummary, setWasteSummary] = useState(null);
  const [wasteFindings, setWasteFindings] = useState([]);

  const [anomalySummary, setAnomalySummary] = useState(null);
  const [anomalyFindings, setAnomalyFindings] = useState([]);

  const [forecastSummary, setForecastSummary] = useState(null);
  const [dailyForecast, setDailyForecast] = useState([]);

  const [warehouseHealth, setWarehouseHealth] = useState(null);
  const [serviceCost, setServiceCost] = useState([]);

  const [chatQuestion, setChatQuestion] = useState("Give me cloud cost overview");
  const [chatAnswer, setChatAnswer] = useState("");
  const [chatHistory, setChatHistory] = useState([]);

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  function hasModuleAccess(moduleName) {
    if (!currentUser) {
      return false;
    }

    if (currentUser.role === "admin") {
      return true;
    }

    const allowedModules = currentUser.allowed_modules || [];
    return allowedModules.includes(moduleName);
  }

  function loadResetTokenFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("reset_token");

    if (token) {
      setResetToken(token);
      setAuthMode("reset");
      setCurrentUser(null);
      logout();
    }
  }

  function buildCsv(rows) {
    return rows
      .map((row) =>
        row
          .map((value) => `"${String(value ?? "").replaceAll('"', '""')}"`)
          .join(",")
      )
      .join("\n");
  }

  function handleExportDashboardCsv() {
    const rows = [
      ["FinOps AI Dashboard Export"],
      ["Start Date", filterStartDate || "All"],
      ["End Date", filterEndDate || "All"],
      [],
      ["KPI", "Value"],
      ["Total Cost", costSummary?.total_cost ?? 0],
      ["Total Accounts", costSummary?.total_accounts ?? 0],
      ["Total Providers", costSummary?.total_providers ?? 0],
      ["Total Services", costSummary?.total_services ?? 0],
      ["Waste Savings", wasteSummary?.total_estimated_monthly_saving ?? 0],
      ["Active Anomalies", anomalySummary?.active_anomalies ?? 0],
      ["Forecasted Cost", forecastSummary?.total_forecasted_cost ?? 0],
      [],
      ["Provider Breakdown"],
      ["Provider", "Total Cost", "Accounts", "Services", "Records"],
      ...providerBreakdown.map((item) => [
        item.provider,
        item.total_cost,
        item.account_count,
        item.service_count,
        item.record_count,
      ]),
      [],
      ["Cost By Service"],
      ["Service", "Provider", "Total Cost", "Accounts", "Records"],
      ...dashboardServiceCost.map((item) => [
        item.service_name,
        item.provider,
        item.total_cost,
        item.account_count,
        item.record_count,
      ]),
    ];

    const csv = buildCsv(rows);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = "finops-dashboard-export.csv";
    link.click();

    URL.revokeObjectURL(url);
  }

  async function handleLogin() {
    setLoginError("");
    setSignupMessage("");
    setMessage("");

    if (!loginEmail || !loginPassword) {
      setLoginError("Please enter email and password.");
      return;
    }

    try {
      const result = await login(loginEmail, loginPassword);

      saveAuth(result.access_token, result.user);
      setCurrentUser(result.user);
      setActiveTab("dashboard");
    } catch (error) {
      setLoginError(`Login failed: ${error.message}`);
    }
  }

  async function handleSignup() {
    setLoginError("");
    setSignupMessage("");
    setMessage("");

    if (!signupName || !signupEmail || !signupPassword) {
      setLoginError("Please enter name, email, and password.");
      return;
    }

    try {
      const result = await signup(
        signupName,
        signupEmail,
        signupPassword,
        signupRole
      );

      setSignupMessage(result.message);
      setAuthMode("login");
      setLoginEmail(signupEmail);
      setLoginPassword("");

      setSignupName("");
      setSignupEmail("");
      setSignupPassword("");
      setSignupRole("viewer");
    } catch (error) {
      setLoginError(`Signup failed: ${error.message}`);
    }
  }

  async function handleForgotPassword() {
    setLoginError("");
    setSignupMessage("");
    setMessage("");

    if (!forgotEmail) {
      setLoginError("Please enter your email.");
      return;
    }

    try {
      const result = await forgotPassword(forgotEmail);

      if (result.dev_reset_link) {
        setSignupMessage(
          `${result.message} Development reset link: ${result.dev_reset_link}`
        );
      } else {
        setSignupMessage(result.message);
      }
    } catch (error) {
      setLoginError(`Forgot password failed: ${error.message}`);
    }
  }

  async function handleResetPassword() {
    setLoginError("");
    setSignupMessage("");
    setMessage("");

    if (!resetToken || !newPassword) {
      setLoginError("Reset token and new password are required.");
      return;
    }

    try {
      const result = await resetPassword(resetToken, newPassword);

      setSignupMessage(result.message);
      setAuthMode("login");
      setLoginPassword("");
      setNewPassword("");
      setResetToken("");

      window.history.replaceState({}, document.title, window.location.pathname);
    } catch (error) {
      setLoginError(`Reset password failed: ${error.message}`);
    }
  }

  function handleLogout() {
    logout();
    setCurrentUser(null);
    setProfileOpen(false);
    setActiveTab("dashboard");
    setMessage("");
    setChatAnswer("");
    setLoginPassword("");
  }

  function handleOpenSettings() {
    setProfileOpen(false);
    setActiveTab("settings");
    loadSettingsData();
  }

  async function loadDashboardData(
    customStartDate = filterStartDate,
    customEndDate = filterEndDate
  ) {
    if (!currentUser) {
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const [
        cost,
        providers,
        serviceRows,
        waste,
        wasteList,
        anomaly,
        anomalyList,
        forecast,
        forecastRows,
        warehouse,
        warehouseServiceRows,
        chats,
      ] = await Promise.all([
        getCostSummary(customStartDate, customEndDate),
        getProviderBreakdown(customStartDate, customEndDate),
        getCostByService(customStartDate, customEndDate),
        getWasteSummary(),
        getWasteFindings(),
        getAnomalySummary(),
        getAnomalyFindings(),
        getForecastSummary(),
        getDailyForecast(),
        getWarehouseHealth(),
        getServiceCost(),
        getChatHistory(),
      ]);

      setCostSummary(cost);
      setProviderBreakdown(providers);
      setDashboardServiceCost(serviceRows);

      setWasteSummary(waste);
      setWasteFindings(wasteList);

      setAnomalySummary(anomaly);
      setAnomalyFindings(anomalyList);

      setForecastSummary(forecast);
      setDailyForecast(forecastRows);

      setWarehouseHealth(warehouse);
      setServiceCost(warehouseServiceRows);

      setChatHistory(chats);
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleApplyDateFilter() {
    await loadDashboardData(filterStartDate, filterEndDate);
  }

  async function handleClearDateFilter() {
    setFilterStartDate("");
    setFilterEndDate("");
    await loadDashboardData("", "");
  }

  async function loadSettingsData() {
    if (!currentUser || currentUser.role !== "admin") {
      return;
    }

    setLoading(true);

    try {
      const [usersResult, settingsResult] = await Promise.all([
        getUsers(),
        getAppSettings(),
      ]);

      setUsers(usersResult);
      setAppSettings(settingsResult);
    } catch (error) {
      setMessage(`Settings load failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateUser() {
    setMessage("");

    if (!newUser.email || !newUser.full_name || !newUser.password) {
      setMessage("Please enter email, full name, and password.");
      return;
    }

    try {
      const result = await createUser(newUser);
      setMessage(result.message);

      setNewUser({
        email: "",
        full_name: "",
        password: "",
        role: "viewer",
        allowed_modules: ["dashboard"],
      });

      await loadSettingsData();
    } catch (error) {
      setMessage(`User creation failed: ${error.message}`);
    }
  }

  async function handleActivateUser(user) {
    setMessage("");

    try {
      const result = await updateUser(user.id, {
        full_name: user.full_name,
        role: user.role === "viewer" ? "analyst" : user.role,
        is_active: true,
        allowed_modules: [
          "dashboard",
          "cost",
          "waste",
          "anomaly",
          "forecast",
          "warehouse",
          "chatbot",
        ],
      });

      setMessage(result.message);
      await loadSettingsData();
    } catch (error) {
      setMessage(`User activation failed: ${error.message}`);
    }
  }

  async function handleDeactivateUser(user) {
    setMessage("");

    if (user.id === currentUser.id) {
      setMessage("You cannot deactivate your own account.");
      return;
    }

    try {
      const result = await updateUser(user.id, {
        full_name: user.full_name,
        role: user.role,
        is_active: false,
        allowed_modules: user.allowed_modules || ["dashboard"],
      });

      setMessage(result.message);
      await loadSettingsData();
    } catch (error) {
      setMessage(`User deactivation failed: ${error.message}`);
    }
  }

  async function handleDeleteUser(user) {
    setMessage("");

    if (user.id === currentUser.id) {
      setMessage("You cannot remove your own admin account.");
      return;
    }

    const confirmed = window.confirm(
      `Are you sure you want to permanently remove ${user.email}?`
    );

    if (!confirmed) {
      return;
    }

    try {
      const result = await deleteUser(user.id);
      setMessage(result.message);
      await loadSettingsData();
    } catch (error) {
      setMessage(`User removal failed: ${error.message}`);
    }
  }

  async function handleSaveAppSettings() {
    setMessage("");

    if (!appSettings) {
      setMessage("Settings are not loaded.");
      return;
    }

    try {
      const result = await saveAppSettings(appSettings);
      setMessage(result.message);
      await loadSettingsData();
    } catch (error) {
      setMessage(`Settings save failed: ${error.message}`);
    }
  }

  async function handleRunWasteScan() {
    setLoading(true);

    try {
      const result = await runWasteScan();
      setMessage(result.message);
      await loadDashboardData();
    } catch (error) {
      setMessage(`Waste scan failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleRunAnomalyScan() {
    setLoading(true);

    try {
      const result = await runAnomalyScan();
      setMessage(result.message);
      await loadDashboardData();
    } catch (error) {
      setMessage(`Anomaly scan failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleRunForecast() {
    setLoading(true);

    try {
      const result = await runForecast();
      setMessage(result.message);
      await loadDashboardData();
    } catch (error) {
      setMessage(`Forecast failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleRefreshWarehouse() {
    setLoading(true);

    try {
      const result = await refreshWarehouse();
      setMessage(result.message);
      await loadDashboardData();
    } catch (error) {
      setMessage(`Warehouse refresh failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleAskChatbot() {
    if (!chatQuestion.trim()) {
      return;
    }

    setLoading(true);

    try {
      const result = await askChatbot(chatQuestion);
      setChatAnswer(result.answer);
      await loadDashboardData();
    } catch (error) {
      setChatAnswer(`Chatbot failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadResetTokenFromUrl();
  }, []);

  useEffect(() => {
    if (currentUser) {
      loadDashboardData();

      if (currentUser.role === "admin") {
        loadSettingsData();
      }
    }
  }, [currentUser]);

  if (!currentUser) {
    return (
      <div className="login-page">
        <div className="login-card">
          <div className="login-logo-wrap">
            <img
              src={seamlessLogo}
              alt="Seamless Infinite Innovations"
              className="login-logo-img"
            />
          </div>

          <h1>
            {authMode === "login" && "Welcome to FinOps AI"}
            {authMode === "signup" && "Request Access"}
            {authMode === "forgot" && "Forgot Password"}
            {authMode === "reset" && "Reset Password"}
          </h1>

          <p>
            {authMode === "login" && "Sign in to manage cloud cost intelligence."}
            {authMode === "signup" &&
              "Create an access request for admin approval."}
            {authMode === "forgot" &&
              "Enter your email to receive a password reset link."}
            {authMode === "reset" && "Enter your new password."}
          </p>

          {loginError && <div className="error-box">{loginError}</div>}
          {signupMessage && <div className="success-box">{signupMessage}</div>}

          {authMode === "signup" && (
            <>
              <label>Full Name</label>
              <input
                value={signupName}
                onChange={(event) => setSignupName(event.target.value)}
                placeholder="Your full name"
              />
            </>
          )}

          {(authMode === "login" || authMode === "signup") && (
            <>
              <label>Email</label>
              <input
                value={authMode === "login" ? loginEmail : signupEmail}
                onChange={(event) =>
                  authMode === "login"
                    ? setLoginEmail(event.target.value)
                    : setSignupEmail(event.target.value)
                }
                placeholder="Enter your email"
              />
            </>
          )}

          {authMode === "forgot" && (
            <>
              <label>Email</label>
              <input
                value={forgotEmail}
                onChange={(event) => setForgotEmail(event.target.value)}
                placeholder="Enter your email"
              />
            </>
          )}

          {(authMode === "login" || authMode === "signup") && (
            <>
              <label>Password</label>
              <div className="password-field">
                <input
                  type={showLoginPassword ? "text" : "password"}
                  value={authMode === "login" ? loginPassword : signupPassword}
                  onChange={(event) =>
                    authMode === "login"
                      ? setLoginPassword(event.target.value)
                      : setSignupPassword(event.target.value)
                  }
                  placeholder="Password"
                />

                <button
                  type="button"
                  className="eye-button"
                  onClick={() => setShowLoginPassword(!showLoginPassword)}
                >
                  {showLoginPassword ? "Hide" : "Show"}
                </button>
              </div>
            </>
          )}

          {authMode === "reset" && (
            <>
              <label>New Password</label>
              <div className="password-field">
                <input
                  type={showLoginPassword ? "text" : "password"}
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  placeholder="New password"
                />

                <button
                  type="button"
                  className="eye-button"
                  onClick={() => setShowLoginPassword(!showLoginPassword)}
                >
                  {showLoginPassword ? "Hide" : "Show"}
                </button>
              </div>
            </>
          )}

          {authMode === "signup" && (
            <>
              <label>Requested Role</label>
              <select
                value={signupRole}
                onChange={(event) => setSignupRole(event.target.value)}
              >
                <option value="viewer">Viewer</option>
                <option value="analyst">Analyst</option>
              </select>
            </>
          )}

          {authMode === "login" && <button onClick={handleLogin}>Login</button>}

          {authMode === "signup" && (
            <button onClick={handleSignup}>Submit Access Request</button>
          )}

          {authMode === "forgot" && (
            <button onClick={handleForgotPassword}>Send Reset Link</button>
          )}

          {authMode === "reset" && (
            <button onClick={handleResetPassword}>Reset Password</button>
          )}

          {authMode === "login" && (
            <>
              <button
                type="button"
                className="link-button"
                onClick={() => {
                  setLoginError("");
                  setSignupMessage("");
                  setAuthMode("signup");
                }}
              >
                New user? Request access
              </button>

              <button
                type="button"
                className="link-button"
                onClick={() => {
                  setLoginError("");
                  setSignupMessage("");
                  setForgotEmail(loginEmail);
                  setAuthMode("forgot");
                }}
              >
                Forgot password?
              </button>
            </>
          )}

          {authMode !== "login" && (
            <button
              type="button"
              className="link-button"
              onClick={() => {
                setLoginError("");
                setSignupMessage("");
                setAuthMode("login");
              }}
            >
              Back to login
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="main-nav">
        <div className="nav-brand">
          <img
            src={seamlessLogo}
            alt="Seamless Infinite Innovations"
            className="brand-logo-img"
          />
        </div>

        <nav className="nav-links">
          {hasModuleAccess("dashboard") && (
            <button
              className={activeTab === "dashboard" ? "active" : ""}
              onClick={() => setActiveTab("dashboard")}
            >
              Dashboard
            </button>
          )}

          {hasModuleAccess("waste") && (
            <button
              className={activeTab === "waste" ? "active" : ""}
              onClick={() => setActiveTab("waste")}
            >
              Waste
            </button>
          )}

          {hasModuleAccess("anomaly") && (
            <button
              className={activeTab === "anomalies" ? "active" : ""}
              onClick={() => setActiveTab("anomalies")}
            >
              Anomalies
            </button>
          )}

          {hasModuleAccess("forecast") && (
            <button
              className={activeTab === "forecast" ? "active" : ""}
              onClick={() => setActiveTab("forecast")}
            >
              Forecast
            </button>
          )}

          {hasModuleAccess("warehouse") && (
            <button
              className={activeTab === "warehouse" ? "active" : ""}
              onClick={() => setActiveTab("warehouse")}
            >
              Warehouse
            </button>
          )}

          {hasModuleAccess("chatbot") && (
            <button
              className={activeTab === "chatbot" ? "active" : ""}
              onClick={() => setActiveTab("chatbot")}
            >
              Chatbot
            </button>
          )}

          {currentUser.role === "admin" && (
            <button
              className={activeTab === "settings" ? "active" : ""}
              onClick={() => {
                setActiveTab("settings");
                loadSettingsData();
              }}
            >
              Settings
            </button>
          )}
        </nav>

        <div className="nav-actions">
          <button
            className="refresh-button"
            onClick={() => loadDashboardData()}
            disabled={loading}
          >
            {loading ? "Loading..." : "Refresh"}
          </button>

          <div className="profile-menu">
            <button
              className="profile-button"
              type="button"
              onClick={() => setProfileOpen(!profileOpen)}
            >
              <span className="profile-avatar">{getUserInitials(currentUser)}</span>
              <span className="profile-text">
                <strong>{currentUser.full_name}</strong>
                <small>{currentUser.role}</small>
              </span>
              <span className="profile-caret">▾</span>
            </button>

            {profileOpen && (
              <div className="profile-dropdown">
                <div className="profile-dropdown-header">
                  <div className="profile-avatar large">
                    {getUserInitials(currentUser)}
                  </div>

                  <div>
                    <strong>{currentUser.full_name}</strong>
                    <span>{currentUser.email}</span>
                    <small>{currentUser.role}</small>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setProfileOpen(false);
                    setActiveTab("dashboard");
                  }}
                >
                  Dashboard
                </button>

                {currentUser.role === "admin" && (
                  <button type="button" onClick={handleOpenSettings}>
                    User & Access Settings
                  </button>
                )}

                <button
                  type="button"
                  onClick={() => {
                    setProfileOpen(false);
                    setAuthMode("login");
                    handleLogout();
                  }}
                >
                  Switch Account
                </button>

                <button
                  type="button"
                  className="dropdown-danger"
                  onClick={handleLogout}
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="main-content">
        <div className="page-title-row compact">
          <div>
            <p className="eyebrow">Executive cloud cost overview</p>
            <h1>FinOps Dashboard</h1>
            <p>
              Monitor cloud spend, account usage, provider split, service cost,
              waste, anomalies, and forecasts.
            </p>
          </div>
        </div>

        {message && <div className="message">{message}</div>}

        {activeTab === "dashboard" && hasModuleAccess("dashboard") && (
          <section>
            <div className="dashboard-toolbar">
              <div className="filter-group">
                <label>
                  Start date
                  <input
                    type="date"
                    value={filterStartDate}
                    onChange={(event) => setFilterStartDate(event.target.value)}
                  />
                </label>

                <label>
                  End date
                  <input
                    type="date"
                    value={filterEndDate}
                    onChange={(event) => setFilterEndDate(event.target.value)}
                  />
                </label>
              </div>

              <div className="toolbar-actions">
                <button onClick={handleApplyDateFilter} disabled={loading}>
                  Apply Filter
                </button>

                <button
                  className="secondary-button"
                  onClick={handleClearDateFilter}
                  disabled={loading}
                >
                  Clear
                </button>

                <button className="export-button" onClick={handleExportDashboardCsv}>
                  Export CSV
                </button>
              </div>
            </div>

            <div className="metric-grid">
              <StatCard
                title="Total Cost"
                value={formatCurrency(costSummary?.total_cost)}
                subtitle={`${formatNumber(costSummary?.record_count)} cost records`}
                color="blue"
              />

              <StatCard
                title="Total Accounts"
                value={formatNumber(costSummary?.total_accounts)}
                subtitle={`${formatNumber(costSummary?.total_services)} services tracked`}
                color="cyan"
              />

              <StatCard
                title="Waste Savings"
                value={formatCurrency(wasteSummary?.total_estimated_monthly_saving)}
                subtitle={`${formatNumber(wasteSummary?.active_findings)} active findings`}
                color="green"
              />

              <StatCard
                title="Anomaly Delta"
                value={formatCurrency(anomalySummary?.active_delta_cost)}
                subtitle={`${formatNumber(anomalySummary?.active_anomalies)} active anomalies`}
                color="red"
              />

              <StatCard
                title="Forecast"
                value={formatCurrency(forecastSummary?.total_forecasted_cost)}
                subtitle={forecastSummary?.budget_status ?? "Run forecast"}
                color="purple"
              />
            </div>

            <div className="dashboard-grid">
              <div className="panel provider-panel">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">Provider breakdown</p>
                    <h2>AWS / Azure / GCP cost split</h2>
                  </div>
                </div>

                <div className="provider-grid">
                  {providerBreakdown.length === 0 && (
                    <div className="empty-state">No provider data found.</div>
                  )}

                  {providerBreakdown.map((item) => (
                    <ProviderCard key={item.provider} item={item} />
                  ))}
                </div>

                <div className="chart compact-chart">
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={providerBreakdown}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="provider" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="total_cost" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="panel service-panel">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">Service cost</p>
                    <h2>Top cloud services by spend</h2>
                  </div>
                </div>

                <div className="chart">
                  <ResponsiveContainer width="100%" height={340}>
                    <BarChart data={dashboardServiceCost.slice(0, 12)}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="service_name" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="total_cost" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">Detailed cost table</p>
                  <h2>Cost by service</h2>
                </div>
              </div>

              <table>
                <thead>
                  <tr>
                    <th>Service</th>
                    <th>Provider</th>
                    <th>Total Cost</th>
                    <th>Accounts</th>
                    <th>Records</th>
                  </tr>
                </thead>

                <tbody>
                  {dashboardServiceCost.map((item) => (
                    <tr key={`${item.provider}-${item.service_name}`}>
                      <td>{item.service_name}</td>
                      <td>{item.provider}</td>
                      <td>{formatCurrency(item.total_cost)}</td>
                      <td>{formatNumber(item.account_count)}</td>
                      <td>{formatNumber(item.record_count)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === "waste" && hasModuleAccess("waste") && (
          <section>
            <div className="section-header">
              <h2>Waste Detection</h2>
              <button onClick={handleRunWasteScan} disabled={loading}>
                Run Waste Scan
              </button>
            </div>

            <div className="metric-grid four">
              <StatCard title="Active" value={formatNumber(wasteSummary?.active_findings)} subtitle="waste findings" color="green" />
              <StatCard title="Dismissed" value={formatNumber(wasteSummary?.dismissed_findings)} subtitle="dismissed findings" color="blue" />
              <StatCard title="Resolved" value={formatNumber(wasteSummary?.resolved_findings)} subtitle="resolved findings" color="purple" />
              <StatCard title="Savings" value={formatCurrency(wasteSummary?.total_estimated_monthly_saving)} subtitle="monthly estimate" color="cyan" />
            </div>

            <div className="panel">
              <h3>Active Waste Findings</h3>
              <table>
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Service</th>
                    <th>Severity</th>
                    <th>Saving</th>
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {wasteFindings.map((item) => (
                    <tr key={item.id}>
                      <td>{item.title}</td>
                      <td>{item.service_name}</td>
                      <td>{item.severity}</td>
                      <td>{formatCurrency(item.estimated_monthly_saving)}</td>
                      <td>{item.confidence_score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === "anomalies" && hasModuleAccess("anomaly") && (
          <section>
            <div className="section-header">
              <h2>Anomaly Detection</h2>
              <button onClick={handleRunAnomalyScan} disabled={loading}>
                Run Anomaly Scan
              </button>
            </div>

            <div className="metric-grid four">
              <StatCard title="Active" value={formatNumber(anomalySummary?.active_anomalies)} subtitle="cost anomalies" color="red" />
              <StatCard title="Dismissed" value={formatNumber(anomalySummary?.dismissed_anomalies)} subtitle="dismissed anomalies" color="blue" />
              <StatCard title="Resolved" value={formatNumber(anomalySummary?.resolved_anomalies)} subtitle="resolved anomalies" color="green" />
              <StatCard title="Delta Cost" value={formatCurrency(anomalySummary?.active_delta_cost)} subtitle="active impact" color="purple" />
            </div>

            <div className="panel">
              <h3>Active Anomalies</h3>
              <table>
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Date</th>
                    <th>Level</th>
                    <th>Severity</th>
                    <th>Delta</th>
                  </tr>
                </thead>
                <tbody>
                  {anomalyFindings.map((item) => (
                    <tr key={item.id}>
                      <td>{item.title}</td>
                      <td>{item.anomaly_date}</td>
                      <td>{item.level}</td>
                      <td>{item.severity}</td>
                      <td>{formatCurrency(item.delta_cost)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === "forecast" && hasModuleAccess("forecast") && (
          <section>
            <div className="section-header">
              <h2>Cost Forecasting</h2>
              <button onClick={handleRunForecast} disabled={loading}>
                Run Forecast
              </button>
            </div>

            <div className="metric-grid four">
              <StatCard title="Forecasted Cost" value={formatCurrency(forecastSummary?.total_forecasted_cost)} subtitle="next period" color="purple" />
              <StatCard title="Daily Average" value={formatCurrency(forecastSummary?.average_daily_forecast)} subtitle="average forecast" color="blue" />
              <StatCard title="Budget Status" value={forecastSummary?.budget_status ?? "NA"} subtitle="budget comparison" color="red" />
              <StatCard title="Confidence" value={forecastSummary?.confidence_score ?? "NA"} subtitle="model confidence" color="green" />
            </div>

            <div className="panel">
              <h3>Daily Forecast</h3>
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Predicted</th>
                    <th>Lower Bound</th>
                    <th>Upper Bound</th>
                  </tr>
                </thead>
                <tbody>
                  {dailyForecast.map((item) => (
                    <tr key={item.id}>
                      <td>{item.forecast_date}</td>
                      <td>{formatCurrency(item.predicted_cost)}</td>
                      <td>{formatCurrency(item.lower_bound)}</td>
                      <td>{formatCurrency(item.upper_bound)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === "warehouse" && hasModuleAccess("warehouse") && (
          <section>
            <div className="section-header">
              <h2>Warehouse</h2>
              <button onClick={handleRefreshWarehouse} disabled={loading}>
                Refresh Warehouse
              </button>
            </div>

            <div className="metric-grid four">
              <StatCard title="Warehouse Ready" value={warehouseHealth?.warehouse_ready ? "Yes" : "No"} subtitle="aggregate status" color="green" />
              <StatCard title="Source Records" value={formatNumber(warehouseHealth?.source_record_count)} subtitle="raw cost rows" color="blue" />
              <StatCard title="Aggregates" value={formatNumber(warehouseHealth?.aggregate_record_count)} subtitle="summary rows" color="purple" />
              <StatCard title="Last Status" value={warehouseHealth?.latest_refresh?.status ?? "NA"} subtitle="refresh status" color="cyan" />
            </div>

            <div className="panel">
              <h3>Service Cost Aggregates</h3>
              <table>
                <thead>
                  <tr>
                    <th>Service</th>
                    <th>Provider</th>
                    <th>Total Cost</th>
                    <th>Records</th>
                  </tr>
                </thead>
                <tbody>
                  {serviceCost.map((item) => (
                    <tr key={`${item.service_name}-${item.cloud_provider}`}>
                      <td>{item.service_name}</td>
                      <td>{item.cloud_provider}</td>
                      <td>{formatCurrency(item.total_cost)}</td>
                      <td>{formatNumber(item.record_count)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === "chatbot" && hasModuleAccess("chatbot") && (
          <section>
            <div className="section-header">
              <h2>Natural Language Chatbot</h2>
            </div>

            <div className="panel">
              <textarea
                value={chatQuestion}
                onChange={(event) => setChatQuestion(event.target.value)}
                rows="3"
                placeholder="Ask something about cloud cost..."
              />

              <button onClick={handleAskChatbot} disabled={loading}>
                Ask
              </button>

              {chatAnswer && (
                <div className="answer">
                  <h3>Answer</h3>
                  <p>{chatAnswer}</p>
                </div>
              )}
            </div>

            <div className="panel">
              <h3>Chat History</h3>
              <table>
                <thead>
                  <tr>
                    <th>Question</th>
                    <th>Intent</th>
                    <th>Answer</th>
                  </tr>
                </thead>
                <tbody>
                  {chatHistory.map((item) => (
                    <tr key={item.id}>
                      <td>{item.question}</td>
                      <td>{item.intent}</td>
                      <td>{item.answer}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === "settings" && currentUser.role === "admin" && (
          <section>
            <div className="section-header">
              <h2>Settings</h2>
              <button onClick={loadSettingsData}>Reload Settings</button>
            </div>

            <div className="settings-grid">
              <div className="panel">
                <h3>Data Fetch Settings</h3>

                {!appSettings && (
                  <p className="muted">Click Reload Settings to load settings.</p>
                )}

                {appSettings && (
                  <>
                    <label>Fetch Mode</label>
                    <select
                      value={appSettings.data_fetch_mode}
                      onChange={(event) =>
                        setAppSettings({
                          ...appSettings,
                          data_fetch_mode: event.target.value,
                        })
                      }
                    >
                      <option value="manual">Manual</option>
                      <option value="scheduled">Scheduled</option>
                    </select>

                    <label>Fetch Frequency</label>
                    <select
                      value={appSettings.fetch_frequency}
                      onChange={(event) =>
                        setAppSettings({
                          ...appSettings,
                          fetch_frequency: event.target.value,
                        })
                      }
                    >
                      <option value="hourly">Hourly</option>
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                    </select>

                    <label>Fetch Time</label>
                    <input
                      value={appSettings.fetch_time}
                      onChange={(event) =>
                        setAppSettings({
                          ...appSettings,
                          fetch_time: event.target.value,
                        })
                      }
                      placeholder="02:00"
                    />

                    <label>Enabled Modules comma separated</label>
                    <input
                      value={(appSettings.enabled_modules || []).join(",")}
                      onChange={(event) =>
                        setAppSettings({
                          ...appSettings,
                          enabled_modules: event.target.value
                            .split(",")
                            .map((item) => item.trim())
                            .filter(Boolean),
                        })
                      }
                      placeholder="cost,waste,anomaly,forecast,warehouse"
                    />

                    <label>Notify Emails comma separated</label>
                    <input
                      value={(appSettings.notify_emails || []).join(",")}
                      onChange={(event) =>
                        setAppSettings({
                          ...appSettings,
                          notify_emails: event.target.value
                            .split(",")
                            .map((item) => item.trim())
                            .filter(Boolean),
                        })
                      }
                    />

                    <button onClick={handleSaveAppSettings}>Save Settings</button>
                  </>
                )}
              </div>

              <div className="panel">
                <h3>Create User</h3>

                <label>Email</label>
                <input
                  value={newUser.email}
                  onChange={(event) =>
                    setNewUser({ ...newUser, email: event.target.value })
                  }
                  placeholder="user@example.com"
                />

                <label>Full Name</label>
                <input
                  value={newUser.full_name}
                  onChange={(event) =>
                    setNewUser({ ...newUser, full_name: event.target.value })
                  }
                  placeholder="User Name"
                />

                <label>Password</label>
                <input
                  type="password"
                  value={newUser.password}
                  onChange={(event) =>
                    setNewUser({ ...newUser, password: event.target.value })
                  }
                  placeholder="Password"
                />

                <label>Role</label>
                <select
                  value={newUser.role}
                  onChange={(event) =>
                    setNewUser({ ...newUser, role: event.target.value })
                  }
                >
                  <option value="admin">Admin</option>
                  <option value="analyst">Analyst</option>
                  <option value="viewer">Viewer</option>
                </select>

                <label>Allowed Modules comma separated</label>
                <input
                  value={newUser.allowed_modules.join(",")}
                  onChange={(event) =>
                    setNewUser({
                      ...newUser,
                      allowed_modules: event.target.value
                        .split(",")
                        .map((item) => item.trim())
                        .filter(Boolean),
                    })
                  }
                  placeholder="dashboard,waste,anomaly,forecast"
                />

                <button onClick={handleCreateUser}>Create User</button>
              </div>
            </div>

            <div className="panel">
              <h3>Users / Access Requests</h3>

              <table>
                <thead>
                  <tr>
                    <th>Email</th>
                    <th>Name</th>
                    <th>Role</th>
                    <th>Active</th>
                    <th>Allowed Modules</th>
                    <th>Action</th>
                  </tr>
                </thead>

                <tbody>
                  {users.map((user) => (
                    <tr key={user.id}>
                      <td>{user.email}</td>
                      <td>{user.full_name}</td>
                      <td>{user.role}</td>
                      <td>{user.is_active ? "Yes" : "No"}</td>
                      <td>{(user.allowed_modules || []).join(", ")}</td>
                      <td>
                        <div className="user-action-buttons">
                          {!user.is_active ? (
                            <button onClick={() => handleActivateUser(user)}>
                              Activate
                            </button>
                          ) : user.id === currentUser.id ? (
                            <span className="muted">Current Admin</span>
                          ) : (
                            <button
                              className="secondary-button"
                              onClick={() => handleDeactivateUser(user)}
                            >
                              Deactivate
                            </button>
                          )}

                          {user.id !== currentUser.id && (
                            <button
                              className="danger-button"
                              onClick={() => handleDeleteUser(user)}
                            >
                              Remove
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;