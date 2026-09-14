# Verifiche frontend prima del rilascio

Il pannello non produce overflow orizzontale del documento alle larghezze
320, 360, 393, 600, 768 e 1280 px. I controlli hanno aree interattive di almeno
44 × 44 px; gli indicatori Blink mantengono cerchi visivi di 8 px.

Gli errori di inventario sono distinti dai provider non configurati. Il ritorno
a Home Assistant usa la dashboard predefinita o `/lovelace`, senza percorsi
personali. Ring seleziona il citofono per entry: apertura e cronologia restano
associate all’ingresso scelto. EZVIZ associa ogni camera tramite alias esatto;
la pagina dispositivo mostra la batteria dell’entità EZVIZ nativa associata e
raggruppa i controlli realmente esposti da Home Assistant in sezioni ispirate
all’app. Ogni riga apre il controllo nativo di HA; le impostazioni non esposte
restano dichiarate non disponibili. Le impostazioni cloud verificate ma omesse
da HA vengono lette dal coordinator EZVIZ nativo associato esattamente e salvate
solo dopo conferma amministratore, controllo di concorrenza e verifica
read-after-write con rollback. Lo swipe non trasforma mai lo snapshot fermo e
l’intera card della telecamera.
non aggiorna immagini di altre camere se l’associazione è ambigua. Aprire il
pannello legge soltanto immagini già salvate, senza risvegliare dispositivi.

## Italiano e inglese

Il live compatibile Blink deve funzionare anche entrando direttamente in
`/vistoda/blink`, senza aver prima visitato Lovelace. `ha-card-helpers.js` carica
il modulo tramite il loader della rotta registrata da Home Assistant quando
manca l'helper globale. Non cambia URL, non monta altre dashboard, non indovina
hash degli asset e non richiede media durante il caricamento. Chiudere il live
in attesa impedisce di creare successivamente la card della telecamera.
`tests/browser/ha-card-helpers.mjs` verifica il percorso DOM sui tre browser
con loader sintetico; la prova su HA e media reali resta distinta.

`panel-localize.js` copre navigazione, panoramica e cronologia.
`panel-copy.js` e i cataloghi common/Ring/Blink/storage coprono impostazioni,
archivi, liste, audio, registrazione, messaggi, conferme, dialoghi, tooltip e
nomi accessibili. Solo etichette scritte da Vistoda ricevono marcatori espliciti
`data-copy` o chiamate `copy()`. Nomi di dispositivi, liste, percorsi, valori
inseriti e contenuti del provider non vengono tradotti automaticamente.
Le lingue non supportate usano l’inglese; una voce mancante mantiene il testo
originale. I test controllano copertura e parametri dei cataloghi.

La griglia zone Blink 20 × 15 è contenuta in un’area scorrevole: ogni cella è
raggiungibile, larga e alta almeno 44 px, senza disallineamenti con l’immagine.
Tab e Spazio modificano soltanto la bozza delle zone attività; l’invio richiede
il comando esplicito Salva e la conferma. Le celle privacy o in sola lettura
non possono essere modificate.

Ring, Blink ed EZVIZ usano lo stesso controllo segmentato 10/25/50/100. Su
mobile le checkbox compaiono solo in modalità selezione: una pressione di 420 ms
seleziona la prima card, il trascinamento estende la selezione e un normale
movimento verticale annulla il gesto senza bloccare lo scorrimento. Il pulsante
di selezione etichettato e il contatore restano sempre disponibili.

I live condividono gli stati di rotazione Auto/Disattivata/90 gradi senza ruotare
i controlli. Blink nasconde i dettagli tecnici ordinari dietro il pulsante debug.
I dati USB compatti conservano label accessibili; le azioni Sync Module non
verificate sono `aria-disabled` e non hanno callback mutanti.

## Esecuzione

```sh
node --test tests/*.mjs
NODE_PATH=/percorso/node_modules node tests/browser/panel-responsive.mjs
NODE_PATH=/percorso/node_modules node tests/browser/blink-live-controls.mjs
NODE_PATH=/percorso/node_modules node tests/browser/mobile-card-selection.mjs
```

I test usano Chromium, Firefox e WebKit tramite Playwright, un server solo loopback e risposte Home
Assistant sintetiche. Verifica 48 combinazioni provider/lingua/larghezza,
archivi, liste, identità Ring e ritorno del focus, impostazioni Blink, zone,
conferma formattazione USB, errori e recupero. Nomi utente come “Elimina” devono
rimanere invariati. Test separati coprono rotazione/debug/teardown del live e
selezione mobile con pressione prolungata. Nessun servizio reale viene invocato, nessuna apertura,
registrazione, formattazione o notifica viene effettuata. Il gate non certifica
connettività vendor, runtime HA distribuito o risultato di uno screen reader.
