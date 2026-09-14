import { BASE_STYLES } from "./panel-styles.js";
import { ARCHIVE_FILTER_STYLES, NETWORK_ARCHIVE_STYLES } from "./archive-layout-styles.js";
import { copy, localizeCopy } from "./panel-copy.js";
import { PAGE_SIZE_TEMPLATE, bindPageSize, renderPageSize } from "./archive-page-size.js";
import { ProviderRecordingListManager } from "./provider-recording-list-manager.js";
import { PROVIDER_LIST_STYLES, PROVIDER_LIST_TEMPLATE } from "./provider-recording-list-template.js";
import { ProviderRecordingBulkLists, PROVIDER_BULK_LIST_STYLES,
  PROVIDER_BULK_LIST_TEMPLATE } from "./provider-recording-bulk-lists.js";

class NetworkArchive extends HTMLElement {
  constructor() {
    super(); this.attachShadow({ mode: "open" }); this.page = 1; this.size = 10;
    this.generation = 0;
    this._selected = new Set();
    this._listManager = new ProviderRecordingListManager(this);
    this._bulkListManager = new ProviderRecordingBulkLists(this, this._listManager, () => [...this._selected]);
    this.shadowRoot.innerHTML = `<style>${BASE_STYLES}${PROVIDER_LIST_STYLES}${PROVIDER_BULK_LIST_STYLES}
      ${ARCHIVE_FILTER_STYLES}${NETWORK_ARCHIVE_STYLES}
    </style><header><h3 data-copy="Backup NFS">Backup NFS</h3>
      <button id="reload" class="icon-action" aria-label="Aggiorna" data-copy-aria-label="Aggiorna"><ha-icon icon="mdi:refresh"></ha-icon></button></header>
      <p><a href="/config/integrations/integration/media_bridge" data-copy="Configura backup di rete e backup automatico">Configura backup di rete e backup automatico</a></p>
      <p id="automatic"></p><p id="last-run"></p><code id="path"></code>
      <p data-copy="Le copie sono indipendenti dagli originali. Il checksum viene verificato prima del download.">Le copie sono indipendenti dagli originali. Il checksum viene verificato prima del download.</p>
      <div class="archive-filter"><label for="camera" data-copy="Telecamera">Telecamera</label><select id="camera"><option value="" data-copy="Tutte le telecamere">Tutte le telecamere</option></select></div>
      ${PAGE_SIZE_TEMPLATE}${PROVIDER_LIST_TEMPLATE}${PROVIDER_BULK_LIST_TEMPLATE}
      <div class="archive-toolbar"><strong id="count"></strong><button class="icon-action" id="add-selected-to-lists" disabled
      aria-label="Aggiungi selezionate alle liste" data-copy-aria-label="Aggiungi selezionate alle liste"><ha-icon icon="mdi:playlist-plus"></ha-icon></button></div>
      <section id="player" hidden><button id="close" data-copy="Chiudi riproduzione">Chiudi riproduzione</button><video id="video" controls playsinline></video></section>
      <div id="items"></div><p id="status" role="status"></p>
      <div class="archive-pagination"><button class="icon-action" id="previous" aria-label="Pagina precedente" data-copy-aria-label="Pagina precedente"><ha-icon icon="mdi:chevron-left"></ha-icon></button>
      <span id="page"></span><button class="icon-action" id="next" aria-label="Pagina successiva" data-copy-aria-label="Pagina successiva"><ha-icon icon="mdi:chevron-right"></ha-icon></button></div>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this._listManager.mount(this.shadowRoot); this._bulkListManager.mount(this.shadowRoot);
    this.$("reload").onclick = () => this.reload();
    this.$("camera").onchange = () => { this.page = 1; this.reload(); };
    this.$("previous").onclick = () => { this.page--; this.reload(); };
    this.$("next").onclick = () => { this.page++; this.reload(); };
    this.$("close").onclick = () => this.pausePlayback();
    bindPageSize(this.shadowRoot, (size) => { this.size = size; this.page = 1; this.reload(); });
  }
  configure(hass, entryId) {
    this._hass = hass; localizeCopy(this.shadowRoot, this);
    if (entryId === this.entryId) return;
    this.entryId = entryId; this.generation++; this.page = 1; this.pausePlayback();
    this._config = entryId ? { provider: "blink", entryId } : null;
    this._selected.clear(); this._listManager.configure(this._config);
    this.reload();
  }
  disconnectedCallback() { this.generation++; this.pausePlayback(); }
  pausePlayback() {
    this.$("video").pause(); this.$("video").removeAttribute("src");
    this.$("video").load(); this.$("player").hidden = true;
  }
  async reload() {
    if (!this.entryId) return;
    const generation = ++this.generation; this.pausePlayback();
    this.$("status").textContent = copy(this, "Verifica…");
    this.$("previous").disabled = this.$("next").disabled = true;
    renderPageSize(this.shadowRoot, this.size, true, this._hass?.locale?.language);
    try {
      const result = await this._hass.callWS({ type: "media_bridge/network_archive/list",
        entry_id: this.entryId, page: this.page, page_size: this.size, camera: this.$("camera").value,
        list_id: this._listManager.filterId });
      if (generation !== this.generation) return;
      const selected = this.$("camera").value;
      const cameras = ["", ...result.cameras];
      if (JSON.stringify(cameras) !== this.cameraKey) {
        this.cameraKey = JSON.stringify(cameras);
        this.$("camera").replaceChildren(...cameras.map((name) => {
          const option = document.createElement("option"); option.value = name;
          option.textContent = name || copy(this, "Tutte le telecamere"); return option;
        })); this.$("camera").value = selected;
      }
      this.$("path").textContent = result.directory;
      this.$("automatic").textContent = copy(this, result.automatic.enabled
        ? "Backup automatico USB attivo (ogni ora)." : "Backup automatico USB disattivato.");
      const last = result.automatic.last_run;
      this.$("last-run").textContent = last ? copy(this, "Ultimo controllo: {p0}", {
        p0: new Date(last.checked_at).toLocaleString(this._hass?.locale?.language),
      }) : copy(this, "Nessun ciclo automatico ancora eseguito.");
      const paging = result.pagination; this.page = paging.page;
      this.$("count").textContent = copy(this, "{p0} registrazioni", { p0: paging.total_items });
      this.$("page").textContent = copy(this, "Pagina {p0} di {p1}", { p0: paging.page, p1: paging.total_pages });
      this.$("previous").disabled = !paging.has_previous; this.$("next").disabled = !paging.has_next;
      this.items = result.items; this.renderItems();
      this.$("status").textContent = "";
    } catch {
      if (generation === this.generation) {
        this.$("items").replaceChildren(); this.$("count").textContent = "";
        this.$("status").textContent = copy(this, "Archivio di rete non disponibile. Verifica mount e permessi amministrativi.");
      }
    } finally {
      if (generation === this.generation) renderPageSize(this.shadowRoot, this.size, false, this._hass?.locale?.language);
    }
  }
  row(item) {
    const row = document.createElement("div"); row.className = "row";
    const text = document.createElement("div"), name = document.createElement("strong"), date = document.createElement("div");
    name.textContent = item.camera; date.className = "muted";
    date.textContent = new Date(item.created_at || item.backed_up_at).toLocaleString(this._hass?.locale?.language);
    text.append(name, date); row.append(text);
    const actions = document.createElement("div"); actions.className = "row-actions";
    const selection = document.createElement("label"); selection.className = "select-clip";
    const checkbox = document.createElement("input"); checkbox.type = "checkbox";
    checkbox.checked = this._selected.has(item.media_id);
    checkbox.setAttribute("aria-label", copy(this, "Seleziona clip") + " " + item.camera);
    checkbox.onchange = () => {
      checkbox.checked ? this._selected.add(item.media_id) : this._selected.delete(item.media_id);
      this.$("add-selected-to-lists").disabled = !this._selected.size;
    }; selection.append(checkbox); actions.append(selection);
    for (const [play, icon, label] of [[true, "mdi:play", "Riproduci"], [false, "mdi:download", "Scarica"]]) {
      const button = document.createElement("button"), glyph = document.createElement("ha-icon");
      button.className = "icon-action";
      glyph.setAttribute("icon", icon); button.append(glyph); button.title = copy(this, label);
      button.setAttribute("aria-label", copy(this, label)); button.disabled = play && item.media_type !== "video/mp4";
      button.onclick = () => this.open(item, play); actions.append(button);
    }
    row.append(actions); return row;
  }
  renderItems() {
    this.$("items").replaceChildren(...(this.items || []).map((item) => this.row(item)));
    this.$("add-selected-to-lists").disabled = !this._selected.size;
  }
  _listsChanged() { this.page = 1; this.reload(); }
  _bulkListsApplied() { this._selected.clear(); this.renderItems(); }
  _setMessage(text) { this.$("status").textContent = text; }
  async open(item, play) {
    const generation = this.generation;
    try {
      const signed = await this._hass.callWS({ type: "auth/sign_path", path: item.media_path, expires: 300 });
      if (generation !== this.generation) return;
      const url = this._hass.hassUrl(signed.path);
      if (play) { this.$("video").src = url; this.$("player").hidden = false; this.$("video").load(); }
      else { const link = document.createElement("a"); link.href = url; link.download = item.id.split("/").pop(); link.click(); }
    } catch { this.$("status").textContent = copy(this, "Download non disponibile."); }
  }
}
if (!customElements.get("vistoda-network-archive")) customElements.define("vistoda-network-archive", NetworkArchive);
