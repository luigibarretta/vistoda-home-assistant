import { copy } from "./panel-copy.js";
import { cameraDraft, commitDraft, reconcileDraft } from "./blink-setting-draft.js";

export const blinkSettingsIo = {
  async _load() {
    if (!this._hass || !this._camera?.alias) return;
    const generation = this._generation;
    const alias = this._camera.alias;
    const hass = this._hass;
    const request = ++this._request;
    this.$("status").textContent = copy(this, "Lettura impostazioni…");
    this.$("reload").disabled = true;
    try {
      const result = await hass.callWS({ type: "blink_live_bridge/camera/settings", alias });
      if (request === this._request && generation === this._generation
          && alias === this._camera?.alias) {
        this._settings = result;
        reconcileDraft(result, cameraDraft(this._drafts, alias));
        this._render();
      }
    } catch (_error) {
      if (request === this._request) this.$("status").textContent =
        copy(this, "Impostazioni avanzate non disponibili per questo modello.");
    } finally {
      if (request === this._request) this.$("reload").disabled = false;
    }
  },

  async _saveDraft() {
    const draft = this._draft(); const count = draft.size;
    if (!count || !globalThis.confirm(copy(this, "Confermi {p0} {p1} a questa telecamera?", {
      p0: count, p1: count === 1 ? copy(this, "modifica") : copy(this, "modifiche"),
    }))) return;
    const generation = this._generation;
    const alias = this._camera.alias;
    const hass = this._hass;
    const settings = this._settings;
    this.$("status").textContent = copy(this, "Salvataggio e verifica…");
    try {
      const result = await commitDraft(hass, alias, settings, draft);
      if (generation !== this._generation || alias !== this._camera?.alias) return;
      this._settings = result;
      draft.clear(); this._render();
      this.$("status").textContent = copy(this, "Modifiche verificate sulla camera.");
    } catch (error) {
      if (generation !== this._generation || alias !== this._camera?.alias) return;
      await this._load();
      if (generation !== this._generation || alias !== this._camera?.alias) return;
      this.$("status").textContent = error.rollbackFailed
        ? copy(this, "Salvataggio fallito: rileggi lo stato prima di riprovare.")
        : copy(this, "Salvataggio fallito: le modifiche già inviate sono state ripristinate.");
    }
  },
};
