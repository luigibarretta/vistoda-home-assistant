# Dichiarazione di accessibilità Vistoda

Ultimo aggiornamento: 12 settembre 2026.

Vistoda mira a rendere il proprio pannello Home Assistant utilizzabile dal maggior numero possibile di persone. L’obiettivo tecnico corrente è [WCAG 2.2 livello AA](https://www.w3.org/TR/WCAG22/).

Questa è una dichiarazione volontaria del progetto, non una certificazione. Vistoda non dichiara ancora una conformità WCAG formale perché non sono stati completati un audit indipendente e una matrice completa di test con tecnologie assistive.

## Ambito

La dichiarazione copre il pannello fornito da `vistoda-home-assistant`: Panoramica, Ring, Blink ed EZVIZ; paginazione delle telecamere; impostazioni; archivi registrazioni; liste; finestre di conferma; finestra informazioni.

Home Assistant, i siti dei produttori, i media forniti dai produttori, le richieste di permesso del browser e le integrazioni di terze parti non rientrano nell’ambito diretto di questa dichiarazione.

## Misure implementate

- pulsanti, link, etichette dei campi, titoli, aree di stato e finestre native con semantica appropriata;
- focus da tastiera visibile e controlli di provider, telecamere, archivi e zone utilizzabili da tastiera;
- etichette testuali o nomi accessibili per i controlli a icona, con stato esposto tramite attributi come `aria-current`, `aria-pressed`, `aria-checked`, `aria-expanded` e `aria-busy`;
- controlli progettati attorno a un’area tattile di 44 per 44 pixel CSS;
- layout provati per il reflow senza scorrimento orizzontale della pagina a partire da 320 pixel CSS;
- testo e icone che non affidano gli stati importanti al solo colore;
- animazioni e scorrimento fluido disabilitati quando è richiesta la riduzione del movimento;
- nomi accessibili e istruzioni in inglese e italiano.

## Evidenze dell’audit interno

L’audit interno del 12 settembre 2026 ha usato dati Home Assistant sintetici e Playwright. Ha coperto Chromium, Firefox e WebKit; larghezze da 320 a 1280 pixel CSS; inglese e italiano; navigazione tra provider; selezione telecamere; archivi; finestre; recupero dagli errori; dimensione dei target tattili e overflow della pagina. Combina controlli automatici e revisione visiva umana, come raccomandato dalle [linee guida W3C per la valutazione dell’accessibilità](https://www.w3.org/WAI/test-evaluate/).

L’audit ha incluso anche la revisione visiva delle schermate mobile e desktop e controlli da tastiera per apertura delle finestre, chiusura con Esc, ripristino del focus ed editor delle zone Blink. Durante la revisione di rilascio le evidenze sono conservate nella directory `artifacts/accessibility-audit-2026-09-12` del repository.

Questo documento segue la struttura raccomandata dalle [linee guida W3C per le dichiarazioni di accessibilità](https://www.w3.org/WAI/planning/statements/).

## Problemi risolti con questo audit

- La tela fissa delle zone Blink causava in Firefox un overflow di un pixel a una larghezza desktop. Dimensioni intere mantengono ora tutte le celle 20 per 15 dentro le coordinate dell’immagine su ogni engine provato.
- L’editor mobile delle zone ha ora un nome programmatico, trattiene il focus mentre è aperto, rende inattivi i controlli circostanti, si chiude con Esc e restituisce il focus al pulsante di apertura.
- I controlli della modalità zone Blink sono ora un gruppo di pulsanti etichettato con stato `aria-pressed`, invece di un pattern tab incompleto.
- I pulsanti di eliminazione delle zone privacy sono passati da 32 a 44 pixel CSS.
- Il selettore Ring duplicato e nascosto è stato rimosso dall’ordine di tastiera e dall’albero di accessibilità; il listbox visibile ed etichettato resta il selettore interattivo.
- Testi accentati piccoli e link ai documenti usano ora il colore principale del testo di Home Assistant, senza dipendere da un colore di accento del tema che potrebbe non raggiungere il contrasto minimo.

## Limiti noti e verifiche mancanti

- Non è ancora stata completata una regressione integrale con NVDA, JAWS, VoiceOver o TalkBack.
- I video delle telecamere e le registrazioni dei produttori potrebbero non avere sottotitoli, trascrizioni o descrizioni audio.
- L’editor Blink da 20 per 15 zone è utilizzabile da tastiera, ma modificare centinaia di celle rimane un’attività complessa per alcuni utenti.
- I temi Home Assistant scelti dall’utente possono cambiare il contrasto rispetto alle combinazioni coperte dall’audit di rilascio.
- Le finestre di permesso, autoplay e microfono sono controllate dal browser e dal sistema operativo.

## Segnalazioni

Segnala un problema di accessibilità nel [tracker di Vistoda](https://github.com/luigibarretta/vistoda-home-assistant/issues). Indica versione Vistoda, versione Home Assistant, browser, sistema operativo, tecnologia assistiva, pagina e passaggi per riprodurre il problema. Non includere credenziali, immagini delle telecamere o registrazioni private.

Per la versione inglese, consulta [ACCESSIBILITY.md](ACCESSIBILITY.md).
