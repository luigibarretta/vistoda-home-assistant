export class RingRecordingListManager {
  constructor(host) {
    this.host = host;
    this.lists = [];
    this.filterId = "";
    this.openRecordingId = null;
  }

  mount(root) {
    this.$ = (id) => root.getElementById(id);
    this.$("list-filter").addEventListener("change", (event) => {
      this.filterId = event.target.value;
      this.openRecordingId = null;
      this.host.changed(true);
    });
    this.$("new-list").addEventListener("click", () => this._showForm());
    this.$("cancel-list").addEventListener("click", () => this._hideForm());
    this.$("list-form").addEventListener("submit", (event) => {
      event.preventDefault();
      this._create();
    });
    this.$("delete-list").addEventListener("click", () => this._delete());
  }

  update(lists) {
    this.lists = Array.isArray(lists) ? lists : [];
    if (this.filterId && !this.lists.some((item) => item.list_id === this.filterId)) {
      this.filterId = "";
    }
    const select = this.$("list-filter");
    const all = document.createElement("option");
    all.value = "";
    all.textContent = "Tutte le registrazioni";
    const options = this.lists.map((item) => {
      const option = document.createElement("option");
      option.value = item.list_id;
      option.textContent = `${item.name} (${item.recording_ids.length})`;
      return option;
    });
    select.replaceChildren(all, ...options);
    select.value = this.filterId;
    this.$("delete-list").hidden = !this.filterId;
  }

  filtered(recordings) {
    if (!this.filterId) return recordings;
    const list = this.lists.find((item) => item.list_id === this.filterId);
    const members = new Set(list?.recording_ids || []);
    return recordings.filter((item) => members.has(item.recording_id));
  }

  names(recordingId) {
    return this.lists
      .filter((item) => item.recording_ids.includes(recordingId))
      .map((item) => item.name);
  }

  toggle(recordingId) {
    this.openRecordingId = this.openRecordingId === recordingId ? null : recordingId;
    this.host.changed(false);
  }

  picker(recording) {
    const wrap = document.createElement("div");
    wrap.className = "list-picker";
    const title = document.createElement("strong");
    title.textContent = "Aggiungi alle liste";
    wrap.append(title);
    if (!this.lists.length) {
      const empty = document.createElement("div");
      empty.className = "hint";
      empty.textContent = "Crea prima una lista personalizzata.";
      const create = document.createElement("button");
      create.className = "row-action";
      create.innerHTML = '<ha-icon icon="mdi:playlist-plus"></ha-icon><span>Nuova lista</span>';
      create.addEventListener("click", () => this._showForm());
      wrap.append(empty, create);
      return wrap;
    }
    for (const item of this.lists) {
      const label = document.createElement("label");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = item.recording_ids.includes(recording.recording_id);
      input.addEventListener("change", () => this._membership(recording, item, input));
      const text = document.createElement("span");
      text.textContent = item.name;
      label.append(input, text);
      wrap.append(label);
    }
    return wrap;
  }

  async _create() {
    const input = this.$("list-name");
    const name = input.value.trim();
    if (!name) return this.host.status("Inserisci un nome per la lista.");
    await this._mutate({
      type: "media_bridge/ring/recording_lists/create", name,
    }, "Lista creata.", () => {
      input.value = "";
      this._hideForm();
    });
  }

  async _delete() {
    const item = this.lists.find((value) => value.list_id === this.filterId);
    if (!item || !window.confirm(`Eliminare la lista “${item.name}”? Le registrazioni resteranno salvate.`)) return;
    await this._mutate({
      type: "media_bridge/ring/recording_lists/delete", list_id: item.list_id,
    }, "Lista eliminata.", () => { this.filterId = ""; });
  }

  async _membership(recording, item, input) {
    input.disabled = true;
    await this._mutate({
      type: "media_bridge/ring/recording_lists/set_membership",
      list_id: item.list_id,
      recording_id: recording.recording_id,
      included: input.checked,
    }, input.checked ? "Registrazione aggiunta alla lista." : "Registrazione rimossa dalla lista.");
  }

  async _mutate(payload, success, after = () => {}) {
    try {
      const result = await this.host.hass.callWS({
        ...payload, entry_id: this.host.entry.entry_id,
      });
      after();
      this.update(result.lists);
      this.host.status(success);
    } catch (error) {
      const messages = {
        duplicate_name: "Esiste già una lista con questo nome.",
        invalid_name: "Il nome della lista non è valido.",
        list_limit: "Hai raggiunto il numero massimo di liste.",
        membership_limit: "Questa lista ha raggiunto il numero massimo di registrazioni.",
      };
      this.host.status(messages[error?.code] || "Impossibile aggiornare le liste.");
    }
    this.host.changed(false);
  }

  _showForm() {
    this.$("list-form").hidden = false;
    this.$("list-name").focus();
  }

  _hideForm() {
    this.$("list-form").hidden = true;
    this.$("list-name").value = "";
  }
}
