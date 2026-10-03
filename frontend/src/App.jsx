import { useEffect, useMemo, useState } from "react";
import { Pie } from "react-chartjs-2";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from "chart.js";
import "./App.css";

ChartJS.register(ArcElement, Tooltip, Legend);

const API_BASE = import.meta.env.VITE_API_BASE_URL;


const REMEDIATION_BY_COLUMN = {
  customer_name: "Remove or mask the customer's full name.",
  email: "Remove or mask the personal email address.",
  phone: "Remove or mask the phone number.",
  address: "Remove or generalize the postal/home address.",
  dob: "Remove or generalize the date of birth.",
  gender: "Remove or generalize gender information where required.",
  passport_number: "Remove the passport number completely.",
  ni_number: "Remove the National Insurance number completely.",
  credit_card_number: "Remove or mask the payment card number.",
  bank_account: "Remove or mask the bank account number.",
  medical_condition: "Remove the medical information.",
  ethnicity: "Remove the ethnicity information.",
  religion: "Remove the religion or belief information.",
  political_view: "Remove the political opinion information.",
  employee_id: "Remove or mask the employee identifier.",
  department: "Remove or generalize the department when it contributes to identification.",
  job_role: "Remove or generalize the job role when it contributes to identification.",
  customer_id: "Remove or mask the customer identifier.",
  ip_address: "Remove or mask the IP address.",
};


const getRuleColumns = (rule) => {
  if (!rule || typeof rule !== "object") {
    return [];
  }

  const directColumns = Array.isArray(rule.columns)
    ? rule.columns
        .map((column) => String(column || "").trim())
        .filter(Boolean)
    : [];

  if (directColumns.length > 0) {
    return [...new Set(directColumns)];
  }

  const discoveredColumns = [];

  const collectConditionColumns = (condition) => {
    if (!condition || typeof condition !== "object") {
      return;
    }

    const fields = Array.isArray(condition.fields)
      ? condition.fields
      : [];

    fields.forEach((field) => {
      if (!field || typeof field !== "object") {
        return;
      }

      const column = String(
        field.column || ""
      ).trim();

      if (column) {
        discoveredColumns.push(column);
      }

      collectConditionColumns(
        field.condition
      );
    });
  };

  collectConditionColumns(
    rule.condition
  );

  return [
    ...new Set(
      discoveredColumns
    ),
  ];
};

const normalizeRuleId = (ruleId, category = "") => {
  const value = String(ruleId || "").trim().toUpperCase();
  const categoryValue = String(category || "").trim().toUpperCase();

  if (!value) return "";

  if (
    categoryValue &&
    value.startsWith(`${categoryValue}-${categoryValue}-`)
  ) {
    return value.slice(categoryValue.length + 1);
  }

  return value;
};

function App() {
  // ==========================================
  // PAGE
  // ==========================================

  const [page, setPage] = useState("upload");

  // ==========================================
  // UPLOAD PAGE
  // ==========================================

  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStep, setUploadStep] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [syntheticDataReady, setSyntheticDataReady] = useState(false);

  // ==========================================
  // DASHBOARD
  // ==========================================

  const [dashboardData, setDashboardData] = useState(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState("");

  const [currentRun, setCurrentRun] = useState(null);
  const [runs, setRuns] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);

  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");
  const [selectedId, setSelectedId] = useState(null);

  const [showDefinitions, setShowDefinitions] = useState(false);

  // ==========================================
  // FILE SELECTION
  // ==========================================

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];

    if (!selectedFile) return;

    if (selectedFile.type !== "application/pdf") {
      alert("Please select a PDF file.");
      return;
    }

    setFile(selectedFile);
  };

  // ==========================================
  // UPLOAD POLICY
  // ==========================================

const handleUpload = async () => {
    if (!file) {
      alert("Please select a PDF first.");
      return;
    }

    // A new upload starts a new evaluation.
    setCurrentRun(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      setIsUploading(true);
      setUploadProgress(5);
      setUploadStep("Uploading policy...");

      const response = await fetch(
        `${API_BASE}/upload-policy`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error("Upload failed.");
      }

      const result = await response.json();

      console.log("Policy upload response:", result);

      if (!result.success || !result.job_id) {
        throw new Error(
          result.message ||
            "Policy processing could not be started."
        );
      }

      const jobId = result.job_id;

      setUploadProgress(5);
      setUploadStep("Policy upload complete. Starting processing...");

      let completed = false;

      while (!completed) {
        await new Promise(
          (resolve) => setTimeout(resolve, 1000)
        );

        const statusResponse = await fetch(
          `${API_BASE}/upload-status/${jobId}`
        );

        if (!statusResponse.ok) {
          throw new Error(
            "Failed to check policy processing status."
          );
        }

        const statusResult = await statusResponse.json();

        console.log("Policy processing status:", statusResult);

        if (typeof statusResult.progress === "number") {
          setUploadProgress(statusResult.progress);
        }

        if (statusResult.current_step) {
          setUploadStep(statusResult.current_step);
        } else if (statusResult.message) {
          setUploadStep(statusResult.message);
        }

        if (statusResult.status === "completed") {
          completed = true;
          setUploadProgress(100);
          setUploadStep("Processing complete. Loading dashboard...");

          setPage("dashboard");
          await loadDashboard();
        } else if (statusResult.status === "failed") {
          throw new Error(
            statusResult.message ||
              "Policy processing failed."
          );
        }
      }
    } catch (error) {
      console.error("Upload error:", error);

      setUploadStep("");

      alert(
        error.message ||
          "Failed to upload the PDF."
      );
    } finally {
      setIsUploading(false);
    }
  };


  // ==========================================
  // GENERATE SYNTHETIC DATA
  // ==========================================

  const handleGenerateData = async () => {
  try {
    setIsGenerating(true);

    const response = await fetch(
      `${API_BASE}/generate-data`,
      {
        method: "POST",
      }
    );

    if (!response.ok) {
      throw new Error(
        "Synthetic data generation failed."
      );
    }

    const result = await response.json();

    console.log(
      "Synthetic data response:",
      result
    );

    if (!result.success) {
      throw new Error(
        result.message ||
          "Synthetic data generation failed."
      );
    }

    setSyntheticDataReady(true);

    alert(
      `Synthetic dataset generated successfully: ${result.records} records`
    );
  } catch (error) {
    console.error(
      "Synthetic data generation error:",
      error
    );

    alert(
      error.message ||
        "Failed to generate synthetic data."
    );
  } finally {
    setIsGenerating(false);
  }
};

  const handleDownloadSyntheticData = () => {
    window.open(
      `${API_BASE}/download-synthetic-data`,
      "_blank"
    );
  };

  // Upload-page workflow downloads:
  // use the selected historical run when one is open,
  // otherwise use the current generated files.
  const getWorkflowArtifactUrl = (artifactName, currentEndpoint) => {
    if (currentRun?.id) {
      return `${API_BASE}/api/runs/${currentRun.id}/artifact/${artifactName}`;
    }

    return `${API_BASE}${currentEndpoint}`;
  };

  const handleDownloadPolicyText = () => {
    window.open(
      getWorkflowArtifactUrl(
        "policy_text",
        "/download-policy-text"
      ),
      "_blank"
    );
  };

  const handleDownloadRulesExcel = () => {
    window.open(
      getWorkflowArtifactUrl(
        "rules_excel",
        "/download-rules-excel"
      ),
      "_blank"
    );
  };

  const handleDownloadResultsExcel = () => {
    window.open(
      getWorkflowArtifactUrl(
        "results_excel",
        "/download-results-excel"
      ),
      "_blank"
    );
  };

  const handleDownloadRegoExcel = () => {
    window.open(
      getWorkflowArtifactUrl(
        "policy_excel",
        "/download-policy-results-excel"
      ),
      "_blank"
    );
  };

  const handleDownloadDashboardSummaryExcel = () => {
    window.open(
      getWorkflowArtifactUrl(
        "dashboard_summary_excel",
        "/download-dashboard-summary-excel"
      ),
      "_blank"
    );
  };

  // Dashboard downloads use the selected run's stored artifacts.
  const handleDownloadPolicyPdf = () => {
    if (!currentRun?.id) {
      alert("No evaluation run selected.");
      return;
    }

    window.open(
      `${API_BASE}/api/runs/${currentRun.id}/artifact/policy_pdf`,
      "_blank"
    );
  };

  const handleDownloadPolicyResultsExcel = () => {
    if (!currentRun?.id) {
      alert("No evaluation run selected.");
      return;
    }

    window.open(
      `${API_BASE}/api/runs/${currentRun.id}/artifact/policy_excel`,
      "_blank"
    );
  };


  // ==========================================
  // LOAD DASHBOARD
  // ==========================================

  const loadRun = async (runId) => {
    try {
      setDashboardLoading(true);
      setDashboardError("");

      const response = await fetch(
        `${API_BASE}/api/runs/${runId}`
      );

      if (!response.ok) {
        throw new Error(
          "Failed to load the selected evaluation run."
        );
      }

      const run = await response.json();

      if (run.success === false) {
        throw new Error(
          run.message ||
            "Failed to load the selected evaluation run."
        );
      }

      const runSummary = {
        total_records: run.total_records || 0,
        pass: run.pass_count || 0,
        flag: run.flag_count || 0,
        block: run.block_count || 0,
        pass_rate: run.total_records
          ? ((run.pass_count / run.total_records) * 100)
          : 0,
      };

      setCurrentRun(run);
      setDashboardData({
        summary: runSummary,
        records: run.records || [],
      });

      const loadedRecords = run.records || [];

      setSelectedId(
        loadedRecords.length > 0
          ? loadedRecords[0].record_id
          : null
      );

      setSearch("");
      setFilter("All");
      setShowHistory(false);
    } catch (error) {
      console.error(
        "Run loading error:",
        error
      );

      setDashboardError(error.message);
    } finally {
      setDashboardLoading(false);
    }
  };

  const loadDashboard = async () => {
    try {
      setDashboardLoading(true);
      setDashboardError("");

      const response = await fetch(
        `${API_BASE}/api/runs`
      );

      if (!response.ok) {
        throw new Error(
          "Failed to load evaluation history."
        );
      }

      const runList = await response.json();

      setRuns(runList);

      if (runList.length === 0) {
        throw new Error(
          "No evaluation runs found in the database."
        );
      }

      await loadRun(runList[0].id);
    } catch (error) {
      console.error(
        "Dashboard error:",
        error
      );

      setDashboardError(error.message);
      setDashboardLoading(false);
    }
  };

  const openHistory = async () => {
    setShowHistory(true);
    setHistoryLoading(true);

    try {
      const response = await fetch(
        `${API_BASE}/api/runs`
      );

      if (!response.ok) {
        throw new Error(
          "Could not load evaluation history."
        );
      }

      const runList = await response.json();
      setRuns(runList);
    } catch (error) {
      console.error(
        "History loading error:",
        error
      );

      setDashboardError(error.message);
    } finally {
      setHistoryLoading(false);
    }
  };

  // ==========================================
  // OPEN DASHBOARD
  // ==========================================

  const handleOpenDashboard = async () => {
    setPage("dashboard");
    await loadDashboard();
  };

  // ==========================================
  // BACK TO UPLOAD
  // ==========================================

  const handleBackToUpload = () => {
    setPage("upload");
  };

  // ==========================================
  // DASHBOARD DATA
  // ==========================================

  const records = dashboardData?.records || [];

  const summary = dashboardData?.summary || {
    total_records: 0,
    pass: 0,
    flag: 0,
    block: 0,
    pass_rate: 0,
  };

  const total = summary.total_records || 0;
  const passed = summary.pass || 0;
  const flagged = summary.flag || 0;
  const blocked = summary.block || 0;

  const passRate = Number(
    summary.pass_rate || 0
  ).toFixed(1);

  // ==========================================
  // SEARCH + FILTER
  // ==========================================

  const filteredData = useMemo(() => {
    let filtered = [...records];

    if (filter !== "All") {
      filtered = filtered.filter(
        (record) =>
          record.outcome === filter
      );
    }

    if (search.trim()) {
      const query =
        search.toLowerCase().trim();

      filtered = filtered.filter(
        (record) => {
          const recordId = String(
            record.record_id || ""
          ).toLowerCase();

          const outcome = String(
            record.outcome || ""
          ).toLowerCase();

          const ruleIds =
            Array.isArray(
              record.triggered_rule_ids
            )
              ? record.triggered_rule_ids
                  .join(" ")
                  .toLowerCase()
              : "";

          const descriptions =
            Array.isArray(
              record.triggered_rules
            )
              ? record.triggered_rules
                  .map(
                    (rule) =>
                      rule.description || ""
                  )
                  .join(" ")
                  .toLowerCase()
              : "";

          return (
            recordId.includes(query) ||
            outcome.includes(query) ||
            ruleIds.includes(query) ||
            descriptions.includes(query)
          );
        }
      );
    }

    return filtered;
  }, [records, filter, search]);

  // ==========================================
  // SELECTED RECORD
  // ==========================================

  const selectedRecord = useMemo(() => {
    return records.find(
      (record) =>
        String(record.record_id) ===
        String(selectedId)
    );
  }, [records, selectedId]);

  // ==========================================
  // CHART
  // ==========================================

  const pieData = {
    labels: [
      "PASS",
      "FLAG",
      "BLOCK",
    ],
    datasets: [
      {
        data: [
          passed,
          flagged,
          blocked,
        ],
        backgroundColor: [
          "#22c55e",
          "#f59e0b",
          "#ef4444",
        ],
        borderWidth: 0,
      },
    ],
  };

  const pieOptions = {
    responsive: true,
    maintainAspectRatio: false,

    plugins: {
      legend: {
        position: "bottom",

        labels: {
          padding: 20,
        },
      },

      tooltip: {
        callbacks: {
          label: function (context) {
            const chartTotal =
              context.dataset.data.reduce(
                (sum, value) =>
                  sum + value,
                0
              );

            const percentage =
              chartTotal
                ? (
                    (context.raw /
                      chartTotal) *
                    100
                  ).toFixed(1)
                : 0;

            return `${context.label}: ${percentage}%`;
          },
        },
      },
    },
  };

  // ==========================================
  // HELPERS
  // ==========================================

  const getOutcomeClass = (
    outcome
  ) => {
    if (outcome === "PASS") {
      return "pass";
    }

    if (outcome === "FLAG") {
      return "flag";
    }

    return "block";
  };

  const getIcon = (outcome) => {
    if (outcome === "PASS") {
      return "✓";
    }

    if (outcome === "FLAG") {
      return "⚠";
    }

    return "✕";
  };

  const formatFieldName = (
    field
  ) => {
    return field
      .replaceAll("_", " ")
      .replace(
        /\b\w/g,
        (letter) =>
          letter.toUpperCase()
      );
  };

  const getRecordNumber = (
    recordId
  ) => {
    return String(recordId).padStart(
      4,
      "0"
    );
  };

  const getWorkflowStatus = (step) => {
    if (step === "synthetic") {
      return syntheticDataReady || currentRun?.id
        ? "completed"
        : "pending";
    }

    if (currentRun?.id && !isUploading) {
      return "completed";
    }

    if (!isUploading && uploadProgress === 0) {
      return "pending";
    }

    const thresholds = {
      ingestion: 15,
      rules: 42,
      rego: 62,
      opa: 88,
      dashboard: 100,
    };

    if (uploadProgress >= thresholds[step]) {
      return "completed";
    }

    if (step === "ingestion" && uploadProgress > 0) {
      return "processing";
    }

    if (step === "rules" && uploadProgress >= 20) {
      return "processing";
    }

    if (step === "rego" && uploadProgress >= 50) {
      return "processing";
    }

    if (step === "opa" && uploadProgress >= 70) {
      return "processing";
    }

    if (step === "dashboard" && uploadProgress >= 88) {
      return "processing";
    }

    return "pending";
  };

  const workflowSteps = [
    {
      key: "synthetic",
      number: 1,
      title: "Generate Synthetic Data",
      description: "Create the fixed 250-record evaluation dataset.",
      downloadLabel: "Download Excel",
      download: handleDownloadSyntheticData,
    },
  {
      key: "ingestion",
      number: 2,
      title: "PDF Ingestion & Text Extraction",
      description: "Read the uploaded policy PDF page by page and extract text.",
      downloadLabel: "Download TXT",
  download: handleDownloadPolicyText,
    },
    {
      key: "rules",
      number: 3,
      title: "Rule Extraction & Validation",
      description: "Extract and validate only PII, SPII and CPII rules.",
      downloadLabel: "Download Excel",
      download: handleDownloadRulesExcel,
    },
    {
      key: "rego",
      number: 4,
      title: "Rego Policy Generation",
      description: "Convert the validated rules into the executable Rego policy.",
      downloadLabel: "Download Excel",
      download: handleDownloadRegoExcel,
    },
    {
      key: "opa",
      number: 5,
      title: "OPA Evaluation",
      description: "Evaluate all synthetic records against the generated policy.",
      downloadLabel: "Download Excel",
      download: handleDownloadResultsExcel
    },
    {
      key: "dashboard",
      number: 6,
      title: "Results & Dashboard",
      description: "Store the run and present PASS, FLAG and BLOCK results.",
      downloadLabel: "Download Excel",
      download: handleDownloadDashboardSummaryExcel,
    },
  ];

  const workflowStatusLabel = {
    pending: "Pending",
    processing: "In Progress",
    completed: "Completed",
  };

  const workflowStatusStyle = {
    pending: {
      background: "#f8fafc",
      border: "#cbd5e1",
      color: "#64748b",
    },
    processing: {
      background: "#eff6ff",
      border: "#93c5fd",
      color: "#2563eb",
    },
    completed: {
      background: "#f0fdf4",
      border: "#86efac",
      color: "#16a34a",
    },
  };

  const workflowDownloadReady = (status) =>
    status === "completed";

  // ==========================================
  // PAGE 1 — UPLOAD
  // ==========================================

  if (page === "upload") {
    return (
      <div className="upload-page">

        <div className="upload-card">

          <h1>
            Policy as Code
          </h1>

          <p className="upload-subtitle">
            Upload your policy document
            to begin
          </p>


          {/* PDF DROP AREA */}

          <label className="drop-zone">

            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={
                handleFileChange
              }
            />

            <div className="upload-icon">
              ↑
            </div>

            <h2>
              {file
                ? file.name
                : "Upload Policy PDF"}
            </h2>

            <p>
              {file
                ? "PDF selected"
                : "Click here to select your policy document"}
            </p>

          </label>


          {/* SELECTED FILE */}

          {file && (
            <div className="file-info">

              <span>
                Selected file
              </span>

              <strong>
                {file.name}
              </strong>

            </div>
          )}


          {/* UPLOAD */}

          <button
            className="upload-button"
            onClick={
              handleUpload
            }
            disabled={isUploading}
          >

            {isUploading
              ? `Processing... ${uploadProgress}%`
              : "Upload Policy"}

          </button>

          {isUploading && (
            <div
              style={{
                width: "100%",
                marginTop: "12px",
              }}
            >
              <div
                style={{
                  width: "100%",
                  height: "8px",
                  background: "#e5e7eb",
                  borderRadius: "999px",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${uploadProgress}%`,
                    height: "100%",
                    background: "#2563eb",
                    borderRadius: "999px",
                    transition: "width 0.3s ease",
                  }}
                />
              </div>

              <div
                style={{
                  marginTop: "8px",
                  textAlign: "center",
                  fontSize: "13px",
                  color: "#64748b",
                }}
              >
                {uploadStep || "Processing policy..."}
              </div>
            </div>
          )}


{/* GENERATE DATA */}

<div
  style={{
    display: "flex",
    gap: "10px",
    width: "100%",
  }}
>
  <button
    className="generate-button"
    onClick={handleGenerateData}
    disabled={isGenerating}
    style={{ flex: 1 }}
  >
    {isGenerating
      ? "Generating..."
      : "Generate Synthetic Data"}
  </button>

  <button
    className="generate-button"
    onClick={handleDownloadSyntheticData}
    style={{ flex: 1 }}
  >
    Download Synthetic Data
  </button>
</div>


          {/* WORKFLOW */}

          <section className="workflow-section">

            <div className="workflow-heading">

              <h3>
                Policy Evaluation Workflow
              </h3>

              <p>
                Follow each processing stage and download its output.
              </p>

            </div>

            <div className="workflow-scroll">

              <div className="workflow-track">

                {workflowSteps.map((step, index) => {
                  const status = getWorkflowStatus(step.key);
                  const statusColors = workflowStatusStyle[status];
                  const isDownloadReady =
                    workflowDownloadReady(status);

                  return (
                    <div
                      key={step.key}
                      className="workflow-step-item"
                    >

                      <div
                        className="workflow-card"
                        style={{
                          borderColor: statusColors.border,
                          background: statusColors.background,
                        }}
                      >

                        <div className="workflow-card-top">

                          <div
                            className="workflow-number"
                            style={{
                              borderColor: statusColors.border,
                              color: statusColors.color,
                            }}
                          >
                            {status === "completed"
                              ? "✓"
                              : step.number}
                          </div>

                          <span
                            className="workflow-status"
                            style={{
                              color: statusColors.color,
                            }}
                          >
                            {workflowStatusLabel[status]}
                          </span>

                        </div>

                        <strong className="workflow-title">
                          {step.title}
                        </strong>

                        <p className="workflow-description">
                          {step.description}
                        </p>

                        <button
                          type="button"
                          className="workflow-download"
                          onClick={step.download}
                          disabled={!isDownloadReady}
                        >
                          {isDownloadReady
                            ? step.downloadLabel
                            : "Available after completion"}
                        </button>

                      </div>

                      {index < workflowSteps.length - 1 && (
                        <div
                          className="workflow-connector"
                          style={{
                            background:
                              status === "completed"
                                ? "#86efac"
                                : "#cbd5e1",
                          }}
                        >
                          <span
                            style={{
                              color:
                                status === "completed"
                                  ? "#16a34a"
                                  : "#94a3b8",
                            }}
                          >
                            ›
                          </span>
                        </div>
                      )}

                    </div>
                  );
                })}

              </div>

            </div>

          </section>


          {/* DASHBOARD */}

          <button
            className="dashboard-button"
            onClick={
              handleOpenDashboard
            }
          >
            View Evaluation Dashboard
          </button>


          <p className="supported">
            Supported format: PDF
          </p>

        </div>

      </div>
    );
  }

  // ==========================================
  // DASHBOARD LOADING
  // ==========================================

  if (dashboardLoading) {
    return (
      <div className="loading-page">

        <div className="loading-card">

          <div className="loading-spinner"></div>

          <h2>
            Loading Evaluation Dashboard
          </h2>

          <p>
            Fetching the latest policy
            evaluation results...
          </p>

        </div>

      </div>
    );
  }

  // ==========================================
  // DASHBOARD ERROR
  // ==========================================

  if (dashboardError) {
    return (
      <div className="error-page">

        <div className="error-card">

          <h2>
            Unable to load dashboard
          </h2>

          <p>
            {dashboardError}
          </p>

          <p>
            Make sure the FastAPI
            backend is running on
            <b>
              {" "}
              http://127.0.0.1:8001
            </b>.
          </p>

          <div className="error-buttons">

            <button
              className="retry-button"
              onClick={
                loadDashboard
              }
            >

              Retry
            </button>

            <button
              className="back-upload-button"
              onClick={
                handleBackToUpload
              }
            >
              Back to Upload
            </button>

          </div>

        </div>

      </div>
    );
  }

  // ==========================================
  // DASHBOARD
  // ==========================================

  return (
    <div className="app">

      {/* ======================================
          HEADER
      ====================================== */}

      <header className="header">

        <div>

          <div className="breadcrumb">
            Evaluations / Run #{currentRun.run_number}
          </div>

          <h1>
            Policy Evaluation Results
          </h1>

          <p>
            {total} records evaluated
          </p>

        </div>


        <div className="header-actions">

          <button
            type="button"
            className="header-button"
            onClick={() =>
              setShowDefinitions(true)
            }
          >
            DEFINITIONS
          </button>

          <button
            type="button"
            className="header-button"
            onClick={openHistory}
          >
            EVALUATION HISTORY
          </button>


          <button
            type="button"
            className="header-button"
            onClick={
              handleDownloadPolicyResultsExcel
            }
          >
            POLICY EXCEL
          </button>

          <button
            type="button"
            className="header-button policy-pdf-button"
            onClick={
              handleDownloadPolicyPdf
            }
          >
            POLICY PDF
          </button>



          <button
            type="button"
            className="header-button"
            onClick={
              handleBackToUpload
            }
          >
            UPLOAD PAGE
          </button>

          <div className="run-info">

            <span>
              RUN DATE & TIME
            </span>

            <strong>
              {currentRun
                ? `${new Date(
                    currentRun.run_date
                  ).toLocaleDateString()} ${new Date(
                    currentRun.run_date
                  ).toLocaleTimeString()}`
                : "-"}
            </strong>

          </div>

        </div>

      </header>


      {/* ======================================
          EVALUATION HISTORY
      ====================================== */}

      {showHistory && (
        <div
          className="modal-overlay"
          onClick={() => setShowHistory(false)}
        >
          <div
            className="definitions-modal"
            style={{
              width: "min(760px, 92vw)",
              maxHeight: "90vh",
              overflowY: "auto",
            }}
            onClick={(event) =>
              event.stopPropagation()
            }
          >
            <div className="modal-header">
              <div>
                <div className="modal-label">
                  DATABASE
                </div>

                <h2>
                  Evaluation History
                </h2>
              </div>

              <button
                type="button"
                className="close-button"
                onClick={() =>
                  setShowHistory(false)
                }
                aria-label="Close evaluation history"
              >
                ×
              </button>
            </div>

            {historyLoading ? (
              <p>
                Loading evaluation history...
              </p>
            ) : runs.length === 0 ? (
              <p>
                No evaluation runs found.
              </p>
            ) : (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                }}
              >
                {runs.map((run) => (
                  <button
                    key={run.id}
                    type="button"
                    onClick={() =>
                      loadRun(run.id)
                    }
                    style={{
                      width: "100%",
                      textAlign: "left",
                      border: "1px solid #e1e7ef",
                      background:
                        currentRun &&
                        currentRun.id === run.id
                          ? "#f5f8fc"
                          : "#ffffff",
                      borderRadius: "10px",
                      padding: "16px",
                      cursor: "pointer",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent:
                          "space-between",
                        alignItems: "center",
                        gap: "16px",
                      }}
                    >
                      <div>
                        <strong
                          style={{
                            fontSize: "16px",
                          }}
                        >
                          Run #{run.run_number}
                        </strong>

                        <div
                          style={{
                            marginTop: "5px",
                            fontSize: "13px",
                            color: "#718096",
                          }}
                        >
                          {new Date(
                            run.run_date
                          ).toLocaleDateString()}{" "}
                          {new Date(
                            run.run_date
                          ).toLocaleTimeString()}
                        </div>

                        <div
                          style={{
                            marginTop: "4px",
                            fontSize: "13px",
                            color: "#718096",
                          }}
                        >
                          {run.policy_name ||
                            "Unknown policy"}{" "}
                          ·{" "}
                          {run.dataset_name} ·{" "}
                          {run.total_records} records
                        </div>
                      </div>

                      <div
                        style={{
                          display: "flex",
                          gap: "12px",
                          fontSize: "13px",
                          whiteSpace: "nowrap",
                        }}
                      >
                        <span>
                          ✓ {run.pass_count}
                        </span>

                        <span>
                          ⚠ {run.flag_count}
                        </span>

                        <span>
                          ✕ {run.block_count}
                        </span>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ======================================
          DEFINITIONS MODAL
      ====================================== */}

      {showDefinitions && (
        <div
          className="modal-overlay"
          onClick={() =>
            setShowDefinitions(false)
          }
        >

          <div
            className="definitions-modal"
            onClick={(event) =>
              event.stopPropagation()
            }
          >

            <div className="modal-header">

              <div>

                <div className="modal-label">
                  POLICY REFERENCE
                </div>

                <h2>
                  Data Classification Definitions
                </h2>

              </div>


              <button
                type="button"
                className="close-button"
                onClick={() =>
                  setShowDefinitions(false)
                }
              >
                ×
              </button>

            </div>


            <div className="definitions-list">

              <div className="definition-item">

                <strong>
                  PII — Personally
                  Identifiable Information
                </strong>

                <p>
                  Information that
                  directly identifies a
                  person, such as their
                  name, email, phone
                  number, or address.
                </p>

              </div>


              <div className="definition-item">

                <strong>
                  SPII — Sensitive
                  Personally Identifiable
                  Information
                </strong>

                <p>
                  Sensitive personal
                  information such as
                  health, ethnicity,
                  religion, political
                  opinion, or other
                  sensitive attributes.
                </p>

              </div>


              <div className="definition-item">

                <strong>
                  CPII — Combination
                  Personally Identifiable
                  Information
                </strong>

                <p>
                  Information that can
                  identify a person when
                  multiple attributes are
                  combined, such as name
                  and date of birth or
                  name and address.
                </p>

              </div>

            </div>

          </div>

        </div>
      )}


      {/* ======================================
          OVERVIEW
      ====================================== */}

      <section className="overview">

        <div className="summary-section">

          <div className="summary-grid">

            <div className="summary-card pass-card">

              <span className="card-label">
                ✓ PASS
              </span>

              <strong>
                {passed}
              </strong>

              <small>
                {total
                  ? (
                      (passed /
                        total) *
                      100
                    ).toFixed(1)
                  : 0}
                %
              </small>

            </div>


            <div className="summary-card flag-card">

              <span className="card-label">
                ⚠ FLAG
              </span>

              <strong>
                {flagged}
              </strong>

              <small>
                {total
                  ? (
                      (flagged /
                        total) *
                      100
                    ).toFixed(1)
                  : 0}
                %
              </small>

            </div>


            <div className="summary-card block-card">

              <span className="card-label">
                ✕ BLOCK
              </span>

              <strong>
                {blocked}
              </strong>

              <small>
                {total
                  ? (
                      (blocked /
                        total) *
                      100
                    ).toFixed(1)
                  : 0}
                %
              </small>

            </div>


            <div className="summary-card rate-card">

              <span className="card-label">
                ◔ PASS RATE
              </span>

              <strong>
                {passRate}%
              </strong>

              <small>
                {passed}/{total} passed
              </small>

            </div>

          </div>

        </div>


        <div className="chart-section">

          <h3>
            Outcome Distribution
          </h3>

          <div className="pie-container">

            <Pie
              data={pieData}
              options={pieOptions}
            />

          </div>

        </div>

      </section>


      {/* ======================================
          RECORDS + ANALYSIS
      ====================================== */}

      <section className="main-content">

        {/* RECORDS */}

        <div className="records-panel">

          <div className="panel-header">

            <div>

              <h2>
                Records
              </h2>

              <span>
                {filteredData.length} records shown
              </span>

            </div>

          </div>


          <input
            className="search"
            placeholder="Search records..."
            value={search}
            onChange={(event) =>
              setSearch(
                event.target.value
              )
            }
          />


          <div className="filters">

            {[
              "All",
              "PASS",
              "FLAG",
              "BLOCK",
            ].map((name) => (

              <button
                key={name}
                type="button"
                className={`filter-button ${
                  filter === name
                    ? "active"
                    : ""
                }`}
                onClick={() =>
                  setFilter(name)
                }
              >

                {name === "PASS" &&
                  "✓ "}

                {name === "FLAG" &&
                  "⚠ "}

                {name === "BLOCK" &&
                  "✕ "}

                {name}

              </button>

            ))}

          </div>


          <div className="record-list">

            {filteredData.length === 0 ? (

              <div className="no-records">
                No records match your
                search.
              </div>

            ) : (

              filteredData.map(
                (record) => {

                  const outcome =
                    record.outcome;

                  const rules =
                    Array.isArray(
                      record.triggered_rule_ids
                    )
                      ? record.triggered_rule_ids.join(
                          ", "
                        )
                      : "No violations";

                  return (

                    <button
                      key={
                        record.record_id
                      }
                      type="button"
                      className={`record-item ${
                        String(
                          selectedId
                        ) ===
                        String(
                          record.record_id
                        )
                          ? "selected"
                          : ""
                      }`}
                      onClick={() =>
                        setSelectedId(
                          record.record_id
                        )
                      }
                    >

                      <span
                        className={`status-dot ${getOutcomeClass(
                          outcome
                        )}`}
                      >
                        {getIcon(
                          outcome
                        )}
                      </span>


                      <div className="record-info">

                        <strong>
                          REC-
                          {getRecordNumber(
                            record.record_id
                          )}
                        </strong>

                        <span>
                          {rules}
                        </span>

                      </div>


                      <span
                        className={`outcome-text ${getOutcomeClass(
                          outcome
                        )}`}
                      >
                        {outcome}
                      </span>

                    </button>

                  );
                }
              )

            )}

          </div>

        </div>


        {/* ANALYSIS */}

        <div className="analysis-panel">

          {selectedRecord ? (

            <>

              <div className="analysis-header">

                <div>

                  <span className="analysis-label">
                    RECORD POLICY ANALYSIS
                  </span>

                  <h2>
                    REC-
                    {getRecordNumber(
                      selectedRecord.record_id
                    )}
                  </h2>

                </div>


                <span
                  className={`outcome-badge ${getOutcomeClass(
                    selectedRecord.outcome
                  )}`}
                >

                  {getIcon(
                    selectedRecord.outcome
                  )}{" "}

                  {selectedRecord.outcome}

                </span>

              </div>


              <div className="analysis-content">

                {/* POLICY RULES */}

                <section className="analysis-section">

                  <h3>
                    Policy Rules
                  </h3>


                  {selectedRecord.triggered_rules &&
                  selectedRecord
                    .triggered_rules
                    .length > 0 ? (

                    <div className="rule-list">

                      {selectedRecord.triggered_rules.map(
                        (rule, index) => (

                          <div
                            className="rule-item"
                            key={`${rule.rule_id}-${index}`}
                          >

                            <div className="rule-top">

                              <strong>
                                {normalizeRuleId(rule.rule_id, rule.category)}
                              </strong>

                              <span
                                className={`rule-outcome ${getOutcomeClass(
                                  rule.outcome
                                )}`}
                              >
                                {rule.outcome}
                              </span>

                            </div>

                            <span>
                              {rule.description}
                            </span>

                            <div className="rule-category">
                              {rule.category}
                            </div>

                            {(() => {
                              const columns =
                                getRuleColumns(rule);

                              if (columns.length === 0) {
                                return null;
                              }

                              return (
                                <div className="rule-category">
                                  Fields:{" "}
                                  {columns
                                    .map(formatFieldName)
                                    .join(", ")}
                                </div>
                              );
                            })()}

                          </div>

                        )
                      )}

                    </div>

                  ) : (

                    <div className="no-violations">
                      ✓ No policy violations
                      detected
                    </div>

                  )}

                </section>


                {/* EXPLANATION */}

                <section className="analysis-section">

                  <h3>
                    Explanation
                  </h3>


                  {selectedRecord.triggered_rules &&
                  selectedRecord
                    .triggered_rules
                    .length > 0 ? (

                    <div className="line-list">

                      {selectedRecord.triggered_rules.map(
                        (rule, index) => (

                          <div
                            className="line-item"
                            key={index}
                          >

                            <span>
                              •
                            </span>

                            <div>

                              <strong>
                                  {normalizeRuleId(rule.rule_id, rule.category)}:
                              </strong>

                              {rule.explanation ||
                                "Policy condition detected."}

                            </div>

                          </div>

                        )
                      )}

                    </div>

                  ) : (

                    <div className="line-item">

                      <span>
                        •
                      </span>

                      No PII or sensitive
                      information detected.

                    </div>

                  )}

                </section>


                {/* INPUT DATA */}

                <section className="analysis-section">

                  <h3>
                    Input Data
                  </h3>


                  <div className="input-grid">

                    {selectedRecord.input &&
                      Object.entries(
                        selectedRecord.input
                      ).map(
                        ([field, value]) => {

                          if (
                            value ===
                              undefined ||
                            value ===
                              null ||
                            String(
                              value
                            ).trim() ===
                              ""
                          ) {
                            return null;
                          }

                          return (

                            <div
                              className="input-item"
                              key={field}
                            >

                              <span>
                                {formatFieldName(
                                  field
                                )}
                              </span>

                              <strong>
                                {String(
                                  value
                                )}
                              </strong>

                            </div>

                          );
                        }
                      )}

                  </div>

                </section>


                {/* REMEDIATION */}

                <section className="analysis-section">

                  <h3>
                    Suggested Remediation
                  </h3>

                  {selectedRecord.triggered_rules &&
                  selectedRecord.triggered_rules.length > 0 ? (

                    <div className="remediation-list">

                      {(() => {
                        const remediationItems = [];
                        const seenColumns = new Set();

                        selectedRecord.triggered_rules.forEach((rule) => {
                          const columns = getRuleColumns(rule);

                          columns.forEach((column) => {
                            const normalizedColumn = String(
                              column || ""
                            ).trim();

                            const value =
                              selectedRecord.input?.[normalizedColumn];

                            if (
                              !normalizedColumn ||
                              value === undefined ||
                              value === null ||
                              String(value).trim() === "" ||
                              !REMEDIATION_BY_COLUMN[normalizedColumn] ||
                              seenColumns.has(normalizedColumn)
                            ) {
                              return;
                            }

                            seenColumns.add(normalizedColumn);

                            remediationItems.push({
                              column: normalizedColumn,
                              remediation:
                                REMEDIATION_BY_COLUMN[normalizedColumn],
                            });
                          });
                        });

                        if (remediationItems.length === 0) {
                          return (
                            <div className="remediation-item">
                              <span>→</span>
                              <span>
                                No remediation required.
                              </span>
                            </div>
                          );
                        }

                        return remediationItems.map((item, index) => (
                          <div
                            className="remediation-item"
                            key={`${item.column}-${index}`}
                          >
                            <span>→</span>

                            <span>
                              <strong>
                                {formatFieldName(item.column)}:
                              </strong>{" "}
                              {item.remediation}
                            </span>
                          </div>
                        ));
                      })()}

                    </div>

                  ) : (

                    <div className="remediation-item">

                      <span>→</span>

                      <span>
                        No remediation required.
                      </span>

                    </div>

                  )}

                </section>

              </div>

            </>

          ) : (

            <div className="empty-analysis">
              Select a record to view
              analysis
            </div>

          )}

        </div>

      </section>

    </div>
  );
}

export default App;