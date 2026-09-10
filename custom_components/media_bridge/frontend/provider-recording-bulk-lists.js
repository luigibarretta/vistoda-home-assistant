export const PROVIDER_BULK_LIST_TEMPLATE = `
  <dialog class="bulk-list-dialog" id="bulk-list-dialog" aria-labelledby="bulk-list-title">
    <form method="dialog"><h4 id="bulk-list-title">Aggiungi clip alle liste</h4>
      <p class="muted" id="bulk-list-summary"></p><div class="bulk-list-options"
      id="bulk-list-options"></div><div class="muted" id="bulk-list-empty" hidden>
      Non hai ancora creato liste personalizzate.</div><div class="dialog-actions">
      <button value="cancel">Annulla</button><button type="button" id="bulk-new-list">
      <ha-icon icon="mdi:playlist-plus"></ha-icon><span>Nuova lista</span></button>
      <button type="button" class="primary" id="apply-bulk-lists" disabled>
      Aggiungi</button></div></form></dialog>`;

export const PROVIDER_BULK_LIST_STYLES = `
  .bulk-list-dialog { width:min(470px,calc(100vw - 28px)); box-sizing:border-box; padding:0;
    border:1px solid var(--divider-color); border-radius:18px; color:var(--primary-text-color);
    background:var(--card-background-color); box-shadow:0 18px 55px #0007; }
  .bulk-list-dialog::backdrop { background:#0009; }
  .bulk-list-dialog form { display:grid; gap:13px; padding:20px; }
  .bulk-list-dialog h4, .bulk-list-dialog p { margin:0; }
  .bulk-list-options { display:grid; gap:6px; max-height:min(45vh,360px); overflow:auto; }
  .bulk-list-options label { display:grid; grid-template-columns:auto minmax(0,1fr); gap:10px;
    align-items:center; min-height:46px; padding:7px 9px; border-radius:11px;
    background:var(--secondary-background-color); }
  .bulk-list-options input { width:20px; height:20px; }
  .bulk-list-options span { display:grid; gap:2px; }
  .bulk-list-options small { color:var(--secondary-text-color); }
  .bulk-list-dialog .dialog-actions { display:flex; flex-wrap:wrap; justify-content:flex-end;
    gap:8px; margin-top:4px; }
  .bulk-list-dialog button { display:inline-flex; align-items:center; justify-content:center; gap:7px; }
  @media (max-width:600px) {
    .bulk-list-dialog .dialog-actions button { flex:1 1 auto; }
    .bulk-list-dialog .dialog-actions .primary { flex-basis:100%; }
  }`;

export function bulkMembershipCommand(config, listIds, recordingIds) {
  return {
    type: "media_bridge/provider/recording_lists/add_memberships",
    provider: config.provider,
    entry_id: config.entryId,
    list_ids: [...new Set(listIds)],
    recording_ids: [...new Set(recordingIds)],
  };
}

export class ProviderRecordingBulkLists {
  constructor(host, listManager, selectedIds) {
    this.host = host;
    this.listManager = listManager;
    this.selectedIds = selectedIds;
    this.recordingIds = [];
    this.busy = false;
  }

  mount(root) {
    this.$ = (id) => root.getElementById(id);
    this.$("add-selected-to-lists").addEventListener("click", () => this.open());
    this.$("bulk-list-options").addEventListener("change", () => this._updateApply());
    this.$("apply-bulk-lists").addEventListener("click", () => this._apply());
    this.$("bulk-new-list").addEventListener("click", () => {
      this.$("bulk-list-dialog").close();
      this.$("new-list").click();
    });
  }

  open() {
    this.recordingIds = [...new Set(this.selectedIds())];
    if (!this.recordingIds.length || this.busy) return;
    this._render();
    this.$("bulk-list-dialog").showModal();
  }

  _render() {
    const total = this.recordingIds.length;
    this.$("bulk-list-summary").textContent = `${total} clip selezionate. Scegli una o più liste:`;
    this.$("bulk-list-empty").hidden = this.listManager.lists.length !== 0;
    this.$("bulk-list-options").replaceChildren(...this.listManager.lists.map((item) => {
      const label = document.createElement("label");
      const input = document.createElement("input");
      const present = this.recordingIds.filter((id) => item.recording_ids.includes(id)).length;
      input.type = "checkbox"; input.value = item.list_id; input.disabled = this.busy || present === total;
      const text = document.createElement("span"); const name = document.createElement("strong");
      const detail = document.createElement("small"); name.textContent = item.name;
      detail.textContent = present === total ? "Già presenti tutte"
        : present ? `${present}/${total} già presenti` : "Nessuna già presente";
      text.append(name, detail); label.append(input, text); return label;
    }));
    this.$("bulk-new-list").disabled = this.busy;
    this._updateApply();
  }

  _selectedLists() {
    return [...this.$("bulk-list-options").querySelectorAll("input:checked")]
      .map((input) => input.value);
  }

  _updateApply() {
    this.$("apply-bulk-lists").disabled = this.busy || this._selectedLists().length === 0;
  }

  async _apply() {
    const listIds = this._selectedLists();
    if (!listIds.length || this.busy) return;
    this.busy = true; this._render();
    try {
      const result = await this.host._hass.callWS(bulkMembershipCommand(
        this.listManager.config, listIds, this.recordingIds));
      this.listManager.update(result.lists);
      this.host._setMessage?.(`${result.added_memberships} associazioni aggiunte alle liste.`);
      this.host._bulkListsApplied?.();
      this.$("bulk-list-dialog").close();
    } catch (error) {
      const message = error?.code === "membership_limit"
        ? "Una delle liste ha raggiunto il limite di video. Nessuna associazione è stata modificata."
        : "Impossibile aggiungere le clip alle liste. Nessuna associazione è stata modificata.";
      this.host._setMessage?.(message);
    } finally { this.busy = false; this._render(); }
  }
}
