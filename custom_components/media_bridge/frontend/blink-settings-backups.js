import { copy, localizeCopy } from "./panel-copy.js";
import { BASE_STYLES } from "./panel-styles.js";

class VistodaBlinkSettingsBackups extends HTMLElement {
  constructor() {
    super(); this.attachShadow({ mode: "open" });
    this._items = []; this._busy = false; this._loaded = false;
    this.shadowRoot.innerHTML = `<style>${BASE_STYLES}
      :host{display:block;margin-top:14px}details{border-top:1px solid var(--divider-color)}
      summary{display:flex;align-items:center;gap:9px;min-height:48px;cursor:pointer;font-weight:750}
      summary ha-icon{color:var(--primary-color)}.create{display:flex;gap:8px;flex-wrap:wrap;margin:5px 0 12px}
      input{flex:1;min-width:180px;padding:9px 11px;border:1px solid var(--divider-color);border-radius:11px;
        color:var(--primary-text-color);background:var(--secondary-background-color);font:inherit}.list{display:grid;gap:8px}
      .backup{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;align-items:center;padding:11px;
        border-radius:13px;background:var(--secondary-background-color)}.backup small{display:block;margin-top:3px;
        color:var(--secondary-text-color)}.actions{display:flex;gap:6px}.actions button{width:42px;min-width:42px;padding:8px}
      #status{min-height:20px;margin-top:8px}@media(max-width:520px){.backup{grid-template-columns:1fr}
        .actions{justify-content:flex-end}.create>*{flex:1 1 100%}}
    </style><details><summary><ha-icon icon="mdi:backup-restore"></ha-icon><span data-copy="Backup impostazioni telecamere">Backup impostazioni telecamere</span></summary>
      <p class="muted" data-copy="Salva insieme le impostazioni di tutte le telecamere Blink e ripristina una versione precedente.">Salva insieme le impostazioni di tutte le telecamere Blink e ripristina una versione precedente.</p>
      <form class="create" id="create"><input id="name" maxlength="64" autocomplete="off" placeholder="Nome backup" data-copy-placeholder="Nome backup"
        aria-label="Nome backup" data-copy-aria-label="Nome backup"><button class="primary" id="save"><ha-icon icon="mdi:content-save-outline"></ha-icon><span data-copy="Crea backup">Crea backup</span></button></form>
      <div class="list" id="list"></div><div class="muted" id="empty" data-copy="Nessun backup delle impostazioni salvato.">Nessun backup delle impostazioni salvato.</div>
      <div class="muted" id="status" role="status"></div></details>`;
    localizeCopy(this.shadowRoot, this); this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("create").addEventListener("submit", (event) => { event.preventDefault(); this._create(); });
  }
  configure(hass, aliases) {
    this._hass = hass; this._aliases = aliases || []; this._render();
    if (hass && !this._loaded && !this._busy) this.reload();
  }
  async reload() {
    if (!this._hass || this._busy) return; this._setBusy(true, copy(this, "Lettura backup impostazioni…"));
    try {
      const result = await this._hass.callWS({ type: "blink_live_bridge/camera/settings/backups" });
      this._items = result.backups || []; this._loaded = true; this._status("");
    } catch { this._status(copy(this, "Backup impostazioni non disponibili.")); }
    finally { this._setBusy(false); }
  }
  async _create() {
    if (!this._aliases.length || this._busy) return;
    const name = this.$("name").value.trim() || copy(this, "Impostazioni Blink");
    this._setBusy(true, copy(this, "Creazione backup e verifica…"));
    try {
      await this._hass.callWS({ type: "blink_live_bridge/camera/settings/backups/create", name });
      this.$("name").value = ""; this._busy = false; await this.reload();
      this._status(copy(this, "Backup delle impostazioni creato."));
    } catch { this._status(copy(this, "Creazione backup non riuscita.")); }
    finally { this._setBusy(false); }
  }
  async _apply(item) {
    if (this._busy || !globalThis.confirm(copy(this,
      "Applicare “{p0}” a tutte le telecamere? Verrà creato un backup di rollback.", { p0: item.name }))) return;
    this._setBusy(true, copy(this, "Ripristino e verifica delle telecamere…"));
    try {
      await this._hass.callWS({ type: "blink_live_bridge/camera/settings/backups/apply", backup_id: item.backup_id });
      this._busy = false; await this.reload(); this._status(copy(this, "Impostazioni ripristinate e verificate."));
    } catch { this._status(copy(this, "Ripristino non completato; usa il backup di rollback creato automaticamente.")); }
    finally { this._setBusy(false); }
  }
  async _delete(item) {
    if (this._busy || !globalThis.confirm(copy(this, "Eliminare il backup “{p0}”?", { p0: item.name }))) return;
    this._setBusy(true, copy(this, "Eliminazione backup…"));
    try {
      await this._hass.callWS({ type: "blink_live_bridge/camera/settings/backups/delete", backup_id: item.backup_id });
      this._busy = false; await this.reload(); this._status(copy(this, "Backup eliminato."));
    } catch { this._status(copy(this, "Eliminazione backup non riuscita.")); }
    finally { this._setBusy(false); }
  }
  _render() {
    if (!this.$) return; localizeCopy(this.shadowRoot, this);
    const rows = this._items.map((item) => {
      const row = document.createElement("article"); row.className = "backup";
      const text = document.createElement("div"); const title = document.createElement("strong"); title.textContent = item.name;
      const meta = document.createElement("small"); meta.textContent = `${this._date(item.created_at)} · ${copy(this, "{p0} telecamere", { p0: item.camera_count })}`;
      text.append(title, meta); const actions = document.createElement("div"); actions.className = "actions";
      actions.append(this._button("mdi:backup-restore", copy(this, "Applica backup"), () => this._apply(item)),
        this._button("mdi:delete-outline", copy(this, "Elimina backup"), () => this._delete(item), true));
      row.append(text, actions); return row;
    });
    this.$("list").replaceChildren(...rows); this.$("empty").hidden = Boolean(rows.length);
    this.$("save").disabled = this._busy || !this._aliases.length;
    for (const button of this.$("list").querySelectorAll("button")) button.disabled = this._busy;
  }
  _button(icon, label, action, danger = false) {
    const button = document.createElement("button"); button.type = "button";
    if (danger) button.className = "danger"; button.title = label; button.setAttribute("aria-label", label);
    button.innerHTML = `<ha-icon icon="${icon}"></ha-icon>`; button.addEventListener("click", action); return button;
  }
  _setBusy(value, message = "") { this._busy = value; if (message) this._status(message); this._render(); }
  _status(value) { this.$("status").textContent = value; }
  _date(value) { const date = new Date(value); return Number.isNaN(date.valueOf()) ? "—" : date.toLocaleString(this._hass?.locale?.language || "en"); }
}
if (!customElements.get("vistoda-blink-settings-backups")) customElements.define("vistoda-blink-settings-backups", VistodaBlinkSettingsBackups);
