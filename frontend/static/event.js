/* ==========================================================================
   Event details page (/event?id=N).

   Renders one opportunity from /api/event. Every field is optional: the
   database stores "" for anything that could not be read off the official
   source, and a field with no value is left out of the page entirely rather
   than rendered as a blank row. A missing deadline must never look like
   "no deadline".
   ========================================================================== */

const eventId = new URLSearchParams(window.location.search).get("id");

/** One label/value row, or nothing at all when the value is empty. */
function detailRow(label, value) {
  if (!value) return "";
  return `
    <div class="detail-row">
      <dt>${esc(label)}</dt>
      <dd>${esc(value)}</dd>
    </div>`;
}

/** A row whose value is an external link. */
function linkRow(label, url) {
  if (!url) return "";
  const href = safeUrl(url);
  if (href === "#") return "";
  return `
    <div class="detail-row">
      <dt>${esc(label)}</dt>
      <dd><a href="${esc(href)}" target="_blank" rel="noopener noreferrer">
        ${esc(hostOf(href))} ↗</a></dd>
    </div>`;
}

/** Paint the whole page for one event. */
function renderDetail(event) {
  document.title = `${event.title} · Rextech Studios`;
  document.getElementById("pageTitle").textContent = event.category || "Opportunity";
  document.getElementById("pageSub").textContent =
    event.organizer || event.source || "";

  const tags = (event.priority_tags || "")
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean)
    .map((t) => `<a class="tag prio" href="/events?tag=${encodeURIComponent(t)}">${esc(t)}</a>`)
    .join("");

  const action = primaryAction(event);

  // The event's own dates. start/end are the curated fields; `date` is what a
  // scraped page published, and is shown when the structured ones are empty.
  const dates =
    event.start_date && event.end_date && event.start_date !== event.end_date
      ? `${event.start_date} – ${event.end_date}`
      : event.start_date || event.date || "";

  const location = [event.venue, event.city, event.region, event.country]
    .filter(Boolean)
    .join(", ") || event.location || "";

  // A closed application is stated outright rather than left for the user to
  // infer from a date they have to compare against today themselves.
  const closedNote =
    event.status === "Closed"
      ? `<p class="detail-note">This opportunity's application period has
           closed according to the dates on record. Check the official page
           below before assuming it is unavailable.</p>`
      : "";

  document.getElementById("detail").innerHTML = `
    <div class="card-top">
      <span class="tag">${esc(event.category)}</span>
      ${event.subcategory ? `<span class="tag sub">${esc(event.subcategory)}</span>` : ""}
      ${tags}
      ${event.focus > 0 ? '<span class="tag focus">★ FOCUS</span>' : ""}
      ${event.is_verified ? '<span class="tag verified">✓ VERIFIED</span>' : ""}
      <span class="status ${statusClass(event.status)}">
        ${esc(statusLabel(event.status))}</span>
    </div>

    <h2 class="detail-title">${esc(event.title)}</h2>
    ${event.description ? `<p class="detail-desc">${esc(event.description)}</p>` : ""}
    ${closedNote}

    <dl class="detail-grid">
      ${detailRow("Organizer", event.organizer)}
      ${detailRow("Date", dates)}
      ${detailRow("Application deadline", event.deadline)}
      ${detailRow("Location", location)}
      ${detailRow("Mode", event.mode)}
      ${detailRow("Eligibility", event.eligibility)}
      ${detailRow("Cost", event.cost)}
      ${detailRow("Prize / funding", event.prize_or_funding)}
      ${detailRow("Tags", event.tags)}
      ${detailRow("Discovered from", event.source)}
      ${detailRow("Last verified", event.last_verified_at)}
      ${linkRow("Official page", event.source_url || event.website)}
      ${linkRow("Application page", event.application_url || event.registration_url)}
    </dl>

    <div class="card-actions">
      ${action
        ? `<a class="apply-btn${action.primary ? "" : " secondary"}"
              href="${esc(action.href)}" target="_blank"
              rel="noopener noreferrer">${action.label}</a>`
        : `<span class="apply-btn disabled">No official link on record</span>`}
      <a class="details-btn" href="/events">Browse all opportunities</a>
    </div>`;
}

/** Send the ← link back where the user actually came from, when we can tell. */
function wireBackLink() {
  const back = document.getElementById("backLink");
  const from = document.referrer;
  if (!from) return;
  try {
    const url = new URL(from);
    if (url.origin === window.location.origin && url.pathname !== "/event") {
      back.href = url.pathname + url.search;
    }
  } catch (error) {
    /* a referrer we cannot parse just leaves the default /events link */
  }
}

async function loadEvent() {
  wireBackLink();

  if (!eventId) {
    document.getElementById("detail").innerHTML =
      '<p class="empty-state">No opportunity was requested. ' +
      '<a href="/events">Browse all opportunities</a>.</p>';
    return;
  }

  try {
    const data = await apiGet("/api/event?id=" + encodeURIComponent(eventId));
    renderDetail(data.event);
  } catch (error) {
    document.getElementById("pageSub").textContent = "";
    document.getElementById("detail").innerHTML =
      '<p class="empty-state">This opportunity is no longer listed. It may ' +
      'have been removed as a duplicate or pruned after its date passed. ' +
      '<a href="/events">Browse all opportunities</a>.</p>';
  }
}

loadEvent();
