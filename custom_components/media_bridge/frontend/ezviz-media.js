import { copy, localizeCopy } from "./panel-copy.js";
import { panelLanguage } from "./panel-localize.js";
import { capacityText, clampDay, dayRange, encryptionView, recordRows, storageView } from "./ezviz-media-model.js";

// Read-only encryption, microSD and per-day SD record list for one EZVIZ entry.
// Everything stays hidden when the Vistoda EZVIZ app predates these routes.
class VistodaEzvizMedia extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._entryId = "";
    this._request = 0;
    this._records = null;
    this._recordState = "idle";
    this._unsupported = false;
  }

  configure(hass, entry) {
    this._hass = hass;
    this._entry = entry;
    if (!this._mounted) this._mount();
    const entryId = entry?.entry_id || "";
    if (entryId !== this._entryId) {
      this._entryId = entryId;
      this._request += 1;
      this._records = null;
      this._recordState = "idle";
      this._unsupported = false;
      this.$("timeline").open = false;
      this.$("day").value = "";
    }
    this._render();
  }

  _mount() {
    this._mounted = true;
    this.shadowRoot.innerHTML = `<style>
      :host{display:block;margin-top:14px}:host([hidden]),[hidden]{display:none!important}h3{margin:0 0 8px;font-size:16px}
      .facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px}
      .fact{display:flex;gap:10px;align-items:flex-start;padding:10px;border-radius:12px;
        background:color-mix(in srgb,var(--primary-color) 7%,transparent)}.fact ha-icon{color:var(--primary-color)}
      .fact span{display:block;color:var(--secondary-text-color);font-size:13px}.fact strong{display:block}
      .warning{margin:10px 0 0;padding:10px 12px;border-radius:12px;line-height:1.4;
        background:color-mix(in srgb,var(--warning-color,#ffa600) 16%,transparent)}
      details{margin-top:10px;border-top:1px solid var(--divider-color,#ffffff1f)}
      summary{min-height:44px;display:flex;align-items:center;cursor:pointer;font-weight:600}
      label{display:flex;align-items:center;gap:10px;flex-wrap:wrap}input{min-height:40px;border-radius:10px;padding:4px 8px;
        border:1px solid var(--divider-color);color:var(--primary-text-color);background:var(--card-background-color);font:inherit}
      ul{list-style:none;margin:8px 0 0;padding:0;max-height:320px;overflow:auto}
      li{display:flex;justify-content:space-between;gap:12px;padding:7px 2px;border-top:1px solid var(--divider-color,#ffffff14)}
      time{font-variant-numeric:tabular-nums}.type{color:var(--secondary-text-color)}.status{color:var(--secondary-text-color)}
    </style><section id="root"><h3 data-copy="Crittografia e microSD">Crittografia e microSD</h3><div class="facts">
      <div class="fact" id="encryption-fact" hidden><ha-icon icon="mdi:lock-outline"></ha-icon><div>
        <span data-copy="Crittografia video">Crittografia video</span><strong id="encryption"></strong><span id="key-source"></span></div></div>
      <div class="fact" id="storage-fact" hidden><ha-icon id="storage-icon" icon="mdi:micro-sd"></ha-icon><div>
        <span data-copy="Scheda microSD">Scheda microSD</span><strong id="storage"></strong><span id="capacity"></span></div></div></div>
      <p class="warning" id="encryption-warning" role="alert" hidden><span data-copy="Video crittografato senza codice di verifica: per il live attiva l’opzione del codice di verifica nell’app Vistoda EZVIZ.">Video crittografato senza codice di verifica: per il live attiva l’opzione del codice di verifica nell’app Vistoda EZVIZ.</span></p>
      <details id="timeline" hidden><summary data-copy="Registrazioni sulla microSD">Registrazioni sulla microSD</summary>
        <label><span data-copy="Giorno (ultimi 7 giorni)">Giorno (ultimi 7 giorni)</span><input type="date" id="day"></label>
        <p class="status" id="records-status" role="status"></p><ul id="records"></ul></details></section>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("timeline").addEventListener("toggle", () => { if (this.$("timeline").open && !this._records) this._load(); });
    this.$("day").addEventListener("change", () => this._load());
  }

  _render() {
    localizeCopy(this.shadowRoot, this);
    const locale = this._hass?.locale?.language || "it-IT";
    const media = this._entry?.media;
    const encryption = encryptionView(media?.encryption);
    const storage = storageView(media?.storage, this._hass?.states?.[this._entry?.microsd_entity_id]);
    this.$("encryption-fact").hidden = !encryption;
    this.$("encryption").textContent = encryption ? copy(this, encryption.label) : "";
    this.$("key-source").textContent = encryption?.source ? copy(this, encryption.source) : "";
    this.$("encryption-warning").hidden = !encryption?.warning;
    this.$("storage-fact").hidden = !storage;
    this.$("storage").textContent = storage ? copy(this, storage.label) : "";
    this.$("storage-icon").setAttribute("icon", storage?.problem ? "mdi:micro-sd-off" : "mdi:micro-sd");
    this.$("capacity").textContent = storage?.capacityMb
      ? copy(this, "Capacità {p0}", { p0: capacityText(storage.capacityMb, locale) }) : "";
    this.$("timeline").hidden = !storage || storage.status === "no_card" || this._unsupported;
    this.hidden = !encryption && !storage;
    const range = dayRange();
    this.$("day").min = range.min;
    this.$("day").max = range.max;
    this._renderRecords(locale);
  }

  async _load() {
    const range = dayRange();
    const day = clampDay(this.$("day").value, range);
    this.$("day").value = day;
    const request = ++this._request;
    this._recordState = "loading";
    this._renderRecords();
    try {
      const result = await this._hass.callWS({ type: "media_bridge/ezviz/sd_records/list", entry_id: this._entryId, date: day });
      if (request !== this._request) return;
      this._unsupported = result?.supported === false;
      this._records = this._unsupported ? [] : result?.records || [];
      this._recordState = this._records.length ? "ready" : "empty";
    } catch {
      if (request !== this._request) return;
      this._records = null;
      this._recordState = "error";
    }
    this._render();
  }

  _renderRecords(locale = this._hass?.locale?.language || "it-IT") {
    // Frequent HA state pushes must not rebuild the list and reset its scroll.
    const key = `${this._recordState}|${locale}|${panelLanguage(this._hass)}|${this._request}`;
    if (key === this._recordsKey) return;
    this._recordsKey = key;
    const status = {
      loading: copy(this, "Caricamento…"),
      empty: copy(this, "Nessuna registrazione sulla microSD in questo giorno."),
      error: copy(this, "Registrazioni microSD non disponibili. Riprova più tardi."),
    }[this._recordState] || "";
    this.$("records-status").textContent = status;
    const rows = this._recordState === "ready" ? recordRows(this._records, locale) : [];
    this.$("records").replaceChildren(...rows.map((row) => {
      const item = document.createElement("li");
      const time = document.createElement("time");
      time.textContent = row.text;
      const type = document.createElement("span");
      type.className = "type";
      type.textContent = copy(this, row.label);
      item.append(time, type);
      return item;
    }));
  }
}

if (!customElements.get("vistoda-ezviz-media")) customElements.define("vistoda-ezviz-media", VistodaEzvizMedia);
