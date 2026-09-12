# Blink live controls

Open a camera's live stream, then use the **Fullscreen** icon at the top right
of the video. Use the same icon or the browser's exit control to return. The
existing stream stays mounted; fullscreen does not start another camera session.
On iPhone browsers without container fullscreen, Vistoda uses the native video
fullscreen control when available. Browser or embedded-app restrictions can
still prevent fullscreen; Vistoda reports this without stopping playback.

The microphone control is enabled only on an interactive transport. The current
Walnut/Home Assistant player supports viewing, but not sending your voice to
the camera. Its disabled microphone button has a visible explanation. This is
not a missing phone permission, and granting microphone access cannot enable an
unsupported transport. Experimental Walnut audio work is not part of this release.

## Italiano

Apri il live della telecamera e premi l'icona **Schermo intero** in alto a destra
nel video. Usa la stessa icona o il comando del browser per uscire. La sessione
rimane aperta: il fullscreen non avvia una seconda connessione alla telecamera.
Su iPhone, quando il fullscreen del contenitore non è disponibile, viene usato
quello nativo del video se supportato. Eventuali restrizioni del browser o
dell'app vengono segnalate senza interrompere il live.

Il microfono è abilitato soltanto con un trasporto interattivo. Il player attuale
Walnut/Home Assistant non permette ancora di inviare la voce alla telecamera:
il pulsante disabilitato mostra una spiegazione. Non dipende dai permessi del
telefono. Lo sviluppo audio Walnut sperimentale non è incluso in questa release.
