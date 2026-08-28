/* ==========================================================================
   Events page logic.

   Serves two modes from one file:

     /new     - the New Events page opened from the 🔔 bell.
                Shows a table with Event Name, Category, Location, Date,
                Registration Status, Website and an Apply Now button.
     /events  - the full searchable / filterable list, shown as cards.
   ========================================================================== */

// True when we are on the New Events page.
const IS_NEW_PAGE = window.location.pathname.replace(/\/$/, "") === "/new";

// Query string of the current URL, used to pre-set filters when the user
// arrives from a "See all" link on the home page.
const urlParams = new URLSearchParams(window.location.search);

// Debounce handle for the search box.
let searchTimer = null;

/*
 * Timestamp of the batch shown on the New Events page.
 *
 * Opening the page clears the 🔔 badge, which used to wipe `is_new` and leave
 * the page querying for events that no longer existed - so the table went
 * empty as soon as a filter changed or the page was reloaded. The backend now
 * hands back the cutoff of the batch it just cleared, and we filter on that
 * instead, which survives both.
 */
let newCutoff = null;

/* ---------------------------------------------------------------- setup */

/** Fill the category / country / state drop-downs from /api/stats. */
async function loadFilterOptions() {
  const stats = await apiGet("/api/stats");

  const fill = (selectId, values) => {
    const select = document.getElementById(selectId);
    values.forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    });
  };

  fill("fCategory", stats.categories || []);
  fill("fCountry", stats.countries || []);
  fill("fState", stats.regions || []);

  // Apply any filters that came in through the URL. Setting a <select> to a
  // value it does not have silently leaves it on "all", so unknown values in
  // the query string simply do nothing.
  const preset = (id, param) => {
    const value = urlParams.get(param);
    if (value) document.getElementById(id).value = value;
  };
  preset("fCategory", "category");
  preset("fStatus", "status");
  preset("fCountry", "country");
  preset("fState", "state");
  preset("fMode", "mode");

  if (urlParams.get("upcoming") === "1") document.getElementById("fUpcoming").checked = true;
  if (urlParams.get("focus") === "1") document.getElementById("fFocus").checked = true;
}

/** Build the /api/events query string from the current control values. */
function buildQuery() {
  const params = new URLSearchParams();

  if (IS_NEW_PAGE) {
    // Once the badge has been cleared we ask for "discovered since <cutoff>";
    // only on the very first paint, before mark-seen has answered, do we fall
    // back to the is_new flag.
    if (newCutoff) params.set("since", newCutoff);
    else params.set("new", "1");
  }

  const search = document.getElementById("searchInput").value.trim();
  if (search) params.set("q", search);

  const category = document.getElementById("fCategory").value;
  if (category !== "all") params.set("category", category);

  const country = document.getElementById("fCountry").value;
  if (country !== "all") params.set("country", country);

  const state = document.getElementById("fState").value;
  if (state !== "all") params.set("state", state);

  const mode = document.getElementById("fMode").value;
  if (mode !== "all") params.set("mode", mode);

  const status = document.getElementById("fStatus").value;
  if (status !== "all") params.set("status", status);

  if (document.getElementById("fUpcoming").checked) params.set("upcoming", "1");

  // Games / AR-VR / apps only.
  if (document.getElementById("fFocus").checked) params.set("focus", "1");

  // "See all" from Recent Events sorts by discovery time instead of date.
  if (urlParams.get("order") === "recent") params.set("order", "recent");

  // No cap: the events page shows everything that matches, not the first page.
  params.set("limit", "2000");

  return params.toString();
}

/** True when the user has narrowed the list with at least one control. */
function filtersActive() {
  const narrowed = ["fCategory", "fCountry", "fState", "fMode", "fStatus"]
    .some((id) => document.getElementById(id).value !== "all");

  return (
    narrowed ||
    document.getElementById("fUpcoming").checked ||
    document.getElementById("fFocus").checked ||
    document.getElementById("searchInput").value.trim() !== ""
  );
}

/* --------------------------------------------------------------- render */

/** One table row for the New Events page. */
function eventRow(event) {
  const link = safeUrl(event.registration_url || event.website);
  const site = safeUrl(event.website || event.registration_url);

  return `
    <tr>
      <td class="title-cell">${event.focus > 0 ? '<span class="focus-star" title="Game / AR-VR / App event">★</span> ' : ""}${esc(event.title)}</td>
      <td><span class="tag">${esc(event.category)}</span></td>
      <td>${esc(event.location || "Not specified")}</td>
      <td>${esc(event.date || "Date TBA")}</td>
      <td><span class="status ${statusClass(event.status)}">
            ${esc(statusLabel(event.status))}</span></td>
      <td><a class="src-link" href="${esc(site)}" target="_blank"
             rel="noopener noreferrer">${esc(hostOf(site))}</a></td>
      <td><a class="table-apply" href="${esc(link)}" target="_blank"
             rel="noopener noreferrer">Apply Now</a></td>
    </tr>`;
}

/** Fetch the filtered events and draw them as a table or as cards. */
async function loadEvents() {
  const query = buildQuery();
  const data = await apiGet("/api/events?" + query);

  document.getElementById("resultCount").textContent =
    `${data.count} event${data.count === 1 ? "" : "s"} found`;

  const tableWrap = document.getElementById("tableWrap");
  const cardGrid = document.getElementById("cardGrid");

  if (IS_NEW_PAGE) {
    // Table view - exactly the columns the brief asked for.
    tableWrap.hidden = false;
    cardGrid.innerHTML = "";

    const body = document.getElementById("tableBody");
    // The empty state has to distinguish "nothing was found" from "your
    // filters excluded everything", otherwise a stray filter looks like a bug.
    const empty = filtersActive()
      ? "No new events match these filters. Clear them to see the whole batch."
      : "No new events right now. The next check runs within 6 hours.";

    body.innerHTML = data.events.length
      ? data.events.map(eventRow).join("")
      : `<tr><td colspan="7" style="text-align:center;padding:36px;color:var(--muted)">
           ${empty}</td></tr>`;
  } else {
    // Card view.
    tableWrap.hidden = true;
    renderCards(
      "cardGrid",
      data.events,
      filtersActive()
        ? "No events match these filters."
        : "No events stored yet. The first crawl may still be running."
    );
  }
}

/* ----------------------------------------------------------- page setup */

async function init() {
  // Page heading depends on which page we are on.
  if (IS_NEW_PAGE) {
    document.getElementById("pageTitle").textContent = "New Events";
    document.getElementById("pageSub").textContent =
      "Discovered since you last checked";
  } else {
    document.getElementById("pageTitle").textContent = "All Events";
    document.getElementById("pageSub").textContent =
      "Search and filter every event we track";
  }

  await loadFilterOptions();

  // Opening the New Events page counts as reading them, so clear the badge
  // first and remember which batch we are showing. Doing this before the
  // first query - rather than after it - is what keeps the list from
  // disappearing on the next reload or filter change.
  if (IS_NEW_PAGE) {
    try {
      const seen = await apiPost("/api/mark-seen");
      newCutoff = seen.cutoff || null;
    } catch (error) {
      newCutoff = null;   // fall back to is_new; the list still renders
    }
  }

  await loadEvents();
}

/* -------------------------------------------------------------- events */

// Search by title, debounced so we do not hit the API on every keystroke.
document.getElementById("searchInput").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadEvents, 250);
});

// Every drop-down and the toggle re-run the query immediately.
["fCategory", "fCountry", "fState", "fMode", "fStatus", "fUpcoming", "fFocus"]
  .forEach((id) => {
    document.getElementById(id).addEventListener("change", loadEvents);
  });

// Clear resets every control back to its default.
document.getElementById("clearBtn").addEventListener("click", () => {
  document.getElementById("searchInput").value = "";
  ["fCategory", "fCountry", "fState", "fMode", "fStatus"]
    .forEach((id) => { document.getElementById(id).value = "all"; });
  document.getElementById("fUpcoming").checked = false;
  document.getElementById("fFocus").checked = false;
  loadEvents();
});

init();
