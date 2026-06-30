import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  getAnomalyFindings,
  getAnomalySummary,
  getChatHistory,
  getCostSummary,
  getDailyForecast,
  getForecastSummary,
  getServiceCost,
  getWarehouseHealth,
  getWasteFindings,
  getWasteSummary,
  refreshWarehouse,
  runAnomalyScan,
  runForecast,
  runWasteScan,
  askChatbot,
} from "./api";
import "./App.css";

function StatCard({ title, value, subtitle, color = "default" }) {
  return (
    <div className={`stat-card stat-${color}`}>
      <p className="muted">{title}</p>
      <h2>{value}</h2>
      <span>{subtitle}</span>
    </div>
  );
}

function App() {
  const [activeTab, setActiveTab] = useState("dashboard");

  const [costSummary, setCostSummary] = useState(null);
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

  async function loadDashboardData() {
    setLoading(true);
    setMessage("");

    try {
      const [
        cost,
        waste,
        wasteList,
        anomaly,
        anomalyList,
        forecast,
        forecastRows,
        warehouse,
        serviceRows,
        chats,
      ] = await Promise.all([
        getCostSummary(),
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
      setWasteSummary(waste);
      setWasteFindings(wasteList);
      setAnomalySummary(anomaly);
      setAnomalyFindings(anomalyList);
      setForecastSummary(forecast);
      setDailyForecast(forecastRows);
      setWarehouseHealth(warehouse);
      setServiceCost(serviceRows);
      setChatHistory(chats);
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    } finally {
      setLoading(false);
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
    if (!chatQuestion.trim()) return;

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
    loadDashboardData();
  }, []);

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo">F</div>
          <div>
            <h1>FinOps AI</h1>
            <p>Cloud Cost Intelligence</p>
          </div>
        </div>

        <nav>
          <button className={activeTab === "dashboard" ? "active" : ""} onClick={() => setActiveTab("dashboard")}>
            Dashboard
          </button>
          <button className={activeTab === "waste" ? "active" : ""} onClick={() => setActiveTab("waste")}>
            Waste
          </button>
          <button className={activeTab === "anomalies" ? "active" : ""} onClick={() => setActiveTab("anomalies")}>
            Anomalies
          </button>
          <button className={activeTab === "forecast" ? "active" : ""} onClick={() => setActiveTab("forecast")}>
            Forecast
          </button>
          <button className={activeTab === "warehouse" ? "active" : ""} onClick={() => setActiveTab("warehouse")}>
            Warehouse
          </button>
          <button className={activeTab === "chatbot" ? "active" : ""} onClick={() => setActiveTab("chatbot")}>
            Chatbot
          </button>
        </nav>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h1>FinOps Dashboard</h1>
            <p>Cost visibility, waste detection, anomalies, forecasting, and AI-style insights.</p>
          </div>

          <button onClick={loadDashboardData} disabled={loading}>
            {loading ? "Loading..." : "Refresh"}
          </button>
        </header>

        {message && <div className="message">{message}</div>}

        {activeTab === "dashboard" && (
          <section>
            <div className="grid four">
              <StatCard
                title="Total Cost"
                value={`$${costSummary?.total_cost ?? 0}`}
                subtitle={`${costSummary?.record_count ?? 0} records`}
                color="blue"
              />
              <StatCard
                title="Waste Savings"
                value={`$${wasteSummary?.total_estimated_monthly_saving ?? 0}`}
                subtitle={`${wasteSummary?.active_findings ?? 0} active findings`}
                color="green"
              />
              <StatCard
                title="Anomaly Delta"
                value={`$${anomalySummary?.active_delta_cost ?? 0}`}
                subtitle={`${anomalySummary?.active_anomalies ?? 0} active anomalies`}
                color="red"
              />
              <StatCard
                title="Forecast"
                value={`$${forecastSummary?.total_forecasted_cost ?? 0}`}
                subtitle={forecastSummary?.budget_status ?? "Run forecast"}
                color="purple"
              />
            </div>

            <div className="grid two">
              <div className="card">
                <h3>Service Cost</h3>
                <div className="chart">
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={serviceCost}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="service_name" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="total_cost" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="card">
                <h3>Forecast Trend</h3>
                <div className="chart">
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={dailyForecast}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="forecast_date" />
                      <YAxis />
                      <Tooltip />
                      <Line type="monotone" dataKey="predicted_cost" />
                      <Line type="monotone" dataKey="upper_bound" />
                      <Line type="monotone" dataKey="lower_bound" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </section>
        )}

        {activeTab === "waste" && (
          <section>
            <div className="section-header">
              <h2>Waste Detection</h2>
              <button onClick={handleRunWasteScan} disabled={loading}>Run Waste Scan</button>
            </div>

            <div className="grid four">
              <StatCard title="Active" value={wasteSummary?.active_findings ?? 0} subtitle="waste findings" />
              <StatCard title="Dismissed" value={wasteSummary?.dismissed_findings ?? 0} subtitle="dismissed findings" />
              <StatCard title="Resolved" value={wasteSummary?.resolved_findings ?? 0} subtitle="resolved findings" />
              <StatCard title="Savings" value={`$${wasteSummary?.total_estimated_monthly_saving ?? 0}`} subtitle="monthly estimate" />
            </div>

            <div className="card">
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
                      <td>${item.estimated_monthly_saving}</td>
                      <td>{item.confidence_score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === "anomalies" && (
          <section>
            <div className="section-header">
              <h2>Anomaly Detection</h2>
              <button onClick={handleRunAnomalyScan} disabled={loading}>Run Anomaly Scan</button>
            </div>

            <div className="grid four">
              <StatCard title="Active" value={anomalySummary?.active_anomalies ?? 0} subtitle="cost anomalies" />
              <StatCard title="Dismissed" value={anomalySummary?.dismissed_anomalies ?? 0} subtitle="dismissed anomalies" />
              <StatCard title="Resolved" value={anomalySummary?.resolved_anomalies ?? 0} subtitle="resolved anomalies" />
              <StatCard title="Delta Cost" value={`$${anomalySummary?.active_delta_cost ?? 0}`} subtitle="active impact" />
            </div>

            <div className="card">
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
                      <td>${item.delta_cost}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === "forecast" && (
          <section>
            <div className="section-header">
              <h2>Cost Forecasting</h2>
              <button onClick={handleRunForecast} disabled={loading}>Run Forecast</button>
            </div>

            <div className="grid four">
              <StatCard title="Forecasted Cost" value={`$${forecastSummary?.total_forecasted_cost ?? 0}`} subtitle="next period" />
              <StatCard title="Daily Average" value={`$${forecastSummary?.average_daily_forecast ?? 0}`} subtitle="average forecast" />
              <StatCard title="Budget Status" value={forecastSummary?.budget_status ?? "NA"} subtitle="budget comparison" />
              <StatCard title="Confidence" value={forecastSummary?.confidence_score ?? "NA"} subtitle="model confidence" />
            </div>

            <div className="card">
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
                      <td>${item.predicted_cost}</td>
                      <td>${item.lower_bound}</td>
                      <td>${item.upper_bound}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === "warehouse" && (
          <section>
            <div className="section-header">
              <h2>Warehouse</h2>
              <button onClick={handleRefreshWarehouse} disabled={loading}>Refresh Warehouse</button>
            </div>

            <div className="grid four">
              <StatCard title="Warehouse Ready" value={warehouseHealth?.warehouse_ready ? "Yes" : "No"} subtitle="aggregate status" />
              <StatCard title="Source Records" value={warehouseHealth?.source_record_count ?? 0} subtitle="raw cost rows" />
              <StatCard title="Aggregates" value={warehouseHealth?.aggregate_record_count ?? 0} subtitle="summary rows" />
              <StatCard title="Last Status" value={warehouseHealth?.latest_refresh?.status ?? "NA"} subtitle="refresh status" />
            </div>

            <div className="card">
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
                      <td>${item.total_cost}</td>
                      <td>{item.record_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === "chatbot" && (
          <section>
            <div className="section-header">
              <h2>Natural Language Chatbot</h2>
            </div>

            <div className="card">
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

            <div className="card">
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
      </main>
    </div>
  );
}

export default App;