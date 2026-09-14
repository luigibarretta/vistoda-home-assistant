import { copy, localizeCopy } from "./panel-copy.js";
import { BASE_STYLES } from "./panel-styles.js";
import { LiveRecordingDeadline } from "./live-recording-deadline.js";

// The floating controls reuse the archive's recording action and validation.
export class LiveRecordingMenu {
  constructor(view) {
    this.view = view;
    this.generation = 0;
    this.deadline = new LiveRecordingDeadline(() => this.finish());
    this.host = document.createElement("div");
    this.host.hidden = true;
    Object.assign(this.host.style, { position: "absolute", right: "8px", top: "116px",
      zIndex: "7", width: "min(320px, calc(100% - 16px))" });
    view.$("stage").append(this.host);
    this.root = this.host.attachShadow({ mode: "open" });
    this.root.innerHTML = `<style>${BASE_STYLES}
      section { padding:16px; background:#181818; color:white; border:1px solid #777;
        border-radius:12px; max-height:55dvh; overflow:auto; }
      label, select { display:block; width:100%; margin-bottom:8px; }
      p { font-size:13px; } button { min-height:44px; }
      </style><section aria-label="Registrazione live" data-copy-aria-label="Registrazione live">
      <label for="duration" data-copy="Durata">Durata</label><select id="duration">
      <option value="0" selected data-copy="Fino alla chiusura della live">Fino alla chiusura della live</option>
      <option value="15" data-copy="15 secondi">15 secondi</option>
      <option value="30" data-copy="30 secondi">30 secondi</option>
      <option value="60" data-copy="60 secondi">60 secondi</option></select>
      <label for="destination" data-copy="Destinazione">Destinazione</label><select id="destination">
      <option value="provider" data-copy="Archivio Blink (USB se attivo)">Archivio Blink (USB se attivo)</option>
      <option value="ha" data-copy="Archivio locale HA">Archivio locale HA</option></select>
      <p id="destination-note"></p>
      <button id="start" data-copy="Registra live">Registra live</button>
      <button id="finish" hidden data-copy="Chiudi questa live e conserva">Chiudi questa live e conserva</button>
      <p id="status" role="status"></p></section>`;
    this.root.getElementById("start").addEventListener("click", () => this.start());
    this.root.getElementById("finish").addEventListener("click", () => {
      if (globalThis.confirm(copy(view, "Chiudere questa live mantenendo il salvataggio Blink? Gli altri spettatori non verranno disconnessi."))) this.finish();
    });
    this.root.getElementById("destination").addEventListener("change", () => this._destination());
    view.$("record-live").addEventListener("click", () => this.toggle());
    this.root.addEventListener("keydown", (event) => {
      if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); this.close(); view.$("record-live").focus(); }
    });
  }
  toggle() {
    this.host.hidden = !this.host.hidden;
    this.view.$("record-live").setAttribute("aria-expanded", String(!this.host.hidden));
    localizeCopy(this.root, this.view);
    this._destination();
    if (!this.host.hidden) this.root.getElementById("duration").focus();
  }
  close() { this.host.hidden = true; this.view.$("record-live").setAttribute("aria-expanded", "false"); }
  resetProvider() { this.generation++; this.deadline.reset(); this.providerSaving = false; this.providerLocked = false; this._destination(); }
  finish() {
    if (!this.providerSaving) return;
    this.deadline.reset();
    this.view._liveControls.close();
    this.view._liveState.message = copy(this.view, "Live chiusa. Il salvataggio Blink resta attivo; se ci sono altri spettatori, la clip termina quando finisce la sessione condivisa.");
    this.view._renderLive();
  }
  _destination() {
    const provider = this.root.getElementById("destination").value === "provider";
    const duration = this.root.getElementById("duration");
    duration.disabled = provider && Boolean(this.providerSaving);
    duration.querySelector('option[value="0"]').disabled = !provider;
    if (!provider && duration.value === "0") duration.value = "30";
    this.root.getElementById("finish").hidden = !provider || !this.providerSaving;
    this.root.getElementById("destination-note").textContent = provider
      ? copy(this.view, "Blink salva l’intera sessione, anche la parte precedente a REC. La durata chiude solo questa vista: altri spettatori possono prolungare la clip. Per un segmento preciso usa Locale HA.")
      : copy(this.view, "La copia HA usa l'archivio locale separato di Vistoda.");
    this.root.getElementById("start").textContent = provider && this.providerLocked
      ? copy(this.view, "Salvataggio in preparazione") : provider && this.providerSaving
        ? copy(this.view, "Non salvare questa live") : copy(this.view, "Registra live");
    this.root.getElementById("start").disabled = provider && Boolean(this.providerLocked);
  }
  async start() {
    const generation = this.generation;
    const button = this.root.getElementById("start");
    if (button.disabled) return;
    button.disabled = true;
    this.root.getElementById("status").textContent = copy(this.view, "Avvio registrazione…");
    try {
      if (this.root.getElementById("destination").value === "provider") {
        const camera = this.view._current("camera");
        const alias = this.view._hass?.states?.[camera?.entity_id]?.attributes?.alias;
        if (!alias) throw new Error("missing camera alias");
        const save = !this.providerSaving;
        const result = await this.view._hass.callWS({
          type: "blink_live_bridge/recordings/provider", alias, save,
        });
        if (generation !== this.generation) return;
        this.providerSaving = save;
        this.providerLocked = save && result?.status === 2;
        if (save) this.deadline.start(Number(this.root.getElementById("duration").value));
        else this.deadline.reset();
        this.root.getElementById("status").textContent = save
          ? copy(this.view, result?.status === 2 ? "Blink sta preparando il salvataggio della live."
            : "La live verrà salvata nell'archivio Blink configurato.")
          : copy(this.view, "Il salvataggio Blink di questa live è stato annullato.");
        this._destination();
      } else {
        const duration = Number(this.root.getElementById("duration").value);
        const camera = this.view._current("camera");
        const alias = this.view._hass?.states?.[camera?.entity_id]?.attributes?.alias;
        if (!alias) throw new Error("missing camera alias");
        if (!globalThis.confirm(copy(this.view, "Registrare {p0} secondi del live in archivio locale?", { p0: duration }))) return;
        await this.view._hass.callWS({ type: "blink_live_bridge/recordings/create", alias,
          duration_seconds: duration, request_id: globalThis.crypto.randomUUID() });
        if (generation !== this.generation) return;
        this.root.getElementById("status").textContent = copy(this.view,
          "Registrazione di {p0} secondi avviata.", { p0: duration });
        this.view.$("recordings").reload();
      }
    } catch {
      if (generation === this.generation) this.root.getElementById("status").textContent = copy(this.view,
        "Salvataggio Blink non disponibile: avvia prima una live compatibile e riprova.");
    } finally { if (generation === this.generation) button.disabled = Boolean(this.providerLocked); }
  }
}
