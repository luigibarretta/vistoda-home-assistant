import { BASE_STYLES } from "./panel-styles.js";
import { BLINK_STORAGE_STYLES } from "./blink-storage-styles.js";

class VistodaBlinkStorage extends HTMLElement {
  constructor() {
    super(); this.attachShadow({ mode: "open" }); this._storages = []; this._busy = false;
    this._loaded = false; this._page = 1; this._pageSize = 10; this._mount();
  }

  set hass(value) {
    this._hass = value;
    if (value && !this._loaded && !this._busy) this.reload();
  }

  _mount() {
    this.shadowRoot.innerHTML = `<style>${BASE_STYLES}${BLINK_STORAGE_STYLES}</style>
      <section class="card storage"><header><div><div class="eyebrow">Sync Module</div>
        <h3>Archivio Blink su chiavetta USB</h3><div class="muted">File presenti sul supporto
        collegato al bridge Blink.</div></div><div class="header-actions"><button id="backup-all">
        Backup archivio NFS</button><button id="reload">Rileggi chiavetta</button></div></header>
        <section class="player" id="player" hidden><div class="player-head"><strong
        id="player-title">Riproduzione clip</strong><button id="close-player">Chiudi</button></div>
        <video id="video" controls playsinline preload="metadata"></video></section>
        <div id="content"></div><div class="muted" id="status" role="status"></div>
        <div class="readonly-note muted"><strong>Supporto Blink in sola lettura.</strong> Vistoda
        può elencare, riprodurre, scaricare e copiare le clip su NFS, ma non espone cancellazione,
        espulsione, formattazione o mount.</div></section>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("reload").addEventListener("click", () => this.reload());
    this.$("backup-all").addEventListener("click", () => this._backupAll());
    this.$("close-player").addEventListener("click", () => this._closePlayer());
    this._render();
  }

  async _fetch(page, pageSize = this._pageSize) {
    return this._hass.callWS({
      type: "blink_live_bridge/local_storage/list", page, page_size: pageSize,
    });
  }

  async reload() {
    if (!this._hass || this._busy) return;
    this._busy = true; this.$("status").textContent = "Lettura indice USB Blink…"; this._render();
    try {
      const result = await this._fetch(this._page);
      this._storages = Array.isArray(result.storages) ? result.storages : [];
      this._loaded = true; this.$("status").textContent = "";
    } catch (_error) {
      this.$("status").textContent = "Archivio USB non disponibile o Sync Module senza supporto.";
    } finally { this._busy = false; this._render(); }
  }

  _render() {
    this.$("reload").disabled = this._busy || !this._hass;
    this.$("backup-all").disabled = this._busy || !this._hass;
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
    const count = document.createElement("span");
    count.textContent = `${storage.pagination?.total_items ?? storage.clips?.length ?? 0} clip`;
    summary.append(title, count);
    const body = document.createElement("div"); body.className = "module-body";
    const facts = document.createElement("div"); facts.className = "module-facts";
    facts.append(this._fact(`USB: ${storage.status?.usb_state || "stato sconosciuto"}`));
    if (Number.isFinite(storage.status?.usb_storage_used)) {
      facts.append(this._fact(`Utilizzo riportato: ${storage.status.usb_storage_used}`));
    }
    if (storage.status?.last_backup_completed) {
      facts.append(this._fact(`Ultimo backup Blink: ${this._date(storage.status.last_backup_completed)}`));
    }
    const rows = (storage.clips || []).map((clip) => this._clip(storage, clip));
    if (!rows.length) {
      const empty = document.createElement("div"); empty.className = "muted";
      empty.textContent = "Nessuna clip indicizzata in questa pagina."; rows.push(empty);
    }
    body.append(facts, ...rows, this._pager(storage.pagination));
    details.append(summary, body); return details;
  }

  _clip(storage, clip) {
    const row = document.createElement("article"); row.className = "clip";
    const text = document.createElement("div"); const title = document.createElement("strong");
    title.textContent = clip.device_name || "Telecamera Blink";
    const meta = document.createElement("small");
    const duration = Number.isFinite(clip.clip_length_ms)
      ? ` · ${(clip.clip_length_ms / 1000).toFixed(1)} s` : "";
    meta.textContent = `${this._date(clip.created_at)}${duration}`; text.append(title, meta);
    const actions = document.createElement("div"); actions.className = "clip-actions";
    actions.append(this._button("Riproduci", () => this._play(storage, clip), !clip.media_available));
    actions.append(this._button("Scarica", () => this._download(storage, clip), !clip.media_available));
    actions.append(this._button("Backup NFS", () => this._backupSingle(storage, clip), !clip.media_available));
    row.append(text, actions); return row;
  }

  _pager(pagination = {}) {
    const pager = document.createElement("nav"); pager.className = "archive-pager";
    pager.setAttribute("aria-label", "Pagine archivio Blink");
    const previous = this._button("Precedente", () => this._go(pagination.page - 1),
      !pagination.has_previous);
    const label = document.createElement("span");
    label.textContent = `Pagina ${pagination.page || 1} di ${pagination.total_pages || 1}`;
    const next = this._button("Successiva", () => this._go(pagination.page + 1),
      !pagination.has_next);
    pager.append(previous, label, next); return pager;
  }

  async _go(page) {
    if (page < 1 || this._busy) return;
    this._page = page; this._closePlayer(); await this.reload();
  }

  _path(storage, clip) {
    return `/api/blink_live_bridge/v1/local-storage/${storage.network_id}/` +
      `${storage.sync_module_id}/${storage.manifest_id}/${clip.id}/media`;
  }

  async _signedPath(storage, clip) {
    const signed = await this._hass.callWS({
      type: "auth/sign_path", path: this._path(storage, clip), expires: 900,
    });
    return this._hass.hassUrl(signed.path);
  }

  async _play(storage, clip) {
    try {
      this._closePlayer(); this.$("player-title").textContent =
        `${clip.device_name || "Telecamera Blink"} · ${this._date(clip.created_at)}`;
      this.$("video").src = await this._signedPath(storage, clip);
      this.$("player").hidden = false; this.$("video").load();
      this.$("player").scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (_error) { this.$("status").textContent = "Riproduzione clip non disponibile."; }
  }

  _closePlayer() {
    const video = this.$("video"); video.pause(); video.removeAttribute("src"); video.load();
    this.$("player").hidden = true;
  }

  async _download(storage, clip) {
    try {
      const link = document.createElement("a"); link.href = await this._signedPath(storage, clip);
      link.download = `blink-usb-${clip.device_name || "camera"}-${clip.id}.mp4`; link.click();
    } catch (_error) { this.$("status").textContent = "Download clip non disponibile."; }
  }

  _backupMessage(storage, clip) {
    return { type: "media_bridge/blink/usb/backup", network_id: Number(storage.network_id),
      sync_module_id: Number(storage.sync_module_id), manifest_id: Number(storage.manifest_id),
      clip_id: Number(clip.id), camera: this._safeCamera(clip.device_name),
      created_at: String(clip.created_at || ""), clip_length_ms: clip.clip_length_ms ?? null };
  }

  async _backupSingle(storage, clip) {
    try { await this._backup(storage, clip); }
    catch (_error) { this.$("status").textContent = "Backup NFS Blink non riuscito."; }
  }

  async _backup(storage, clip, confirmed = false) {
    if (!confirmed && !globalThis.confirm("Copiare e verificare questa clip Blink sul backup NFS?")) return;
    const result = await this._hass.callWS(this._backupMessage(storage, clip));
    this.$("status").textContent = result.status === "existing"
      ? `Backup già verificato: ${result.relative_path}` : `Backup NFS completato: ${result.relative_path}`;
  }

  async _backupAll() {
    if (!this._hass || this._busy) return;
    this._busy = true; this._render();
    try {
      const first = await this._fetch(1, 50); const storages = first.storages || [];
      const total = storages.reduce((sum, item) => sum + (item.pagination?.total_items || 0), 0);
      if (!total) { this.$("status").textContent = "Nessuna clip Blink da copiare."; return; }
      if (!globalThis.confirm(`Copiare e verificare ${total} clip Blink sul backup NFS?`)) return;
      const pages = Math.max(1, ...storages.map((item) => item.pagination?.total_pages || 1));
      let completed = 0;
      for (let page = 1; page <= pages; page += 1) {
        const batch = page === 1 ? first : await this._fetch(page, 50);
        for (const storage of batch.storages || []) {
          for (const clip of (storage.clips || []).filter((item) => item.media_available)) {
            await this._backup(storage, clip, true); completed += 1;
            this.$("status").textContent = `Backup NFS Blink: ${completed}/${total} verificati…`;
          }
        }
      }
      this.$("status").textContent = `Backup NFS Blink completato: ${completed} clip verificate.`;
    } catch (_error) { this.$("status").textContent = "Backup NFS Blink interrotto."; }
    finally { this._busy = false; this._render(); }
  }

  _button(label, action, disabled = false) {
    const button = document.createElement("button"); button.textContent = label;
    button.disabled = disabled || this._busy; button.addEventListener("click", action); return button;
  }
  _safeCamera(value) { return String(value || "Telecamera_Blink").replace(/[^A-Za-z0-9_-]/g, "_").slice(0, 64) || "Telecamera_Blink"; }
  _fact(text) { const node = document.createElement("span"); node.textContent = text; return node; }
  _date(value) { const numeric = typeof value === "string" && /^\d{11,}$/.test(value)
    ? Number(value) : value; const date = new Date(numeric); return Number.isNaN(date.valueOf())
    ? (value || "Data non disponibile") : date.toLocaleString("it-IT"); }
}

if (!customElements.get("vistoda-blink-storage")) {
  customElements.define("vistoda-blink-storage", VistodaBlinkStorage);
}
