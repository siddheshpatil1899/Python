const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export const TENANT_ID = "11111111-1111-1111-1111-111111111111";

export function getToken() {
  return localStorage.getItem("finops_token");
}

export function saveAuth(accessToken, user) {
  localStorage.setItem("finops_token", accessToken);
  localStorage.setItem("finops_user", JSON.stringify(user));
}

export function getSavedUser() {
  const rawUser = localStorage.getItem("finops_user");

  if (!rawUser) {
    return null;
  }

  try {
    return JSON.parse(rawUser);
  } catch {
    localStorage.removeItem("finops_user");
    return null;
  }
}

export function logout() {
  localStorage.removeItem("finops_token");
  localStorage.removeItem("finops_user");
}

function buildCostQuery(startDate = "", endDate = "") {
  const params = new URLSearchParams();

  params.append("tenant_id", TENANT_ID);

  if (startDate) {
    params.append("start_date", startDate);
  }

  if (endDate) {
    params.append("end_date", endDate);
  }

  return params.toString();
}

async function request(path, options = {}) {
  const token = getToken();

  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "API request failed");
  }

  return response.json();
}

export function login(email, password) {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify({
      email,
      password,
    }),
  });
}

export function signup(fullName, email, password, requestedRole) {
  return request("/auth/signup", {
    method: "POST",
    body: JSON.stringify({
      full_name: fullName,
      email,
      password,
      requested_role: requestedRole,
    }),
  });
}

export function forgotPassword(email) {
  return request("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({
      email,
    }),
  });
}

export function resetPassword(token, newPassword) {
  return request("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({
      token,
      new_password: newPassword,
    }),
  });
}

export function getMe() {
  return request("/auth/me");
}

export function getUsers() {
  return request("/settings/users");
}

export function createUser(userData) {
  return request("/settings/users", {
    method: "POST",
    body: JSON.stringify(userData),
  });
}

export function updateUser(userId, userData) {
  return request(`/settings/users/${userId}`, {
    method: "PUT",
    body: JSON.stringify(userData),
  });
}

export function deleteUser(userId) {
  return request(`/settings/users/${userId}`, {
    method: "DELETE",
  });
}

export function getAppSettings() {
  return request(`/settings/app?tenant_id=${TENANT_ID}`);
}

export function saveAppSettings(settings) {
  return request("/settings/app", {
    method: "POST",
    body: JSON.stringify(settings),
  });
}

export function getCostSummary(startDate = "", endDate = "") {
  return request(`/costs/summary?${buildCostQuery(startDate, endDate)}`);
}

export function getProviderBreakdown(startDate = "", endDate = "") {
  return request(
    `/costs/provider-breakdown?${buildCostQuery(startDate, endDate)}`
  );
}

export function getCostByService(startDate = "", endDate = "") {
  return request(`/costs/service-cost?${buildCostQuery(startDate, endDate)}`);
}

export function getDailyCost(startDate = "", endDate = "") {
  return request(`/costs/daily?${buildCostQuery(startDate, endDate)}`);
}

export function getAccountsCost(startDate = "", endDate = "") {
  return request(`/costs/accounts?${buildCostQuery(startDate, endDate)}`);
}

export function getWasteSummary() {
  return request(`/waste/summary?tenant_id=${TENANT_ID}`);
}

export function getWasteFindings() {
  return request(`/waste/findings?tenant_id=${TENANT_ID}&status=active`);
}

export function runWasteScan() {
  return request(`/waste/run-scan?tenant_id=${TENANT_ID}`, {
    method: "POST",
  });
}

export function getAnomalySummary() {
  return request(`/anomalies/summary?tenant_id=${TENANT_ID}`);
}

export function getAnomalyFindings() {
  return request(`/anomalies/findings?tenant_id=${TENANT_ID}&status=active`);
}

export function runAnomalyScan() {
  return request(`/anomalies/run-scan?tenant_id=${TENANT_ID}`, {
    method: "POST",
  });
}

export function getForecastSummary() {
  return request(`/forecast/summary?tenant_id=${TENANT_ID}`);
}

export function getDailyForecast() {
  return request(`/forecast/daily?tenant_id=${TENANT_ID}`);
}

export function runForecast() {
  return request(`/forecast/run?tenant_id=${TENANT_ID}&horizon_days=30`, {
    method: "POST",
  });
}

export function getWarehouseHealth() {
  return request(`/warehouse/health?tenant_id=${TENANT_ID}`);
}

export function getServiceCost() {
  return request(`/warehouse/service-cost?tenant_id=${TENANT_ID}`);
}

export function refreshWarehouse() {
  return request(`/warehouse/refresh?tenant_id=${TENANT_ID}`, {
    method: "POST",
  });
}

export function askChatbot(question) {
  return request("/chat/ask", {
    method: "POST",
    body: JSON.stringify({
      tenant_id: TENANT_ID,
      question,
    }),
  });
}

export function getChatHistory() {
  return request(`/chat/history?tenant_id=${TENANT_ID}`);
}