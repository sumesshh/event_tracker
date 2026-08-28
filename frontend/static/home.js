/* ==========================================================================
   Home page logic.

   One call to /api/summary fills the notification box, the four counters and
   the three sections: Recent, Upcoming and Registration Closing Soon.
   ========================================================================== */

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
      text.textContent = `${count} New Event${count === 1 ? "" : "s"}`;
      box.classList.remove("empty");
    } else {
      text.textContent = "No New Events";
      box.classList.add("empty");
    }

    // ---- counters ---------------------------------------------------
    const stats = data.stats || {};
    document.getElementById("statTotal").textContent = stats.total ?? 0;
    document.getElementById("statUpcoming").textContent = stats.upcoming ?? 0;
    document.getElementById("statClosing").textContent = stats.closing_soon ?? 0;
    document.getElementById("statFocus").textContent = stats.focus ?? 0;
    document.getElementById("statNew").textContent = stats.new ?? 0;

    // ---- learning programs counters ----------------------------------
    const learning = stats.learning || {};
    document.getElementById("statLearnTotal").textContent = learning.total ?? 0;
    document.getElementById("statLearnFree").textContent = learning.free ?? 0;
    document.getElementById("statLearnScholar").textContent = learning.scholarships ?? 0;
    document.getElementById("statLearnFunded").textContent = learning.fully_funded ?? 0;
    document.getElementById("statLearnCert").textContent = learning.certificates ?? 0;
    document.getElementById("statLearnClosing").textContent = learning.closing_soon ?? 0;

    // ---- the sections -----------------------------------------------
    renderCards("focusGrid", data.focus,
      "No game, AR/VR or app events open right now.");
    renderCards("recentGrid", data.recent,
      "No events discovered yet. The first crawl may still be running.");
    renderCards("upcomingGrid", data.upcoming,
      "No upcoming events found yet.");
    renderCards("closingGrid", data.closing_soon,
      "Nothing closing in the next two weeks.");

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
