/* ==========================================================================
   Shared helpers used by both pages.
   Plain browser JavaScript - no build step, no framework, no CDN.
   ========================================================================== */

/** GET a JSON endpoint and return the parsed body. */
async function apiGet(path) {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error("Request failed: " + response.status);
  return response.json();
}

/** POST to an action endpoint (mark-seen / refresh). */
async function apiPost(path) {
  const response = await fetch(path, { method: "POST" });
  return response.json();
}

/** Escape text before putting it into innerHTML - scraped titles are untrusted. */
function esc(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Only allow http/https links through.
 * Registration URLs come from scraped pages, so a hostile source could in
 * theory hand us a "javascript:" URL; this turns those into a dead link.
 */
function safeUrl(url) {
  try {
    const parsed = new URL(url, window.location.origin);
    return parsed.protocol === "http:" || parsed.protocol === "https:"
      ? parsed.href
      : "#";
  } catch (e) {
    return "#";
  }
}

/** Map a status string to the CSS class that colours it. */
function statusClass(status) {
  if (status === "Closing Soon") return "closing";
  if (status === "Closed") return "closed";
  return "open";
}

/** Human label shown in the "Registration Status" column. */
function statusLabel(status) {
  if (status === "Closing Soon") return "Closing Soon";
  if (status === "Closed") return "Closed";
  return "Registration Open";
}

/** Turn "https://unity.com/events" into "unity.com" for compact display. */
function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch (e) {
    return url || "";
  }
}

/**
 * Build one event card.
 * Shows: title, category, location, date, source and an Apply Now button
 * that opens the official event website in a new tab.
 */
function eventCard(event) {
  const isNew = event.is_new ? '<span class="tag new">NEW</span>' : "";
  // A star marks the studio's own line of work: games, AR/VR and apps.
  const isFocus = event.focus > 0 ? '<span class="tag focus">★ FOCUS</span>' : "";
  const link = safeUrl(event.registration_url || event.website);

  return `
    <article class="card${event.focus > 0 ? " card-focus" : ""}">
      <div class="card-top">
        <span class="tag">${esc(event.category)}</span>
        ${isFocus}
        ${isNew}
        <span class="status ${statusClass(event.status)}">
          ${esc(statusLabel(event.status))}
        </span>
      </div>

      <h3>${esc(event.title)}</h3>

      <div class="meta">
        <div>📍 ${esc(event.location || "Not specified")}</div>
        <div>📅 ${esc(event.date || "Date TBA")}</div>
        <div>🌐 ${esc(event.source)}</div>
      </div>

      <a class="apply-btn" href="${esc(link)}" target="_blank" rel="noopener noreferrer">
        Apply Now
      </a>
    </article>`;
}

/** Render a list of events into a container, with an empty state fallback. */
function renderCards(containerId, events, emptyMessage) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (!events || events.length === 0) {
    container.innerHTML =
      `<div class="empty-state">${esc(emptyMessage || "Nothing here yet.")}</div>`;
    return;
  }
  container.innerHTML = events.map(eventCard).join("");
}

/** Update the 🔔 badge in the header. */
function setBellCount(count) {
  const badge = document.getElementById("bellCount");
  if (!badge) return;
  badge.textContent = count;
  badge.classList.toggle("empty", !count);
}
