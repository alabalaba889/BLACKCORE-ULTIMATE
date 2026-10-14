"use strict";
(() => {
  const el = id => document.getElementById(id);
  const ids = ["cpu","ram","disk","freeDisk","ramAvailable","networkSent","networkReceived","packets","uptime","processes","cores","battery","bridgeUptime","system"];
  let timer = null;
  let lastSnapshot = null;
  let activeController = null;

  function message(text, kind="") {
    el("message").textContent = text;
    el("message").className = kind;
  }
  function state(text) { el("state").textContent = text; }
  function formatBytes(value) {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) return "N/D";
    const units = ["B","KB","MB","GB","TB"];
    let n = Number(value), i = 0;
    while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
    return (i ? n.toFixed(1) : String(Math.round(n))) + " " + units[i];
  }
  function duration(seconds) {
    if (seconds === null || seconds === undefined || !Number.isFinite(Number(seconds))) return "N/D";
    let n = Math.max(0, Math.floor(Number(seconds)));
    const d = Math.floor(n / 86400); n %= 86400;
    const h = Math.floor(n / 3600); n %= 3600;
    const m = Math.floor(n / 60);
    return (d ? d + "d " : "") + h + "h " + m + "m";
  }
  function setMetric(id, value, detail="") {
    el(id).textContent = value;
    const detailEl = el(id + "Detail");
    if (detailEl) detailEl.textContent = detail;
  }
  function render(d, latency) {
    setMetric("cpu", d.cpu_percent == null ? "N/D" : Number(d.cpu_percent).toFixed(1) + "%");
    setMetric("ram", d.memory ? Number(d.memory.percent_used).toFixed(1) + "%" : "N/D",
      d.memory ? formatBytes(d.memory.used_bytes) + " / " + formatBytes(d.memory.total_bytes) : "psutil não disponível");
    setMetric("disk", d.disk ? Number(d.disk.percent_used).toFixed(1) + "%" : "N/D",
      d.disk ? formatBytes(d.disk.used_bytes) + " usados" : "");
    setMetric("freeDisk", d.disk ? formatBytes(d.disk.free_bytes) : "N/D");
    setMetric("ramAvailable", d.memory ? formatBytes(d.memory.available_bytes) : "N/D");
    setMetric("networkSent", d.network ? formatBytes(d.network.bytes_sent) : "N/D");
    setMetric("networkReceived", d.network ? formatBytes(d.network.bytes_received) : "N/D");
    setMetric("packets", d.network ? (Number(d.network.packets_sent).toLocaleString() + " enviados / " + Number(d.network.packets_received).toLocaleString() + " recebidos") : "N/D");
    setMetric("uptime", duration(d.uptime_seconds));
    setMetric("processes", d.process_count == null ? "N/D" : Number(d.process_count).toLocaleString());
    setMetric("cores", d.cpu_count == null ? "N/D" : String(d.cpu_count));
    setMetric("battery", d.battery ? Number(d.battery.percent).toFixed(0) + "%" + (d.battery.plugged ? " • carregando" : "") : "N/D");
    setMetric("bridgeUptime", duration(d.bridge_uptime_seconds));
    el("system").textContent = d.platform + " • Python " + (d.python_version || "N/D") +
      " • resposta " + latency + " ms • atualizado " + new Date(d.timestamp * 1000).toLocaleTimeString();
    el("system").className = "notice";
    el("snapshot").textContent = JSON.stringify(d, null, 2);
    el("snapshotWrap").classList.remove("hidden");
    lastSnapshot = d;
  }
  async function connect() {
    const base = el("endpoint").value.trim().replace(/\/+$/, "");
    const token = el("token").value.trim();
    if (!base || token.length < 32) {
      state("CONFIGURAÇÃO");
      message("Informe o endereço do bridge e um token de pelo menos 32 caracteres.", "bad");
      return;
    }
    let parsed;
    try { parsed = new URL(base); } catch (_) {
      message("O endereço não é uma URL válida.", "bad"); return;
    }
    const localHttp = parsed.protocol === "http:" &&
      ["localhost","127.0.0.1","[::1]"].includes(parsed.hostname);
    if (parsed.protocol !== "https:" && !localHttp) {
      message("Use HTTPS para Wi-Fi/VPN. HTTP só é aceito em localhost.", "bad"); return;
    }
    if (parsed.username || parsed.password || parsed.search || parsed.hash) {
      message("Remova usuário, senha, query e fragmento do endereço.", "bad"); return;
    }
    if (activeController) activeController.abort();
    activeController = new AbortController();
    const timeout = setTimeout(() => activeController?.abort(), 9000);
    const started = performance.now();
    state("CONECTANDO…"); el("connect").disabled = true; el("refresh").disabled = true;
    message("Consultando telemetria em modo somente leitura…");
    try {
      const response = await fetch(base + "/api/status", {
        headers: {Authorization: "Bearer " + token, Accept: "application/json"},
        cache: "no-store", credentials: "omit", redirect: "error", signal: activeController.signal
      });
      if (!response.ok) {
        if (response.status === 401) throw new Error("Token recusado (401).");
        if (response.status === 404) throw new Error("Bridge encontrado, endpoint de status ausente (404).");
        if (response.status === 405) throw new Error("O bridge recusou esta operação (405).");
        throw new Error("Resposta HTTP " + response.status + ".");
      }
      const data = await response.json();
      if (!data || typeof data !== "object" || !data.capabilities) throw new Error("Resposta do bridge inválida.");
      const latency = Math.round(performance.now() - started);
      render(data, latency);
      state("CONECTADO");
      message("Conectado com sucesso. Somente leitura: nenhum comando foi enviado ao PC.", "good");
      el("refresh").classList.remove("hidden");
      el("disconnect").classList.remove("hidden");
      el("export").classList.remove("hidden");
      el("copy").classList.remove("hidden");
      el("autoRefreshRow").classList.remove("hidden");
      el("showSnapshot").classList.remove("hidden");
    } catch (error) {
      state("ERRO");
      const detail = error.name === "AbortError" ? "Tempo limite excedido (9 s)." : error.message;
      message("Falha na conexão: " + detail + "\nConfira endereço, token, certificado HTTPS e se o bridge está rodando.", "bad");
    } finally {
      clearTimeout(timeout); activeController = null;
      el("connect").disabled = false; el("refresh").disabled = false;
    }
  }
  function stopAuto() {
    if (timer !== null) clearInterval(timer);
    timer = null;
  }
  function startAuto() {
    stopAuto();
    if (el("autoRefresh").checked) timer = setInterval(() => {
      if (document.visibilityState === "visible" && !el("connect").disabled) connect();
    }, Number(el("interval").value));
  }
  function disconnect() {
    stopAuto();
    if (activeController) activeController.abort();
    el("token").value = "";
    lastSnapshot = null;
    ids.forEach(id => { if (el(id)) el(id).textContent = "—"; });
    el("snapshot").textContent = "";
    el("snapshotWrap").classList.add("hidden");
    ["refresh","disconnect","export","copy","autoRefreshRow","showSnapshot"].forEach(id => el(id).classList.add("hidden"));
    state("DESCONECTADO");
    message("Desconectado. O token foi apagado desta tela e não foi salvo no navegador.");
  }
  async function copySummary() {
    if (!lastSnapshot) return;
    const summary = "BLACKCORE ULTIMATE\nSistema: " + lastSnapshot.platform +
      "\nCPU: " + (lastSnapshot.cpu_percent ?? "N/D") +
      "\nRAM: " + (lastSnapshot.memory?.percent_used ?? "N/D") +
      "\nDisco: " + (lastSnapshot.disk?.percent_used ?? "N/D") +
      "\nModo: somente leitura";
    try {
      await navigator.clipboard.writeText(summary);
      message("Resumo copiado para a área de transferência.", "good");
    } catch (_) { message("A cópia não foi permitida pelo navegador. Use Exportar JSON.", "warn"); }
  }
  function exportSnapshot() {
    if (!lastSnapshot) return;
    const blob = new Blob([JSON.stringify(lastSnapshot, null, 2)], {type:"application/json"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "blackcore-status-" + new Date().toISOString().replace(/[:.]/g,"-") + ".json";
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  }
  el("connect").addEventListener("click", connect);
  el("refresh").addEventListener("click", connect);
  el("disconnect").addEventListener("click", disconnect);
  el("copy").addEventListener("click", copySummary);
  el("export").addEventListener("click", exportSnapshot);
  el("autoRefresh").addEventListener("change", startAuto);
  el("interval").addEventListener("change", startAuto);
  el("showSnapshot").addEventListener("click", () => el("snapshotWrap").classList.toggle("hidden"));
  el("toggleToken").addEventListener("click", () => {
    const field = el("token"); const visible = field.type === "password";
    field.type = visible ? "text" : "password";
    el("toggleToken").textContent = visible ? "Ocultar token" : "Mostrar token";
  });
  el("endpoint").addEventListener("keydown", e => { if (e.key === "Enter") connect(); });
  el("token").addEventListener("keydown", e => { if (e.key === "Enter") connect(); });
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "visible" && activeController) activeController.abort();
  });
  if (location.protocol === "https:" || location.hostname === "localhost" || location.hostname === "127.0.0.1") el("endpoint").value = location.origin;
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("./sw.js").catch(() => {});
})();