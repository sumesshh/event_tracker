/* ==========================================================================
   Learning Programs page logic.

   Talks to /api/learning, which is backed by database/learning_db.py - real
   programs discovered by the source adapters in scraper/learning_adapters/,
   never generated client-side. The stat strip and the list below are always
   built from the exact same filtered query (see buildFilterParams()), so the
   counters can never drift from what "Learning Programs" actually shows.
   ========================================================================== */

const urlParams = new URLSearchParams(window.location.search);
let searchTimer = null;

const COST_LABELS = {
  FREE: "Free", PAID: "Paid", SCHOLARSHIP: "Scholarship",
  PARTIALLY_FUNDED: "Partially Funded", FULLY_FUNDED: "Fully Funded", UNKNOWN: "Cost Unknown",
};
const FUNDING_LABELS = {
  NONE: "", SCHOLARSHIP: "Scholarship", GRANT: "Grant", STIPEND: "Stipend",
  FULLY_FUNDED: "Fully Funded", PARTIALLY_FUNDED: "Partially Funded", UNKNOWN: "",
};
const STATUS_LABELS = {
  UPCOMING: "Upcoming", OPEN: "Open", CLOSING_SOON: "Closing Soon",
  CLOSED: "Closed", ONGOING: "Ongoing",
};
const STATUS_CLASS = {
  OPEN: "open", UPCOMING: "open", ONGOING: "open",
  CLOSING_SOON: "closing", CLOSED: "closed",
};

/** Fill the drop-downs that depend on what is actually in the database. */
async function loadFilterOptions() {
  const stats = await apiGet("/api/stats");
  const opts = stats.learning_filters || {};

  const fill = (selectId, values) => {
    const select = document.getElementById(selectId);
    values.forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    });
  };

  fill("fCategory", opts.categories || []);
  fill("fProgramType", opts.program_types || []);
  fill("fCountry", opts.countries || []);

  const preset = (id, param) => {
    const value = urlParams.get(param);
    if (value) document.getElementById(id).value = value;
  };
  preset("fCategory", "category");
  preset("fProgramType", "programType");
  preset("fCostType", "costType");
  preset("fFundingType", "fundingType");
  preset("fCertificate", "certificate");
  preset("fLocationType", "locationType");
  preset("fCountry", "country");
  if (urlParams.get("closingSoon") === "1") document.getElementById("fClosingSoon").checked = true;
}

/** The filter arguments shared by the list query and the stats query. */
function buildFilterParams() {
  const params = new URLSearchParams();

  const search = document.getElementById("searchInput").value.trim();
  if (search) params.set("q", search);

  const map = {
    fCategory: "category", fProgramType: "programType", fCostType: "costType",
    fFundingType: "fundingType", fCertificate: "certificate",
    fLocationType: "locationType", fCountry: "country",
  };
  Object.entries(map).forEach(([id, param]) => {
    const value = document.getElementById(id).value;
    if (value !== "all") params.set(param, value);
  });

  if (document.getElementById("fClosingSoon").checked) params.set("closingSoon", "1");

  return params;
}

function filtersActive() {
  const narrowed = ["fCategory", "fProgramType", "fCostType", "fFundingType",
    "fCertificate", "fLocationType", "fCountry"]
    .some((id) => document.getElementById(id).value !== "all");

  return (
    narrowed ||
    document.getElementById("fClosingSoon").checked ||
    document.getElementById("searchInput").value.trim() !== ""
  );
}

/** One learning-program card. */
function learningCard(program) {
  const fundingLabel = FUNDING_LABELS[program.funding_type] || "";
  const costLabel = COST_LABELS[program.cost_type] || program.cost_type;
  const isGoodDeal = ["FREE", "SCHOLARSHIP", "FULLY_FUNDED"].includes(program.cost_type)
    || ["SCHOLARSHIP", "FULLY_FUNDED", "GRANT", "STIPEND"].includes(program.funding_type);

  const skills = (program.skills || []).slice(0, 4)
    .map((s) => `<span class="tag skill">${esc(s)}</span>`).join("");

  const cert = program.certificate_available;
  const certLine = cert === true ? "🎓 Certificate available"
    : cert === false ? "No certificate" : "Certificate status: unknown";

  const location = [program.city, program.country].filter(Boolean).join(", ")
    || program.country || "Location unknown";

  const deadline = program.application_deadline
    ? `Deadline: ${esc(program.application_deadline)}`
    : program.status === "ONGOING" ? "Ongoing - no fixed deadline" : "No published deadline";

  const eligibility = program.eligibility || {};
  const eligibilityText = eligibility.description || eligibility.programAlignedTo || "";

  const viewLink = safeUrl(program.official_url);
  const applyLink = program.application_url ? safeUrl(program.application_url) : "";
  const verifiedBadge = program.verified
    ? '<span class="tag funding-good" title="Verified against the official source">✓ Verified</span>' : "";

  return `
    <article class="card">
      <div class="card-top">
        <span class="tag">${esc(program.program_type || "Program")}</span>
        <span class="tag${isGoodDeal ? " funding-good" : ""}">${esc(costLabel)}</span>
        ${fundingLabel ? `<span class="tag${isGoodDeal ? " funding-good" : ""}">${esc(fundingLabel)}</span>` : ""}
        ${verifiedBadge}
        <span class="status ${STATUS_CLASS[program.status] || "open"}">
          ${esc(STATUS_LABELS[program.status] || program.status)}
        </span>
      </div>

      <h3>${esc(program.title)}</h3>

      <div class="meta">
        <div>🏫 ${esc(program.provider)}</div>
        <div>📍 ${esc(location)} · ${esc(program.location_type || "Unknown")}</div>
        <div>📅 ${deadline}</div>
        <div>${certLine}</div>
        ${eligibilityText ? `<div>👤 ${esc(eligibilityText)}</div>` : ""}
      </div>

      ${skills ? `<div class="card-top">${skills}</div>` : ""}

      <div class="card-top">
        <a class="apply-btn" style="flex:1" href="${esc(viewLink)}" target="_blank" rel="noopener noreferrer">
          View Program
        </a>
        ${applyLink ? `<a class="apply-btn" style="flex:1;background:linear-gradient(135deg,#2fd47a,#22b868)" href="${esc(applyLink)}" target="_blank" rel="noopener noreferrer">Apply / Enroll</a>` : ""}
      </div>
    </article>`;
}

function renderLearningCards(programs) {
  const container = document.getElementById("cardGrid");
  if (!programs || programs.length === 0) {
    container.innerHTML = `<div class="empty-state">${
      filtersActive()
        ? "No learning programs match these filters."
        : "No learning programs discovered yet. Run the ingestion pipeline (python -m scraper.learning_pipeline) or wait for the next scheduled crawl."
    }</div>`;
    return;
  }
  container.innerHTML = programs.map(learningCard).join("");
}

function paintStats(stats) {
  document.getElementById("statLTotal").textContent = stats.total ?? 0;
  document.getElementById("statLFree").textContent = stats.free ?? 0;
  document.getElementById("statLScholar").textContent = stats.scholarships ?? 0;
  document.getElementById("statLFunded").textContent = stats.fully_funded ?? 0;
  document.getElementById("statLCert").textContent = stats.certificates ?? 0;
  document.getElementById("statLClosing").textContent = stats.closing_soon ?? 0;
}

async function loadLearning() {
  const params = buildFilterParams();
  params.set("limit", "1000");
  const data = await apiGet("/api/learning?" + params.toString());

  document.getElementById("resultCount").textContent =
    `${data.count} learning program${data.count === 1 ? "" : "s"} found`;
  document.getElementById("pageSub").textContent =
    `${data.stats.total} programs matching these filters · ${data.stats.verified} verified against their official source`;

  renderLearningCards(data.programs);
  // The dashboard-style counters describe this exact filtered set, coming
  // back from the server in the same response as the list (rule #10).
  paintStats(data.stats);
}

async function init() {
  await loadFilterOptions();
  await loadLearning();
}

document.getElementById("searchInput").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadLearning, 250);
});

["fCategory", "fProgramType", "fCostType", "fFundingType", "fCertificate",
  "fLocationType", "fCountry", "fClosingSoon"].forEach((id) => {
  document.getElementById(id).addEventListener("change", loadLearning);
});

document.getElementById("clearBtn").addEventListener("click", () => {
  document.getElementById("searchInput").value = "";
  ["fCategory", "fProgramType", "fCostType", "fFundingType", "fCertificate",
    "fLocationType", "fCountry"].forEach((id) => { document.getElementById(id).value = "all"; });
  document.getElementById("fClosingSoon").checked = false;
  loadLearning();
});

init();
