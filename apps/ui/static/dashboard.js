(() => {
  const $ = (id) => document.getElementById(id);

  function setMetric(id, value) {
    const el = $(id);
    if (el) el.textContent = typeof value === "number" ? value.toFixed(3) : value;
  }

  function renderTrace(trace) {
    const root = $("reasoning-trace");
    if (!root) return;
    root.innerHTML = "";
    (trace || []).forEach((t) => {
      const li = document.createElement("li");
      li.textContent = typeof t === "string" ? t : JSON.stringify(t);
      root.appendChild(li);
    });
  }

  async function runEval() {
    const query = $("eval-query")?.value?.trim();
    if (!query) return;
    $("eval-status").textContent = "Running agentic evaluation…";
    try {
      const res = await fetch("/api/agentic/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          fleet_id: $("eval-fleet")?.value || null,
          rack_id: $("eval-rack")?.value || null,
        }),
      });
      const data = await res.json();
      const r = data.ragas || {};
      setMetric("m-ragas", r.ragas_score ?? data.confidence_score);
      setMetric("m-faith", r.faithfulness);
      setMetric("m-rel", r.answer_relevance);
      setMetric("m-prec", r.context_precision);
      setMetric("m-recall", r.context_recall);
      $("eval-answer").textContent = data.answer || "";
      $("eval-status").textContent = data.threshold_met
        ? "Passed accuracy threshold"
        : "Below threshold (best-effort)";
      renderTrace(data.reasoning_trace);
    } catch (e) {
      $("eval-status").textContent = "Error: " + e.message;
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    $("run-eval")?.addEventListener("click", runEval);
  });
})();
