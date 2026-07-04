/* Skills page — client-side filter + promote/retire actions.
 * No framework, vanilla. All DOM mutations are explicit (no innerHTML).
 */
(function () {
  "use strict";

  const grid = document.getElementById("skillsGrid");
  const search = document.getElementById("skillSearch");
  const countLabel = document.getElementById("skillCount");
  const pills = document.querySelectorAll(".filter-pill");

  let activeFilter = "all";

  function applyFilters() {
    if (!grid) return;
    const q = (search?.value || "").trim().toLowerCase();
    const cards = grid.querySelectorAll(".skill-card");
    let visible = 0;
    cards.forEach((card) => {
      const text = card.dataset.search || "";
      const status = card.dataset.status || "";
      const compiled = card.dataset.compiled === "1";
      const matchesQ = !q || text.indexOf(q) !== -1;
      let matchesFilter = true;
      if (activeFilter === "compiled") matchesFilter = compiled;
      else if (activeFilter !== "all") matchesFilter = status === activeFilter;
      const show = matchesQ && matchesFilter;
      card.style.display = show ? "" : "none";
      if (show) visible += 1;
    });
    if (countLabel) {
      countLabel.textContent =
        visible === cards.length
          ? cards.length + " skills"
          : visible + " of " + cards.length + " shown";
    }
  }

  pills.forEach((pill) => {
    pill.addEventListener("click", () => {
      pills.forEach((p) => {
        p.classList.remove("is-active");
        p.setAttribute("aria-selected", "false");
      });
      pill.classList.add("is-active");
      pill.setAttribute("aria-selected", "true");
      activeFilter = pill.dataset.filter || "all";
      applyFilters();
    });
  });

  if (search) search.addEventListener("input", applyFilters);

  // Promote / retire — confirm then POST then refresh
  function bindAction(selector, endpoint, confirmMsg) {
    document.querySelectorAll(selector).forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.id;
        if (!id) return;
        if (!window.confirm(confirmMsg)) return;
        btn.disabled = true;
        try {
          const res = await fetch(endpoint.replace("{id}", id), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
          });
          if (!res.ok) throw new Error("HTTP " + res.status);
          location.reload();
        } catch (err) {
          btn.disabled = false;
          window.alert("Action failed: " + err.message);
        }
      });
    });
  }
  bindAction(".js-promote", "/api/skills/{id}/promote", "Promote this skill?");
  bindAction(".js-retire",  "/api/skills/{id}/retire",  "Retire this skill?");
})();
