const API_BASE_URL = "https://fieldsync-ai-9aqn.onrender.com";

// DOM Elements
const activityCount = document.getElementById("activityCount");
const completedCount = document.getElementById("completedCount");
const eventCount = document.getElementById("eventCount");
const pendingCount = document.getElementById("pendingCount");
const delayedCount = document.getElementById("delayedCount");
const unmatchedCount = document.getElementById("unmatchedCount");

const activityTableBody = document.getElementById("activityTableBody");
const eventTableBody = document.getElementById("eventTableBody");
const pendingMatchList = document.getElementById("pendingMatchList");

const disciplineTableBody = document.getElementById("disciplineTableBody");
const memoryTableBody = document.getElementById("memoryTableBody");
const auditTableBody = document.getElementById("auditTableBody");

const messageBox = document.getElementById("messageBox");
const apiDot = document.getElementById("apiDot");
const apiStatus = document.getElementById("apiStatus");

// --- UI Utilities ---

function showMessage(message, type = "success") {
  const icon = type === "success" ? '<i class="fa-solid fa-circle-check"></i>' : '<i class="fa-solid fa-circle-exclamation"></i>';
  messageBox.innerHTML = `${icon} ${message}`;
  messageBox.className = `message-box ${type}`;
}

function hideMessage() {
  messageBox.className = "message-box hidden";
}

function setLoadingState(button, isLoading, originalHtml = "") {
  if (isLoading) {
    button.disabled = true;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
  } else {
    button.disabled = false;
    button.innerHTML = originalHtml;
  }
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(`${value}T00:00:00`).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function createStatusBadge(status) {
  const currentStatus = status || "not_started";
  const readableStatus = currentStatus.replace("_", " ");
  return `<span class="status-badge ${currentStatus}">${readableStatus}</span>`;
}

// --- API Handling ---

async function apiRequest(endpoint, options = {}) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
  let responseData = null;

  try {
    responseData = await response.json();
  } catch {
    responseData = null;
  }

  if (!response.ok) {
    throw new Error(responseData?.detail || responseData?.message || "Backend request failed.");
  }
  return responseData;
}

async function checkApiHealth() {
  try {
    await apiRequest("/health");
    apiDot.className = "status-dot online";
    apiStatus.textContent = "System Online";
  } catch {
    apiDot.className = "status-dot offline";
    apiStatus.textContent = "System Offline";
  }
}

// --- Render Functions ---

function renderActivities(activities) {
  if (!activities.length) {
    activityTableBody.innerHTML = `<tr><td colspan="6" class="empty-cell"><i class="fa-solid fa-folder-open"></i> No schedule activities found.</td></tr>`;
    return;
  }
  activityTableBody.innerHTML = activities.map((activity) => `
    <tr>
      <td><strong>${activity.activity_code}</strong></td>
      <td>${activity.activity_name}</td>
      <td>${activity.discipline || "-"}</td>
      <td>${formatDate(activity.planned_finish)}</td>
      <td>${formatDate(activity.actual_finish)}</td>
      <td>${createStatusBadge(activity.status)}</td>
    </tr>
  `).join("");
}

function renderEvents(events) {
  if (!events.length) {
    eventTableBody.innerHTML = `<tr><td colspan="7" class="empty-cell"><i class="fa-solid fa-folder-open"></i> No progress events found.</td></tr>`;
    return;
  }
  eventTableBody.innerHTML = events.map((event) => `
    <tr>
      <td>${event.id}</td>
      <td>${event.reported_description}</td>
      <td>${event.discipline || "-"}</td>
      <td><span class="badge" style="background:#f1f5f9; color:#475569;">${event.event_type || "-"}</span></td>
      <td>${formatDate(event.event_date)}</td>
      <td><strong>${Number(event.extraction_confidence || 0).toFixed(0)}%</strong></td>
      <td>
        <button class="small-button primary-button outline" style="margin-top:0;" onclick="suggestMatch(${event.id})">
          <i class="fa-solid fa-wand-magic-sparkles"></i> Match
        </button>
      </td>
    </tr>
  `).join("");
}

function renderPendingMatches(matches) {
  if (!matches.length) {
    pendingMatchList.innerHTML = `<p class="empty-cell"><i class="fa-solid fa-check-double"></i> Queue clear. No pending AI matches.</p>`;
    return;
  }
  pendingMatchList.innerHTML = matches.map((match) => `
    <article class="match-card">
      <div class="match-info">
        <h4>Match ID: ${match.id}</h4>
        <p>Event #${match.progress_event_id} ➔ Activity #${match.schedule_activity_id}</p>
        <p>Method: ${match.match_method}</p>
      </div>
      <div class="match-actions">
        <div class="confidence">${Number(match.confidence_score).toFixed(1)}%</div>
        <button class="small-button approve-button" onclick="reviewMatch(${match.id}, 'approved')" title="Approve">
          <i class="fa-solid fa-check"></i> Approve
        </button>
        <button class="small-button reject-button" onclick="reviewMatch(${match.id}, 'rejected')" title="Reject">
          <i class="fa-solid fa-xmark"></i> Reject
        </button>
      </div>
    </article>
  `).join("");
}

function renderDisciplineSummary(disciplineSummary) {
  const disciplines = Object.entries(disciplineSummary);
  if (!disciplines.length) {
    disciplineTableBody.innerHTML = `<tr><td colspan="5" class="empty-cell">No analytics available.</td></tr>`;
    return;
  }
  disciplineTableBody.innerHTML = disciplines.map(([discipline, data]) => `
    <tr>
      <td><strong>${discipline}</strong></td>
      <td>${data.total}</td>
      <td><span style="color:var(--success); font-weight:600;">${data.completed}</span></td>
      <td>${data.in_progress}</td>
      <td><span style="color:var(--danger); font-weight:600;">${data.delayed}</span></td>
    </tr>
  `).join("");
}

function renderInstitutionalMemory(memoryData) {
  const patterns = Object.entries(memoryData.discipline_execution_patterns);
  if (!patterns.length) {
    memoryTableBody.innerHTML = `<tr><td colspan="5" class="empty-cell">No historical data available yet.</td></tr>`;
    return;
  }
  memoryTableBody.innerHTML = patterns.map(([discipline, data]) => `
    <tr>
      <td><strong>${discipline}</strong></td>
      <td>${data.completed_activity_count}</td>
      <td>${data.delayed_activity_count}</td>
      <td>${data.average_planned_duration_days === null ? "-" : `${data.average_planned_duration_days} d`}</td>
      <td>${data.average_actual_duration_days === null ? "-" : `${data.average_actual_duration_days} d`}</td>
    </tr>
  `).join("");
}

function renderAuditLogs(logs) {
  if (!logs.length) {
    auditTableBody.innerHTML = `<tr><td colspan="5" class="empty-cell">No audit records yet.</td></tr>`;
    return;
  }
  auditTableBody.innerHTML = logs.map((log) => `
    <tr>
      <td style="color:var(--text-muted); font-size:12px;">${new Date(log.created_at).toLocaleString("en-IN")}</td>
      <td><strong>${log.entity_type} #${log.entity_id}</strong></td>
      <td><span class="badge" style="background:#f1f5f9; color:#475569;">${log.action}</span></td>
      <td style="font-family:monospace; font-size:12px;">${JSON.stringify(log.old_value || {})}</td>
      <td style="font-family:monospace; font-size:12px;">${JSON.stringify(log.new_value || {})}</td>
    </tr>
  `).join("");
}

// --- Core Logic ---

async function loadDashboard() {
  try {
    const [activities, events, pendingMatches, analytics, institutionalMemory, auditLogs] = await Promise.all([
      apiRequest("/api/activities"),
      apiRequest("/api/reports/events/all"),
      apiRequest("/api/matches/pending"),
      apiRequest("/api/analytics/summary"),
      apiRequest("/api/insights/institutional-memory"),
      apiRequest("/api/audit-logs"),
    ]);

    const summary = analytics.project_summary;
    activityCount.textContent = summary.total_schedule_activities;
    completedCount.textContent = summary.completed_activities;
    eventCount.textContent = summary.total_progress_events;
    pendingCount.textContent = summary.pending_planner_reviews;
    delayedCount.textContent = summary.delayed_activities;
    unmatchedCount.textContent = summary.unmatched_progress_events;

    renderActivities(activities);
    renderEvents(events);
    renderPendingMatches(pendingMatches);
    renderDisciplineSummary(analytics.discipline_summary);
    renderInstitutionalMemory(institutionalMemory);
    renderAuditLogs(auditLogs);
  } catch (error) {
    showMessage(`Dashboard error: ${error.message}`, "error");
  }
}

async function suggestMatch(eventId) {
  try {
    const result = await apiRequest(`/api/events/${eventId}/match`, { method: "POST" });
    showMessage(`AI suggested "${result.suggested_activity_code} — ${result.suggested_activity_name}" with ${result.confidence_score}% confidence.`, "success");
    await loadDashboard();
  } catch (error) {
    showMessage(`AI matching failed: ${error.message}`, "error");
  }
}

async function reviewMatch(matchId, decision) {
  try {
    const result = await apiRequest(`/api/matches/${matchId}/review`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision: decision }),
    });
    showMessage(`${result.message} Schedule activity status is now "${result.activity_status}".`, "success");
    await loadDashboard();
  } catch (error) {
    showMessage(`Planner review failed: ${error.message}`, "error");
  }
}

// --- Event Listeners ---

document.getElementById("reportForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const reportText = document.getElementById("reportText").value.trim();
  const submitBtn = event.target.querySelector('button[type="submit"]');
  const originalHtml = submitBtn.innerHTML;
  
  setLoadingState(submitBtn, true);
  
  try {
    const report = await apiRequest("/api/reports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_type: "text", raw_content: reportText }),
    });
    
    document.getElementById("reportText").value = "";
    
    try {
      const extraction = await apiRequest(`/api/reports/${report.id}/extract`, { method: "POST" });
      showMessage(`Report saved and ${extraction.extracted_count} progress events extracted.`, "success");
    } catch (extractionError) {
      showMessage(`Report saved, but no events were extracted: ${extractionError.message}`, "warning");
    }
    await loadDashboard();
  } catch (error) {
    showMessage(`Could not save report: ${error.message}`, "error");
  } finally {
    setLoadingState(submitBtn, false, originalHtml);
  }
});

document.getElementById("scheduleUploadForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const fileInput = document.getElementById("scheduleFile");
  const file = fileInput.files[0];
  if (!file) {
    showMessage("Please select a schedule file.", "error");
    return;
  }

  const submitBtn = event.target.querySelector('button[type="submit"]');
  const originalHtml = submitBtn.innerHTML;
  setLoadingState(submitBtn, true);

  const formData = new FormData();
  formData.append("file", file);

  try {
    const result = await apiRequest("/api/activities/upload", { method: "POST", body: formData });
    fileInput.value = "";
    showMessage(`${result.imported_count} schedule activities imported.`, "success");
    await loadDashboard();
  } catch (error) {
    showMessage(`Schedule upload failed: ${error.message}`, "error");
  } finally {
    setLoadingState(submitBtn, false, originalHtml);
  }
});

document.getElementById("progressSheetForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const fileInput = document.getElementById("progressSheetFile");
  const file = fileInput.files[0];
  if (!file) {
    showMessage("Please select a progress sheet.", "error");
    return;
  }

  const submitBtn = event.target.querySelector('button[type="submit"]');
  const originalHtml = submitBtn.innerHTML;
  setLoadingState(submitBtn, true);

  const formData = new FormData();
  formData.append("file", file);

  try {
    const result = await apiRequest("/api/reports/upload-sheet", { method: "POST", body: formData });
    fileInput.value = "";
    showMessage(`${result.events_created} progress events created.`, "success");
    await loadDashboard();
  } catch (error) {
    showMessage(`Progress-sheet upload failed: ${error.message}`, "error");
  } finally {
    setLoadingState(submitBtn, false, originalHtml);
  }
});

document.getElementById("refreshButton").addEventListener("click", async (e) => {
  hideMessage();
  const originalHtml = e.target.innerHTML;
  e.target.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Refreshing...';
  await checkApiHealth();
  await loadDashboard();
  e.target.innerHTML = originalHtml;
});

// --- Voice Agent ---

function setupVoiceTimeAgent() {
  const voiceButton = document.getElementById("voiceButton");
  const voiceStatus = document.getElementById("voiceStatus");
  const reportText = document.getElementById("reportText");

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    voiceButton.disabled = true;
    voiceStatus.textContent = "Voice input is supported best in Google Chrome or Microsoft Edge.";
    return;
  }

  const recognition = new SpeechRecognition();
  recognition.lang = "en-IN";
  recognition.continuous = false;
  recognition.interimResults = false;

  voiceButton.addEventListener("click", () => {
    recognition.start();
  });

  recognition.onstart = () => {
    voiceButton.classList.add("listening");
    voiceButton.innerHTML = '<i class="fa-solid fa-microphone-lines"></i> Listening...';
    voiceStatus.textContent = "Listening now. Describe the activity, status, and date.";
  };

  recognition.onresult = (event) => {
    const spokenText = event.results[0][0].transcript;
    if (reportText.value.trim()) {
      reportText.value += ` ${spokenText}`;
    } else {
      reportText.value = spokenText;
    }
    voiceStatus.textContent = "Voice captured successfully. Review text and click Save Report.";
  };

  recognition.onerror = (event) => {
    voiceStatus.textContent = `Voice input error: ${event.error}. Please type the report instead.`;
  };

  recognition.onend = () => {
    voiceButton.classList.remove("listening");
    voiceButton.innerHTML = '<i class="fa-solid fa-microphone"></i> Start Voice Agent';
  };
}

async function initializeApplication() {
  setupVoiceTimeAgent();
  await checkApiHealth();
  await loadDashboard();
}

initializeApplication();