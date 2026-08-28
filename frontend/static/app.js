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
 * The link an event's primary button should open, and what to call it.
 *
 * An `application_url` is a real application form, so that button says "Apply
 * Now". Anything else is further reading and says so instead of promising a
 * form that is not there. A closed opportunity never gets an Apply button at
 * all - sending someone to an application that shut is worse than telling
 * them it shut.
 */
function primaryAction(event) {
  const applyUrl = event.application_url || event.registration_url;
  const siteUrl = event.source_url || event.website;
  const closed = event.status === "Closed";

  if (applyUrl && !closed) {
    return { href: safeUrl(applyUrl), label: "Apply Now", primary: true };
  }
  const fallback = siteUrl || applyUrl;
  if (fallback) {
    return { href: safeUrl(fallback), label: "View Official Page", primary: false };
  }
  return null;
}

/**
 * Build one event card.
 *
 * Shows title, category, location, date and source. "Details" opens the
 * in-app details page; the second button leaves for the official source.
 */
function eventCard(event) {
  const isNew = event.is_new ? '<span class="tag new">NEW</span>' : "";
  // A star marks the studio's own line of work: games, AR/VR and apps.
  const isFocus = event.focus > 0 ? '<span class="tag focus">★ FOCUS</span>' : "";
  // Curated rows are checked against the official source; scraped rows are not.
  const isVerified = event.is_verified
    ? '<span class="tag verified">✓ VERIFIED</span>'
    : "";
  const sub = event.subcategory
    ? `<span class="tag sub">${esc(event.subcategory)}</span>`
    : "";
  // The priority collections the record's own fields put it in.
  const tags = (event.priority_tags || "")
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean)
    .map((t) => `<span class="tag prio">${esc(t)}</span>`)
    .join("");

  // Optional detail lines. Anything unverified is simply absent - an empty
  // field must never render as a confident-looking blank or a guess.
  const extra = [
    event.organizer ? `<div>🏛 ${esc(event.organizer)}</div>` : "",
    event.deadline ? `<div>⏳ Deadline: ${esc(event.deadline)}</div>` : "",
    event.cost ? `<div>💳 ${esc(event.cost)}</div>` : "",
    event.prize_or_funding ? `<div>🏆 ${esc(event.prize_or_funding)}</div>` : "",
  ].join("");

  const description = event.description
    ? `<p class="card-desc">${esc(event.description)}</p>`
    : "";

  const action = primaryAction(event);
  const outbound = action
    ? `<a class="apply-btn${action.primary ? "" : " secondary"}"
          href="${esc(action.href)}" target="_blank"
          rel="noopener noreferrer">${action.label}</a>`
    : `<span class="apply-btn disabled">Link not available</span>`;

  return `
    <article class="card${event.focus > 0 ? " card-focus" : ""}">
      <div class="card-top">
        <span class="tag">${esc(event.category)}</span>
        ${sub}
        ${tags}
        ${isFocus}
        ${isVerified}
        ${isNew}
        <span class="status ${statusClass(event.status)}">
          ${esc(statusLabel(event.status))}
        </span>
      </div>

      <h3><a class="card-title-link" href="/event?id=${encodeURIComponent(event.id)}">${esc(event.title)}</a></h3>
      ${description}

      <div class="meta">
        <div>📍 ${esc(event.location || "Not specified")}</div>
        <div>📅 ${esc(event.date || "Date TBA")}</div>
        <div>🌐 ${esc(event.source)}</div>
        ${extra}
      </div>

      <div class="card-actions">
        <a class="details-btn" href="/event?id=${encodeURIComponent(event.id)}">Details</a>
        ${outbound}
      </div>
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
