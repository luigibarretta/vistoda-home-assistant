# Blink live controls

Requires Vistoda HA 0.31.4 and Blink 0.17.1 for the complete control contract.

The mobile refinement adds a loading spinner over the HA player placeholder,
a compact 44 px-high hold-to-talk control with status outside the finger area, and shared
Blink/EZVIZ drag feedback (disabled for reduced-motion preferences). A failed
opening snapshot displays a separate warning; it is not a failed live session.

Home Wi-Fi does not exempt microphone capture from HTTPS. In Companion's server
connection settings, use a valid HTTPS URL for the internal connection too.
The same hostname can work internally using local DNS and a trusted certificate.
Vistoda cannot read or edit Companion's trusted-network/SSID preferences, nor
override the browser secure-context requirement. Changing the HA server's URL
alone does not rewrite a URL already saved in the phone. See
[Companion networking](https://companion.home-assistant.io/docs/troubleshooting/networking/#setting-up-the-app).

Open live requests a snapshot first, then starts video. This avoids overlapping
provider commands; a failed snapshot does not prevent viewing. Merely opening
the Blink page still uses the existing image, without waking a camera.

On mobile, live opens in a full-viewport dialog with controls over the video.
Close or Back/Escape ends that viewer's session and restores the snapshot.
Desktop keeps inline playback and optional browser fullscreen. Closing desktop
fullscreen alone does not stop playback. Other viewers retain their sessions;
HA Stream may retain its shared source briefly after the last viewer leaves.

From HA 0.30.4 onward, leaving the Blink route or hiding the app stops that viewer,
even when HA keeps the panel cached. Teardown explicitly pauses media and
releases receiving tracks. Continue does not override navigation cleanup.
The floating recording button opens duration and destination controls using
the same local archive action. USB is visibly disabled: direct live recording
to the Sync Module drive is not implemented, and local recording is not USB.

Camera audio is enabled by default where the browser permits it. If autoplay
with sound is blocked, use the speaker button. Opening live never requests
microphone permission automatically. Use HTTPS, hold the microphone button and
allow capture. Release it to stop talking; keyboard users hold Space or Enter.
Losing focus, microphone permission or the page stops capture.

Multiple devices may watch the same camera. Only one can own that camera's talk
channel at a time. A busy message does not interrupt video; retry after the
other user releases their microphone. Vistoda also prevents competing captures
in the same browser. Errors distinguish permissions, contention, unsupported
formats, encoder failure and connection stalls in English and Italian.

Duplex is selected from the actual session offer, not battery/powered model
names. Supported AAC with camera AEC and confirmed browser echo cancellation
allows simultaneous listening and speaking. Otherwise Vistoda uses talk/listen:
camera audio is muted locally during capture and restored on release. Unknown
formats or policy never enable capture. These capability checks are not acoustic
proof; verify audibility and echo on the actual camera before relying on duplex.

“Continue?” uses provider interval/warning metadata, with documented Android
defaults of 30/10 seconds. Continue renews only the local inactivity timer, not
the absolute backend limit. Battery sessions remain capped at 75 seconds;
powered sessions use the provider duration with a 600-second ceiling (duration
defaults to 300 seconds). Later viewers inherit the shared remaining time.
No timeout automatically restarts or wakes the camera.

Transient congestion drops unsent audio rather than replaying a backlog. The
codec retains a 200 ms deadline from PCM receipt at the engine, not a measured
browser-to-camera deadline. Sustained stalls and lease revocation stop capture.
Audio controls never change volume, motion, privacy or alarm settings.

## Italiano

Il contratto completo richiede Vistoda HA 0.31.4 e Blink 0.17.1.

Il miglioramento mobile aggiunge uno spinner sopra il placeholder del player HA,
un pulsante premi-per-parlare compatto alto 44 px con stato fuori dall'area coperta dal dito,
e trascinamento condiviso Blink/EZVIZ (disattivato con animazioni ridotte).
Il fallimento dello snapshot iniziale è un avviso distinto dall'esito del live.

Il Wi-Fi di casa non esenta il microfono da HTTPS. Nelle impostazioni di connessione
del server Companion usa un URL HTTPS valido anche per la connessione interna.
Lo stesso hostname può funzionare in LAN con DNS locale e certificato attendibile.
Vistoda non può leggere o modificare le preferenze SSID/reti fidate di Companion,
né aggirare il requisito del browser. Modificare l'URL del server HA non riscrive
un URL già salvato nel telefono. Consulta la
[guida di rete Companion](https://companion.home-assistant.io/docs/troubleshooting/networking/#setting-up-the-app).
Apri live richiede prima uno snapshot e poi avvia il video; il fallimento dello
snapshot non impedisce il live. Entrare nella pagina non risveglia le camere.

Su mobile il live occupa tutto lo schermo, con i comandi sul video. Chiudi o
Indietro/Escape termina la sessione dello spettatore e ripristina lo snapshot.
Sul desktop resta il live nella pagina, con fullscreen facoltativo: uscire dal
fullscreen non lo interrompe. Gli altri spettatori restano collegati; HA Stream
può mantenere brevemente la sorgente condivisa dopo l'ultimo spettatore.

Da HA 0.30.4 uscire dalla pagina Blink o mettere l'app in background ferma
lo spettatore anche quando HA conserva il pannello in cache. La chiusura
mette in pausa i media e rilascia le tracce ricevute: Continua non annulla
questa protezione. Il pulsante flottante apre durata e destinazione usando
la stessa azione dell'archivio locale. USB è visibile ma disabilitato:
la registrazione live diretta sulla chiavetta non è implementata.

L'audio parte attivo se il browser lo consente; altrimenti premi l'altoparlante.
Il microfono richiede HTTPS, autorizzazione e pressione esplicita del pulsante.
Tienilo premuto per parlare e rilascialo per fermarti; da tastiera usa Spazio o
Invio. Perdita del focus, dei permessi o della pagina ferma la cattura.

Più dispositivi possono guardare, ma un solo spettatore per camera può parlare.
L'errore di canale occupato non ferma il video: riprova dopo il rilascio. Gli
errori di permessi, formato, connessione e codifica hanno messaggi distinti.

Il duplex dipende dall'offerta della sessione e dall'AEC del browser, non
dall'alimentazione della camera. Se entrambe le capacità necessarie sono
presenti, ascolto e voce possono essere simultanei; altrimenti l'ascolto viene
sospeso durante la pressione e ripristinato al rilascio. Formati e capacità
sconosciuti restano disabilitati. Serve comunque una prova acustica reale.

“Continua?” rinnova l'inattività locale, non il limite assoluto del motore.
Default Android: intervallo 30 secondi, avviso negli ultimi 10. Le camere a
batteria mantengono il limite di 75 secondi; per quelle alimentate vale la durata
upstream, massimo 600 secondi e default 300. Un secondo spettatore eredita il
tempo residuo. Nessuna scadenza riavvia automaticamente la camera.

I campioni non inviati per congestione vengono scartati, non riaccodati.
Il limite codec di 200 ms parte dalla ricezione nel motore, non misura l'intero
tragitto dal browser. Stallo prolungato o revoca del canale fermano il microfono.
