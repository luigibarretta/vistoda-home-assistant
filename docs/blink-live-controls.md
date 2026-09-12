# Blink live controls

Requires Vistoda HA 0.29.0 and Blink 0.16.0 for the complete control contract.

Open live requests a snapshot first, then starts video. This avoids overlapping
provider commands; a failed snapshot does not prevent viewing. Merely opening
the Blink page still uses the existing image, without waking a camera.

On mobile, live opens in a full-viewport dialog with controls over the video.
Close or Back/Escape ends that viewer's session and restores the snapshot.
Desktop keeps inline playback and optional browser fullscreen. Closing desktop
fullscreen alone does not stop playback. Other viewers retain their sessions;
HA Stream may retain its shared source briefly after the last viewer leaves.

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

Il contratto completo richiede Vistoda HA 0.29.0 e Blink 0.16.0.
Apri live richiede prima uno snapshot e poi avvia il video; il fallimento dello
snapshot non impedisce il live. Entrare nella pagina non risveglia le camere.

Su mobile il live occupa tutto lo schermo, con i comandi sul video. Chiudi o
Indietro/Escape termina la sessione dello spettatore e ripristina lo snapshot.
Sul desktop resta il live nella pagina, con fullscreen facoltativo: uscire dal
fullscreen non lo interrompe. Gli altri spettatori restano collegati; HA Stream
può mantenere brevemente la sorgente condivisa dopo l'ultimo spettatore.

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
