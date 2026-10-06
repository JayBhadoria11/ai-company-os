import { useEffect, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Brain,
  Building2,
  CheckCircle2,
  Clock3,
  Database,
  FileSpreadsheet,
  Layers,
  LayoutDashboard,
  Menu,
  Network,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Trash2,
  UploadCloud,
  X,
  Save,
} from "lucide-react";
import "./App.css";
import "./company-workshop.css";

// In development this defaults to the local backend. Production builds load
// frontend/.env.production (VITE_API_URL="") so requests go to the same origin
// when the API serves the built dashboard as a single service.
const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

const navItems = [
  { name: "Command Center", icon: LayoutDashboard },
  { name: "Company Workshop", icon: Building2 },
  { name: "Intelligence", icon: Brain },
  { name: "Agents", icon: Network },
  { name: "Financials", icon: BarChart3 },
  { name: "Approvals", icon: ShieldCheck },
  { name: "History", icon: Clock3 },
];

function App() {
  const [activePage, setActivePage] = useState("Command Center");
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="app-shell">
      {mobileOpen && (
        <button
          className="mobile-overlay"
          onClick={() => setMobileOpen(false)}
          aria-label="Close navigation"
        />
      )}

      <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark">N</div>

          <div>
            <div className="brand-name">AI Company OS</div>
            <div className="brand-subtitle">NVIDIA INTELLIGENCE LAYER</div>
          </div>

          <button
            className="mobile-close"
            onClick={() => setMobileOpen(false)}
            aria-label="Close menu"
          >
            <X size={18} />
          </button>
        </div>

        <div className="nav-label">Workspace</div>

        <nav className="navigation">
          {navItems.map(({ name, icon: Icon }) => (
            <button
              key={name}
              className={`nav-item ${activePage === name ? "active" : ""}`}
              onClick={() => {
                setActivePage(name);
                setMobileOpen(false);
              }}
            >
              <Icon size={17} />
              <span>{name}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="nav-label">System</div>

          <div className="system-item">
            <Activity size={14} />
            <span>Deterministic analytics</span>
          </div>

          <div className="system-item">
            <Sparkles size={14} />
            <span>Nemotron synthesis</span>
          </div>

          <div className="system-item">
            <ShieldCheck size={14} />
            <span>Human approval gate</span>
          </div>

          <div className="system-status">
            <span className="status-dot" />
            SYSTEM ONLINE
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <button
            className="menu-button"
            onClick={() => setMobileOpen(true)}
            aria-label="Open navigation"
          >
            <Menu size={20} />
          </button>

          <div className="topbar-brand">
            <Building2 size={16} />
            <span>AI COMPANY OS</span>
          </div>

          <div className="topbar-status">
            <span className="status-dot" />
            NVIDIA INTELLIGENCE ONLINE
          </div>
        </header>

        <div className="content">
          {activePage === "Command Center" ? (
            <CommandCenter />
          ) : activePage === "Company Workshop" ? (
            <CompanyWorkshop />
          ) : activePage === "Intelligence" ? (
            <Intelligence />
          ) : activePage === "Agents" ? (
            <Agents />
          ) : activePage === "Financials" ? (
            <Financials />
          ) : activePage === "Approvals" ? (
            <Approvals />
          ) : activePage === "History" ? (
            <History />
          ) : (
            <PlaceholderPage title={activePage} />
          )}
        </div>
      </main>
    </div>
  );
}

const EMPTY_PROFILE = {
  name: "",
  industry: "",
  description: "",
  website: "",
  headquarters: "",
  stage: "",
  team_size: "",
  founded_year: "",
  currency: "USD",
  reporting_period: "Monthly",
  primary_kpi: "Revenue",
  revenue_target: "",
  growth_target: "",
};

async function apiRequest(url, options = {}, timeoutMs = 15000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

function formatCount(value) {
  if (value == null) return "—";
  return Number(value).toLocaleString("en-US");
}

function formatTimestamp(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatCell(value) {
  if (value == null || value === "") return "—";
  if (typeof value === "number") {
    return Number.isInteger(value)
      ? value.toLocaleString("en-US")
      : value.toLocaleString("en-US", { maximumFractionDigits: 2 });
  }
  return String(value);
}

function CompanyWorkshop() {
  const [profile, setProfile] = useState(EMPTY_PROFILE);
  const [dataset, setDataset] = useState(null);

  const [loadingProfile, setLoadingProfile] = useState(true);
  const [loadingDataset, setLoadingDataset] = useState(true);

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [resetting, setResetting] = useState(false);

  const [profileError, setProfileError] = useState("");
  const [datasetError, setDatasetError] = useState("");
  const [notice, setNotice] = useState("");
  const [showResetConfirm, setShowResetConfirm] = useState(false);

  const fileInputRef = useRef(null);

  useEffect(() => {
    loadProfile();
    loadDataset();
  }, []);

  async function loadProfile() {
    setLoadingProfile(true);
    setProfileError("");

    try {
      const response = await apiRequest(`${API_URL}/api/company/profile`);

      if (!response.ok) {
        throw new Error(`Profile API returned ${response.status}`);
      }

      const data = await response.json();

      if (data.profile) {
        setProfile({ ...EMPTY_PROFILE, ...data.profile });
      }
    } catch (err) {
      setProfileError(
        err.name === "AbortError"
          ? "The company profile request timed out."
          : "Could not load the company profile."
      );
    } finally {
      setLoadingProfile(false);
    }
  }

  async function loadDataset() {
    setLoadingDataset(true);
    setDatasetError("");

    try {
      const response = await apiRequest(`${API_URL}/api/company/dataset`);

      if (!response.ok) {
        throw new Error(`Dataset API returned ${response.status}`);
      }

      const data = await response.json();

      if (data.status !== "success") {
        throw new Error(data.message || "Dataset API failed.");
      }

      setDataset(data);
    } catch (err) {
      setDatasetError(
        err.name === "AbortError"
          ? "The company dataset request timed out."
          : "Could not load the company dataset."
      );
    } finally {
      setLoadingDataset(false);
    }
  }

  const updateField = (field, value) => {
    setSaved(false);
    setProfile((current) => ({ ...current, [field]: value }));
  };

  async function saveProfile(event) {
    event.preventDefault();

    try {
      setSaving(true);
      setSaved(false);
      setProfileError("");
      setNotice("");

      const response = await apiRequest(`${API_URL}/api/company/profile`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile),
      });

      const data = await response.json();

      if (!response.ok || data.status !== "success") {
        throw new Error(data.message || "Could not save company profile.");
      }

      if (data.profile) {
        setProfile({ ...EMPTY_PROFILE, ...data.profile });
      }

      setSaved(true);
      setNotice("Company profile saved to the workspace.");
    } catch (err) {
      setProfileError(err.message || "Could not save company profile.");
    } finally {
      setSaving(false);
    }
  }

  function openFilePicker() {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  }

  async function handleFiles(files) {
    const file = files && files[0];

    if (!file) return;

    const lower = (file.name || "").toLowerCase();

    if (
      !lower.endsWith(".csv") &&
      !lower.endsWith(".xlsx") &&
      !lower.endsWith(".xls")
    ) {
      setDatasetError("Only CSV or Excel datasets are supported.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      setUploading(true);
      setDatasetError("");
      setNotice("");

      const response = await apiRequest(
        `${API_URL}/api/company/dataset`,
        { method: "POST", body: formData },
        60000
      );

      const data = await response.json();

      if (!response.ok || data.status !== "success") {
        throw new Error(data.message || "Dataset upload failed.");
      }

      setDataset(data);
      setNotice(data.message || "Dataset connected to the company workspace.");
    } catch (err) {
      setDatasetError(err.message || "Dataset upload failed.");
    } finally {
      setUploading(false);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  async function removeDataset(datasetId) {
    try {
      setUploading(true);
      setDatasetError("");
      setNotice("");

      const url =
        datasetId == null
          ? `${API_URL}/api/company/dataset`
          : `${API_URL}/api/company/dataset?id=${encodeURIComponent(datasetId)}`;

      const response = await apiRequest(
        url,
        { method: "DELETE" },
        30000
      );

      const data = await response.json();

      if (!response.ok || data.status !== "success") {
        throw new Error(data.message || "Could not remove the dataset.");
      }

      // The API returns the complete, ordered dataset collection.
      setDataset(data);
      setNotice("Dataset removed from the company workspace.");
    } catch (err) {
      setDatasetError(err.message || "Could not remove the dataset.");
    } finally {
      setUploading(false);
    }
  }

  async function resetWorkspace() {
    try {
      setResetting(true);
      setProfileError("");
      setDatasetError("");
      setNotice("");

      const response = await apiRequest(
        `${API_URL}/api/company/workspace`,
        { method: "DELETE" },
        30000
      );

      const data = await response.json();

      if (!response.ok || data.status !== "success") {
        throw new Error(data.message || "Workspace reset failed.");
      }

      setProfile(EMPTY_PROFILE);
      await loadDataset();
      setNotice("Company workspace reset. Profile, dataset, and derived state cleared.");
    } catch (err) {
      setProfileError(err.message || "Workspace reset failed.");
    } finally {
      setResetting(false);
      setShowResetConfirm(false);
    }
  }

  const activeDataset = dataset?.active || null;
  // The API returns the full collection in newest-first order. This array is
  // the source of truth for the dataset list, never a single dataset object.
  const datasetList = Array.isArray(dataset?.datasets) ? dataset.datasets : [];
  const preview = dataset?.preview || null;
  const metrics = dataset?.metrics || {};
  const hasDataset = Boolean(dataset?.has_dataset);
  const hasProfile = Boolean(profile.name || profile.industry);

  const connections = [
    { name: "Intelligence", connected: hasDataset },
    { name: "Agents", connected: hasDataset || hasProfile },
    { name: "Financials", connected: hasDataset },
    { name: "Approvals", connected: hasDataset || hasProfile },
  ];

  if (loadingProfile) {
    return (
      <div className="page-shell">
        <div className="page-header workshop-page-header">
          <div>
            <span className="eyebrow">COMPANY WORKSHOP</span>
            <h1>Build your company workspace</h1>
            <p>Loading company configuration...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-shell">
      <div className="page-header workshop-page-header">
        <div>
          <span className="eyebrow">COMPANY WORKSHOP</span>
          <h1>Company setup &amp; profile</h1>
          <p>
            The central source of truth for the company profile, configuration,
            objectives, and business dataset that powers the operating system.
          </p>
        </div>

        <div className="workshop-save-status">
          {saved && (
            <span className="workshop-saved">
              <CheckCircle2 size={15} />
              Saved
            </span>
          )}

          <button
            className="workshop-reset-btn"
            type="button"
            onClick={() => setShowResetConfirm(true)}
            disabled={resetting}
            aria-label="Reset company workspace"
          >
            <RefreshCw size={15} />
            {resetting ? "Resetting..." : "Reset Workspace"}
          </button>

          <button
            className="workshop-save-btn"
            type="submit"
            form="company-workshop-form"
            disabled={saving}
          >
            <Save size={16} />
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>

      {profileError && (
        <div className="error-banner">
          <AlertTriangle size={16} />
          <span>{profileError}</span>
        </div>
      )}

      {notice && <div className="success-banner">{notice}</div>}

      <form id="company-workshop-form" onSubmit={saveProfile}>
        <div className="workshop-layout">
          <div className="workshop-editor">
            <section className="workshop-section">
              <div className="workshop-section-heading">
                <div>
                  <span className="eyebrow">01 · IDENTITY</span>
                  <h2>Company Profile</h2>
                </div>
                <Building2 size={20} />
              </div>

              <div className="workshop-form-grid">
                <label>
                  <span>Company name</span>
                  <input
                    value={profile.name || ""}
                    onChange={(e) => updateField("name", e.target.value)}
                    placeholder="e.g. Acme AI"
                  />
                </label>

                <label>
                  <span>Industry</span>
                  <input
                    value={profile.industry || ""}
                    onChange={(e) => updateField("industry", e.target.value)}
                    placeholder="e.g. SaaS / FinTech"
                  />
                </label>

                <label className="workshop-full">
                  <span>Company description</span>
                  <textarea
                    value={profile.description || ""}
                    onChange={(e) => updateField("description", e.target.value)}
                    placeholder="Describe what your company does..."
                    rows="4"
                  />
                </label>

                <label>
                  <span>Website</span>
                  <input
                    value={profile.website || ""}
                    onChange={(e) => updateField("website", e.target.value)}
                    placeholder="https://..."
                  />
                </label>

                <label>
                  <span>Headquarters</span>
                  <input
                    value={profile.headquarters || ""}
                    onChange={(e) => updateField("headquarters", e.target.value)}
                    placeholder="City, Country"
                  />
                </label>
              </div>
            </section>

            <section className="workshop-section">
              <div className="workshop-section-heading">
                <div>
                  <span className="eyebrow">02 · ORGANIZATION</span>
                  <h2>Company configuration</h2>
                </div>
                <Activity size={20} />
              </div>

              <div className="workshop-form-grid">
                <label>
                  <span>Company stage</span>
                  <select
                    value={profile.stage || ""}
                    onChange={(e) => updateField("stage", e.target.value)}
                  >
                    <option value="">Select stage</option>
                    <option value="Idea">Idea</option>
                    <option value="Pre-seed">Pre-seed</option>
                    <option value="Seed">Seed</option>
                    <option value="Growth">Growth</option>
                    <option value="Scale-up">Scale-up</option>
                    <option value="Enterprise">Enterprise</option>
                  </select>
                </label>

                <label>
                  <span>Team size</span>
                  <input
                    value={profile.team_size || ""}
                    onChange={(e) => updateField("team_size", e.target.value)}
                    placeholder="e.g. 25"
                  />
                </label>

                <label>
                  <span>Founded year</span>
                  <input
                    value={profile.founded_year || ""}
                    onChange={(e) => updateField("founded_year", e.target.value)}
                    placeholder="e.g. 2024"
                  />
                </label>

                <label>
                  <span>Currency</span>
                  <select
                    value={profile.currency || "USD"}
                    onChange={(e) => updateField("currency", e.target.value)}
                  >
                    <option value="USD">USD — US Dollar</option>
                    <option value="INR">INR — Indian Rupee</option>
                    <option value="EUR">EUR — Euro</option>
                    <option value="GBP">GBP — Pound</option>
                  </select>
                </label>

                <label>
                  <span>Reporting period</span>
                  <select
                    value={profile.reporting_period || "Monthly"}
                    onChange={(e) =>
                      updateField("reporting_period", e.target.value)
                    }
                  >
                    <option value="Monthly">Monthly</option>
                    <option value="Quarterly">Quarterly</option>
                    <option value="Yearly">Yearly</option>
                  </select>
                </label>

                <label>
                  <span>Primary KPI</span>
                  <select
                    value={profile.primary_kpi || "Revenue"}
                    onChange={(e) => updateField("primary_kpi", e.target.value)}
                  >
                    <option value="Revenue">Revenue</option>
                    <option value="Net Sales">Net Sales</option>
                    <option value="Orders">Orders</option>
                    <option value="Units">Units</option>
                    <option value="Profit">Profit</option>
                  </select>
                </label>
              </div>
            </section>

            <section className="workshop-section">
              <div className="workshop-section-heading">
                <div>
                  <span className="eyebrow">03 · OBJECTIVES</span>
                  <h2>Business targets</h2>
                </div>
                <Sparkles size={20} />
              </div>

              <div className="workshop-form-grid">
                <label>
                  <span>Revenue target</span>
                  <input
                    value={profile.revenue_target || ""}
                    onChange={(e) => updateField("revenue_target", e.target.value)}
                    placeholder="e.g. 1000000"
                  />
                </label>

                <label>
                  <span>Growth target</span>
                  <input
                    value={profile.growth_target || ""}
                    onChange={(e) => updateField("growth_target", e.target.value)}
                    placeholder="e.g. 25%"
                  />
                </label>
              </div>
            </section>

            <section className="workshop-section">
              <div className="workshop-section-heading">
                <div>
                  <span className="eyebrow">04 · DATA</span>
                  <h2>Company Dataset</h2>
                </div>
                <Database size={20} />
              </div>

              {datasetError && (
                <div className="error-banner">
                  <AlertTriangle size={16} />
                  <span>{datasetError}</span>
                </div>
              )}

              <div
                className="workshop-dropzone"
                onClick={openFilePicker}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  handleFiles(e.dataTransfer.files);
                }}
              >
                <UploadCloud size={26} />
                <strong>
                  {hasDataset ? "Add another dataset" : "Upload company dataset"}
                </strong>
                <span>CSV or Excel · drop a file here or click to browse</span>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  className="workshop-file-input"
                  onChange={(e) => handleFiles(e.target.files)}
                />
              </div>

              {uploading && (
                <div className="workshop-inline-status">
                  <RefreshCw size={14} className="workshop-spin" />
                  Uploading and persisting dataset...
                </div>
              )}

              {loadingDataset ? (
                <div className="workshop-inline-status">Loading dataset status...</div>
              ) : hasDataset ? (
                <div className="workshop-data-block">
                  {datasetList.length > 0 && (
                    <div className="workshop-dataset-collection">
                      <span className="eyebrow">
                        CONNECTED DATASETS ({datasetList.length})
                      </span>

                      <ul className="workshop-dataset-list">
                        {datasetList.map((item) => (
                          <li
                            key={item.id ?? item.filename}
                            className="workshop-dataset-row"
                          >
                            <div className="workshop-dataset-row-file">
                              <FileSpreadsheet size={16} />
                              <div>
                                <strong>{item.filename}</strong>
                                <span>
                                  {formatTimestamp(item.uploaded_at)} ·{" "}
                                  {formatCount(item.rows)} rows ·{" "}
                                  {formatCount(item.columns)} columns
                                </span>
                              </div>
                            </div>

                            <button
                              type="button"
                              className="workshop-mini-btn danger"
                              onClick={() => removeDataset(item.id)}
                              disabled={uploading}
                            >
                              <Trash2 size={14} />
                              Delete
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="workshop-data-header">
                    <div className="workshop-data-file">
                      <FileSpreadsheet size={18} />
                      <div>
                        <strong>{activeDataset.filename}</strong>
                        <span>
                          Active · {formatCount(activeDataset.rows)} rows ·{" "}
                          {formatCount(activeDataset.columns)} columns
                        </span>
                      </div>
                    </div>

                    <div className="workshop-data-actions">
                      <button
                        type="button"
                        className="workshop-mini-btn"
                        onClick={openFilePicker}
                        disabled={uploading}
                      >
                        <UploadCloud size={14} />
                        Add
                      </button>
                      <button
                        type="button"
                        className="workshop-mini-btn danger"
                        onClick={() => removeDataset(activeDataset.id)}
                        disabled={uploading}
                      >
                        <Trash2 size={14} />
                        Delete
                      </button>
                    </div>
                  </div>

                  <div className="workshop-dataset-stats">
                    <div>
                      <span>ROWS</span>
                      <strong>{formatCount(activeDataset.rows)}</strong>
                    </div>
                    <div>
                      <span>COLUMNS</span>
                      <strong>{formatCount(activeDataset.columns)}</strong>
                    </div>
                    <div>
                      <span>DATASET TYPE</span>
                      <strong>{dataset?.dataset_type || "generic"}</strong>
                    </div>
                    <div>
                      <span>CONNECTED FILES</span>
                      <strong>{formatCount(dataset?.count)}</strong>
                    </div>
                  </div>

                  {activeDataset.column_names?.length > 0 && (
                    <div className="workshop-columns">
                      <span className="eyebrow">COLUMNS</span>
                      <div className="workshop-column-chips">
                        {activeDataset.column_names.slice(0, 40).map((column) => (
                          <span key={column} className="workshop-column-chip">
                            {column}
                          </span>
                        ))}
                        {activeDataset.column_names.length > 40 && (
                          <span className="workshop-column-chip more">
                            +{activeDataset.column_names.length - 40} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {preview && preview.rows?.length > 0 && (
                    <div className="workshop-preview-table-wrap">
                      <table className="workshop-preview-table">
                        <thead>
                          <tr>
                            {preview.columns.map((column) => (
                              <th key={column}>{column}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {preview.rows.map((row, rowIndex) => (
                            <tr key={rowIndex}>
                              {preview.columns.map((column) => (
                                <td key={column}>{formatCell(row[column])}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {dataset?.limitations?.length > 0 && (
                    <div className="workshop-limitations">
                      <span className="eyebrow">NOT AVAILABLE FROM CURRENT DATASET</span>
                      <ul>
                        {dataset.limitations.slice(0, 4).map((item, index) => (
                          <li key={index}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="workshop-data-empty">
                  <FileSpreadsheet size={20} />
                  <div>
                    <strong>No dataset connected</strong>
                    <span>
                      Upload the company's CSV to power Intelligence, Agents,
                      Financials, and Approvals from one shared dataset.
                    </span>
                  </div>
                </div>
              )}

              <div className="workshop-connections">
                <span className="eyebrow">CONNECTED TO</span>
                <div className="workshop-connection-list">
                  {connections.map((item) => (
                    <span
                      key={item.name}
                      className={`workshop-connection ${
                        item.connected ? "is-connected" : "is-offline"
                      }`}
                    >
                      <CheckCircle2 size={13} />
                      {item.name}
                    </span>
                  ))}
                </div>
              </div>
            </section>

            <button
              className="workshop-mobile-save"
              type="submit"
              disabled={saving}
            >
              <Save size={16} />
              {saving ? "Saving..." : "Save Company Profile"}
            </button>
          </div>

          <aside className="workshop-preview">
            <div className="workshop-preview-label">
              <span className="eyebrow">LIVE PREVIEW</span>
              <span className="workshop-live-dot">
                {dataset?.has_dataset ? "LIVE" : "STANDBY"}
              </span>
            </div>

            <div className="workshop-company-card">
              <div className="workshop-company-mark">
                {(profile.name || "C").charAt(0).toUpperCase()}
              </div>

              <div>
                <h2>{profile.name || "Your Company"}</h2>
                <p>{profile.industry || "Industry not configured"}</p>
              </div>
            </div>

            <div className="workshop-description">
              {profile.description ||
                "Add a company description to give the operating system context about your business."}
            </div>

            <div className="workshop-profile-list">
              <div>
                <span>HEADQUARTERS</span>
                <strong>{profile.headquarters || "Not configured"}</strong>
              </div>

              <div>
                <span>STAGE</span>
                <strong>{profile.stage || "Not configured"}</strong>
              </div>

              <div>
                <span>TEAM</span>
                <strong>{profile.team_size || "Not configured"}</strong>
              </div>

              <div>
                <span>FOUNDED</span>
                <strong>{profile.founded_year || "Not configured"}</strong>
              </div>
            </div>

            <div className="workshop-preview-divider" />

            <div className="workshop-data-heading">
              <div>
                <span className="eyebrow">CONNECTED DATA</span>
                <h3>Business dataset</h3>
              </div>
              <CheckCircle2 size={18} />
            </div>

            <div className="workshop-data-stats">
              <div>
                <span>NET SALES</span>
                <strong>
                  {metrics.net_sales != null
                    ? `$${metrics.net_sales.toLocaleString("en-US", {
                        maximumFractionDigits: 0,
                      })}`
                    : "—"}
                </strong>
              </div>

              <div>
                <span>ORDERS</span>
                <strong>{formatCount(metrics.orders)}</strong>
              </div>

              <div>
                <span>ROWS</span>
                <strong>{formatCount(activeDataset?.rows)}</strong>
              </div>

              <div>
                <span>COLUMNS</span>
                <strong>{formatCount(activeDataset?.columns)}</strong>
              </div>
            </div>

            <div className="workshop-config-card">
              <span className="eyebrow">OPERATING CONFIG</span>

              <div>
                <span>Currency</span>
                <strong>{profile.currency}</strong>
              </div>

              <div>
                <span>Reporting</span>
                <strong>{profile.reporting_period}</strong>
              </div>

              <div>
                <span>Primary KPI</span>
                <strong>{profile.primary_kpi}</strong>
              </div>

              <div>
                <span>Revenue target</span>
                <strong>{profile.revenue_target || "Not set"}</strong>
              </div>

              <div>
                <span>Growth target</span>
                <strong>{profile.growth_target || "Not set"}</strong>
              </div>
            </div>

            <div className="workshop-source-note">
              <Layers size={14} />
              <span>
                One authoritative dataset shared by every module. No module
                keeps its own copy.
              </span>
            </div>
          </aside>
        </div>
      </form>

      {showResetConfirm && (
        <div className="reset-modal-overlay reset-modal-overlay--workspace">
          <div
            className="reset-modal reset-modal--workspace"
            role="dialog"
            aria-modal="true"
            aria-labelledby="workspace-reset-title"
          >
            <div className="reset-modal-icon">
              <AlertTriangle size={20} />
            </div>
            <h3 id="workspace-reset-title">Reset company workspace?</h3>
            <p>
              This will clear the current company profile, uploaded dataset,
              derived workspace state, actions, and approvals.
            </p>
            <div className="reset-modal-actions">
              <button
                className="reset-cancel-btn"
                onClick={() => setShowResetConfirm(false)}
                disabled={resetting}
              >
                Cancel
              </button>
              <button
                className="reset-confirm-btn"
                onClick={resetWorkspace}
                disabled={resetting}
              >
                {resetting ? "Resetting..." : "Reset Workspace"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


function CommandCenter() {
  const [company, setCompany] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadCompany() {
      try {
        setLoading(true);

        const response = await fetch(`${API_URL}/api/company`);

        if (!response.ok) {
          throw new Error(`API returned ${response.status}`);
        }

        const data = await response.json();
        setCompany(data);
        setError("");
      } catch (err) {
        console.error("Failed to load company data:", err);
        setError("Unable to connect to the Python backend.");
      } finally {
        setLoading(false);
      }
    }

    loadCompany();
  }, []);

  const metrics = company?.metrics || {};

  const netSales =
    metrics.net_sales != null
      ? `$${metrics.net_sales.toLocaleString("en-US", {
          maximumFractionDigits: 0,
        })}`
      : null;

  const orders =
    metrics.orders != null
      ? metrics.orders.toLocaleString("en-US")
      : null;

  const units =
    metrics.units != null
      ? metrics.units.toLocaleString("en-US")
      : null;

  const aov =
    metrics.aov != null
      ? `$${metrics.aov.toLocaleString("en-US", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })}`
      : null;

  return (
    <>
      <section className="page-header">
        <div>
          <div className="eyebrow">COMMAND CENTER</div>
          <h1>Run the company from one intelligence layer</h1>
          <p>
            Executive control surface for financial health, investigations,
            decisions, and agent orchestration.
          </p>
        </div>

        <div className="live-pill">
          <span className="status-dot" />
          {loading ? "CONNECTING..." : error ? "OFFLINE" : "LIVE COMPANY"}
        </div>
      </section>

      <section className="status-grid">
        <StatusCard label="SYSTEM" value="ONLINE" />
        <StatusCard
          label="ACTIVE INVESTIGATION"
          value={
            loading ? <Skeleton width={80} height={16} /> : "NONE"
          }
        />
        <StatusCard
          label="NEMOTRON"
          value={
            loading ? <Skeleton width={90} height={16} /> : "CONNECTED"
          }
        />
        <StatusCard
          label="COMPANY"
          value={
            loading
              ? "CONNECTING..."
              : company?.active
              ? "LIVE"
              : "OFFLINE"
          }
        />
      </section>

      {error && (
        <div className="api-error">
          {error}
          <span>Make sure FastAPI is running on port 8000.</span>
        </div>
      )}

      <section className="hero-grid">
        <div className="hero-card">
          <div className="eyebrow">AI BUSINESS OPERATING SYSTEM</div>

          <h2>
            Understand the business.
            <br />
            Decide with intelligence.
          </h2>

          <p>
            Deterministic analytics establish facts. Commander coordinates
            agents. NVIDIA Nemotron turns evidence into decisions.
          </p>

          <div className="hero-tags">
            <span>VERIFIED DATA</span>
            <span>AGENT NETWORK</span>
            <span>NEMOTRON</span>
          </div>
        </div>

        <div className="spline-card">
          <div className="spline-glow" />
          <div className="ai-core">
            <div className="ai-core-inner" />
          </div>

          <div className="core-label">AI COMPANY OS · INTELLIGENCE CORE</div>
          <div className="core-subtitle">
            Spline scene will be connected here
          </div>
        </div>
      </section>

      <section className="section">
        <div className="section-heading">
          <div>
            <h2>Company Pulse</h2>
            <p>
              {company
                ? `Verified metrics from ${company.dataset} operating dataset`
                : "Loading verified company metrics"}
            </p>
          </div>

          <span className="verified">
            <CheckCircle2 size={14} />
            VERIFIED
          </span>
        </div>

        <div className="metric-grid">
          {loading ? (
            <>
              <MetricCardSkeleton label="NET SALES" />
              <MetricCardSkeleton label="ORDERS" />
              <MetricCardSkeleton label="UNITS" />
              <MetricCardSkeleton label="AOV" />
            </>
          ) : (
            <>
              <MetricCard label="NET SALES" value={netSales} />
              <MetricCard label="ORDERS" value={orders} />
              <MetricCard label="UNITS" value={units} />
              <MetricCard label="AOV" value={aov} />
            </>
          )}
        </div>
      </section>

      <section className="section">
        <div className="section-heading">
          <div>
            <h2>Connected Operating System</h2>
            <p>Live modules connected to the company workspace</p>
          </div>
        </div>

        <div className="module-grid">
          {loading ? (
            <>
              <ModuleCardSkeleton />
              <ModuleCardSkeleton />
              <ModuleCardSkeleton />
              <ModuleCardSkeleton />
            </>
          ) : (
            <>
              <ModuleCard title="Financials" status="LIVE" />
              <ModuleCard title="Intelligence" status="CONNECTED" />
              <ModuleCard title="History" status="PERSISTED" />
              <ModuleCard title="Approvals" status="READY" />
            </>
          )}
        </div>
      </section>
    </>
  );
}

function StatusCard({ label, value }) {
  return (
    <div className="status-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function isUnavailableMetric(value) {
  return value == null || value === "" || value === "?" || value === "—";
}

function MetricCard({ label, value, muted = false }) {
  const unavailable = isUnavailableMetric(value);

  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong className={muted || unavailable ? "muted-value" : ""}>
        {unavailable ? "No verified data" : value}
      </strong>
    </div>
  );
}

function ModuleCard({ title, status }) {
  return (
    <div className="module-card">
      <div>
        <div className="module-title">{title}</div>
        <div className="module-subtitle">Company Workspace</div>
      </div>

      <span className="module-status">{status}</span>
    </div>
  );
}

function Skeleton({ width = "100%", height = 12, block = false, radius, style }) {
  return (
    <span
      className={`skeleton ${block ? "skeleton-block" : ""}`}
      style={{ width, height, borderRadius: radius, ...style }}
      aria-hidden="true"
    />
  );
}

function MetricCardSkeleton({ label }) {
  return (
    <div className="metric-card" aria-busy="true">
      <span>{label}</span>
      <strong>
        <Skeleton width="65%" height={22} block />
      </strong>
    </div>
  );
}

function ModuleCardSkeleton() {
  return (
    <div className="module-card" aria-busy="true">
      <div>
        <Skeleton width="55%" height={13} block />
        <div style={{ height: 6 }} />
        <Skeleton width="40%" height={10} block />
      </div>

      <Skeleton width={54} height={18} radius="999px" />
    </div>
  );
}

function ChartSkeleton() {
  return (
    <div className="chart-skeleton" aria-busy="true">
      <Skeleton width="100%" height={190} radius={12} block />
    </div>
  );
}

function EmptyData() {
  return <div className="data-empty">No verified data available.</div>;
}


function Financials() {
  const [company, setCompany] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadFinancials() {
      try {
        setLoading(true);

        const response = await fetch(`${API_URL}/api/company`);

        if (!response.ok) {
          throw new Error(`API returned ${response.status}`);
        }

        const data = await response.json();
        setCompany(data);
        setError("");
      } catch (err) {
        console.error("Failed to load financials:", err);
        setError("Unable to connect to the Python backend.");
      } finally {
        setLoading(false);
      }
    }

    loadFinancials();
  }, []);

  const metrics = company?.metrics || {};
  const products = company?.products || [];
  const regions = company?.regions || [];
  const monthly = company?.monthly || [];
  const insights = company?.insights || [];
  const limitations = company?.limitations || [];

  const money = (value) =>
    value != null
      ? `$${Number(value).toLocaleString("en-US", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })}`
      : null;

  const number = (value) =>
    value != null ? Number(value).toLocaleString("en-US") : null;

  return (
    <>
      <section className="page-header">
        <div>
          <div className="eyebrow">FINANCIALS</div>
          <h1>Financial health at a glance</h1>
          <p>
            Verified financial metrics from the connected company dataset.
          </p>
        </div>

        <div className="live-pill">
          <span className="status-dot" />
          {loading ? "CONNECTING..." : error ? "OFFLINE" : "LIVE FINANCIALS"}
        </div>
      </section>

      {error && (
        <div className="api-error">
          {error}
          <span>Make sure FastAPI is running on port 8000.</span>
        </div>
      )}

      <section className="status-grid">
        <StatusCard
          label="DATASET"
          value={
            loading ? (
              <Skeleton width={120} height={16} />
            ) : (
              company?.dataset || "No verified data"
            )
          }
        />
        <StatusCard
          label="DATA ROWS"
          value={
            loading ? (
              <Skeleton width={80} height={16} />
            ) : (
              number(company?.rows) || "No verified data"
            )
          }
        />
        <StatusCard
          label="ORDERS"
          value={
            loading ? (
              <Skeleton width={80} height={16} />
            ) : (
              number(metrics.orders) || "No verified data"
            )
          }
        />
        <StatusCard
          label="STATUS"
          value={
            loading
              ? "LOADING..."
              : company?.active
              ? "LIVE"
              : "OFFLINE"
          }
        />
      </section>

      <section className="section">
        <div className="section-heading">
          <div>
            <h2>Company Pulse</h2>
            <p>Verified metrics from the operating dataset</p>
          </div>

          <span className="verified">
            <CheckCircle2 size={14} />
            VERIFIED
          </span>
        </div>

        <div className="metric-grid">
          {loading ? (
            <>
              <MetricCardSkeleton label="NET SALES" />
              <MetricCardSkeleton label="ORDERS" />
              <MetricCardSkeleton label="UNITS" />
              <MetricCardSkeleton label="AOV" />
            </>
          ) : (
            <>
              <MetricCard label="NET SALES" value={money(metrics.net_sales)} />
              <MetricCard label="ORDERS" value={number(metrics.orders)} />
              <MetricCard
                label="UNITS"
                value={number(metrics.units)}
                muted={metrics.units == null}
              />
              <MetricCard
                label="AOV"
                value={money(metrics.aov)}
                muted={metrics.aov == null}
              />
            </>
          )}
        </div>
      </section>

      <section className="section">
        <div className="section-heading">
          <div>
            <h2>Top Products</h2>
            <p>Highest net sales in the connected dataset</p>
          </div>
        </div>

        <div className="module-grid">
          {loading ? (
            Array.from({ length: 6 }, (_, index) => (
              <ModuleCardSkeleton key={index} />
            ))
          ) : products.length === 0 ? (
            <EmptyData />
          ) : (
            products.slice(0, 6).map((product, index) => (
              <div className="module-card" key={product.name || index}>
                <div>
                  <div className="module-title">
                    {product.name}
                  </div>
                  <div className="module-subtitle">
                    {number(product.orders)} orders
                  </div>
                </div>

                <span className="module-status">
                  {money(product.sales)}
                </span>
              </div>
            ))
          )}
        </div>
      </section>

      <section className="section">
        <div className="section-heading">
          <div>
            <h2>Regional Performance</h2>
            <p>Net sales by operating region</p>
          </div>
        </div>

        <div className="module-grid">
          {loading ? (
            Array.from({ length: 4 }, (_, index) => (
              <ModuleCardSkeleton key={index} />
            ))
          ) : regions.length === 0 ? (
            <EmptyData />
          ) : (
            regions.map((region) => (
              <div className="module-card" key={region.name}>
                <div>
                  <div className="module-title">{region.name}</div>
                  <div className="module-subtitle">
                    {number(region.orders)} orders
                  </div>
                </div>

                <span className="module-status">
                  {money(region.sales)}
                </span>
              </div>
            ))
          )}
        </div>
      </section>

      <section className="section">
        <div className="section-heading">
          <div>
            <h2>Monthly Sales</h2>
            <p>Verified monthly net sales history</p>
          </div>
        </div>

        <div className="module-grid">
          {loading ? (
            <ChartSkeleton />
          ) : monthly.length === 0 ? (
            <EmptyData />
          ) : (
            monthly.map((item) => (
              <div className="module-card" key={item.month}>
                <div>
                  <div className="module-title">{item.month}</div>
                </div>

                <span className="module-status">
                  {money(item.sales)}
                </span>
              </div>
            ))
          )}
        </div>
      </section>

      <section className="section">
        <div className="section-heading">
          <div>
            <h2>Financial Insights</h2>
            <p>Deterministic insights generated from verified data</p>
          </div>
        </div>

        <div className="module-grid">
          {loading ? (
            Array.from({ length: 4 }, (_, index) => (
              <ModuleCardSkeleton key={index} />
            ))
          ) : insights.length === 0 ? (
            <EmptyData />
          ) : (
            insights.map((insight, index) => (
              <div className="module-card" key={index}>
                <div>
                  <div className="module-title">INSIGHT</div>
                  <div className="module-subtitle">{insight}</div>
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      <section className="section">
        <div className="section-heading">
          <div>
            <h2>Data Limitations</h2>
            <p>Metrics that cannot be verified from the uploaded dataset</p>
          </div>
        </div>

        <div className="module-grid">
          {loading ? (
            Array.from({ length: 4 }, (_, index) => (
              <ModuleCardSkeleton key={index} />
            ))
          ) : limitations.length === 0 ? (
            <EmptyData />
          ) : (
            limitations.map((item, index) => (
              <div className="module-card" key={index}>
                <div>
                  <div className="module-title">UNAVAILABLE</div>
                  <div className="module-subtitle">{item}</div>
                </div>
              </div>
            ))
          )}
        </div>
      </section>
    </>
  );
}


function splitParagraphs(text) {
  return String(text ?? "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function highlightNumbers(line) {
  // split with a capturing group returns matches at odd indices.
  const parts = String(line).split(/(\$?\d[\d,]*(?:\.\d+)?%?)/g);

  return parts.map((part, index) =>
    index % 2 === 1 ? (
      <strong className="intelligence-number" key={index}>
        {part}
      </strong>
    ) : (
      part
    )
  );
}

function readingBlocks(text) {
  const lines = splitParagraphs(text).filter(
    (line) => !/no question provided/i.test(line)
  );

  const blocks = [];

  lines.forEach((line, index) => {
    const isQuestionHeader = /^question\s+\d+\b/i.test(line);

    if (isQuestionHeader) {
      const next = lines[index + 1];
      const hasBody =
        next &&
        !/^question\s+\d+\b/i.test(next) &&
        !/^executive summary\b/i.test(next);

      if (!hasBody) return;
    }

    blocks.push(line);
  });

  return blocks;
}

function renderReadingText(text) {
  const blocks = readingBlocks(text);

  if (blocks.length === 0) return null;

  return blocks.map((line, index) => (
    <p className="intelligence-paragraph" key={index}>
      {highlightNumbers(line)}
    </p>
  ));
}

function evidenceLabel(evidence) {
  if (!evidence) return null;

  const source =
    typeof evidence === "string" ? evidence : evidence.source;

  if (!source) return null;

  const value = String(source).toLowerCase();

  if (
    value.includes("company") ||
    value.includes("verified") ||
    value.includes("financial_report")
  ) {
    return "VERIFIED EVIDENCE";
  }

  if (value.includes("nemotron") || value.includes("synthesis")) {
    return "NEMOTRON INTERPRETATION";
  }

  return String(source).toUpperCase();
}

function evidenceSource(evidence) {
  if (!evidence || typeof evidence === "string") return null;

  const sources = evidence.source_datasets || evidence.datasets;

  if (Array.isArray(sources) && sources.length > 0) {
    return `Source datasets: ${sources.join(", ")}`;
  }

  if (evidence.dataset) {
    return `Company workspace dataset: ${evidence.dataset}`;
  }

  if (evidence.source) {
    return `Source: ${evidence.source}`;
  }

  return null;
}

function relativeTime(value) {
  if (!value) return "";

  const then = new Date(value);

  if (Number.isNaN(then.getTime())) return "";

  const diffMinutes = Math.floor((Date.now() - then.getTime()) / 60000);

  if (diffMinutes < 1) return "Just now";
  if (diffMinutes < 60) return `${diffMinutes} min ago`;

  const hours = Math.floor(diffMinutes / 60);
  if (hours < 24) return `${hours} hr${hours === 1 ? "" : "s"} ago`;

  const days = Math.floor(hours / 24);
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;

  return then.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

async function fetchPastQuestions() {
  const response = await apiRequest(
    `${API_URL}/api/intelligence/questions`
  );

  if (!response.ok) {
    throw new Error(`Questions API returned ${response.status}`);
  }

  const data = await response.json();

  if (data.status !== "success") {
    throw new Error(data.message || "Questions API failed.");
  }

  return data.questions || [];
}

function questionsErrorMessage(err) {
  return err?.name === "AbortError"
    ? "Past questions request timed out."
    : "Could not load past questions.";
}

function Intelligence() {
  const [query, setQuery] = useState("");
  const [investigation, setInvestigation] = useState(null);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState(0);
  // Single source of truth for the investigation request lifecycle.
  // idle -> running -> success | error
  const [status, setStatus] = useState("idle");

  const loading = status === "running";

  const [pastQuestions, setPastQuestions] = useState([]);
  const [questionsLoading, setQuestionsLoading] = useState(true);
  const [questionsError, setQuestionsError] = useState("");

  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadPastQuestions() {
      setQuestionsLoading(true);
      setQuestionsError("");

      try {
        const questions = await fetchPastQuestions();
        if (active) setPastQuestions(questions);
      } catch (err) {
        if (active) setQuestionsError(questionsErrorMessage(err));
      } finally {
        if (active) setQuestionsLoading(false);
      }
    }

    loadPastQuestions();

    return () => {
      active = false;
    };
  }, []);

  async function refreshPastQuestions() {
    try {
      const questions = await fetchPastQuestions();
      setPastQuestions(questions);
      setQuestionsError("");
    } catch (err) {
      setQuestionsError(questionsErrorMessage(err));
    }
  }

  function openDeleteQuestion(item) {
    setDeleteError("");
    setPendingDelete(item);
  }

  async function deleteQuestion(item) {
    if (!item) return;

    try {
      setDeleting(true);
      setDeleteError("");

      const response = await apiRequest(
        `${API_URL}/api/intelligence/questions/${item.id}`,
        { method: "DELETE" }
      );

      const data = await response.json();

      if (!response.ok || data.status !== "success") {
        throw new Error(data.message || "Could not delete question.");
      }

      setPastQuestions((current) =>
        current.filter((question) => question.id !== item.id)
      );
      setPendingDelete(null);
    } catch (err) {
      setDeleteError(err.message || "Could not delete question.");
    } finally {
      setDeleting(false);
    }
  }

  async function runInvestigation() {
    const trimmedQuery = query.trim();

    if (!trimmedQuery) {
      setError("Enter a business question first.");
      return;
    }

    let progressTimer;

    // Reset for a fresh run.
    setStatus("running");
    setError("");
    setInvestigation(null);
    setProgress(10);

    // Deterministic staged progress. Success always becomes exactly 100; we
    // never advance past 80 until the response arrives, so we never fake a
    // precise completion and never fall back to 0.
    const stages = [50, 80];
    let stageIndex = 0;

    progressTimer = setInterval(() => {
      if (stageIndex < stages.length) {
        setProgress(stages[stageIndex]);
        stageIndex += 1;
      }
    }, 1800);

    try {
      const response = await fetch(
        `${API_URL}/api/intelligence/investigate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            query: trimmedQuery,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok || data.status === "error") {
        throw new Error(
          data.message || `API returned ${response.status}`
        );
      }

      setInvestigation(data);
      setProgress(100);
      setStatus("success");
    } catch (err) {
      console.error("Investigation failed:", err);
      setError(
        err.message || "Unable to run the AI investigation."
      );
      setStatus("error");
    } finally {
      if (progressTimer) {
        clearInterval(progressTimer);
      }
      refreshPastQuestions();
    }
  }

  function handleKeyDown(event) {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      runInvestigation();
    }
  }

  const result = investigation?.result;
  const metrics = result?.metrics || {};
  const synthesis = metrics.nvidia_synthesis || {};
  const findings = result?.findings || [];
  const recommendations = result?.recommendations || [];
  const requiredAgents = metrics.required_agents || [];
  const questions = (metrics.investigation_questions || []).filter(
    (question) => question != null && String(question).trim() !== ""
  );

  // Past Questions contains ONLY persisted user business questions. The count
  // badge and the rendered list use this exact same array so they always match.
  const savedQuestions = (() => {
    const seen = new Set();
    const list = [];

    for (const item of pastQuestions) {
      if (!item) continue;

      const id = item.id ?? item.question;
      if (seen.has(id)) continue;

      const text = String(item.question || "")
        .replace(/\s+/g, " ")
        .trim();

      if (!text) continue;

      seen.add(id);
      list.push({ ...item, displayQuestion: text });
    }

    return list;
  })();

  const companyAnalysis = metrics.company_analysis || {};
  const analysisMetrics = companyAnalysis.metrics || {};
  const analysisBreakdowns = companyAnalysis.breakdowns || {};

  const synthesisText = synthesis.executive_summary || "";
  const synthesisMatchesFinding = findings.some((item) => {
    const text = typeof item === "string" ? item : item?.finding;
    return text && text === synthesisText;
  });

  return (
    <>
      <section className="page-header intelligence-header">
        <div>
          <div className="eyebrow">NVIDIA INTELLIGENCE</div>
          <h1>Ask the company anything</h1>
          <p className="intelligence-header-sub">
            Commander coordinates specialist agents, analyzes verified company
            evidence, and uses NVIDIA Nemotron for executive synthesis.
          </p>
        </div>

        <div className="live-pill">
          <span className="status-dot" />
          {loading ? "INVESTIGATING" : "NEMOTRON ONLINE"}
        </div>
      </section>

      <section className="section intelligence-ask">
        <div className="section-heading">
          <div>
            <h2>AI Investigation</h2>
            <p>
              Ask a business question and let the intelligence layer
              investigate it.
            </p>
          </div>

          <span className="verified">
            <Sparkles size={14} />
            NEMOTRON
          </span>
        </div>

        <div className="intelligence-input-card">
          <textarea
            className="intelligence-input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Example: Which products and regions are driving our sales performance?"
            rows={4}
            disabled={loading}
          />

          <div className="intelligence-input-footer">
            <span className="intelligence-hint">
              {loading
                ? "Commander is investigating the company..."
                : "Ctrl + Enter to run"}
            </span>

            <button
              className="primary-action intelligence-run-btn"
              onClick={runInvestigation}
              disabled={loading || !query.trim()}
            >
              {loading ? "Running Investigation..." : "Run AI Investigation"}
            </button>
          </div>
        </div>

        {error && (
          <div className="api-error">
            {error}
            <span>Make sure FastAPI is running on port 8000.</span>
          </div>
        )}
      </section>

      {(status === "running" || status === "success") && (
        <section className="section">
          <div className="intelligence-progress">
            <div className="intelligence-progress-label">
              <span>INVESTIGATION PROGRESS</span>
              <progress value={progress} max="100" />
              <span>{progress}%</span>
            </div>
            <div className={`intelligence-progress-status ${status === "success" ? "complete" : ""}`}>
              {status === "success"
                ? "✓ INVESTIGATION COMPLETE"
                : "● IN PROGRESS"}
            </div>
            {status === "success" && (
              <div className="intelligence-progress-note">
                Results are ready below
              </div>
            )}
          </div>
        </section>
      )}

      {investigation && status === "success" && result && (
        <>
          <section className="section">
            <div className="intelligence-result">
              <div className="intelligence-result-main">
                <div className="eyebrow">INVESTIGATION RESULT</div>
                <h2>{investigation.query || "Investigation result"}</h2>
              </div>

              <span className="verified">
                <CheckCircle2 size={14} />
                VERIFIED RUN
              </span>
            </div>

            <div className="intelligence-status-row">
              <span className="intelligence-status-pill">
                <span className="label">STATUS</span>
                <strong>{result.status?.toUpperCase() || "SUCCESS"}</strong>
              </span>

              <span className="intelligence-status-pill">
                <span className="label">AGENT</span>
                <strong>{result.agent?.toUpperCase() || "COMMANDER"}</strong>
              </span>

              <span className="intelligence-status-pill">
                <span className="label">COMMANDER</span>
                <strong>ACTIVE</strong>
              </span>

              <span className="intelligence-status-pill">
                <span className="label">NEMOTRON</span>
                <strong>CONNECTED</strong>
              </span>

              {requiredAgents.map((agent, index) => (
                <span
                  className="intelligence-status-pill muted"
                  key={`agent-${index}`}
                >
                  <span className="label">AGENT</span>
                  <strong>{String(agent).toUpperCase()}</strong>
                </span>
              ))}
            </div>
          </section>

          {questions.length > 0 && (
            <section className="section">
              <div className="section-heading">
                <div>
                  <h2>Investigation Questions</h2>
                  <p>Questions used by the intelligence layer for this run.</p>
                </div>
              </div>

              <div className="intelligence-question-list">
                {questions.map((question, index) => (
                  <div className="intelligence-question" key={index}>
                    <span className="intelligence-question-index">
                      Q{index + 1}
                    </span>
                    <p>{question}</p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {findings.length > 0 && (
            <section className="section">
              <div className="section-heading">
                <div>
                  <h2>Commander Findings</h2>
                  <p>
                    Evidence-grounded findings generated from the connected
                    company dataset.
                  </p>
                </div>
              </div>

              <div className="intelligence-finding-list">
                {findings.map((item, index) => {
                  const text =
                    typeof item === "string"
                      ? item
                      : item?.finding || "";
                  const label = evidenceLabel(item?.evidence);
                  const source = evidenceSource(item?.evidence);

                  return (
                    <article className="intelligence-finding-card" key={index}>
                      <div className="intelligence-finding-head">
                        <span className="intelligence-category">
                          COMMANDER FINDING {index + 1}
                        </span>

                        {label && (
                          <span className="intelligence-evidence-tag">
                            {label}
                          </span>
                        )}
                      </div>

                      <div className="intelligence-finding-body">
                        {renderReadingText(text)}
                      </div>

                      {source && (
                        <div className="intelligence-evidence-meta">{source}</div>
                      )}
                    </article>
                  );
                })}
              </div>
            </section>
          )}

          {synthesisText && (
            <section className="section">
              <div className="section-heading">
                <div>
                  <h2>Executive Synthesis</h2>
                  <p>
                    NVIDIA Nemotron synthesis of the verified investigation
                    evidence.
                  </p>
                </div>

                <span className="verified">
                  <Sparkles size={14} />
                  NEMOTRON
                </span>
              </div>

              <div className="intelligence-synthesis-card">
                <div className="intelligence-synthesis-head">
                  <span className="intelligence-nemotron-badge">
                    <Sparkles size={12} />
                    NEMOTRON CONCLUSION
                  </span>

                  {synthesisMatchesFinding && (
                    <span className="intelligence-synthesis-note">
                      Mirrors the Commander findings above
                    </span>
                  )}
                </div>

                <div className="intelligence-synthesis-body">
                  {renderReadingText(synthesisText)}
                </div>
              </div>
            </section>
          )}

          {synthesis.key_insights?.length > 0 && (
            <section className="section">
              <div className="section-heading">
                <div>
                  <h2>Key Insights</h2>
                  <p>Important findings from verified company analytics.</p>
                </div>
              </div>

              <div className="intelligence-insight-grid">
                {synthesis.key_insights.map((item, index) => (
                  <article className="intelligence-insight-card" key={index}>
                    <span className="intelligence-insight-index">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <p>{highlightNumbers(item)}</p>
                  </article>
                ))}
              </div>
            </section>
          )}

          {synthesis.risks?.length > 0 && (
            <section className="section">
              <div className="section-heading">
                <div>
                  <h2>Risks &amp; Limitations</h2>
                  <p>Constraints identified from the verified dataset.</p>
                </div>
              </div>

              <div className="intelligence-limitation-note">
                <AlertTriangle size={15} />
                <span>
                  These limitations describe what the available data can verify,
                  not necessarily problems with the company.
                </span>
              </div>

              <div className="intelligence-limit-grid">
                {synthesis.risks.map((item, index) => (
                  <article className="intelligence-limit-card" key={index}>
                    <span className="intelligence-limit-index">
                      LIMITATION {index + 1}
                    </span>
                    <p>{highlightNumbers(item)}</p>
                  </article>
                ))}
              </div>
            </section>
          )}

          {recommendations.length > 0 && (
            <section className="section">
              <div className="section-heading">
                <div>
                  <h2>Recommended Actions</h2>
                  <p>
                    Actions returned by the Commander intelligence workflow.
                  </p>
                </div>
              </div>

              <div className="intelligence-action-grid">
                {recommendations.map((item, index) => (
                  <article className="intelligence-action-card" key={index}>
                    <div className="intelligence-action-head">
                      <span className="intelligence-action-index">
                        ACTION {index + 1}
                      </span>

                      <span className="intelligence-approval-pill">
                        <ShieldCheck size={12} />
                        APPROVAL CANDIDATE
                      </span>
                    </div>

                    <p className="intelligence-action-title">
                      {typeof item === "string"
                        ? item
                        : JSON.stringify(item)}
                    </p>

                    <p className="intelligence-action-note">
                      Requires human approval before any consequential execution.
                    </p>
                  </article>
                ))}
              </div>
            </section>
          )}

          {Object.keys(analysisMetrics).length > 0 && (
            <section className="section intelligence-evidence-section">
              <div className="section-heading">
                <div>
                  <h2>Verified Company Evidence</h2>
                  <p>
                    Deterministic analytics underlying the intelligence
                    response.
                  </p>
                </div>

                <span className="verified">
                  <CheckCircle2 size={14} />
                  VERIFIED DATA
                </span>
              </div>

              <div className="metric-grid">
                <MetricCard
                  label="NET SALES"
                  value={
                    analysisMetrics.net_sales != null
                      ? `$${Number(
                          analysisMetrics.net_sales
                        ).toLocaleString("en-US", {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}`
                      : "?"
                  }
                />

                <MetricCard
                  label="ORDERS"
                  value={
                    analysisMetrics.orders != null
                      ? Number(
                          analysisMetrics.orders
                        ).toLocaleString("en-US")
                      : "?"
                  }
                />

                <MetricCard
                  label="DATASET ROWS"
                  value={
                    companyAnalysis.rows != null
                      ? Number(companyAnalysis.rows).toLocaleString("en-US")
                      : "?"
                  }
                />

                <MetricCard
                  label="PRODUCTS"
                  value={
                    analysisBreakdowns.products?.length != null
                      ? Number(
                          analysisBreakdowns.products.length
                        ).toLocaleString("en-US")
                      : "?"
                  }
                />

                {analysisMetrics.average_order_value != null && (
                  <MetricCard
                    label="AOV"
                    value={`$${Number(
                      analysisMetrics.average_order_value
                    ).toLocaleString("en-US", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}`}
                  />
                )}

                {analysisMetrics.total_units != null && (
                  <MetricCard
                    label="UNITS"
                    value={Number(
                      analysisMetrics.total_units
                    ).toLocaleString("en-US")}
                  />
                )}
              </div>
            </section>
          )}
        </>
      )}

      <section className="section intelligence-past">
        <div className="section-heading">
          <div>
            <h2>Past Questions</h2>
            <p>
              Previous business questions investigated by the intelligence
              layer.
            </p>
          </div>

          {!questionsLoading && savedQuestions.length > 0 && (
            <span className="verified">
              <Clock3 size={14} />
              {savedQuestions.length} SAVED
            </span>
          )}
        </div>

        {questionsLoading ? (
          <div className="intelligence-past-status">Loading past questions...</div>
        ) : questionsError ? (
          <div className="intelligence-past-status error">{questionsError}</div>
        ) : savedQuestions.length === 0 ? (
          <div className="intelligence-past-empty">
            <strong>No past questions yet</strong>
            <span>
              Run an AI investigation and your questions will appear here.
            </span>
          </div>
        ) : (
          <div className="intelligence-past-list">
            {savedQuestions.map((item) => (
              <div
                className="intelligence-past-item"
                key={item.id ?? item.displayQuestion}
              >
                <button
                  type="button"
                  className="intelligence-past-open"
                  onClick={() => {
                    setQuery(item.displayQuestion || item.question || "");
                    setError("");
                  }}
                >
                  <span className="intelligence-past-text">
                    {item.displayQuestion}
                  </span>

                  <span className="intelligence-past-meta">
                    <Clock3 size={12} />
                    {relativeTime(item.created_at)}
                  </span>
                </button>

                <button
                  type="button"
                  className="intelligence-past-delete"
                  onClick={() => openDeleteQuestion(item)}
                  aria-label={`Delete question: ${item.displayQuestion}`}
                  title="Delete question"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {pendingDelete && (
        <div className="reset-modal-overlay">
          <div
            className="reset-modal reset-modal--question"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-question-title"
          >
            <div className="reset-modal-icon">
              <Trash2 size={20} />
            </div>

            <h3 id="delete-question-title">Delete this question?</h3>
            <p>
              This will remove this question from Past Questions. It will not
              affect your company dataset or workspace.
            </p>

            {pendingDelete.question && (
              <p className="delete-question-preview">
                {pendingDelete.question}
              </p>
            )}

            {deleteError && (
              <div className="delete-question-error">{deleteError}</div>
            )}

            <div className="reset-modal-actions">
              <button
                className="reset-cancel-btn"
                onClick={() => setPendingDelete(null)}
                disabled={deleting}
              >
                Cancel
              </button>

              <button
                className="reset-confirm-btn"
                onClick={() => deleteQuestion(pendingDelete)}
                disabled={deleting}
              >
                {deleting ? "Deleting..." : "Delete Question"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}


function Agents() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadAgents() {
      try {
        setLoading(true);

        const response = await fetch(`${API_URL}/api/agents`);

        if (!response.ok) {
          throw new Error(`API returned ${response.status}`);
        }

        const data = await response.json();

        if (data.status !== "success") {
          throw new Error("Agent API returned an unsuccessful response.");
        }

        setAgents(data.agents || []);
        setError("");
      } catch (err) {
        console.error("Failed to load agents:", err);
        setError("Unable to connect to the Python backend.");
      } finally {
        setLoading(false);
      }
    }

    loadAgents();
  }, []);

  return (
    <>
      <section className="page-header">
        <div>
          <div className="eyebrow">AGENTS</div>
          <h1>Agent network</h1>
          <p>
            The complete AI Company OS intelligence network, including
            specialist capabilities and current participation.
          </p>
        </div>

        <div className="live-pill">
          <span className="status-dot" />
          {loading ? "CONNECTING" : error ? "OFFLINE" : "AGENT NETWORK ONLINE"}
        </div>
      </section>

      {error && (
        <div className="api-error">
          {error}
          <span>Make sure FastAPI is running on port 8000.</span>
        </div>
      )}

      <section className="section">
        <div className="section-heading">
          <div>
            <h2>Intelligence Network</h2>
            <p>
              Commander coordinates the specialist network while Nemotron
              provides executive synthesis.
            </p>
          </div>

          <span className="verified">
            <Network size={14} />
            {agents.length} AGENTS
          </span>
        </div>

        <div className="agent-grid">
          {agents.map((agent) => (
            <div className="module-card" key={agent.key}>
              <div className="module-card-header">
                <div>
                  <div className="eyebrow">{agent.role}</div>
                  <h3>{agent.name}</h3>
                </div>

                <span className="verified">
                  <CheckCircle2 size={14} />
                  {agent.badge}
                </span>
              </div>

              <p>{agent.capability}</p>

              <div className="agent-meta">
                <span>
                  STATUS: <strong>{agent.status.toUpperCase()}</strong>
                </span>

                {agent.last_run && (
                  <span>
                    LAST RUN: {new Date(agent.last_run).toLocaleString()}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {!loading && agents.length === 0 && !error && (
        <section className="section">
          <div className="module-card">
            <h3>No agents returned</h3>
            <p>The backend returned an empty agent network.</p>
          </div>
        </section>
      )}
    </>
  );
}
function Approvals() {
  const [decision, setDecision] = useState("pending");
  const [company, setCompany] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");

      const [companyResult, historyResult] = await Promise.allSettled([
        apiRequest(`${API_URL}/api/company`).then((r) => r.json()),
        apiRequest(`${API_URL}/api/history`).then((r) => r.json()),
      ]);

      if (companyResult.status === "fulfilled") {
        setCompany(companyResult.value);
      } else {
        setError("Unable to load the company workspace context.");
      }

      if (historyResult.status === "fulfilled") {
        setEvents(historyResult.value.events || []);
      }

      setLoading(false);
    }

    load();
  }, []);

  const metrics = company?.metrics || {};
  const active = Boolean(company?.active);
  const limitations = company?.limitations || [];
  const latest = events[0] || null;
  const recommendation = latest?.recommendations?.[0] || null;
  const summary = latest?.executive_summary || "";

  const money = (value) =>
    value != null
      ? `$${Number(value).toLocaleString("en-US", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })}`
      : null;

  const number = (value) =>
    value != null ? Number(value).toLocaleString("en-US") : null;

  const reasoning = [];

  if (metrics.net_sales != null) {
    reasoning.push(`Net sales currently total ${money(metrics.net_sales)}.`);
  } else {
    reasoning.push("Net sales are not available from the current dataset.");
  }

  if (metrics.orders != null) {
    reasoning.push(`The dataset contains ${number(metrics.orders)} orders.`);
  }

  if (metrics.units != null) {
    reasoning.push(`Verified unit volume is ${number(metrics.units)}.`);
  } else {
    reasoning.push("Unit volume is not available from the current dataset.");
  }

  if (metrics.profit != null) {
    reasoning.push(`Verified profit is ${money(metrics.profit)}.`);
  } else {
    reasoning.push(
      "Profit and expense fields are unavailable, so ROI and margin cannot be verified."
    );
  }

  return (
    <>
      <section className="page-header">
        <div>
          <div className="eyebrow">GOVERNANCE</div>
          <h1>Decision &amp; Approval Center</h1>
          <p>
            Human oversight for AI-generated business recommendations before
            consequential actions are taken.
          </p>
        </div>

        <div className="live-pill">
          <span className="status-dot" />
          {loading ? "LOADING CONTEXT" : active ? "HUMAN APPROVAL GATE" : "NO WORKSPACE"}
        </div>
      </section>

      {error && <div className="error-banner">{error}</div>}

      <section className="section">
        <div className="section-heading">
          <div>
            <h2>Pending AI Recommendation</h2>
            <p>
              Review the evidence and reasoning before approving an AI-generated
              business action.
            </p>
          </div>

          <span className="verified">
            <ShieldCheck size={14} />
            {recommendation
              ? decision === "pending"
                ? "REVIEW REQUIRED"
                : decision.toUpperCase()
              : "AWAITING INVESTIGATION"}
          </span>
        </div>

        <div className="approval-layout">
          <div className="module-card approval-main-card">
            {recommendation ? (
              <>
                <div className="approval-card-top">
                  <div>
                    <div className="eyebrow">NEMOTRON RECOMMENDATION</div>
                    <h3>{recommendation}</h3>
                  </div>

                  <span className="risk-badge">EVIDENCE BASED</span>
                </div>

                {summary && <p className="approval-description">{summary}</p>}

                <div className="approval-reasoning">
                  <div className="eyebrow">WHY THIS RECOMMENDATION?</div>

                  <ul>
                    {reasoning.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                </div>

                <div className="approval-actions">
                  {decision === "pending" ? (
                    <>
                      <button
                        className="primary-action"
                        onClick={() => setDecision("approved")}
                      >
                        <CheckCircle2 size={17} />
                        Approve Recommendation
                      </button>

                      <button
                        className="secondary-action"
                        onClick={() => setDecision("rejected")}
                      >
                        <X size={17} />
                        Reject
                      </button>
                    </>
                  ) : (
                    <div className={`decision-result ${decision}`}>
                      {decision === "approved" ? (
                        <CheckCircle2 size={18} />
                      ) : (
                        <X size={18} />
                      )}

                      <div>
                        <strong>Recommendation {decision}</strong>
                        <span>Human decision recorded for this session.</span>
                      </div>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="approval-empty">
                <ShieldCheck size={22} />
                <h3>No pending AI recommendation</h3>
                <p>
                  Run an investigation from Intelligence. Recommendations
                  grounded in the company workspace dataset will appear here
                  for human approval.
                </p>
              </div>
            )}
          </div>

          <div className="approval-side">
            <div className="module-card">
              <div className="eyebrow">DECISION CONTEXT</div>

              <div className="context-row">
                <span>Source</span>
                <strong>{latest ? "AI Investigation" : "Company Workspace"}</strong>
              </div>

              <div className="context-row">
                <span>Company</span>
                <strong>{active ? (company?.company || "LIVE") : "OFFLINE"}</strong>
              </div>

              <div className="context-row">
                <span>Dataset</span>
                <strong>{company?.dataset ? "CONNECTED" : "NONE"}</strong>
              </div>

              <div className="context-row">
                <span>Evidence</span>
                <strong>{active ? "VERIFIED" : "UNAVAILABLE"}</strong>
              </div>
            </div>

            {limitations.length > 0 && (
              <div className="module-card">
                <div className="eyebrow">DATA LIMITATIONS</div>
                <h3>Not verifiable from dataset</h3>
                <ul className="approval-limitations">
                  {limitations.slice(0, 4).map((item, index) => (
                    <li key={index}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="module-card">
              <div className="eyebrow">GOVERNANCE POLICY</div>

              <h3>Human-in-the-loop</h3>

              <p>
                AI systems can investigate and recommend actions, but a human
                remains responsible for approving consequential decisions.
              </p>

              <div className="governance-flow">
                <span>AI analysis</span>
                <span>→</span>
                <span>Human review</span>
                <span>→</span>
                <span>Decision</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="section-heading">
          <div>
            <h2>Audit Trail</h2>
            <p>
              Decisions remain associated with the recommendation that
              generated them.
            </p>
          </div>
        </div>

        <div className="audit-card">
          <div className="audit-icon">
            <ShieldCheck size={18} />
          </div>

          <div>
            <strong>
              {recommendation || "AI recommendation awaiting human decision"}
            </strong>
            <p>
              {recommendation
                ? "Generated by Nemotron · Evidence verified from the company workspace"
                : "No recommendation has been generated yet"}
            </p>
          </div>

          <span className="audit-status">
            {recommendation
              ? decision === "pending"
                ? "PENDING"
                : decision.toUpperCase()
              : "NONE"}
          </span>
        </div>
      </section>
    </>
  );
}


function History() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showResetConfirm, setShowResetConfirm] = useState(false);

  useEffect(() => {
    async function loadHistory() {
      try {
        setLoading(true);

        const response = await fetch(`${API_URL}/api/history`);

        if (!response.ok) {
          throw new Error(`API returned ${response.status}`);
        }

        const data = await response.json();

        if (data.status !== "success") {
          throw new Error(data.message || "History API failed.");
        }

        setEvents(data.events || []);
        setError("");
      } catch (err) {
        console.error("Failed to load history:", err);
        setError("Unable to load decision history from the Python backend.");
      } finally {
        setLoading(false);
      }
    }

    loadHistory();
  }, []);

  const resetHistory = async () => {

    try {
      const response = await fetch(`${API_URL}/api/history`, {
        method: "DELETE",
      });
      const data = await response.json();

      if (data.status !== "success") {
        throw new Error(data.message || "Reset failed.");
      }

      setEvents([]);
      setError("");
    } catch (err) {
      console.error("Failed to reset history:", err);
      setError("Unable to reset decision history.");
    }
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return "Unknown time";

    const date = new Date(timestamp);

    if (Number.isNaN(date.getTime())) {
      return timestamp;
    }

    return date.toLocaleString();
  };

  return (
    <>
      <section className="page-header">
        <div>
          <div className="eyebrow">AUDIT TRAIL</div>
          <h1>Decision History</h1>
          <p>
            A traceable record of investigations, AI recommendations, and
            human decisions across the AI Company OS.
          </p>
        </div>

        <div className="live-pill">
          <span className="status-dot" />
          {loading ? "LOADING HISTORY" : "AUDIT TRAIL ONLINE"}
        </div>
      </section>

      {error && (
        <div className="api-error">
          {error}
          <span>Make sure FastAPI is running on port 8000.</span>
        </div>
      )}

      <section className="section">
        <div className="section-heading">
          <div>
            <h2>Recent Activity</h2>
            <p>
              Follow how intelligence moved from analysis to an executive
              decision.
            </p>
          </div>

          <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
            <span className="verified">
              <Clock3 size={14} />
              {events.length} EVENTS
            </span>
            <button
              className="reset-history-btn"
              type="button"
              onClick={() => setShowResetConfirm(true)}
            >
              Reset History
            </button>
          </div>
        </div>

      {showResetConfirm && (
        <div className="reset-modal-overlay">
          <div className="reset-modal">
            <div className="reset-modal-icon">?</div>
            <h3>Reset decision history?</h3>
            <p>
              This will permanently remove all saved investigations,
              approvals, and action history.
            </p>
            <div className="reset-modal-actions">
              <button
                className="reset-cancel-btn"
                onClick={() => setShowResetConfirm(false)}
              >
                Cancel
              </button>
              <button
                className="reset-confirm-btn"
                onClick={async () => {
                  setShowResetConfirm(false);
                  await resetHistory();
                }}
              >
                Reset History
              </button>
            </div>
          </div>
        </div>
      )}

        {loading ? (
          <div className="module-card">
            <p>Loading persisted decision history...</p>
          </div>
        ) : events.length === 0 ? (
          <div className="module-card">
            <h3>No decision history yet</h3>
            <p>
              Run an AI investigation from Intelligence and completed
              investigations will appear here automatically.
            </p>
          </div>
        ) : (
          <div className="history-list">
            {events.map((item, index) => {
              const recommendation =
                item.recommendations?.[0] || "No recommendation recorded.";

              return (
                <div
                  className="history-item"
                  key={item.id || item.task_id || index}
                >
                  <div className="history-marker">
                    <span />
                    {index < events.length - 1 && (
                      <div className="history-line" />
                    )}
                  </div>

                  <div className="history-card">
                    <div className="history-card-top">
                      <div>
                        <div className="eyebrow">AI INVESTIGATION</div>
                        <h3>
                          {item.query || "Business investigation"}
                        </h3>
                      </div>

                      <span className="history-status">
                        COMPLETED
                      </span>
                    </div>

                    <p>
                      {item.executive_summary ||
                        `Investigation completed with recommendation: ${recommendation}`}
                    </p>

                    <div className="history-meta">
                      <span>
                        {item.model || "NVIDIA NEMOTRON"}
                      </span>
                      <span>
                        {item.task_id || "NO TASK ID"}
                      </span>
                      <span>
                        {formatTime(item.timestamp)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section className="section">
        <div className="section-heading">
          <div>
            <h2>AI Decision Chain</h2>
            <p>
              Every business decision follows a controlled intelligence
              pipeline.
            </p>
          </div>
        </div>

        <div className="decision-chain">
          <div className="chain-step">
            <div className="chain-number">01</div>
            <div>
              <strong>Investigation</strong>
              <span>Business question enters the OS.</span>
            </div>
          </div>

          <div className="chain-arrow">?</div>

          <div className="chain-step">
            <div className="chain-number">02</div>
            <div>
              <strong>Specialist Agents</strong>
              <span>Evidence is analyzed deterministically.</span>
            </div>
          </div>

          <div className="chain-arrow">?</div>

          <div className="chain-step">
            <div className="chain-number">03</div>
            <div>
              <strong>Nemotron</strong>
              <span>Evidence becomes an executive brief.</span>
            </div>
          </div>

          <div className="chain-arrow">?</div>

          <div className="chain-step">
            <div className="chain-number">04</div>
            <div>
              <strong>Human Approval</strong>
              <span>Consequential actions require review.</span>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

function PlaceholderPage({ title }) {
  return (
    <section className="placeholder-page">
      <div className="eyebrow">{title.toUpperCase()}</div>
      <h1>{title}</h1>
      <p>
        This module is connected to the React shell. The existing Python
        backend will be connected next.
      </p>
    </section>
  );
}

export default App;
