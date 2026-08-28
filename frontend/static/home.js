/* ==========================================================================
   Home page logic.

   One call to /api/summary fills the notification box, the counters, the
   priority sections (Kerala first, then the collections and the rest of the
   geographic order) and the two time-based sections.

   The sections are NOT hard-coded here. The backend sends the order and the
   filter behind each one, straight from config/priority.py, and this file
   renders whatever it is given - which is what keeps a section's contents and
   its "See all" link describing the same query.
   ========================================================================== */

/** Turn a section's filter dict into the /events query string for "See all". */
function seeAllHref(filters) {
  const params = new URLSearchParams();
  Object.entries(filters || {}).forEach(([key, value]) => {
    if (value === true) params.set(key === "focus_only" ? "focus" : key, "1");
    else if (value !== false && value != null && value !== "") {
      // build_where reads the state filter under either name; the events page
      // uses `state`, so translate on the way out.
      params.set(key === "region" ? "state" : key, value);
    }
  });
  return "/events?" + params.toString();
}

/** Build one home page section: heading, "See all" link and a card grid. */
function sectionBlock(section, index) {
  const gridId = `sectionGrid${index}`;
  const more =
    section.total > section.events.length
      ? ` <span class="section-count">${section.total}</span>`
      : "";

  return `
    <section class="block">
      <div class="block-head">
        <h2>★ ${esc(section.title)}${more}</h2>
        <a class="see-all" href="${esc(seeAllHref(section.filters))}">See all</a>
      </div>
      <div id="${gridId}" class="grid"></div>
    </section>`;
}

/** Fetch everything the home page shows and paint it. */
async function loadHome() {
  try {
    const data = await apiGet("/api/summary");

    // ---- notification box + bell badge ------------------------------
    const count = data.new_count || 0;
    setBellCount(count);

    const box = document.getElementById("noticeBox");
    const text = document.getElementById("noticeText");

    if (count > 0) {
      text.textContent = `${count} New Opportunit${count === 1 ? "y" : "ies"}`;
      box.classList.remove("empty");
    } else {
      text.textContent = "No New Opportunities";
      box.classList.add("empty");
    }

    // ---- counters ---------------------------------------------------
    const stats = data.stats || {};
    const setCount = (id, value) => {
      const node = document.getElementById(id);
      if (node) node.textContent = value ?? 0;
    };
    setCount("statTotal", stats.total);
    setCount("statUpcoming", stats.upcoming);
    setCount("statClosing", stats.closing_soon);
    setCount("statFocus", stats.focus);
    setCount("statNew", stats.new);

    // ---- opportunity-type counters ----------------------------------
    // One tile per group, each linking to that filtered list. Groups with no
    // records are skipped rather than shown as a dead "0".
    const groups = stats.opportunities || {};
    document.getElementById("opportunityStrip").innerHTML = Object.entries(groups)
      .filter(([, n]) => n > 0)
      .map(
        ([label, n]) =>
          `<a class="stat small" href="/events?category=${encodeURIComponent(label)}">
             <b>${n}</b><span>${esc(label)}</span></a>`
      )
      .join("");

    // ---- priority sections ------------------------------------------
    const host = document.getElementById("sections");
    const sections = data.sections || [];
    host.innerHTML = sections.map(sectionBlock).join("");
    sections.forEach((section, index) =>
      renderCards(`sectionGrid${index}`, section.events, section.empty_message || "")
    );

    // ---- time-based section ------------------------------------------
    renderCards("recentGrid", data.recent,
      "No opportunities discovered yet. The first crawl may still be running.");

    // ---- footer status line -----------------------------------------
    const foot = document.getElementById("footStatus");
    const lastRun = stats.last_run;
    if (lastRun && lastRun.finished_at) {
      foot.textContent =
        `Last checked ${lastRun.finished_at.replace("T", " ")} UTC · ` +
        `${lastRun.sources_ok} sources OK · ` +
        `${lastRun.new_events} new · next check in 6 hours`;
    }
  } catch (error) {
    document.getElementById("noticeText").textContent =
      "Could not reach the backend.";
  }
}

// ---- Refresh button: ask the backend to crawl every source right now ----
document.getElementById("refreshBtn").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  button.textContent = "Checking…";

  await apiPost("/api/refresh");

  // A full crawl takes a while; reload the numbers after a short delay and
  // then keep the normal polling going.
  setTimeout(() => {
    button.disabled = false;
    button.textContent = "Refresh";
    loadHome();
  }, 8000);
});

// Paint immediately, then refresh the page data every 60 seconds so events
// discovered by a background crawl appear without the user doing anything.
loadHome();
setInterval(loadHome, 60000);
