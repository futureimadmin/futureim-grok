(() => {
  const state = {
    fleetId: null,
    rackId: null,
    tierId: null,
    fleets: {},
    mode: "ask",
    language: "python",
  };

  const el = {
    fleetList: document.getElementById("fleet-list"),
    rackSection: document.getElementById("rack-section"),
    rackList: document.getElementById("rack-list"),
    rackFleetLabel: document.getElementById("rack-fleet-label"),
    tierSection: document.getElementById("tier-section"),
    tierList: document.getElementById("tier-list"),
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
    platformBadge: document.getElementById("platform-badge"),
    metaLatency: document.getElementById("meta-latency"),
    metaSources: document.getElementById("meta-sources"),
    metaType: document.getElementById("meta-type"),
    metaFaith: document.getElementById("meta-faith"),
    metaMode: document.getElementById("meta-mode"),
    metaRagas: document.getElementById("meta-ragas"),
    bianPanel: document.getElementById("bian-panel"),
    bianChips: document.getElementById("bian-chips"),
    bianVersion: document.getElementById("bian-version"),
    bianScopeLabel: document.getElementById("bian-scope-label"),
    bianHint: document.getElementById("bian-hint"),
    hintChip: document.getElementById("hint-chip"),
    langSelect: document.getElementById("lang-select"),
    tracePanel: document.getElementById("trace-panel"),
    traceBody: document.getElementById("trace-body"),
  };

  function activeDomains() {
    const fleet = state.fleets[state.fleetId];
    if (!fleet) return [];
    if (state.rackId) {
      const rack = (fleet.racks || []).find((r) => r.rack_id === state.rackId);
      if (rack && rack.bian_service_domains && rack.bian_service_domains.length) {
        return rack.bian_service_domains;
      }
    }
    if (state.tierId) {
      const tier = (fleet.tiers || []).find((t) => t.tier_id === state.tierId);
      if (tier && tier.bian_service_domains && tier.bian_service_domains.length) {
        return tier.bian_service_domains;
      }
    }
    return fleet.bian_domains_all || [];
  }

  function renderBianPanel() {
    const fleet = state.fleets[state.fleetId];
    if (!fleet || fleet.platform !== "bian") {
      el.bianPanel.hidden = true;
      el.platformBadge.hidden = true;
      return;
    }
    el.platformBadge.hidden = false;
    el.platformBadge.textContent = fleet.is_reference
      ? `BIAN v${fleet.bian_version || "12"} · Reference`
      : `BIAN v${fleet.bian_version || "12"}`;
    el.bianPanel.hidden = false;
    const domains = activeDomains();
    el.bianChips.innerHTML = "";
    if (!domains.length) {
      el.bianChips.innerHTML = '<span class="muted">No domains mapped for this scope</span>';
    } else {
      domains.forEach((d) => {
        const chip = document.createElement("span");
        chip.className = "bian-chip";
        chip.textContent = d;
        el.bianChips.appendChild(chip);
      });
    }
    el.bianVersion.textContent = `v${fleet.bian_version || "12"}`;
    const rack = (fleet.racks || []).find((r) => r.rack_id === state.rackId);
    el.bianScopeLabel.textContent = rack
      ? `· ${fleet.name} › ${rack.name}`
      : `· ${fleet.name}`;
    el.bianHint.textContent = fleet.is_reference
      ? "Reference fleet — canonical BIAN knowledge used by banking dual-pull."
      : "Dual-pull enabled: product rack + these BIAN domains from the reference fleet.";
  }

  function updateScope() {
    const fleet = state.fleets[state.fleetId];
    if (!fleet) {
      el.scopePill.textContent = "No fleet selected";
      el.panelTitle.textContent = "Select a fleet to start";
      el.panelSub.textContent =
        "Each fleet is an isolated domain. Racks are specialty knowledge areas. Banking fleets sit on the BIAN platform.";
      el.askBtn.disabled = true;
      el.input.disabled = true;
      el.bianPanel.hidden = true;
      el.platformBadge.hidden = true;
      return;
    }
    const rack = (fleet.racks || []).find((r) => r.rack_id === state.rackId);
    const tier = (fleet.tiers || []).find((t) => t.tier_id === state.tierId);
    let pill = `${fleet.icon} ${fleet.name}`;
    if (rack) pill += ` › ${rack.name}`;
    if (tier) pill += ` · ${tier.name}`;
    el.scopePill.textContent = pill;
    el.panelTitle.textContent = rack ? `${fleet.name} · ${rack.name}` : fleet.name;
    el.panelSub.textContent = rack ? rack.description : fleet.description;
    el.askBtn.disabled = false;
    el.input.disabled = false;
    el.input.focus();
    renderBianPanel();
    updateModeUI();
  }

  function selectFleet(fleetId) {
    state.fleetId = fleetId;
    state.rackId = null;
    state.tierId = null;
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
      const domains = (rack.bian_service_domains || []).slice(0, 3).join(", ");
      btn.innerHTML = `<span><strong>${rack.name}</strong><br><span class="muted" style="font-size:0.75rem">${rack.description}</span>${
        domains
          ? `<br><span class="rack-domains">${domains}${(rack.bian_service_domains || []).length > 3 ? "…" : ""}</span>`
          : ""
      }</span>`;
      btn.addEventListener("click", () => selectRack(rack.rack_id));
      el.rackList.appendChild(btn);
    });
    document.querySelectorAll(".rack-item").forEach((b) => b.classList.remove("active"));

    const tiers = fleet?.tiers || [];
    if (tiers.length) {
      el.tierSection.hidden = false;
      el.tierList.innerHTML = "";
      tiers.forEach((t) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "tier-item";
        btn.dataset.tier = t.tier_id;
        btn.innerHTML = `<strong>${t.name}</strong><br><span class="muted" style="font-size:0.75rem">${t.description || ""}</span>`;
        btn.addEventListener("click", () => selectTier(t.tier_id));
        el.tierList.appendChild(btn);
      });
    } else {
      el.tierSection.hidden = true;
      el.tierList.innerHTML = "";
    }

    updateScope();
  }

  function selectRack(rackId) {
    state.rackId = rackId || null;
    document.querySelectorAll(".rack-item").forEach((btn) => {
      const isAll = btn.classList.contains("rack-all");
      const active = isAll ? !state.rackId : btn.dataset.rack === state.rackId;
      btn.classList.toggle("active", active);
    });
    const fleet = state.fleets[state.fleetId];
    const rack = fleet && (fleet.racks || []).find((r) => r.rack_id === state.rackId);
    if (rack && rack.tier_ids && rack.tier_ids.length) {
      state.tierId = rack.tier_ids[0];
      document.querySelectorAll(".tier-item").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.tier === state.tierId);
      });
    }
    updateScope();
  }

  function selectTier(tierId) {
    state.tierId = tierId || null;
    document.querySelectorAll(".tier-item").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tier === state.tierId);
    });
    updateScope();
  }

  function updateModeUI() {
    const mode = state.mode;
    el.langSelect.hidden = mode !== "codegen";
    if (mode === "codegen") {
      el.askBtn.textContent = "Generate stubs";
      el.hintChip.textContent = "Codegen emits only active BIAN domain service stubs";
      el.input.placeholder =
        "e.g. generate Loan and Credit Management service stubs for this rack";
    } else if (mode === "agentic") {
      el.askBtn.textContent = "Run agent";
      el.hintChip.textContent = "Agentic: plan → dual-pull → generate → RAGAS";
      el.input.placeholder = "Ask with multi-step reasoning and accuracy checks…";
    } else {
      el.askBtn.textContent = "Ask";
      el.hintChip.textContent = "Tip: pick a rack for sharper answers";
      el.input.placeholder = "Ask anything about the selected fleet or rack…";
    }
  }

  async function loadFleets() {
    const res = await fetch("/api/fleets");
    const data = await res.json();
    data.forEach((f) => {
      state.fleets[f.fleet_id] = f;
    });
  }

  function renderMarkdownLite(text) {
    if (!text) return "";
    const escaped = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    return escaped
      .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/^### (.+)$/gm, "<h3>$1</h3>")
      .replace(/^# (.+)$/gm, "<h3>$1</h3>")
      .replace(/\n/g, "<br>");
  }

  async function ask(e) {
    e.preventDefault();
    if (!state.fleetId) return;
    const query = el.input.value.trim();
    if (!query) return;

    el.askBtn.disabled = true;
    const busy =
      state.mode === "codegen"
        ? "Generating…"
        : state.mode === "agentic"
        ? "Agent working…"
        : "Thinking…";
    el.askBtn.textContent = busy;
    el.emptyState.hidden = true;
    el.answerPanel.hidden = true;
    el.cacheBadge.hidden = true;
    el.tracePanel.hidden = true;

    try {
      const res = await fetch("/api/v1/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          fleet_id: state.fleetId,
          rack_id: state.rackId || null,
          tier_id: state.tierId || null,
          mode: state.mode,
          language: state.language,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Query failed");

      el.answerBody.innerHTML = renderMarkdownLite(data.answer || "");
      el.metaLatency.textContent = `${Math.round(data.latency_ms || 0)} ms`;
      el.metaSources.textContent = `${data.sources_used || 0} sources`;
      el.metaType.textContent = (data.query_type || "answer").replaceAll("_", " ");
      el.metaFaith.textContent =
        data.faithfulness_score != null
          ? `faithfulness ${(data.faithfulness_score * 100).toFixed(0)}%`
          : "";
      el.metaMode.textContent = data.mode ? `mode: ${data.mode}` : "";
      if (data.ragas && data.ragas.ragas_score != null) {
        el.metaRagas.textContent = `RAGAS ${(data.ragas.ragas_score * 100).toFixed(0)}%${
          data.threshold_met ? " ✓" : ""
        }`;
      } else {
        el.metaRagas.textContent = "";
      }
      el.cacheBadge.hidden = !data.cache_hit;

      if (data.reasoning_trace && data.reasoning_trace.length) {
        el.tracePanel.hidden = false;
        el.traceBody.textContent = data.reasoning_trace
          .map((t) => (typeof t === "string" ? t : JSON.stringify(t)))
          .join("\n");
      }

      el.citations.innerHTML = "";
      (data.citations || []).forEach((c) => {
        const div = document.createElement("div");
        div.className = "citation";
        div.innerHTML = `<strong>[Source ${c.source_id}]</strong> ${c.path || ""}${
          c.section ? " — " + c.section : ""
        }`;
        el.citations.appendChild(div);
      });
      if (data.bian_domains && data.bian_domains.length) {
        const div = document.createElement("div");
        div.className = "citation bian-cite";
        div.innerHTML =
          "<strong>BIAN domains</strong> " +
          data.bian_domains.map((d) => `<span class="bian-chip">${d}</span>`).join(" ");
        el.citations.appendChild(div);
      }

      el.answerPanel.hidden = false;
    } catch (err) {
      el.answerBody.textContent = err.message || "Something went wrong.";
      el.citations.innerHTML = "";
      el.answerPanel.hidden = false;
    } finally {
      el.askBtn.disabled = false;
      updateModeUI();
    }
  }

  document.querySelectorAll(".fleet-item").forEach((btn) => {
    btn.addEventListener("click", () => selectFleet(btn.dataset.fleet));
  });
  document.querySelectorAll(".rack-all").forEach((btn) => {
    btn.addEventListener("click", () => selectRack(""));
  });
  el.form.addEventListener("submit", ask);

  document.querySelectorAll('input[name="mode"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      state.mode = radio.value;
      updateModeUI();
    });
  });
  el.langSelect.addEventListener("change", () => {
    state.language = el.langSelect.value;
  });

  loadFleets().then(updateScope);
})();
