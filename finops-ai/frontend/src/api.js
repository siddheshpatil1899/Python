const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export const TENANT_ID = "11111111-1111-1111-1111-111111111111";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
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

export function getCostSummary() {
  return request(`/costs/summary?tenant_id=${TENANT_ID}`);
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