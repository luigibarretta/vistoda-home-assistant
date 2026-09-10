export class BlinkLegacyLiveSession {
  constructor(hass, host) {
    this._hass = hass;
    this.host = host;
    this.card = null;
    this.request = 0;
  }

  set hass(value) {
    this._hass = value;
    if (this.card) this.card.hass = value;
  }

  async start(entityId) {
    if (!entityId) throw new Error("Entità camera Blink non disponibile");
    const request = ++this.request;
    const load = globalThis.loadCardHelpers;
    if (typeof load !== "function") throw new Error("Player Home Assistant non disponibile");
    const helpers = await load();
    const card = await helpers.createCardElement({
      type: "picture-entity",
      entity: entityId,
      camera_view: "live",
      show_name: false,
      show_state: false,
      tap_action: { action: "none" },
      hold_action: { action: "none" },
    });
    if (request !== this.request) return;
    card.hass = this._hass;
    card.classList.add("blink-legacy-card");
    this.card = card;
    this.host.replaceChildren(card);
    this.host.hidden = false;
  }

  stop() {
    ++this.request;
    this.card = null;
    this.host.replaceChildren();
    this.host.hidden = true;
  }
}
