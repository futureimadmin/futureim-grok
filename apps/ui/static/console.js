(() => {
  const state = { fleetId: null, rackId: null, fleets: {} };

  const el = {
    rackSection: document.getElementById("rack-section"),
    rackList: document.getElementById("rack-list"),
    rackFleetLabel: document.getElementById("rack-fleet-label"),
    scopePill: document.getElementById("scope-pill"),
    panelTitle: document.getElementById("panel-title"),
    panelSub: document.getElementById("panel-sub"),
    form: document.getElementById("query-form"),
    input: document.getElementById("query-input"),
    askBtn: document.getElementById("ask-btn"),
    answerPanel: document.getElementById("answer-panel"),
    emptyState: document.getElementById("empty-state"),
    answerBody: document.getElementById("answer-body"),
    citations: document.getElementById("citations"),
    cacheBadge: document.getElementById("cache-badge"),
    metaLatency: document.getElementById("meta-latency"),
    metaSources: document.getElementById("meta-sources"),
    metaType: document.getElementById("meta-type"),
    metaFaith: document.getElementById("meta-faith"),
  };

  function updateScope() {
    const fleet = state.fleets[state.fleetId];
    if (!fleet) {
      el.scopePill.textContent = "No fleet selected";
      el.panelTitle.textContent = "Select a fleet to start";
      el.panelSub.textContent = "Each fleet is an isolated domain. Racks are specialty knowledge areas.";
      el.askBtn.disabled = true;
      el.input.disabled = true;
      return;
    }
    const rack = fleet.racks.find((r) => r.rack_id === state.rackId);
    el.scopePill.textContent = rack
      ? `${fleet.icon} ${fleet.name} › ${rack.name}`
      : `${fleet.icon} ${fleet.name} (all racks)`;
    el.panelTitle.textContent = rack ? `${fleet.name} · ${rack.name}` : fleet.name;
    el.panelSub.textContent = rack ? rack.description : fleet.description;
    el.askBtn.disabled = false;
    el.input.disabled = false;
    el.input.focus();
  }

  function selectFleet(fleetId) {
    state.fleetId = fleetId;
    state.rackId = null;
    document.querySelectorAll(".fleet-item").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.fleet === fleetId);
    });
    const fleet = state.fleets[fleetId];
    el.rackSection.hidden = false;
    el.rackFleetLabel.textContent = fleet ? `· ${fleet.name}` : "";
    el.rackList.innerHTML = "";
    (fleet?.racks || []).forEach((rack) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "rack-item";
      btn.dataset.rack = rack.rack_id;
      btn.innerHTML = `<span><strong>${rack.name}</strong><br><span class="muted" style="font-size:0.75rem">${rack.description}</span></span>`;
      btn.addEventListener("click", () => selectRack(rack.rack_id));
      el.rackList.appendChild(btn);
    });
    document.querySelectorAll(".rack-item").forEach((b) => b.classList.remove("active"));
    updateScope();
  }

  function selectRack(rackId) {
    state.rackId = rackId || null;
    document.querySelectorAll(".rack-item").forEach((btn) => {
      const isAll = btn.classList.contains("rack-all");
      const active = isAll ? !state.rackId : btn.dataset.rack === state.rackId;
      btn.classList.toggle("active", active);
    });
    updateScope();
  }

  async function loadFleets() {
    const res = await fetch("/api/fleets");
    const data = await res.json();
    data.forEach((f) => { state.fleets[f.fleet_id] = f; });
  }

  async function ask(e) {
    e.preventDefault();
    if (!state.fleetId) return;
    const query = el.input.value.trim();
    if (!query) return;

    el.askBtn.disabled = true;
    el.askBtn.textContent = "Thinking…";
    el.emptyState.hidden = true;
    el.answerPanel.hidden = true;
    el.cacheBadge.hidden = true;

    try {
      const res = await fetch("/api/v1/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          fleet_id: state.fleetId,
          rack_id: state.rackId || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Query failed");

      el.answerBody.textContent = data.answer;
      el.metaLatency.textContent = `${Math.round(data.latency_ms)} ms`;
      el.metaSources.textContent = `${data.sources_used} sources`;
      el.metaType.textContent = data.query_type.replaceAll("_", " ");
      el.metaFaith.textContent =
        data.faithfulness_score != null
          ? `faithfulness ${(data.faithfulness_score * 100).toFixed(0)}%`
          : "faithfulness n/a";
      el.cacheBadge.hidden = !data.cache_hit;

      el.citations.innerHTML = "";
      (data.citations || []).forEach((c) => {
        const div = document.createElement("div");
        div.className = "citation";
        div.innerHTML = `<strong>[Source ${c.source_id}]</strong> ${c.path}${
          c.section ? " — " + c.section : ""
        }`;
        el.citations.appendChild(div);
      });
      el.answerPanel.hidden = false;
    } catch (err) {
      el.answerBody.textContent = err.message || "Something went wrong.";
      el.citations.innerHTML = "";
      el.answerPanel.hidden = false;
    } finally {
      el.askBtn.disabled = false;
      el.askBtn.textContent = "Ask";
    }
  }

  document.querySelectorAll(".fleet-item").forEach((btn) => {
    btn.addEventListener("click", () => selectFleet(btn.dataset.fleet));
  });
  document.querySelectorAll(".rack-all").forEach((btn) => {
    btn.addEventListener("click", () => selectRack(""));
  });
  el.form.addEventListener("submit", ask);
  loadFleets().then(updateScope);
})();
