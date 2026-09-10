export const PROVIDER_LIST_TEMPLATE = `
  <div class="list-controls"><select id="list-filter" aria-label="Filtra per lista">
    <option value="">Tutte le registrazioni</option></select>
    <button id="new-list"><ha-icon icon="mdi:playlist-plus"></ha-icon><span>Nuova lista</span></button>
    <button id="manage-lists" aria-expanded="false"><ha-icon icon="mdi:playlist-edit"></ha-icon>
      <span>Gestisci liste</span><span class="count" id="manage-count">0</span></button></div>
  <form class="list-form" id="list-form" hidden><input id="list-name" maxlength="64"
    autocomplete="off" placeholder="Nome della lista" aria-label="Nome della nuova lista">
    <button type="submit">Crea</button><button type="button" id="cancel-list">Annulla</button></form>
  <section class="list-manager" id="list-manager" hidden><div class="muted" id="list-empty">
    Non hai ancora creato liste.</div><div id="list-items"></div></section>`;

export const PROVIDER_LIST_STYLES = `
  .list-controls { display:flex; flex-wrap:wrap; align-items:center; gap:8px; margin:12px 0; }
  .list-controls select { flex:1 1 190px; min-height:44px; box-sizing:border-box;
    padding:9px 38px 9px 12px; border:1px solid var(--divider-color); border-radius:13px;
    color:var(--primary-text-color); background-color:var(--secondary-background-color);
    font:inherit; color-scheme:dark; }
  .list-controls button { display:inline-flex; align-items:center; gap:7px; }
  .list-controls .count { display:grid; place-items:center; min-width:20px; min-height:20px;
    padding:0 5px; border-radius:999px; background:var(--secondary-background-color); font-size:11px; }
  .list-form, .list-edit { display:flex; flex-wrap:wrap; gap:8px; margin:10px 0; }
  .list-form input, .list-edit input { flex:1 1 180px; min-height:44px; box-sizing:border-box;
    padding:9px 12px; border:1px solid var(--divider-color); border-radius:11px;
    color:var(--primary-text-color); background:var(--card-background-color); }
  .list-manager { margin:10px 0 14px; padding:10px 12px; border:1px solid var(--divider-color);
    border-radius:14px; }
  .list-item { display:flex; align-items:center; justify-content:space-between; gap:10px;
    min-height:52px; border-top:1px solid var(--divider-color); }
  .list-item:first-child { border-top:0; }
  .list-item > div:first-child { display:grid; gap:2px; min-width:0; }
  .list-item-actions { display:flex; gap:6px; }
  .list-icon { width:42px; height:42px; min-width:42px; padding:0; display:grid; place-items:center; }
  .list-icon ha-icon { --mdc-icon-size:21px; }
  .list-picker { grid-column:1 / -1; display:grid; gap:8px; width:100%; margin-top:8px;
    padding:11px; box-sizing:border-box; border-radius:12px; background:var(--card-background-color); }
  .list-picker label { display:flex; align-items:center; gap:9px; min-height:40px; }
  .list-picker input { width:20px; height:20px; }
  .list-tags { display:flex; flex-wrap:wrap; gap:5px; margin-top:6px; }
  .list-tag { padding:3px 7px; border-radius:999px; font-size:11px;
    background:color-mix(in srgb,var(--primary-color) 13%,transparent); }
  @media (max-width:600px) {
    .list-controls > button { flex:1 1 auto; }
    .list-item { align-items:flex-start; padding:8px 0; }
  }`;

export class ProviderRecordingListManager {
  constructor(host) {
    this.host = host;
    this.lists = [];
    this.filterId = "";
    this.openRecordingId = null;
    this.editingId = null;
    this.managing = false;
  }

  mount(root) {
    this.$ = (id) => root.getElementById(id);
    this.$("list-filter").addEventListener("change", (event) => {
      this.filterId = event.target.value;
      this.openRecordingId = null;
      this.host._listsChanged?.(true);
    });
    this.$("new-list").addEventListener("click", () => {
      this.managing = true; this._showForm(); this._renderManager();
    });
    this.$("manage-lists").addEventListener("click", () => {
      this.managing = !this.managing; this.editingId = null; this._renderManager();
    });
    this.$("cancel-list").addEventListener("click", () => this._hideForm());
    this.$("list-form").addEventListener("submit", (event) => {
      event.preventDefault(); this._create();
    });
  }

  async configure(config) {
    const key = `${config?.provider || ""}:${config?.entryId || ""}`;
    if (key === this._key) return;
    this._key = key; this.config = config; this.filterId = ""; this.openRecordingId = null;
    this.lists = []; this.update([]);
    if (!config?.entryId || !this.host._hass) return;
    try {
      const result = await this.host._hass.callWS(this._message("list"));
      this.update(result.lists);
    } catch (_error) { this.host._setMessage?.("Liste temporaneamente non disponibili."); }
  }

  update(lists) {
    this.lists = Array.isArray(lists) ? lists : [];
    if (this.filterId && !this.lists.some((item) => item.list_id === this.filterId)) {
      this.filterId = "";
    }
    if (!this.$) return;
    const options = [this._option("", "Tutte le registrazioni"), ...this.lists.map((item) => (
      this._option(item.list_id, `${item.name} (${item.recording_ids.length})`)
    ))];
    this.$("list-filter").replaceChildren(...options);
    this.$("list-filter").value = this.filterId;
    this.$("manage-count").textContent = String(this.lists.length);
    this._renderManager();
  }

  filtered(items, identity) {
    if (!this.filterId) return items;
    const list = this.lists.find((item) => item.list_id === this.filterId);
    const members = new Set(list?.recording_ids || []);
    return items.filter((item) => members.has(identity(item)));
  }

  names(recordingId) {
    return this.lists.filter((item) => item.recording_ids.includes(recordingId))
      .map((item) => item.name);
  }

  async forget(recordingId) {
    for (const item of this.lists.filter((value) => value.recording_ids.includes(recordingId))) {
      const result = await this.host._hass.callWS({ ...this._message("set_membership"),
        list_id: item.list_id, recording_id: recordingId, included: false });
      this.update(result.lists);
    }
  }

  toggle(recordingId) {
    this.openRecordingId = this.openRecordingId === recordingId ? null : recordingId;
    this.host._listsChanged?.(false);
  }

  picker(recordingId) {
    const wrap = document.createElement("div"); wrap.className = "list-picker";
    const title = document.createElement("strong"); title.textContent = "Aggiungi alle liste";
    wrap.append(title);
    if (!this.lists.length) {
      const empty = document.createElement("div"); empty.className = "muted";
      empty.textContent = "Crea prima una lista personalizzata.";
      wrap.append(empty); return wrap;
    }
    for (const item of this.lists) {
      const label = document.createElement("label"); const input = document.createElement("input");
      input.type = "checkbox"; input.checked = item.recording_ids.includes(recordingId);
      input.addEventListener("change", () => this._membership(recordingId, item, input));
      const text = document.createElement("span"); text.textContent = item.name;
      label.append(input, text); wrap.append(label);
    }
    return wrap;
  }

  tags(recordingId) {
    const names = this.names(recordingId);
    if (!names.length) return null;
    const tags = document.createElement("div"); tags.className = "list-tags";
    tags.append(...names.map((name) => {
      const tag = document.createElement("span"); tag.className = "list-tag"; tag.textContent = name;
      return tag;
    }));
    return tags;
  }

  _message(action) {
    return { type: `media_bridge/provider/recording_lists/${action}`,
      provider: this.config.provider, entry_id: this.config.entryId };
  }

  async _create() {
    const input = this.$("list-name"); const name = input.value.trim();
    if (!name) return this.host._setMessage?.("Inserisci un nome per la lista.");
    await this._mutate({ ...this._message("create"), name }, "Lista creata.", () => {
      input.value = ""; this._hideForm();
    });
  }

  async _rename(item, name) {
    if (!name) return this.host._setMessage?.("Inserisci un nome per la lista.");
    await this._mutate({ ...this._message("update"), list_id: item.list_id, name },
      "Lista modificata.", () => { this.editingId = null; });
  }

  async _delete(item) {
    if (!globalThis.confirm(`Eliminare la lista “${item.name}”? I video resteranno salvati.`)) return;
    await this._mutate({ ...this._message("delete"), list_id: item.list_id },
      "Lista eliminata.", () => { if (this.filterId === item.list_id) this.filterId = ""; });
  }

  async _membership(recordingId, item, input) {
    input.disabled = true;
    await this._mutate({ ...this._message("set_membership"), list_id: item.list_id,
      recording_id: recordingId, included: input.checked }, input.checked
      ? "Video aggiunto alla lista." : "Video rimosso dalla lista.");
  }

  async _mutate(payload, success, after = () => {}) {
    try {
      const result = await this.host._hass.callWS(payload); after(); this.update(result.lists);
      this.host._setMessage?.(success);
    } catch (error) {
      const messages = { duplicate_name: "Esiste già una lista con questo nome.",
        invalid_name: "Il nome della lista non è valido.", list_limit: "Numero massimo di liste raggiunto.",
        membership_limit: "Questa lista ha raggiunto il limite di video.",
        list_not_found: "La lista non esiste più." };
      this.host._setMessage?.(messages[error?.code] || "Impossibile aggiornare le liste.");
    }
    this.host._listsChanged?.(false);
  }

  _showForm() { this.$("list-form").hidden = false; this.$("list-name").focus(); }
  _hideForm() { this.$("list-form").hidden = true; this.$("list-name").value = ""; }
  _option(value, label) { const option = document.createElement("option");
    option.value = value; option.textContent = label; return option; }

  _renderManager() {
    if (!this.$) return;
    this.$("list-manager").hidden = !this.managing;
    this.$("manage-lists").setAttribute("aria-expanded", String(this.managing));
    if (!this.managing) return;
    this.$("list-empty").hidden = this.lists.length !== 0;
    this.$("list-items").replaceChildren(...this.lists.map((item) => this._row(item)));
  }

  _row(item) {
    const row = document.createElement("div"); row.className = "list-item";
    if (this.editingId === item.list_id) {
      const form = document.createElement("form"); form.className = "list-edit";
      const input = document.createElement("input"); input.value = item.name; input.maxLength = 64;
      input.setAttribute("aria-label", `Nuovo nome per ${item.name}`);
      form.append(input, this._icon("mdi:content-save", "Salva", "submit"),
        this._icon("mdi:close", "Annulla", "button", () => {
          this.editingId = null; this._renderManager();
        }));
      form.addEventListener("submit", (event) => {
        event.preventDefault(); this._rename(item, input.value.trim());
      });
      row.append(form); queueMicrotask(() => input.focus()); return row;
    }
    const summary = document.createElement("div"); const name = document.createElement("strong");
    name.textContent = item.name; const count = document.createElement("span"); count.className = "muted";
    count.textContent = `${item.recording_ids.length} video`; summary.append(name, count);
    const actions = document.createElement("div"); actions.className = "list-item-actions";
    actions.append(this._icon("mdi:pencil-outline", "Modifica lista", "button", () => {
      this.editingId = item.list_id; this._renderManager();
    }), this._icon("mdi:delete-outline", "Elimina lista", "button", () => this._delete(item), true));
    row.append(summary, actions); return row;
  }

  _icon(icon, label, type, action = null, danger = false) {
    const button = document.createElement("button"); button.type = type;
    button.className = `list-icon${danger ? " danger" : ""}`;
    button.setAttribute("aria-label", label); button.title = label; button.dataset.tooltip = label;
    button.innerHTML = `<ha-icon icon="${icon}"></ha-icon>`;
    if (action) button.addEventListener("click", action); return button;
  }
}
