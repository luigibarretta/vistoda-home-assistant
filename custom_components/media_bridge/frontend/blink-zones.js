import { copy, localizeCopy } from "./panel-copy.js";
import { BASE_STYLES } from "./panel-styles.js";
import {
  GRID_COLUMNS, GRID_ROWS, activityEnabled, allActivityDisabled, privacyContains,
  rectangleFromCells, sameZoneDraft, setActivity,
} from "./blink-zone-model.js";
import { BLINK_ZONE_STYLES } from "./blink-zone-styles.js";

class VistodaBlinkZones extends HTMLElement {
  constructor() {
    super(); this.attachShadow({ mode: "open" }); this._request = 0; this._tab = "activity";
    this._zones = null; this._masks = []; this._privacy = []; this._drag = null; this._mount();
  }

  set hass(value) { this._hass = value; this._render(); }
  set camera(value) {
    if (value?.alias === this._camera?.alias && value?.snapshot === this._camera?.snapshot) return;
    const changed = value?.alias !== this._camera?.alias; this._camera = value;
    if (changed) { this._request += 1; this._zones = null; this._masks = []; this._privacy = []; this._load(); }
    else this._render();
  }

  _mount() {
    this.shadowRoot.innerHTML = `<style>${BASE_STYLES}${BLINK_ZONE_STYLES}</style>
      <section class="card zones"><header><div><div class="eyebrow"><span data-copy="Rilevamento e privacy">Rilevamento e privacy</span></div>
        <h3><span data-copy="Zone telecamera">Zone telecamera</span></h3><div class="muted"><span data-copy="Griglia Blink nativa 20 × 15.">Griglia Blink nativa 20 × 15.</span></div></div>
        <button id="reload" aria-label="Rileggi le zone dal cloud Blink" data-copy-aria-label="Rileggi le zone dal cloud Blink"
          title="Rileggi le zone dal cloud Blink" data-copy-title="Rileggi le zone dal cloud Blink"
          data-tooltip="Rilegge dal cloud Blink le zone di questa telecamera" data-copy-data-tooltip="Rilegge dal cloud Blink le zone di questa telecamera">↻</button></header>
        <div class="tabs" role="tablist"><button id="activity" role="tab"><span data-copy="Zone attività">Zone attività</span></button>
          <button id="privacy" role="tab"><span data-copy="Zone privacy">Zone privacy</span></button></div>
        <div class="editor-viewport" id="editor-viewport" tabindex="0" role="region" data-copy-aria-label="Scorri la griglia delle zone">
        <div class="editor" id="editor"><img id="photo" alt=""><div class="grid" id="grid"></div>
          <div id="overlays"></div></div></div><div class="legend" id="legend"></div>
        <p class="muted" data-copy="Scorri la griglia per raggiungere tutte le zone. Usa Tab e Spazio per modificarle da tastiera."></p>
        <div class="zone-actions"><button id="add"><span data-copy="+ Area privacy">+ Area privacy</span></button><button id="reset"><span data-copy="Ripristina">Ripristina</span></button>
          <button class="primary save" id="save"><span data-copy="Salva e verifica">Salva e verifica</span></button></div>
        <div class="muted" id="status" role="status"></div></section>`; localizeCopy(this.shadowRoot, this);
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("reload").addEventListener("click", () => this._load());
    this.$("activity").addEventListener("click", () => this._selectTab("activity"));
    this.$("privacy").addEventListener("click", () => this._selectTab("privacy"));
    this.$("add").addEventListener("click", () => { this._addingPrivacy = true; this._status(copy(this, "Trascina sull’immagine per creare l’area.")); });
    this.$("reset").addEventListener("click", () => this._reset());
    this.$("save").addEventListener("click", () => this._save());
    this.$("editor").addEventListener("pointerdown", (event) => this._pointerDown(event));
    this.$("editor").addEventListener("pointermove", (event) => this._pointerMove(event));
    this.$("editor").addEventListener("pointerup", (event) => this._pointerUp(event));
    this.$("editor").addEventListener("pointercancel", () => { this._drag = null; this._render(); });
  }

  async _load() {
    if (!this._hass || !this._camera?.alias) { this._render(); return; }
    const request = ++this._request; this._status(copy(this, "Lettura zone…")); this.$("reload").disabled = true;
    try {
      const zones = await this._hass.callWS({ type: "blink_live_bridge/camera/zones", alias: this._camera.alias });
      if (request === this._request) { this._zones = zones; this._masks = [...zones.activity_masks];
        this._privacy = zones.privacy_zones.map((zone) => ({ ...zone })); this._status(""); this._render(); }
    } catch (_error) {
      if (request === this._request) { this._zones = null; this._status(copy(this, "Zone non supportate da questo modello.")); this._render(); }
    } finally { if (request === this._request) this.$("reload").disabled = false; }
  }

  _selectTab(tab) { if (tab === "privacy" && !this._zones?.privacy_supported) return;
    this._tab = tab; this._addingPrivacy = false; this._render(); }

  _render() {
    localizeCopy(this.shadowRoot, this);
    this.hidden = !this._camera?.alias; if (this.hidden) return;
    this.$("photo").src = this._camera.snapshot || ""; this.$("photo").alt = copy(this, "Snapshot {p0}", { p0: this._camera.name || "Blink" });
    const ready = Boolean(this._zones); this.$("editor-viewport").hidden = !ready;
    for (const tab of ["activity", "privacy"]) { const button = this.$(tab);
      button.classList.toggle("active", this._tab === tab); button.setAttribute("aria-selected", String(this._tab === tab)); }
    this.$("privacy").disabled = !this._zones?.privacy_supported;
    this.$("add").hidden = this._tab !== "privacy"; this.$("add").disabled = !ready || this._privacy.length >= 2;
    this.$("reset").disabled = !ready; this.$("save").disabled = !ready || !this._editable() || this._clean();
    this.$("legend").innerHTML = this._tab === "activity"
      ? '<span class="swatch"></span><span data-copy="Verde: rilevamento attivo · Tocca o trascina per modificare"></span>'
      : '<span class="swatch private"></span><span data-copy="Scuro: area esclusa da movimento e registrazione"></span>'; localizeCopy(this.$("legend"), this);
    if (ready) { this._renderGrid(); this._renderPrivacy(); }
  }

  _renderGrid() {
    const cells = [];
    for (let y = 0; y < GRID_ROWS; y += 1) for (let x = 0; x < GRID_COLUMNS; x += 1) {
      const cell = document.createElement("button"); const active = activityEnabled(this._masks, x, y);
      const privateCell = privacyContains(this._privacy, x, y); cell.className = `cell${active ? " active" : ""}${privateCell ? " private" : ""}`;
      cell.dataset.x = x; cell.dataset.y = y; cell.tabIndex = this._tab === "activity" ? 0 : -1;
      cell.setAttribute("aria-label", copy(this, "Riga {p0}, colonna {p1}: {p2}", { p0: y + 1, p1: x + 1, p2: privateCell ? "privacy" : copy(this, active ? "attiva" : "inattiva") }));
      cell.setAttribute("aria-pressed", String(active));
      cell.disabled = !this._editable() || privateCell || this._tab !== "activity";
      cell.addEventListener("click", (event) => {
        if (event.detail !== 0 || cell.disabled) return;
        this._masks = setActivity(this._masks, x, y, !active); this._render();
        this.$("grid").children[y * GRID_COLUMNS + x]?.focus();
      });
      cells.push(cell);
    }
    this.$("grid").replaceChildren(...cells);
  }

  _renderPrivacy() {
    const overlays = this._privacy.map((zone, index) => this._overlay(zone, index));
    if (this._drag?.kind === "privacy") overlays.push(this._overlay(rectangleFromCells(this._drag.start, this._drag.end), -1));
    this.$("overlays").replaceChildren(...overlays);
  }

  _overlay(zone, index) {
    const item = document.createElement("div"); item.className = `privacy-overlay${index < 0 ? " preview" : ""}`;
    Object.assign(item.style, { left: `${zone.x / GRID_COLUMNS * 100}%`, top: `${zone.y / GRID_ROWS * 100}%`,
      width: `${zone.w / GRID_COLUMNS * 100}%`, height: `${zone.h / GRID_ROWS * 100}%` });
    if (index >= 0 && this._tab === "privacy" && this._editable()) { const remove = document.createElement("button");
      remove.textContent = "×"; remove.setAttribute("aria-label", copy(this, "Elimina zona privacy {p0}", { p0: index + 1 }));
      remove.title = copy(this, "Elimina zona privacy {p0}", { p0: index + 1 });
      remove.addEventListener("click", () => { this._privacy.splice(index, 1); this._render(); }); item.append(remove); }
    return item;
  }

  _pointerDown(event) {
    if (!this._editable() || !this._zones) return; const point = this._point(event);
    if (this._tab === "privacy") { if (!this._addingPrivacy || this._privacy.length >= 2) return;
      this._drag = { kind: "privacy", start: point, end: point }; }
    else if (!privacyContains(this._privacy, point.x, point.y)) { const enabled = !activityEnabled(this._masks, point.x, point.y);
      this._drag = { kind: "activity", enabled, seen: new Set() }; this._paint(point); }
    if (!this._drag) return;
    this.$("editor").setPointerCapture(event.pointerId); event.preventDefault(); this._render();
  }

  _pointerMove(event) { if (!this._drag) return; const point = this._point(event);
    if (this._drag.kind === "privacy") this._drag.end = point; else this._paint(point); this._render(); }

  _pointerUp(event) { if (!this._drag) return;
    if (this._drag.kind === "privacy") { this._drag.end = this._point(event);
      this._privacy.push(rectangleFromCells(this._drag.start, this._drag.end)); this._addingPrivacy = false; }
    this._drag = null; this._render(); }

  _paint(point) { const key = `${point.x}:${point.y}`;
    if (this._drag.seen.has(key) || privacyContains(this._privacy, point.x, point.y)) return;
    this._drag.seen.add(key); this._masks = setActivity(this._masks, point.x, point.y, this._drag.enabled); }

  _point(event) { const box = this.$("editor").getBoundingClientRect();
    return { x: Math.max(0, Math.min(19, Math.floor((event.clientX - box.left) / box.width * 20))),
      y: Math.max(0, Math.min(14, Math.floor((event.clientY - box.top) / box.height * 15))) }; }

  _reset() { const privacy = this._tab === "privacy";
    if (!globalThis.confirm(privacy ? copy(this, "Eliminare tutte le zone privacy?") : copy(this, "Riattivare tutte le zone di movimento?"))) return;
    if (privacy) this._privacy = []; else this._masks = Array(25).fill(4095); this._render(); }

  async _save() {
    if (allActivityDisabled(this._masks)) { this._status(copy(this, "Almeno una zona attività deve restare attiva.")); return; }
    if (!globalThis.confirm(copy(this, "Confermi il salvataggio delle zone Blink per questa telecamera?"))) return;
    this._status(copy(this, "Salvataggio, verifica e ripristino automatico in caso di errore…")); this.$("save").disabled = true;
    const request = ++this._request; const alias = this._camera.alias; const hass = this._hass;
    try { const zones = await hass.callWS({ type: "blink_live_bridge/camera/zones/update",
      alias, revision: this._zones.revision, activity_masks: this._masks, privacy_zones: this._privacy });
      if (request !== this._request || this._camera?.alias !== alias) return;
      this._zones = zones; this._masks = [...zones.activity_masks]; this._privacy = zones.privacy_zones.map((zone) => ({ ...zone }));
      this._status(copy(this, "Zone verificate sulla telecamera.")); this._render();
    } catch (_error) { if (request !== this._request || this._camera?.alias !== alias) return;
      this._status(copy(this, "Modifica non confermata: configurazione precedente ripristinata.")); await this._load(); }
  }

  _editable() { return this._hass?.user?.is_admin === true; }
  _clean() { return sameZoneDraft(this._zones, this._masks, this._privacy); }
  _status(text) { this.$("status").textContent = text; }
}

if (!customElements.get("vistoda-blink-zones")) customElements.define("vistoda-blink-zones", VistodaBlinkZones);
