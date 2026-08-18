(() => {
  const state = {
    fleetId: null,
    rackId: null,
    fleets: {},
  };

  const el = {
    fleetList: () => document.getElementById("fleet-list"),
    rackList: () => document.getElementById("rack-list"),
    chat: () => document.getElementById("chat"),
    query: () => document.getElementById("query"),
    send: () => document.getElementById("send"),
  };

  async function loadFleets() {
    const res = await fetch("/api/fleets");
    const data = await res.json();
    state.fleets = {};
    (data.fleets || []).forEach((f) => {
      state.fleets[f.fleet_id] = f;
    });
    renderFleets();
  }

  function renderFleets() {
    const root = el.fleetList();
    if (!root) return;
    root.innerHTML = "";
    Object.values(state.fleets).forEach((f) => {
      const btn = document.createElement("button");
      btn.className = "fleet-btn" + (state.fleetId === f.fleet_id ? " active" : "");
      btn.textContent = (f.icon || "") + " " + f.name;
      btn.onclick = () => {
        state.fleetId = f.fleet_id;
        state.rackId = null;
        renderFleets();
        renderRacks();
      };
      root.appendChild(btn);
    });
  }

  function renderRacks() {
    const root = el.rackList();
    if (!root) return;
    root.innerHTML = "";
    const f = state.fleets[state.fleetId];
    if (!f) return;
    (f.racks || []).forEach((r) => {
      const btn = document.createElement("button");
      btn.className = "rack-btn" + (state.rackId === r.rack_id ? " active" : "");
      btn.textContent = r.name;
      btn.onclick = () => {
        state.rackId = r.rack_id;
        renderRacks();
      };
      root.appendChild(btn);
    });
  }

  function appendMsg(role, text) {
    const chat = el.chat();
    if (!chat) return;
    const div = document.createElement("div");
    div.className = "msg " + role;
    div.textContent = text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
  }

  async function sendQuery() {
    const q = (el.query()?.value || "").trim();
    if (!q) return;
    appendMsg("user", q);
    el.query().value = "";
    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: q,
          fleet_id: state.fleetId,
          rack_id: state.rackId,
        }),
      });
      const data = await res.json();
      appendMsg("assistant", data.answer || JSON.stringify(data));
    } catch (e) {
      appendMsg("assistant", "Error: " + e.message);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    loadFleets();
    el.send()?.addEventListener("click", sendQuery);
    el.query()?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendQuery();
      }
    });
  });
})();
