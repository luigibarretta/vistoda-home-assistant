import { BASE_STYLES } from "./panel-styles.js";
import { BLINK_STORAGE_STYLES } from "./blink-storage-styles.js";

class VistodaBlinkStorage extends HTMLElement {
  constructor() {
    super(); this.attachShadow({ mode: "open" }); this._storages = []; this._busy = false;
    this._loaded = false; this._mount();
  }

  set hass(value) {
    this._hass = value;
    if (value && !this._loaded && !this._busy) this.reload();
  }

  _mount() {
    this.shadowRoot.innerHTML = `<style>${BASE_STYLES}${BLINK_STORAGE_STYLES}</style>
      <section class="card storage"><header><div><div class="eyebrow">Sync Module</div>
        <h3>Archivio Blink su chiavetta USB</h3><div class="muted">File presenti sul supporto
        collegato al bridge Blink.</div></div><button id="reload">Rileggi chiavetta</button></header>
        <div id="content"></div><div class="muted" id="status" role="status"></div>
        <div class="readonly-note muted"><strong>Sola lettura.</strong> Vistoda può elencare e
        scaricare le clip, ma non espone cancellazione, espulsione, formattazione o mount.</div>
      </section>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("reload").addEventListener("click", () => this.reload());
    this._render();
  }

  async reload() {
    if (!this._hass || this._busy) return;
    this._busy = true; this.$("status").textContent = "Lettura indice USB Blink…"; this._render();
    try {
      const result = await this._hass.callWS({ type: "blink_live_bridge/local_storage/list" });
      this._storages = Array.isArray(result.storages) ? result.storages : [];
      this._loaded = true; this.$("status").textContent = "";
    } catch (_error) {
      this.$("status").textContent = "Archivio USB non disponibile o Sync Module senza supporto.";
    } finally { this._busy = false; this._render(); }
  }

  _render() {
    this.$("reload").disabled = this._busy || !this._hass;
    const nodes = this._storages.map((storage) => this._module(storage));
    if (!nodes.length && this._loaded) {
      const empty = document.createElement("div"); empty.className = "muted";
      empty.textContent = "Nessuna chiavetta USB Blink disponibile."; nodes.push(empty);
    }
    this.$("content").replaceChildren(...nodes);
  }

  _module(storage) {
    const details = document.createElement("details"); details.className = "module"; details.open = true;
    const summary = document.createElement("summary");
    const title = document.createElement("strong"); title.textContent = storage.network_name || "Sistema Blink";
    const count = document.createElement("span"); count.textContent = `${storage.clips?.length || 0} clip`;
    summary.append(title, count);
    const body = document.createElement("div"); body.className = "module-body";
    const facts = document.createElement("div"); facts.className = "module-facts";
    facts.append(this._fact(`USB: ${storage.status?.usb_state || "stato sconosciuto"}`));
    if (Number.isFinite(storage.status?.usb_storage_used)) {
      facts.append(this._fact(`Utilizzo riportato: ${storage.status.usb_storage_used}`));
    }
    if (storage.status?.last_backup_completed) {
      facts.append(this._fact(`Ultimo backup: ${this._date(storage.status.last_backup_completed)}`));
    }
    const clips = [...(storage.clips || [])].sort((a, b) =>
      String(b.created_at).localeCompare(String(a.created_at))).slice(0, 250);
    const rows = clips.map((clip) => this._clip(storage, clip));
    if (!rows.length) {
      const empty = document.createElement("div"); empty.className = "muted";
      empty.textContent = "Nessuna clip indicizzata sulla chiavetta."; rows.push(empty);
    }
    body.append(facts, ...rows); details.append(summary, body); return details;
  }

  _clip(storage, clip) {
    const row = document.createElement("article"); row.className = "clip";
    const text = document.createElement("div"); const title = document.createElement("strong");
    title.textContent = clip.device_name || "Telecamera Blink";
    const meta = document.createElement("small");
    const duration = Number.isFinite(clip.clip_length_ms) ? ` · ${(clip.clip_length_ms / 1000).toFixed(1)} s` : "";
    meta.textContent = `${this._date(clip.created_at)}${duration}`; text.append(title, meta);
    const download = document.createElement("button"); download.textContent = "Scarica";
    download.disabled = !clip.media_available; download.addEventListener("click", () =>
      this._download(storage, clip)); row.append(text, download); return row;
  }

  async _download(storage, clip) {
    const path = `/api/blink_live_bridge/v1/local-storage/${storage.network_id}/` +
      `${storage.sync_module_id}/${storage.manifest_id}/${clip.id}/media`;
    try {
      const signed = await this._hass.callWS({ type: "auth/sign_path", path, expires: 300 });
      const link = document.createElement("a"); link.href = this._hass.hassUrl(signed.path);
      link.download = `blink-usb-${clip.device_name || "camera"}-${clip.id}.mp4`; link.click();
    } catch (_error) { this.$("status").textContent = "Download clip non disponibile."; }
  }

  _fact(text) { const node = document.createElement("span"); node.textContent = text; return node; }
  _date(value) { const numeric = typeof value === "string" && /^\d{11,}$/.test(value)
    ? Number(value) : value; const date = new Date(numeric); return Number.isNaN(date.valueOf())
    ? (value || "Data non disponibile") : date.toLocaleString("it-IT"); }
}

if (!customElements.get("vistoda-blink-storage")) {
  customElements.define("vistoda-blink-storage", VistodaBlinkStorage);
}
