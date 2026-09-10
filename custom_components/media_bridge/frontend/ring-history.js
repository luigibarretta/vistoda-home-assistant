import { BASE_STYLES } from "./panel-styles.js";
import "./ring-identity-dialog.js";

const PAGE_SIZE = 20;
const META = {
  unlock: ["mdi:lock-open-outline", "Portone aperto da te", "unlock"],
  live_view: ["mdi:play-circle-outline", "Live View", "live"],
  ding: ["mdi:bell-ring-outline", "Chiamata al citofono", "ding"],
  motion: ["mdi:motion-sensor", "Movimento rilevato", "motion"],
  activity: ["mdi:history", "Attività Ring", "activity"],
};

export class RingHistory extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._mounted = false;
    this._events = [];
    this._cursor = null;
    this._generation = 0;
    this._filter = "all";
  }

  configure(hass, entry) {
    this._hass = hass;
    this._entry = entry;
    if (!this._mounted) this._mount();
    this.$("device-filter").textContent = entry.device_name || entry.name;
    this.$("location").textContent = this._location(entry);
    this._load(true);
  }

  _mount() {
    this._mounted = true;
    this.shadowRoot.innerHTML = `
      <style>${BASE_STYLES}
        :host{width:100%;max-width:100%;min-width:0}.history{width:100%;max-width:100%;overflow:hidden}
        .head{display:flex;align-items:center;gap:13px;padding:19px 20px;
          border-bottom:1px solid var(--divider-color)}.head h2{margin:0;font-size:22px;flex:1;
          min-width:0}
        .head button{min-width:44px;padding:8px}.location{padding:0 20px 16px;
          color:var(--secondary-text-color);font-size:13px}
        .filters{display:flex;gap:9px;padding:16px 20px;overflow-x:auto;
          border-bottom:1px solid var(--divider-color)}.pill{min-height:40px;border:1px solid
          var(--divider-color);border-radius:999px;padding:8px 13px;display:inline-flex;
          align-items:center;gap:7px;white-space:nowrap;font-weight:650;background:transparent}
        .pill.active{border-color:#229ed9;background:color-mix(in srgb,#229ed9 22%,transparent)}
        .pill ha-icon{--mdc-icon-size:19px;color:#229ed9}.select-pill{position:relative;padding:0}
        select{min-height:40px;border:0;border-radius:999px;padding:8px 35px 8px 13px;
          appearance:none;color:var(--primary-text-color);background:transparent;font:inherit;
          font-weight:650;cursor:pointer}.select-pill>ha-icon{position:absolute;right:10px;
          pointer-events:none;color:var(--secondary-text-color);--mdc-icon-size:18px}
        .body{min-height:180px}.day h3{margin:0;padding:17px 20px 11px;color:var(--secondary-text-color);
          font-size:14px;border-bottom:1px solid var(--divider-color)}
        .event{display:grid;grid-template-columns:42px minmax(0,1fr) auto;gap:12px;
          align-items:center;padding:17px 20px;border-bottom:1px solid var(--divider-color)}
        .event-icon{display:grid;place-items:center;width:38px;height:38px;border-radius:50%;
          background:var(--secondary-background-color)}.event-icon ha-icon{--mdc-icon-size:24px}
        .event-icon.unlock{color:#229ed9}.event-icon.live{color:#ef7b2d}
        .event-icon.ding{color:var(--primary-color)}.event-icon.motion{color:#e3a21a}
        .event-icon.activity{color:var(--secondary-text-color)}
        .event strong,.event span{display:block}.event strong{font-size:16px;margin-bottom:4px}
        .event .device{color:var(--secondary-text-color);font-size:14px}.time{font-size:14px;
          color:var(--secondary-text-color);font-variant-numeric:tabular-nums}
        .footer{display:grid;place-items:center;padding:17px 20px}.notice{margin:0;padding:12px 20px;
          color:var(--secondary-text-color);font-size:13px;text-align:center}
        @media(max-width:520px){.head{padding:15px 14px;gap:7px}.head h2{font-size:20px}
          .filters{padding:13px 14px}.event{padding:16px 14px}.day h3{padding-left:14px}
          .location{padding:0 14px 14px}}
      </style>
      <section class="card history"><header class="head"><button id="back"
        aria-label="Torna a Ring Intercom" title="Torna a Ring Intercom">
        <ha-icon icon="mdi:arrow-left"></ha-icon></button><h2>Cronologia eventi</h2>
        <button id="edit" disabled aria-label="Modifica identità Ring" title="Modifica identità Ring"
          data-tooltip="Scegli i nomi usati in cronologia e notifiche">
          <ha-icon icon="mdi:pencil-outline"></ha-icon></button>
        <button id="refresh" aria-label="Aggiorna cronologia" title="Aggiorna cronologia"
          data-tooltip="Rilegge gli eventi più recenti da Ring">
          <ha-icon icon="mdi:refresh"></ha-icon></button></header>
        <div class="location" id="location">Location Ring</div>
        <div class="filters" aria-label="Filtri cronologia">
          <span class="pill active"><ha-icon icon="mdi:lock-outline"></ha-icon>
            Accessi e citofoni</span><span class="pill"><ha-icon icon="mdi:door"></ha-icon>
            <span id="device-filter">Ring Intercom</span></span>
          <label class="pill select-pill"><select id="event-filter" aria-label="Tipo evento">
            <option value="all">Tutti gli eventi</option><option value="unlock">Aperture</option>
            <option value="live_view">Live View</option><option value="ding">Chiamate</option>
          </select><ha-icon icon="mdi:chevron-down"></ha-icon></label></div>
        <p class="notice" id="notice" hidden></p><div class="body" id="body"></div>
        <div class="footer"><button id="more" hidden><ha-icon icon="mdi:chevron-down"></ha-icon>
          Carica eventi precedenti</button></div></section>
        <vistoda-ring-identity-dialog id="identity-dialog"></vistoda-ring-identity-dialog>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("back").addEventListener("click", () => this.dispatchEvent(new CustomEvent(
      "history-close", { bubbles: true, composed: true },
    )));
    this.$("refresh").addEventListener("click", () => this._load(true));
    this.$("edit").addEventListener("click", () => this.$("identity-dialog").show());
    this.$("identity-dialog").addEventListener("identity-updated", (event) => {
      const result = event.detail;
      this._identityConfiguration = result.identity_configuration;
      this.$("device-filter").textContent = result.identity.device_name;
      this.$("location").textContent = this._location(result.identity);
      this.$("identity-dialog").configure(this._hass, this._entry, this._identityConfiguration);
      this._render();
    });
    this.$("more").addEventListener("click", () => this._load(false));
    this.$("event-filter").addEventListener("change", (event) => {
      this._filter = event.target.value; this._render();
    });
  }

  async _load(reset) {
    if (!this._hass || !this._entry) return;
    const generation = ++this._generation;
    if (reset) { this._events = []; this._cursor = null; }
    this.$("refresh").disabled = true; this.$("more").disabled = true;
    this.$("notice").hidden = false;
    this.$("notice").textContent = reset ? "Caricamento cronologia…" : "Caricamento…";
    try {
      const request = { type: "media_bridge/ring/history", entry_id: this._entry.entry_id,
        limit: PAGE_SIZE };
      if (!reset && this._cursor) request.cursor = this._cursor;
      const page = await this._hass.callWS(request);
      if (generation !== this._generation) return;
      this.$("device-filter").textContent = page.identity.device_name;
      this.$("location").textContent = this._location(page.identity);
      this._identityConfiguration = page.identity_configuration;
      this.$("identity-dialog").configure(this._hass, this._entry,
        this._identityConfiguration);
      this.$("edit").disabled = false;
      const known = new Set(this._events.map((item) => item.event_id));
      this._events.push(...page.events.filter((item) => !known.has(item.event_id)));
      this._events.sort((left, right) => right.occurred_at - left.occurred_at);
      this._cursor = page.next_cursor;
      this.$("notice").textContent = page.degraded
        ? "Ring cloud non raggiungibile: sono mostrati gli eventi salvati da Vistoda."
        : "";
      this.$("notice").hidden = !page.degraded;
      this._render();
    } catch (_error) {
      this.$("notice").textContent = "Cronologia Ring temporaneamente non disponibile.";
      this.$("notice").hidden = false;
    } finally {
      if (generation === this._generation) this.$("refresh").disabled = false;
      this.$("more").disabled = false;
    }
  }

  _render() {
    const events = this._filter === "all" ? this._events
      : this._events.filter((item) => item.event_type === this._filter);
    const groups = new Map();
    for (const event of events) {
      const label = this._dayLabel(event.occurred_at);
      if (!groups.has(label)) groups.set(label, []);
      groups.get(label).push(event);
    }
    const nodes = [...groups].map(([label, items]) => {
      const section = document.createElement("section"); section.className = "day";
      const heading = document.createElement("h3"); heading.textContent = label;
      section.append(heading, ...items.map((item) => this._eventNode(item)));
      return section;
    });
    if (!nodes.length) {
      const empty = document.createElement("div"); empty.className = "empty muted";
      empty.textContent = "Nessun evento per questo filtro."; nodes.push(empty);
    }
    this.$("body").replaceChildren(...nodes);
    this.$("more").hidden = !this._cursor;
  }

  _eventNode(event) {
    const [icon, title, className] = META[event.event_type] || META.activity;
    const row = document.createElement("article"); row.className = "event";
    row.innerHTML = `<span class="event-icon ${className}"><ha-icon icon="${icon}"></ha-icon></span>
      <div><strong></strong><span class="device"></span></div><time class="time"></time>`;
    row.querySelector("strong").textContent = title;
    row.querySelector(".device").textContent = this.$("device-filter").textContent;
    row.querySelector("time").textContent = this._time(event.occurred_at);
    return row;
  }

  _dayLabel(timestamp) {
    const date = new Date(timestamp * 1000); const now = new Date();
    const today = this._dateKey(now); const yesterday = this._dateKey(new Date(now - 86400000));
    const key = this._dateKey(date);
    if (key === today) return "Oggi";
    if (key === yesterday) return "Ieri";
    return new Intl.DateTimeFormat("it-IT", { day: "2-digit", month: "long", year: "numeric",
      timeZone: this._timeZone() }).format(date);
  }

  _dateKey(date) {
    return new Intl.DateTimeFormat("en-CA", { year: "numeric", month: "2-digit", day: "2-digit",
      timeZone: this._timeZone() }).format(date);
  }

  _time(timestamp) {
    return new Intl.DateTimeFormat("it-IT", { hour: "2-digit", minute: "2-digit", hour12: false,
      timeZone: this._timeZone() }).format(new Date(timestamp * 1000));
  }

  _timeZone() { return this._hass?.config?.time_zone || "Europe/Rome"; }

  _location(identity) {
    const location = identity.location_name || "Location Ring";
    const city = identity.city || "";
    return city && !location.toLocaleLowerCase("it-IT").endsWith(` in ${city}`
      .toLocaleLowerCase("it-IT")) ? `${location} · ${city}` : location;
  }
}

if (!customElements.get("vistoda-ring-history")) {
  customElements.define("vistoda-ring-history", RingHistory);
}
