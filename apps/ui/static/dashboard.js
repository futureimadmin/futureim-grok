/* Accuracy Dashboard client */

(function () {
  const fleets = window.__FLEETS__ || [];

  const $ = (id) => document.getElementById(id);

  function pct(v) {
    if (v == null || Number.isNaN(v)) return "—";
    return (v * 100).toFixed(1) + "%";
  }

  function setBar(id, value) {
    const el = $(id);
    if (!el) return;
    const p = Math.max(0, Math.min(100, (value || 0) * 100));
    el.style.width = p + "%";
    el.classList.remove("low", "mid", "high");
    if (p < 50) el.classList.add("low");
    else if (p < 80) el.classList.add("mid");
    else el.classList.add("high");
  }

  function renderSummary(data) {
    $("overall-pct").textContent =
      data.total_runs === 0 ? "—" : data.overall_accuracy_pct.toFixed(1) + "%";
    $("pass-rate").textContent =
      data.total_runs === 0 ? "—" : pct(data.pass_rate);
    $("total-runs").textContent = String(data.total_runs || 0);
    $("avg-latency").textContent =
      data.total_runs === 0 ? "—" : Math.round(data.avg_latency_ms) + " ms";
    $("threshold-label").textContent = (data.threshold || 0.8).toFixed(2);

    $("m-faith").textContent = pct(data.avg_faithfulness);
    $("m-rel").textContent = pct(data.avg_answer_relevance);
    $("m-prec").textContent = pct(data.avg_context_precision);
    $("m-recall").textContent = pct(data.avg_context_recall);
    setBar("bar-faith", data.avg_faithfulness);
    setBar("bar-rel", data.avg_answer_relevance);
    setBar("bar-prec", data.avg_context_precision);
    setBar("bar-recall", data.avg_context_recall);

    const ft = $("fleet-tbody");
    const by = data.by_fleet || {};
    const keys = Object.keys(by);
    if (!keys.length) {
      ft.innerHTML = '<tr><td colspan="4" class="muted">No data yet</td></tr>';
    } else {
      ft.innerHTML = keys
        .map((fid) => {
          const b = by[fid];
          return `<tr>
            <td>${escapeHtml(fid)}</td>
            <td>${b.runs}</td>
            <td>${pct(b.avg_ragas)}</td>
            <td>${pct(b.pass_rate)}</td>
          </tr>`;
        })
        .join("");
    }

    const rt = $("recent-tbody");
    const recent = data.recent || [];
    if (!recent.length) {
      rt.innerHTML =
        '<tr><td colspan="11" class="muted">Run an evaluation to populate</td></tr>';
    } else {
      rt.innerHTML = recent
        .map((r) => {
          const t = new Date((r.ts || 0) * 1000).toLocaleTimeString();
          const pass = r.passed
            ? '<span class="badge-pass">✓</span>'
            : '<span class="badge-fail">✗</span>';
          return `<tr>
            <td>${t}</td>
            <td title="${escapeHtml(r.query || "")}">${escapeHtml(
            (r.query || "").slice(0, 40)
          )}${(r.query || "").length > 40 ? "…" : ""}</td>
            <td>${escapeHtml(r.fleet_id || "—")}</td>
            <td>${pct(r.ragas_score)}</td>
            <td>${pct(r.faithfulness)}</td>
            <td>${pct(r.answer_relevance)}</td>
            <td>${pct(r.context_precision)}</td>
            <td>${pct(r.context_recall)}</td>
            <td>${pass}</td>
            <td>${Math.round(r.latency_ms || 0)}</td>
            <td>${r.attempts || 1}</td>
          </tr>`;
        })
        .join("");
    }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function loadSummary() {
    try {
      const res = await fetch("/api/accuracy/summary");
      const data = await res.json();
      renderSummary(data);
    } catch (e) {
      console.error(e);
    }
  }

  const fleetSel = $("eval-fleet");
  const rackSel = $("eval-rack");
  fleetSel.addEventListener("change", () => {
    const fid = fleetSel.value;
    const f = fleets.find((x) => x.fleet_id === fid);
    rackSel.innerHTML = '<option value="">All racks</option>';
    if (f && f.racks) {
      f.racks.forEach((r) => {
        const opt = document.createElement("option");
        opt.value = r.rack_id;
        opt.textContent = r.name;
        rackSel.appendChild(opt);
      });
    }
  });

  $("eval-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const btn = $("eval-btn");
    const out = $("eval-result");
    btn.disabled = true;
    btn.textContent = "Evaluating…";
    out.hidden = true;

    const body = {
      query: $("eval-query").value.trim(),
      fleet_id: fleetSel.value || null,
      rack_id: rackSel.value || null,
      agentic: $("eval-agentic").checked,
    };

    try {
      const res = await fetch("/api/v1/agentic/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Evaluation failed");

      const ragas = data.ragas || {};
      const passClass = data.threshold_met ? "pass" : "fail";
      out.innerHTML = `
        <div class="answer">${escapeHtml(data.answer || "")}</div>
        <div class="scores">
          <span class="score-chip ${passClass}">RAGAS ${pct(ragas.ragas_score)} ${
        data.threshold_met ? "PASS" : "BELOW THRESHOLD"
      }</span>
          <span class="score-chip">Faith ${pct(ragas.faithfulness)}</span>
          <span class="score-chip">Relevance ${pct(ragas.answer_relevance)}</span>
          <span class="score-chip">Precision ${pct(ragas.context_precision)}</span>
          <span class="score-chip">Recall ${pct(ragas.context_recall)}</span>
          <span class="score-chip">${Math.round(data.latency_ms || 0)} ms</span>
          <span class="score-chip">${data.attempts || 1} attempt(s)</span>
          <span class="score-chip">${data.sources_used || 0} sources</span>
        </div>
      `;
      out.hidden = false;
      await loadSummary();
    } catch (e) {
      out.innerHTML = `<div class="answer" style="color:var(--danger)">${escapeHtml(
        e.message || String(e)
      )}</div>`;
      out.hidden = false;
    } finally {
      btn.disabled = false;
      btn.textContent = "Evaluate";
    }
  });

  $("btn-refresh").addEventListener("click", loadSummary);
  $("btn-clear").addEventListener("click", async () => {
    if (!confirm("Clear all accuracy runs?")) return;
    await fetch("/api/accuracy/clear", { method: "POST" });
    loadSummary();
  });

  loadSummary();
  setInterval(loadSummary, 15000);
})();
