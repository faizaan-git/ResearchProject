
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  Activity,
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  FileText,
  FolderOpen,
  Globe,
  PanelLeftClose,
  PanelLeftOpen,
  Server,
  Search,
  Settings,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";

import {
  analyzeProjectArchive,
  getRecentProjectAnalysis,
  getRecentProjects,
  deleteRecentProjectAnalysis,
  ingestGithubRepository,
} from "./services/api";

import "./App.css";

// =====================================================
// CONSTANTS
// =====================================================

const API_HEALTH_URL = "http://127.0.0.1:8000/health";
const MINIMUM_LOADING_DURATION_MS = 1500;
const githubTabs = [
  { id: "overview", label: "Overview" },
  { id: "backend", label: "Backend" },
  { id: "languages", label: "Languages" },
  { id: "dependencies", label: "Dependencies" },
  { id: "files", label: "Files & Folders" },
  { id: "classes", label: "Classes" },
  { id: "functions", label: "Functions" },
  { id: "imports", label: "Imports" },
  { id: "api", label: "API Routes" },
];

// =====================================================
// REUSABLE COMPONENTS
// =====================================================

function PageHeading({ icon: Icon, eyebrow, title, description }) {
  return (
    <div className="plan-success-heading">
      <div className="section-icon success-icon">
        <Icon />
      </div>

      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    </div>
  );
}

function ProjectRow({ title, subtitle, status, icon: Icon = FileText }) {
  return (
    <div className="project-row">
      <div className="project-icon">
        <Icon />
      </div>

      <div className="project-info">
        <strong>{title}</strong>
        {subtitle && <small>{subtitle}</small>}
      </div>

      {status && <span className="draft-label">{status}</span>}
    </div>
  );
}

function SectionHeading({ icon: Icon, children }) {
  return (
    <h3>
      <Icon size={18} />
      {children}
    </h3>
  );
}

function ResultTabNavigation({ activeTab, onChange }) {
  return (
    <div className="github-result-tabs">
      {githubTabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          className={`github-tab ${
            activeTab === tab.id ? "active" : ""
          }`}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

function LoadingPage() {
  return (
    <main className="loading-screen" aria-busy="true">
      <section className="loading-card" role="status" aria-live="polite">
        <div className="loading-brand-mark" aria-hidden="true">
          <Sparkles size={22} />
        </div>
        <span className="loading-eyebrow">PROJECT WORKSPACE</span>
        <h1>Preparing ProjectResearch</h1>
        <p>Connecting to the backend and loading your recent analyses.</p>
        <span className="loading-spinner" aria-hidden="true" />
      </section>
    </main>
  );
}

// =====================================================
// MAIN APPLICATION
// =====================================================

function App() {
  // ---------------------------------------------------
  // GENERAL STATE
  // ---------------------------------------------------

  const activePage = "Project Analysis";
  const [backendStatus, setBackendStatus] = useState("Checking...");
  const [backendCheckComplete, setBackendCheckComplete] = useState(false);
  const [recentProjects, setRecentProjects] = useState([]);
  const [recentLoading, setRecentLoading] = useState(true);
  const [initialRecentLoadComplete, setInitialRecentLoadComplete] =
    useState(false);
  const [minimumLoadingDelayComplete, setMinimumLoadingDelayComplete] =
    useState(false);
  const [recentError, setRecentError] = useState("");
  const [openingProjectId, setOpeningProjectId] = useState(null);
  const [deletingProjectId, setDeletingProjectId] = useState(null);
  const [activeRecentProjectId, setActiveRecentProjectId] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const analysisResultsRef = useRef(null);

  // ---------------------------------------------------
  // PROJECT ANALYSIS STATE
  // ---------------------------------------------------

  const [analysisSource, setAnalysisSource] = useState("github");
  const [githubUrl, setGithubUrl] = useState("");
  const [zipFile, setZipFile] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState("");
  const [analysisResult, setAnalysisResult] = useState(null);

  const [analysisResultTab, setAnalysisResultTab] = useState("overview");
  const [classSearch, setClassSearch] = useState("");
  const [functionSearch, setFunctionSearch] = useState("");

  const refreshRecentProjects = useCallback(async () => {
    setRecentLoading(true);
    setRecentError("");

    try {
      const result = await getRecentProjects();

      if (!result?.success || !Array.isArray(result.data)) {
        throw new Error("Could not load recent projects.");
      }

      setRecentProjects(result.data);
    } catch (error) {
      setRecentError(
        error.response?.data?.detail ||
          error.message ||
          "Unable to load recent projects.",
      );
    } finally {
      setRecentLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;

    getRecentProjects()
      .then((result) => {
        if (!active) return;
        if (!result?.success || !Array.isArray(result.data)) {
          throw new Error("Could not load recent projects.");
        }

        setRecentProjects(result.data);
      })
      .catch((error) => {
        if (active) {
          setRecentError(
            error.response?.data?.detail ||
              error.message ||
              "Unable to load recent projects.",
          );
        }
      })
      .finally(() => {
        if (active) {
          setRecentLoading(false);
          setInitialRecentLoadComplete(true);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const timeoutId = window.setTimeout(
      () => setMinimumLoadingDelayComplete(true),
      MINIMUM_LOADING_DURATION_MS,
    );

    return () => window.clearTimeout(timeoutId);
  }, []);

  useEffect(() => {
    if (analysisResult) {
      analysisResultsRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  }, [analysisResult]);

  // ===================================================
  // BACKEND CONNECTION CHECK
  // ===================================================

  useEffect(() => {
    let active = true;

    async function checkBackend() {
      try {
        const response = await fetch(API_HEALTH_URL);

        if (!response.ok) {
          throw new Error("Backend unavailable");
        }

        if (active) {
          setBackendStatus("Connected");
        }
      } catch {
        if (active) {
          setBackendStatus("Offline");
        }
      } finally {
        if (active) {
          setBackendCheckComplete(true);
        }
      }
    }

    checkBackend();

    return () => {
      active = false;
    };
  }, []);

  // ===================================================
  // ANALYZE SELECTED PROJECT SOURCE
  // ===================================================

  async function analyzeProject(event) {
    event.preventDefault();

    const cleanUrl = githubUrl.trim();
    const zipFilename = zipFile?.name || "";

    if (analysisSource === "github" && !cleanUrl) {
      setAnalysisError("Please enter a GitHub repository URL.");
      return;
    }

    if (analysisSource === "zip" && !zipFile) {
      setAnalysisError("Please choose a project ZIP file.");
      return;
    }

    if (analysisSource === "zip" && !zipFilename.toLowerCase().endsWith(".zip")) {
      setAnalysisError("Choose a file with the .zip extension.");
      return;
    }

    if (analysisSource === "zip" && zipFile.size === 0) {
      setAnalysisError("The selected ZIP file is empty.");
      return;
    }

    if (analysisSource === "zip" && zipFile.size > 100 * 1024 * 1024) {
      setAnalysisError("ZIP files must be 100 MB or smaller.");
      return;
    }

    setAnalysisLoading(true);
    setAnalysisError("");
    setAnalysisResult(null);

    try {
      const result =
        analysisSource === "github"
          ? await ingestGithubRepository(cleanUrl)
          : await analyzeProjectArchive(zipFile);

      if (!result?.success || !result?.data) {
        throw new Error("Project analysis failed.");
      }

      const analyzedProject =
        analysisSource === "zip"
          ? {
              ...result.data,
              source_type: "zip_upload",
              repository_name: zipFilename.replace(/\.zip$/i, ""),
              repository_url: "",
              upload: {
                ...result.data.upload,
                filename: zipFilename,
              },
            }
          : result.data;
      setAnalysisResult(analyzedProject);
      setActiveRecentProjectId(null);

      // Start each analysis on Overview and show its results.
      setAnalysisResultTab("overview");
      setClassSearch("");
      setFunctionSearch("");
      setZipFile(null);
      void refreshRecentProjects();
    } catch (error) {
      setAnalysisError(
        error.response?.data?.detail ||
          error.message ||
          "Unable to analyze the selected project.",
      );
    } finally {
      setAnalysisLoading(false);
    }
  }

  async function openRecentProject(projectId) {
    setOpeningProjectId(projectId);
    setRecentError("");

    try {
      const result = await getRecentProjectAnalysis(projectId);

      if (!result?.success || !result.data) {
        throw new Error("Could not open this project analysis.");
      }

      setAnalysisResult(result.data);
      setActiveRecentProjectId(projectId);
      setAnalysisResultTab("overview");
      setClassSearch("");
      setFunctionSearch("");
      setAnalysisError("");
    } catch (error) {
      setRecentError(
        error.response?.data?.detail ||
          error.message ||
          "Unable to open this project analysis.",
      );
    } finally {
      setOpeningProjectId(null);
    }
  }

  async function deleteRecentProject(project) {
    const confirmed = window.confirm(
      `Delete "${project.project_name}" from recent analyses? This removes the saved analysis only.`,
    );

    if (!confirmed) return;

    setDeletingProjectId(project.id);
    setRecentError("");

    try {
      const result = await deleteRecentProjectAnalysis(project.id);

      if (!result?.success) {
        throw new Error("Could not delete this project analysis.");
      }

      setRecentProjects((projects) =>
        projects.filter((item) => item.id !== project.id),
      );

      if (activeRecentProjectId === project.id) {
        setAnalysisResult(null);
        setActiveRecentProjectId(null);
      }
    } catch (error) {
      setRecentError(
        error.response?.data?.detail ||
          error.message ||
          "Unable to delete this project analysis.",
      );
    } finally {
      setDeletingProjectId(null);
    }
  }

  // ===================================================
  // DERIVED PROJECT ANALYSIS DATA
  // ===================================================

  const classes = useMemo(
    () => analysisResult?.code_analysis?.classes || [],
    [analysisResult],
  );

  const functions = useMemo(
    () => analysisResult?.code_analysis?.functions || [],
    [analysisResult],
  );

  const filteredClasses = useMemo(() => {
    const query = classSearch.trim().toLowerCase();

    if (!query) return classes;

    return classes.filter((item) => {
      const searchableText = [
        item.name,
        item.file,
        ...(item.bases || []),
        item.docstring,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return searchableText.includes(query);
    });
  }, [classes, classSearch]);

  const filteredFunctions = useMemo(() => {
    const query = functionSearch.trim().toLowerCase();

    if (!query) return functions;

    return functions.filter((item) => {
      const searchableText = [
        item.name,
        item.file,
        item.class,
        ...(item.parameters || []),
        ...(item.decorators || []),
        item.docstring,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return searchableText.includes(query);
    });
  }, [functions, functionSearch]);

  if (
    !initialRecentLoadComplete ||
    !backendCheckComplete ||
    !minimumLoadingDelayComplete
  ) {
    return <LoadingPage />;
  }

  // ===================================================
  // APPLICATION UI
  // ===================================================

  return (
    <div className="app-shell">
      <aside
        id="recent-analyses-sidebar"
        className={`history-sidebar ${isSidebarOpen ? "" : "collapsed"}`}
        aria-label="Recent analyses"
        aria-hidden={!isSidebarOpen}
        inert={!isSidebarOpen}
      >
        <div className="history-sidebar-heading">
          <div>
            <span className="history-sidebar-kicker">PROJECT HISTORY</span>
            <h2>Recent analyses</h2>
          </div>
          {recentProjects.length > 0 && (
            <span className="history-project-count">
              {recentProjects.length}
            </span>
          )}
        </div>

        {recentError && (
          <p className="history-message history-error" role="alert">
            {recentError}
          </p>
        )}

        {recentLoading ? (
          <p className="history-message">Loading analyses...</p>
        ) : recentProjects.length === 0 ? (
          <p className="history-message">
            Your analyzed projects will appear here.
          </p>
        ) : (
          <nav className="history-project-list" aria-label="Saved project analyses">
            {recentProjects.map((project) => (
              <div
                className={`history-project-row ${
                  activeRecentProjectId === project.id ? "active" : ""
                }`}
                key={project.id}
              >
                <button
                  className="history-project-item"
                  type="button"
                  title={project.project_name}
                  aria-current={
                    activeRecentProjectId === project.id ? "page" : undefined
                  }
                  disabled={
                    openingProjectId !== null || deletingProjectId !== null
                  }
                  onClick={() => openRecentProject(project.id)}
                >
                  <FolderOpen size={15} aria-hidden="true" />
                  <span className="history-project-copy">
                    <strong>{project.project_name}</strong>
                    <small>
                      {openingProjectId === project.id
                        ? "Opening analysis..."
                        : project.source_type === "zip_upload"
                          ? "ZIP project"
                          : "GitHub repository"}
                    </small>
                  </span>
                </button>
                <button
                  className="history-project-delete"
                  type="button"
                  aria-label={`Delete ${project.project_name} from recent analyses`}
                  title="Delete recent analysis"
                  disabled={
                    openingProjectId !== null || deletingProjectId !== null
                  }
                  onClick={() => deleteRecentProject(project)}
                >
                  <Trash2 size={15} aria-hidden="true" />
                </button>
              </div>
            ))}
          </nav>
        )}

        <div className="history-sidebar-footer">
          Saved analyses are available to reopen anytime.
        </div>
      </aside>

      <main className="main-area">
        {/* TOPBAR */}

        <header className="topbar">
          <div className="topbar-left">
            <button
              className="sidebar-toggle"
              type="button"
              aria-label={isSidebarOpen ? "Close sidebar" : "Open sidebar"}
              aria-expanded={isSidebarOpen}
              aria-controls="recent-analyses-sidebar"
              onClick={() => setIsSidebarOpen((open) => !open)}
            >
              {isSidebarOpen ? (
                <PanelLeftClose size={18} aria-hidden="true" />
              ) : (
                <PanelLeftOpen size={18} aria-hidden="true" />
              )}
            </button>
            <div className="topbar-brand">
              <div className="topbar-brand-mark" aria-hidden="true">
                <Sparkles size={18} />
              </div>
              <span>
                ProjectResearch
              </span>
            </div>
          </div>

          <div className="topbar-right">
            <span className="topbar-status">
              <span
                className={`status-dot ${
                  backendStatus === "Connected" ? "online" : ""
                }`}
              />
              {backendStatus}
            </span>
          </div>
        </header>

        {/* =============================================
            PAGE CONTENT
        ============================================= */}

        <div className="page-content">
          {/* PAGE HEADER */}

          {!analysisResult && (
            <section className="welcome-row">
              <div>
                <div className="eyebrow">
                  <Sparkles size={14} />
                  YOUR PROJECT WORKSPACE
                </div>

                <h1>What would you like to analyze?</h1>

                <p>
                  Start with a GitHub repository or ZIP file. Review the project
                  structure and code findings when the scan is complete.
                </p>
              </div>
            </section>
          )}

          {/* =============================================
              PROJECT ANALYSIS
          ============================================= */}

          {activePage === "Project Analysis" && (
            <>
              {/* PROJECT SOURCE */}

              {!analysisResult && (
                <section className="panel form-panel">
                <div className="section-icon">
                  <Globe />
                </div>

                <h2>Start with a project source</h2>

                <p>
                  Choose how to share your project. ProjectResearch will scan its
                  folders and files, then open a separate results page.
                </p>

                <div
                  className="project-source-options"
                  role="group"
                  aria-label="Project source type"
                >
                  <button
                    className={
                      analysisSource === "github"
                        ? "project-source-option active"
                        : "project-source-option"
                    }
                    type="button"
                    aria-pressed={analysisSource === "github"}
                    disabled={analysisLoading}
                    onClick={() => {
                      setAnalysisSource("github");
                      setAnalysisError("");
                    }}
                  >
                    <Globe size={16} />
                    GitHub URL
                  </button>
                  <button
                    className={
                      analysisSource === "zip"
                        ? "project-source-option active"
                        : "project-source-option"
                    }
                    type="button"
                    aria-pressed={analysisSource === "zip"}
                    disabled={analysisLoading}
                    onClick={() => {
                      setAnalysisSource("zip");
                      setAnalysisError("");
                    }}
                  >
                    <FolderOpen size={16} />
                    ZIP file
                  </button>
                </div>

                <div className="workflow-steps" aria-label="Analysis workflow">
                  <span><b>1</b> Choose source</span>
                  <span><b>2</b> Analyze files</span>
                  <span><b>3</b> Explore findings</span>
                </div>

                <form onSubmit={analyzeProject}>
                  <label
                    htmlFor={
                      analysisSource === "github" ? "github-url" : "project-zip"
                    }
                  >
                    {analysisSource === "github"
                      ? "GitHub repository URL"
                      : "Project ZIP file"}
                  </label>

                  <div
                    className={`source-input-shell ${
                      analysisSource === "zip" ? "zip-source" : ""
                    }`}
                  >
                    {analysisSource === "github" ? (
                      <input
                        key="github-url-input"
                        id="github-url"
                        type="url"
                        value={githubUrl}
                        onChange={(event) => setGithubUrl(event.target.value)}
                        placeholder="https://github.com/owner/repository"
                        required
                        disabled={analysisLoading}
                      />
                    ) : (
                      <input
                        key="project-zip-input"
                        id="project-zip"
                        type="file"
                        accept=".zip,application/zip"
                        onChange={(event) => {
                          const selectedFile =
                            event.currentTarget.files?.[0] || null;
                          event.currentTarget.value = "";
                          setZipFile(selectedFile);
                          setAnalysisError("");
                        }}
                        disabled={analysisLoading}
                      />
                    )}

                    <button
                      className="primary-button"
                      type="submit"
                      disabled={
                        analysisLoading ||
                        (analysisSource === "zip" && !zipFile)
                      }
                    >
                      {analysisSource === "github" ? (
                        <Globe size={17} />
                      ) : (
                        <FolderOpen size={17} />
                      )}
                      {analysisLoading
                        ? "Analyzing..."
                        : "Analyze project"}
                    </button>
                  </div>

                  <div className="form-note">
                    {analysisSource === "github"
                      ? "Enter the URL of a public GitHub repository."
                      : "ZIP format only. Maximum upload size: 100 MB."}
                  </div>

                  {analysisSource === "zip" && zipFile && (
                    <div className="selected-zip-file">
                      Selected: {zipFile.name} (
                      {(zipFile.size / (1024 * 1024)).toFixed(1)} MB)
                    </div>
                  )}
                </form>

                {analysisLoading && (
                  <div className="planning-message">
                    <Activity size={17} />
                    Scanning project folders and files. Please wait...
                  </div>
                )}

                {analysisError && (
                  <div className="error-message" role="alert">
                    <X size={17} />
                    {analysisError}
                  </div>
                )}
                </section>
              )}

              {/* PROJECT ANALYSIS RESULTS */}

              {analysisResult && (
                <section
                  className="panel generated-plan analysis-results"
                  ref={analysisResultsRef}
                >
                  <button
                    className="analysis-back-button"
                    type="button"
                    onClick={() => {
                      setAnalysisResult(null);
                      setActiveRecentProjectId(null);
                    }}
                  >
                    <ArrowLeft size={16} aria-hidden="true" />
                    Back to project setup
                  </button>

                  <PageHeading
                    icon={CheckCircle2}
                    eyebrow="ANALYSIS COMPLETED"
                    title={analysisResult.repository_name || "Repository"}
                    description="Explore the project analysis using the separate sections below."
                  />

                  <ResultTabNavigation
                    activeTab={analysisResultTab}
                    onChange={setAnalysisResultTab}
                  />

                  {/* ---------------------------------------
                      OVERVIEW TAB
                  --------------------------------------- */}

                  {analysisResultTab === "overview" && (
                    <>
                      <div className="plan-section">
                        <SectionHeading icon={FolderOpen}>
                          Project Information
                        </SectionHeading>

                        {analysisResult.repository_owner && (
                          <p>
                            <strong>Owner:</strong>{" "}
                            {analysisResult.repository_owner}
                          </p>
                        )}

                        <p>
                          <strong>Project:</strong>{" "}
                          {analysisResult.repository_name || "Not specified"}
                        </p>

                        <p>
                          <strong>Source type:</strong>{" "}
                          {analysisResult.source_type === "zip_upload"
                            ? "ZIP upload"
                            : analysisResult.source_type || "Not specified"}
                        </p>

                        <p>
                          <strong>Source:</strong>{" "}
                          {analysisResult.repository_url ? (
                            <a
                              href={analysisResult.repository_url}
                              target="_blank"
                              rel="noreferrer"
                            >
                              {analysisResult.repository_url}
                            </a>
                          ) : (
                            analysisResult.upload?.filename ||
                            "Uploaded project archive"
                          )}
                        </p>
                      </div>

                      <div className="plan-section">
                        <SectionHeading icon={Activity}>
                          Project Overview
                        </SectionHeading>

                        <div className="plan-summary">
                          <div className="plan-summary-item">
                            <strong>
                              {analysisResult.upload?.total_files ?? 0}
                            </strong>
                            <span>Project files</span>
                          </div>

                          <div className="plan-summary-item">
                            <strong>
                              {analysisResult.project_analysis?.total_files_scanned ?? 0}
                            </strong>
                            <span>Files scanned</span>
                          </div>

                          <div className="plan-summary-item">
                            <strong>
                              {analysisResult.project_analysis?.skipped_files ?? 0}
                            </strong>
                            <span>Skipped files</span>
                          </div>

                          <div className="plan-summary-item">
                            <strong>
                              {analysisResult.code_analysis?.python_files_scanned ?? 0}
                            </strong>
                            <span>Python files</span>
                          </div>

                          <div className="plan-summary-item">
                            <strong>
                              {analysisResult.code_analysis?.total_classes ?? classes.length}
                            </strong>
                            <span>Classes</span>
                          </div>

                          <div className="plan-summary-item">
                            <strong>
                              {analysisResult.code_analysis?.total_functions ?? functions.length}
                            </strong>
                            <span>Functions</span>
                          </div>

                          <div className="plan-summary-item">
                            <strong>
                              {analysisResult.code_analysis?.total_imports ?? 0}
                            </strong>
                            <span>Imports</span>
                          </div>

                          <div className="plan-summary-item">
                            <strong>
                              {analysisResult.code_analysis?.total_api_routes ?? 0}
                            </strong>
                            <span>API routes</span>
                          </div>
                        </div>
                      </div>

                      <div className="plan-section">
                        <SectionHeading icon={Activity}>
                          Python Code Analysis
                        </SectionHeading>

                        <p>
                          <strong>Analysis type:</strong>{" "}
                          {analysisResult.code_analysis?.analysis_type ||
                            "Not specified"}
                        </p>

                        <p>
                          <strong>Analysis status:</strong>{" "}
                          {analysisResult.code_analysis_status ||
                            "Not specified"}
                        </p>

                        <p>
                          <strong>API routes detected:</strong>{" "}
                          {analysisResult.code_analysis?.total_api_routes ?? 0}
                        </p>
                      </div>
                    </>
                  )}

                  {/* ---------------------------------------
                      BACKEND TAB
                  --------------------------------------- */}

                  {analysisResultTab === "backend" && (
                    <div className="plan-section">
                      <SectionHeading icon={Server}>
                        Detected Backend Technologies
                      </SectionHeading>

                      {analysisResult.project_analysis?.backend_technologies
                        ?.length > 0 ? (
                        analysisResult.project_analysis.backend_technologies.map(
                          (technology) => (
                            <ProjectRow
                              key={technology}
                              title={technology}
                              icon={Server}
                            />
                          ),
                        )
                      ) : (
                        <p>
                          No backend frameworks or server technologies were
                          detected in the project dependency manifests.
                        </p>
                      )}
                    </div>
                  )}

                  {/* ---------------------------------------
                      LANGUAGES TAB
                  --------------------------------------- */}

                  {analysisResultTab === "languages" && (
                    <>
                      <div className="plan-section">
                        <SectionHeading icon={BookOpen}>
                          Programming Languages
                        </SectionHeading>

                        {analysisResult.project_analysis?.programming_languages?.length > 0 ? (
                          analysisResult.project_analysis.programming_languages.map(
                            (language, index) => (
                              <ProjectRow
                                key={`${language.language}-${index}`}
                                title={language.language}
                                status={`${language.file_count} files`}
                              />
                            ),
                          )
                        ) : (
                          <p>No programming languages detected.</p>
                        )}
                      </div>

                      <div className="plan-section">
                        <SectionHeading icon={Sparkles}>
                          Detected Frameworks
                        </SectionHeading>

                        {analysisResult.project_analysis?.detected_frameworks?.length > 0 ? (
                          <ul>
                            {analysisResult.project_analysis.detected_frameworks.map(
                              (framework, index) => (
                                <li key={index}>
                                  {typeof framework === "string"
                                    ? framework
                                    : framework.name ||
                                      JSON.stringify(framework)}
                                </li>
                              ),
                            )}
                          </ul>
                        ) : (
                          <p>
                            No frameworks detected by the current scanner.
                          </p>
                        )}
                      </div>
                    </>
                  )}

                  {/* ---------------------------------------
                      DEPENDENCIES TAB
                  --------------------------------------- */}

                  {analysisResultTab === "dependencies" && (
                    <div className="plan-section">
                      <SectionHeading icon={Settings}>
                        Project Dependencies
                      </SectionHeading>

                      {analysisResult.project_analysis?.dependencies?.length > 0 ? (
                        <ul>
                          {analysisResult.project_analysis.dependencies.map(
                            (dependency, index) => (
                              <li key={index}>
                                {typeof dependency === "string"
                                  ? dependency
                                  : dependency.name ||
                                    dependency.package ||
                                    JSON.stringify(dependency)}
                              </li>
                            ),
                          )}
                        </ul>
                      ) : (
                        <p>
                          No dependencies detected by the current scanner.
                        </p>
                      )}
                    </div>
                  )}

                  {/* ---------------------------------------
                      FILES AND FOLDERS TAB
                  --------------------------------------- */}

                  {analysisResultTab === "files" && (
                    <>
                      <div className="plan-section">
                        <SectionHeading icon={FileText}>
                          Important Project Files
                        </SectionHeading>

                        {analysisResult.project_analysis?.important_files?.length > 0 ? (
                          <ul>
                            {analysisResult.project_analysis.important_files.map(
                              (file, index) => (
                                <li key={`${file}-${index}`}>
                                  <code>{file}</code>
                                </li>
                              ),
                            )}
                          </ul>
                        ) : (
                          <p>No important files identified.</p>
                        )}
                      </div>

                      <div className="plan-section">
                        <SectionHeading icon={FolderOpen}>
                          Folder Structure
                        </SectionHeading>

                        {analysisResult.project_analysis?.folder_structure?.length > 0 ? (
                          <ul>
                            {analysisResult.project_analysis.folder_structure.map(
                              (folder, index) => (
                                <li key={`${folder}-${index}`}>
                                  <code>{folder}</code>
                                </li>
                              ),
                            )}
                          </ul>
                        ) : (
                          <p>No folder structure available.</p>
                        )}
                      </div>
                    </>
                  )}

                  {/* ---------------------------------------
                      CLASSES TAB
                  --------------------------------------- */}

                  {analysisResultTab === "classes" && (
                    <div className="plan-section">
                      <SectionHeading icon={BookOpen}>
                        Detected Classes ({classes.length})
                      </SectionHeading>

                      <div className="github-search-wrapper">
                        <Search size={17} />

                        <input
                          type="search"
                          className="github-search"
                          placeholder="Search classes by name, file, or base class..."
                          value={classSearch}
                          onChange={(event) =>
                            setClassSearch(event.target.value)
                          }
                        />

                        {classSearch && (
                          <button
                            type="button"
                            className="github-search-clear"
                            onClick={() => setClassSearch("")}
                            aria-label="Clear class search"
                          >
                            <X size={16} />
                          </button>
                        )}
                      </div>

                      <p className="form-note">
                        Showing {filteredClasses.length} of {classes.length} classes.
                      </p>

                      {filteredClasses.length > 0 ? (
                        filteredClasses.map((item, index) => (
                          <div
                            className="project-row github-code-row"
                            key={`${item.file}-${item.line}-${index}`}
                          >
                            <div className="project-info">
                              <strong>{item.name}</strong>

                              <small>
                                {item.file || "File not specified"} · Line{" "}
                                {item.line ?? "Not specified"}
                              </small>

                              {item.bases?.length > 0 && (
                                <small>
                                  Inherits: {item.bases.join(", ")}
                                </small>
                              )}

                              {item.docstring && (
                                <small>{item.docstring}</small>
                              )}
                            </div>
                          </div>
                        ))
                      ) : classes.length === 0 ? (
                        <p>No classes detected.</p>
                      ) : (
                        <p>No classes match your search.</p>
                      )}
                    </div>
                  )}

                  {/* ---------------------------------------
                      FUNCTIONS TAB
                  --------------------------------------- */}

                  {analysisResultTab === "functions" && (
                    <div className="plan-section">
                      <SectionHeading icon={Activity}>
                        Detected Functions ({functions.length})
                      </SectionHeading>

                      <div className="github-search-wrapper">
                        <Search size={17} />

                        <input
                          type="search"
                          className="github-search"
                          placeholder="Search functions by name, file, class, or parameter..."
                          value={functionSearch}
                          onChange={(event) =>
                            setFunctionSearch(event.target.value)
                          }
                        />

                        {functionSearch && (
                          <button
                            type="button"
                            className="github-search-clear"
                            onClick={() => setFunctionSearch("")}
                            aria-label="Clear function search"
                          >
                            <X size={16} />
                          </button>
                        )}
                      </div>

                      <p className="form-note">
                        Showing {filteredFunctions.length} of {functions.length} functions.
                      </p>

                      {filteredFunctions.length > 0 ? (
                        filteredFunctions.map((item, index) => (
                          <div
                            className="project-row github-code-row"
                            key={`${item.file}-${item.line}-${index}`}
                          >
                            <div className="project-info">
                              <strong>
                                {item.name}
                                {item.is_async ? " (async)" : ""}
                              </strong>

                              <small>
                                {item.file || "File not specified"} · Line{" "}
                                {item.line ?? "Not specified"}
                              </small>

                              {item.class && (
                                <small>Class: {item.class}</small>
                              )}

                              <small>
                                Parameters:{" "}
                                {Array.isArray(item.parameters)
                                  ? item.parameters.join(", ") || "None"
                                  : item.parameters || "None"}
                              </small>

                              {item.decorators?.length > 0 && (
                                <small>
                                  Decorators: {item.decorators.join(", ")}
                                </small>
                              )}

                              {item.docstring && (
                                <small>{item.docstring}</small>
                              )}
                            </div>
                          </div>
                        ))
                      ) : functions.length === 0 ? (
                        <p>No functions detected.</p>
                      ) : (
                        <p>No functions match your search.</p>
                      )}
                    </div>
                  )}

                  {/* ---------------------------------------
                      IMPORTS TAB
                  --------------------------------------- */}

                  {analysisResultTab === "imports" && (
                    <div className="plan-section">
                      <SectionHeading icon={Settings}>
                        Imported Modules
                      </SectionHeading>

                      <p className="form-note">
                        Total imported modules:{" "}
                        {analysisResult.code_analysis?.imports?.length || 0}
                      </p>

                      {analysisResult.code_analysis?.imports?.length > 0 ? (
                        <ul>
                          {analysisResult.code_analysis.imports.map(
                            (module, index) => (
                              <li key={`${module}-${index}`}>
                                <code>{module}</code>
                              </li>
                            ),
                          )}
                        </ul>
                      ) : (
                        <p>No imports detected.</p>
                      )}
                    </div>
                  )}

                  {/* ---------------------------------------
                      API ROUTES TAB
                  --------------------------------------- */}

                  {analysisResultTab === "api" && (
                    <div className="plan-section">
                      <SectionHeading icon={Globe}>
                        Detected API Routes
                      </SectionHeading>

                      {analysisResult.code_analysis?.api_routes?.length > 0 ? (
                        <pre className="github-api-output">
                          {JSON.stringify(
                            analysisResult.code_analysis.api_routes,
                            null,
                            2,
                          )}
                        </pre>
                      ) : (
                        <p>
                          No API routes detected by the Python AST analyzer.
                        </p>
                      )}
                    </div>
                  )}
                </section>
              )}
            </>
          )}

        </div>

        {/* =============================================
            FOOTER
        ============================================= */}

        <footer className="footer">
          <span>ProjectResearch</span>
          <span>GitHub and ZIP project analysis</span>
        </footer>
      </main>
    </div>
  );
}

export default App;
