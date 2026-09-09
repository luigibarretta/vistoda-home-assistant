import { BASE_STYLES } from "./panel-styles.js";
import { PROVIDER_RECORDING_STYLES } from "./provider-recording-styles.js";
import { backupRecording, readyRecordings } from "./provider-recording-backup.js";
import { recordingItem } from "./provider-recording-item.js";
import "./provider-recording-player.js";
import {
  cameraRecordings,
  recordingCommand,
  recordingMediaPath,
} from "./provider-recording-model.js";

class VistodaProviderRecordings extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = null;
    this._items = [];
    this._pagination = { page: 1, page_size: 10, total_items: 0, total_pages: 1,
      has_previous: false, has_next: false };
    this._busy = false;
    this._timer = null;
    this._mounted = false;
  }

  set hass(value) { this._hass = value; }

  connectedCallback() {
    if (!this._mounted) this._mount();
  }

  disconnectedCallback() { this._clearTimer(); }

  configure(hass, config) {
    this._hass = hass;
    const key = `${config?.provider}:${config?.entryId || ""}:${config?.alias || ""}`;
    if (key === this._key) return;
    this._key = key;
    this._config = config;
    this._items = [];
    this._pagination.page = 1;
    this.$?.("player")?.close();
    if (!this._mounted) this._mount();
    this._render();
    this.reload();
  }

  _mount() {
    this._mounted = true;
    this.shadowRoot.innerHTML = `<style>${BASE_STYLES}${PROVIDER_RECORDING_STYLES}</style>
      <section><div class="head"><div><h4>Registrazione live locale</h4>
        <div class="muted">Cattura il flusso che stai visualizzando, senza creare eventi cloud.</div>
        </div><div class="head-actions"><button id="backup-all" title="Backup archivio"
        data-tooltip="Copia su NFS tutte le registrazioni pronte non ancora presenti">
        <ha-icon icon="mdi:cloud-upload"></ha-icon> Backup archivio</button><button id="reload"
        title="Rileggi archivio" data-tooltip="Aggiorna stati e file locali">
        <ha-icon icon="mdi:refresh"></ha-icon> Aggiorna archivio</button></div></div>
        <div class="capture"><label for="duration">Durata</label><select id="duration">
          <option value="15">15 secondi</option><option value="30" selected>30 secondi</option>
          <option value="60">60 secondi</option></select><label for="destination">Destinazione</label>
          <select id="destination"><option value="ha">Archivio locale HA</option>
          <option id="provider-storage" value="provider" disabled>Supporto della camera</option></select>
          <button class="primary" id="start"
          title="Registra il live localmente">Registra live</button></div>
        <div class="destination-note muted" id="destination-note"></div>
        <div class="message muted" id="message" role="status"></div>
        <vistoda-provider-recording-player id="player"></vistoda-provider-recording-player>
        <details open><summary id="summary">Archivio locale</summary><div class="list" id="list"></div>
        <nav class="archive-pager" aria-label="Pagine archivio"><button id="previous">Precedente</button>
        <span id="page-label">Pagina 1 di 1</span><button id="next">Successiva</button></nav>
        </details></section>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("reload").addEventListener("click", () => this.reload());
    this.$("backup-all").addEventListener("click", () => this._backupAll());
    this.$("start").addEventListener("click", () => this._start());
    this.$("previous").addEventListener("click", () => this._go(this._pagination.page - 1));
    this.$("next").addEventListener("click", () => this._go(this._pagination.page + 1));
    this._render();
  }

  async reload() {
    if (!this._config || !this._hass || this._busy) return;
    this._busy = true;
    this._render();
    try {
      const result = await this._fetch(this._pagination.page, this._pagination.page_size);
      this._items = cameraRecordings(result.recordings || [], this._config.alias);
      this._pagination = result.pagination || this._pagination;
      this._setMessage("");
    } catch (_error) {
      this._setMessage("Archivio temporaneamente non disponibile.");
    } finally {
      this._busy = false;
      this._render();
      this._schedule(this._items.some((item) => ["pending", "recording"].includes(item.status)));
    }
  }

  _fetch(page, pageSize) {
    return this._hass.callWS({ ...this._message("list"), page, page_size: pageSize });
  }

  async _go(page) {
    if (page < 1 || this._busy) return;
    this._pagination.page = page; this.$("player").close(); await this.reload();
  }

  async _start() {
    if (!this._config || this._busy) return;
    const duration = Number(this.$("duration").value);
    if (!globalThis.confirm(`Registrare ${duration} secondi del live in archivio locale?`)) return;
    this._busy = true;
    this._setMessage("Avvio registrazione…");
    this._render();
    try {
      await this._hass.callWS({
        ...this._message("create"),
        duration_seconds: duration,
        request_id: globalThis.crypto.randomUUID(),
      });
      this._setMessage(`Registrazione di ${duration} secondi avviata.`);
    } catch (_error) {
      this._setMessage("Registrazione non avviata: verifica live, disponibilità e quota.");
    } finally {
      this._busy = false;
      await this.reload();
    }
  }

  async _delete(item) {
    if (!globalThis.confirm("Eliminare definitivamente questa registrazione locale?")) return;
    this._busy = true;
    this._render();
    try {
      await this._hass.callWS({ ...this._message("delete"), recording_id: item.recording_id });
      this._setMessage("Registrazione eliminata.");
    } catch (_error) {
      this._setMessage("La registrazione non può essere eliminata mentre è attiva.");
    } finally {
      this._busy = false;
      await this.reload();
    }
  }

  async _backup(item) {
    if (!globalThis.confirm("Copiare e verificare questa registrazione sul backup NFS?")) return;
    this._busy = true;
    this._render();
    try {
      const result = await backupRecording(this._hass, this._config, item);
      this._setMessage(result.status === "existing"
        ? `Backup già verificato: ${result.relative_path}`
        : `Backup NFS completato: ${result.relative_path}`);
    } catch (_error) {
      this._setMessage("Backup non riuscito: mount, spazio o checksum non validi.");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _backupAll() {
    let ready;
    try {
      ready = await readyRecordings((page, size) => this._fetch(page, size), this._config.alias);
    } catch (_error) { this._setMessage("Archivio non leggibile per il backup."); return; }
    if (!ready.length) { this._setMessage("Nessuna registrazione pronta da copiare."); return; }
    if (!globalThis.confirm(`Copiare e verificare ${ready.length} registrazioni sul backup NFS?`)) return;
    this._busy = true;
    this._render();
    let completed = 0;
    try {
      for (const item of ready) {
        await backupRecording(this._hass, this._config, item);
        completed += 1;
        this._setMessage(`Backup NFS: ${completed}/${ready.length} verificati…`);
      }
      this._setMessage(`Backup NFS completato: ${completed} registrazioni verificate.`);
    } catch (_error) {
      this._setMessage(`Backup interrotto: ${completed}/${ready.length} verificati.`);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _download(item) {
    try {
      const path = recordingMediaPath(this._config, item.recording_id);
      const signed = await this._hass.callWS({ type: "auth/sign_path", path, expires: 300 });
      const link = document.createElement("a");
      link.href = this._hass.hassUrl(signed.path);
      link.download = `${this._config.provider}-${item.camera}-${item.recording_id}.${
        this._config.provider === "blink" ? "ts" : "mpeg"}`;
      link.click();
    } catch (_error) {
      this._setMessage("Download non disponibile.");
    }
  }

  async _play(item) {
    try { await this.$("player").open(this._hass, this._config, item); }
    catch (_error) { this._setMessage("Riproduzione non disponibile."); }
  }

  _message(action) { return recordingCommand(this._config, action); }

  _render() {
    if (!this._mounted) return;
    this.$("start").disabled = this._busy || !this._config;
    this.$("reload").disabled = this._busy || !this._config;
    this.$("backup-all").disabled = this._busy || !this._config;
    const providerStorage = this.$("provider-storage");
    providerStorage.textContent = this._config?.provider === "blink"
      ? "Chiavetta Blink" : "MicroSD EZVIZ";
    this.$("destination-note").textContent = this._config?.provider === "blink"
      ? "Blink non espone una scrittura diretta e selettiva sulla chiavetta USB: il salvataggio " +
        "provider resta disabilitato finché il protocollo non è verificabile."
      : "La registrazione standalone resta separata da SceneTrove e dalla microSD della camera.";
    this.$("summary").textContent = `Archivio locale (${this._pagination.total_items})`;
    this.$("page-label").textContent = `Pagina ${this._pagination.page} di ${this._pagination.total_pages}`;
    this.$("previous").disabled = this._busy || !this._pagination.has_previous;
    this.$("next").disabled = this._busy || !this._pagination.has_next;
    const nodes = this._items.map((item) => recordingItem(item, {
      provider: this._config.provider, busy: this._busy,
      play: () => this._play(item), download: () => this._download(item),
      backup: () => this._backup(item), remove: () => this._delete(item),
    }));
    if (!nodes.length) {
      const empty = document.createElement("div");
      empty.className = "muted";
      empty.textContent = "Nessuna registrazione locale per questa telecamera.";
      nodes.push(empty);
    }
    this.$("list").replaceChildren(...nodes);
  }

  _setMessage(value) { if (this.$) this.$("message").textContent = value; }
  _clearTimer() { if (this._timer) globalThis.clearTimeout(this._timer); this._timer = null; }
  _schedule(active) {
    this._clearTimer();
    if (active && this.isConnected) this._timer = globalThis.setTimeout(() => this.reload(), 2000);
  }
}
if (!customElements.get("vistoda-provider-recordings")) {
  customElements.define("vistoda-provider-recordings", VistodaProviderRecordings);
}
