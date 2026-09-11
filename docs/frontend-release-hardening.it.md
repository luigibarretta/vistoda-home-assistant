# Verifiche frontend prima del rilascio

Il pannello non produce overflow orizzontale del documento alle larghezze
320, 360, 393, 600, 768 e 1280 px. I controlli hanno aree interattive di almeno
44 × 44 px; gli indicatori Blink mantengono cerchi visivi di 8 px.

Gli errori di inventario sono distinti dai provider non configurati. Il ritorno
a Home Assistant usa la dashboard predefinita o `/lovelace`, senza percorsi
personali. Ring seleziona il citofono per entry: apertura e cronologia restano
associate all’ingresso scelto. EZVIZ associa ogni camera tramite alias esatto;
non aggiorna immagini di altre camere se l’associazione è ambigua. Aprire il
pannello legge soltanto immagini già salvate, senza risvegliare dispositivi.

## Italiano e inglese

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

## Esecuzione

```sh
node --test tests/*.mjs
NODE_PATH=/percorso/node_modules node tests/browser/panel-responsive.mjs
```

Il browser usa Chromium/Playwright, un server solo loopback e risposte Home
Assistant sintetiche. Verifica 48 combinazioni provider/lingua/larghezza,
archivi, liste, identità Ring e ritorno del focus, impostazioni Blink, zone,
conferma formattazione USB, errori e recupero. Nomi utente come “Elimina” devono
rimanere invariati. Nessun servizio reale viene invocato, nessuna apertura,
registrazione, formattazione o notifica viene effettuata. Il gate non certifica
connettività vendor, runtime HA distribuito o risultato di uno screen reader.
