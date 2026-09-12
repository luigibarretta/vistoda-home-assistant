# Blink live controls

Open a camera's live stream, then use the **Fullscreen** icon at the top right
of the video. Use the same icon or the browser's exit control to return. The
existing stream stays mounted; fullscreen does not start another camera session.
On iPhone browsers without container fullscreen, Vistoda uses the native video
fullscreen control when available. Browser or embedded-app restrictions can
still prevent fullscreen; Vistoda reports this without stopping playback.

With Vistoda Blink engine **0.15.0 or newer**, an administrator can use
**Enable microphone** when the camera offers a supported Walnut audio format.
Open Home Assistant over HTTPS, press the button and allow microphone access.
Press **Disable microphone** to stop talking and restore listening. The button
changes state while capture is active. Opening a live stream never requests
microphone permission by itself.

This is talk/listen mode, **not simultaneous full duplex**: Vistoda mutes the
local camera audio while transmitting your voice. It retains the existing HA
video player and shares the same upstream camera session. Switching cameras,
hiding the page, losing microphone access or closing live stops capture. A slow
connection stops transmission rather than replaying buffered speech later.
Only one Vistoda microphone can be active at a time.

A disabled button means that the active session has not offered a supported
audio format, the backend is unavailable/outdated, or the player is not ready.
On plain HTTP, use HTTPS before granting microphone access. Browser and embedded
app permissions may also restrict capture. The protocol's sent-frame counter
confirms transport writes, not that the camera speaker emitted audible sound;
hardware audio must be checked on the actual device. No camera volume, motion,
privacy or alarm setting is changed by these controls.

## Italiano

Apri il live della telecamera e premi l'icona **Schermo intero** in alto a destra
nel video. Usa la stessa icona o il comando del browser per uscire. La sessione
rimane aperta: il fullscreen non avvia una seconda connessione alla telecamera.
Su iPhone, quando il fullscreen del contenitore non è disponibile, viene usato
quello nativo del video se supportato. Eventuali restrizioni del browser o
dell'app vengono segnalate senza interrompere il live.

Con il motore Vistoda Blink **0.15.0 o successivo**, un amministratore può usare
**Attiva microfono** quando la telecamera offre un formato audio Walnut
supportato. Apri Home Assistant tramite HTTPS, premi il pulsante e autorizza
il microfono. Premi **Disattiva microfono** per smettere di parlare e riprendere
l'ascolto. Il pulsante evidenzia la cattura attiva. Aprire il live da solo non
richiede l'accesso al microfono.

È una modalità parla/ascolta, **non full-duplex simultaneo**: mentre trasmetti,
l'audio della telecamera viene silenziato sul telefono. Il player HA resta
montato e usa la stessa sessione verso la telecamera. Cambio telecamera, pagina
in background, perdita del permesso e chiusura del live fermano la cattura.
Se la connessione è lenta, la trasmissione si ferma senza accodare la voce.
Può essere attivo un solo microfono Vistoda alla volta.

Il pulsante disabilitato indica che la sessione non offre un formato supportato,
il backend non è disponibile/aggiornato oppure il player non è pronto. Su HTTP
occorre passare a HTTPS; anche browser e app possono limitare i permessi.
Il contatore dei frame inviati conferma le scritture di rete, non l'emissione
sonora: l'altoparlante va verificato sul dispositivo reale. Questi controlli
non modificano volume, movimento, privacy o allarmi della telecamera.
