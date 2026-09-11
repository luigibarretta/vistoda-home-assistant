import { copy, localizeCopy } from "./panel-copy.js";

export class ProviderRecordingListManager {
  constructor(host) {
    this.host = host;
    this.lists = [];
    this.filterId = "";
    this.openRecordingId = null;
    this.editingId = null;
    this.managing = false;
    this.generation = 0;
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
    this.generation += 1;
    const generation = this.generation;
    this._key = key; this.config = config ? { ...config } : null; this.filterId = ""; this.openRecordingId = null;
    this.lists = []; this.update([]);
    if (!config?.entryId || !this.host._hass) return;
    try {
      const result = await this.host._hass.callWS(this._message("list", this.config));
      if (generation !== this.generation) return;
      this.update(result.lists);
    } catch (_error) {
      if (generation === this.generation) {
        this.host._setMessage?.(copy(this, "Liste temporaneamente non disponibili."));
      }
    }
  }

  update(lists) {
    this.lists = Array.isArray(lists) ? lists : [];
    if (this.filterId && !this.lists.some((item) => item.list_id === this.filterId)) {
      this.filterId = "";
    }
    if (!this.$) return;
    const options = [this._option("", copy(this, "Tutte le registrazioni")), ...this.lists.map((item) => (
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

  async forget(recordingId, hostContext = null) {
    const generation = this.generation;
    const config = { ...this.config };
    for (const item of this.lists.filter((value) => value.recording_ids.includes(recordingId))) {
      const result = await this.host._hass.callWS({ ...this._message("set_membership", config),
        list_id: item.list_id, recording_id: recordingId, included: false });
      if (generation !== this.generation || (hostContext && !this.host._isCurrent(hostContext))) return;
      this.update(result.lists);
    }
  }

  toggle(recordingId) {
    this.openRecordingId = this.openRecordingId === recordingId ? null : recordingId;
    this.host._listsChanged?.(false);
  }

  picker(recordingId) {
    const wrap = document.createElement("div"); wrap.className = "list-picker";
    const title = document.createElement("strong"); title.textContent = copy(this, "Aggiungi alle liste");
    wrap.append(title);
    if (!this.lists.length) {
      const empty = document.createElement("div"); empty.className = "muted";
      empty.textContent = copy(this, "Crea prima una lista personalizzata.");
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

  _message(action, config = this.config) {
    return { type: `media_bridge/provider/recording_lists/${action}`,
      provider: config.provider, entry_id: config.entryId };
  }

  async _create() {
    const input = this.$("list-name"); const name = input.value.trim();
    if (!name) return this.host._setMessage?.(copy(this, "Inserisci un nome per la lista."));
    await this._mutate({ ...this._message("create"), name }, copy(this, "Lista creata."), () => {
      input.value = ""; this._hideForm();
    });
  }

  async _rename(item, name) {
    if (!name) return this.host._setMessage?.(copy(this, "Inserisci un nome per la lista."));
    await this._mutate({ ...this._message("update"), list_id: item.list_id, name },
      copy(this, "Lista modificata."), () => { this.editingId = null; });
  }

  async _delete(item) {
    if (!globalThis.confirm(copy(this, "Eliminare la lista “{p0}”? I video resteranno salvati.", { p0: item.name }))) return;
    await this._mutate({ ...this._message("delete"), list_id: item.list_id },
      copy(this, "Lista eliminata."), () => { if (this.filterId === item.list_id) this.filterId = ""; });
  }

  async _membership(recordingId, item, input) {
    input.disabled = true;
    await this._mutate({ ...this._message("set_membership"), list_id: item.list_id,
      recording_id: recordingId, included: input.checked }, input.checked
      ? copy(this, "Video aggiunto alla lista.") : copy(this, "Video rimosso dalla lista."));
  }

  async _mutate(payload, success, after = () => {}) {
    const generation = this.generation;
    try {
      const result = await this.host._hass.callWS(payload);
      if (generation !== this.generation) return;
      after(); this.update(result.lists);
      this.host._setMessage?.(success);
    } catch (error) {
      const messages = { duplicate_name: copy(this, "Esiste già una lista con questo nome."),
        invalid_name: copy(this, "Il nome della lista non è valido."), list_limit: copy(this, "Numero massimo di liste raggiunto."),
        membership_limit: copy(this, "Questa lista ha raggiunto il limite di video."),
        list_not_found: copy(this, "La lista non esiste più.") };
      if (generation === this.generation) {
        this.host._setMessage?.(messages[error?.code] || copy(this, "Impossibile aggiornare le liste."));
      }
    }
    if (generation === this.generation) this.host._listsChanged?.(false);
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
      input.setAttribute("aria-label", copy(this, "Nuovo nome per {p0}", { p0: item.name }));
      form.append(input, this._icon("mdi:content-save", copy(this, "Salva"), "submit"),
        this._icon("mdi:close", copy(this, "Annulla"), "button", () => {
          this.editingId = null; this._renderManager();
        }));
      form.addEventListener("submit", (event) => {
        event.preventDefault(); this._rename(item, input.value.trim());
      });
      row.append(form); queueMicrotask(() => input.focus()); return row;
    }
    const summary = document.createElement("div"); const name = document.createElement("strong");
    name.textContent = item.name; const count = document.createElement("span"); count.className = "muted";
    count.textContent = copy(this, "{p0} video", { p0: item.recording_ids.length }); summary.append(name, count);
    const actions = document.createElement("div"); actions.className = "list-item-actions";
    actions.append(this._icon("mdi:pencil-outline", copy(this, "Modifica lista"), "button", () => {
      this.editingId = item.list_id; this._renderManager();
    }), this._icon("mdi:delete-outline", copy(this, "Elimina lista"), "button", () => this._delete(item), true));
    row.append(summary, actions); return row;
  }

  _icon(icon, label, type, action = null, danger = false) {
    const button = document.createElement("button"); button.type = type;
    button.className = `list-icon${danger ? " danger" : ""}`;
    button.setAttribute("aria-label", label); button.title = label; button.dataset.tooltip = label;
    button.innerHTML = `<ha-icon icon="${icon}"></ha-icon>`; localizeCopy(button, this);
    if (action) button.addEventListener("click", action); return button;
  }
}
