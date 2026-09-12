import { copy } from "./panel-copy.js";

// Provider reason codes, not upstream text: safe, stable and fully localized.
const REASONS = {
  busy: "Microfono occupato da un altro dispositivo. Puoi continuare a guardare e riprovare quando viene rilasciato.",
  unavailable: "Il canale microfono non è ancora pronto. Attendi e riprova.",
  disconnected: "Connessione audio interrotta. Riapri il live per riprovare.",
  unsupported_format: "Il formato audio di questa telecamera non supporta l’invio della voce.",
  lease_revoked: "Il canale microfono non è più disponibile. Rilascia il pulsante e riprova.",
  encoder_unavailable: "Il servizio di codifica audio non è disponibile. Controlla lo stato dell’add-on Blink.",
  pcm_rate: "Invio audio troppo rapido. Rilascia il pulsante e riprova.",
  pcm_backlog: "La connessione non riesce a smaltire l’audio. Rilascia il pulsante e riprova.",
  pcm_write_timeout: "Invio audio scaduto. Controlla la connessione VPN e riprova.",
  encoder_failed: "La codifica del microfono si è interrotta. Rilascia il pulsante e riprova.",
  invalid_audio: "Campioni audio non validi. Rilascia il pulsante e riprova.",
  input_idle: "Il microfono non sta inviando audio. Controlla il dispositivo di ingresso e riprova.",
  pcm_format: "Campioni audio non validi. Rilascia il pulsante e riprova.",
  missing_provenance: "Campioni audio non validi. Rilascia il pulsante e riprova.",
  audio_expired: "Invio audio scaduto. Controlla la connessione VPN e riprova.",
  audio_backpressure: "La connessione non riesce a smaltire l’audio. Rilascia il pulsante e riprova.",
  audio_failed: "Connessione audio interrotta. Riapri il live per riprovare.",
};
export function blinkAudioError(context, reason) {
  return copy(context, REASONS[reason] || "Canale microfono non disponibile. Controlla la connessione e riapri il live.");
}
