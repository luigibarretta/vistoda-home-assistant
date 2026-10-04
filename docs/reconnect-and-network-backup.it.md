# Ricollegare gli account e configurare i backup di rete

Apri **Impostazioni → Dispositivi e servizi → Vistoda → Configura** e seleziona
**Ricollega account**. Per le entry Ring ed EZVIZ gestite dall’app, anche
Riconfigura avvia il ricollegamento. Conferma il produttore, accedi allo stesso
account e completa la verifica con il codice più recente, se richiesto.

Home Assistant inoltra le credenziali al provider Vistoda privato esistente
solo per quella richiesta. Password, account e codici OTP non vengono aggiunti
alla config entry. Il ricollegamento mantiene ID della entry, unique ID, titolo,
opzioni, associazione fisica Ring, entity ID e cronologia. Un OTP errato o
scaduto richiede un nuovo accesso senza creare un’altra entry. Ricollegare
l’account non autorizza un alias Ring a cambiare dispositivo fisico.

La discovery Supervisor Ring accetta un payload aggregato `devices` con alias
distinti e `device_id` numerici rappresentati come stringhe. Le entry esistenti
vengono adottate soltanto sullo stesso endpoint autenticato, tramite alias o
ID fisico Ring già memorizzato. Un alias generato dalla discovery non rinomina
la entry: una nuova lettura deve confermare che l'alias originale risolva ancora
quell'ID fisico. ID di entry, device ed entità, opzioni e binding Ring ufficiali
restano invariati. Corrispondenze ambigue o un ID fisico diverso interrompono
l'adozione; un alias originale irraggiungibile non viene sostituito in silenzio.
Si evita così un nuovo **Scoperto → Aggiungi** per un citofono già configurato.
I nuovi citofoni
si scelgono nel flusso nativo; gli alias rimanenti proseguono dopo il primo
accesso senza richiedere nuovamente la password. Rimane compatibile la discovery
precedente con un singolo alias.

Dopo il primo accesso Ring, HA legge l’inventario autenticato `/v1/intercoms`
e propone nomi e luoghi reali dei citofoni. Il provider deve restituire un
`alias` già utilizzabile per ogni dispositivo: HA non inventa né configura gli
alias Rust. Con provider precedenti senza alias, HA accetta un alias configurato
solo se una nuova lettura dello stato conferma il `device_id` fisico esatto.
L’alias iniziale singolo è utilizzabile solo dopo questa verifica; la prima
configurazione automatica multi-dispositivo richiede gli alias automatici del
provider. Il ricollegamento di una entry esistente mantiene il binding originale
senza richiedere la selezione di un nuovo dispositivo.

Gli unique ID delle entità telecamera e connessione EZVIZ includono ora la
config entry. Il caricamento migra gli ID precedenti basati solo sull’alias,
mantenendo entity ID e nomi utente. Un dispositivo legacy condiviso tra entry
viene separato solo per la entry corrente; gli altri dispositivi ed entità
rimangono. Le automazioni basate sugli entity ID continuano a usare gli stessi
ID. Controlla le automazioni basate sul dispositivo quando un dispositivo
precedentemente ambiguo e condiviso deve essere separato.

Per il backup, aggiungi prima uno **spazio di rete NFS o SMB scrivibile** in
**Impostazioni → Sistema → Archiviazione**, con utilizzo **Media**. Inserisci
quindi il suo nome nelle opzioni della entry Blink o EZVIZ, per esempio
`family_archive`: non usare IP, URL della condivisione o percorsi `/media/...`.
Il valore predefinito compatibile è `vistoda_archives`.

Il backup orario Blink si attiva nel tab **Backup NFS** (**Backup automatico
orario su NFS**, solo amministratori) oppure nelle opzioni Blink. La
destinazione deve essere pronta prima di abilitarlo. Il worker gira in Home
Assistant anche con il pannello chiuso e copia sia le clip USB Blink sia le
registrazioni **Locale HA**, comprese quelle da movimento. Crea al massimo 20
nuove copie per passaggio fra le due fonti e prosegue nelle ore successive;
ogni fonte legge al massimo 100 pagine da 50 elementi per passaggio. Le copie
esistenti sono verificate con il checksum, senza riscaricarle. Non elimina gli
originali e non propaga le eliminazioni. Lo stato dell'ultimo passaggio è nella
diagnostica `usb_auto_backup`. Il primo passaggio avviene alla successiva
scadenza oraria del worker; per una copia USB immediata usa **Backup archivio**
nella sezione USB.

Senza chiavetta USB nel Sync Module, il tab **Locale HA** può registrare al
movimento: un amministratore attiva **Registrazione al movimento** (15/30/60 s,
telecamere selezionate). La registrazione parte dopo che Blink segnala
l'evento su una rete armata, quindi riprende la scena successiva, e ogni
registrazione accende la telecamera (quelle a batteria si scaricano prima). Le
registrazioni da movimento sono un buffer circolare; quelle manuali non vengono
mai rimosse automaticamente.

L'**Archivio registrazioni** Blink è separato dal carousel delle telecamere,
con i tab **USB Blink**, **Locale HA** e **Backup NFS**. Cambiare telecamera non
cambia il filtro dell'archivio. USB permette di scegliere Sync Module e camera;
Locale HA e NFS hanno filtri camera e selettori della dimensione pagina propri.
NFS mostra file completi con metadati presenti sul mount, non richieste di
backup in attesa. Gli amministratori possono scaricare file verificati,
riprodurre le copie USB MP4 e aggiungere le copie selezionate alle liste del
video originale. Le copie locali TS sono solo scaricabili in questo tab.
L'eliminazione NFS non è esposta. Eliminare la sorgente non elimina la copia
NFS; un mount mancante non viene sostituito da una cartella locale.

I comandi rimangono nel pulsante **REC** della live. Blink sceglie la propria
destinazione configurata (USB quando Local Storage è attivo). **Chiudi questa
live e conserva** chiude soltanto il proprio visualizzatore, senza inviare
`save=false`. I limiti opzionali di 15/30/60 secondi contano il video ricevuto,
non caricamento o blocchi, poi chiudono quel visualizzatore. Navigazione e
chiusura dell'app possono terminarlo prima. Gli altri spettatori non vengono
disconnessi e possono prolungare la clip condivisa. Blink registra l'intera
sessione, anche prima di REC: non è un segmento ritagliato indipendente né un
timer lato server. Per un file separato di 15/30/60 secondi scegli Locale HA.
Il comando `save=false` continua ad annullare il salvataggio, non a fermarlo
conservando una clip.

Prima di scrivere viene verificato il mount NFS/NFS4/SMB esatto e scrivibile
sotto `/media`, rifiutando cartelle locali e symlink. Sono richiesti almeno
512 MiB liberi. Un mount mancante rende il backup indisponibile: non viene mai
usato lo spazio locale HA come ripiego. Per cambiare nome la nuova destinazione
deve essere pronta. Una destinazione già configurata ma indisponibile non
impedisce il ricollegamento dell’account. L’opzione Blink vale sia per le
registrazioni locali sia per i backup delle clip USB.

Le registrazioni mantengono il formato reale: MPEG-TS (`video/mp2t`) usa `.ts`,
MPEG-PS (`video/mpeg`) usa `.mpegps`; le clip USB Blink rimangono `.mp4`.
I backup locali verificano dimensione e SHA-256 prima di pubblicare il file
atomico e i metadati. Un checksum esistente diverso provoca un errore senza
sovrascrivere il file. I manifest EZVIZ devono corrispondere all’alias della
telecamera configurata nella entry.

La diagnostica scaricabile mostra `reauth_supported` e `backup_storage` con
stato pronto, mount mancante/non scrivibile/indisponibile o spazio insufficiente.
Omette percorsi di server e archivi, credenziali e binding fisici Ring.

Verifica: `python -m pytest -q tests/test_release_*.py tests/test_ring_discovery_identity.py`. I test eseguono i flussi,
la migrazione, il controllo dei mount e il backup con sostituti isolati del
framework HA e file temporanei. Non contattano i produttori, montano
condivisioni, ricollegano account di produzione o aprono ingressi.

## Sessione del produttore e stato dei dispositivi

Se Ring revoca la sessione Vistoda (per esempio dopo un cambio password o la
rimozione del dispositivo dai client autorizzati dell'account Ring), il motore
Ring risponde HTTP 403 `reauth_required`. Vistoda avvia il normale flusso di
nuova autenticazione di Home Assistant per quella entry; il listener eventi
attende cinque minuti tra un controllo e l'altro e non segnala un guasto push.
Un token bridge errato resta HTTP 401 con l'errore esistente.

`binary_sensor.*_connessione_citofono` (Ring) segue lo stato `online` del
motore ogni minuto ed è non disponibile quando il bridge non risponde. Ogni
telecamera EZVIZ ha `binary_sensor.*_connessione_telecamera`, letto
dall'integrazione EZVIZ nativa di Home Assistant (stato 1 online, 2 offline).
Il badge e la voce **Connessione** del pannello EZVIZ mostrano la telecamera;
**App Vistoda** mostra il bridge. Riparazioni segnala `ezviz_core_unavailable`
finché l'integrazione nativa è assente, disattivata o in errore, perché
impostazioni e inserimento EZVIZ dipendono da essa.

I motori Ring dalla 0.15.0 riportano `push_degraded` e `last_missed_ding_at`.
Riparazioni mostra `ring_push_silent_<entry_id>` finché Ring non consegna le
notifiche di chiamata e lo rimuove quando riprendono. Ogni nuova chiamata persa
genera un solo evento `vistoda_ring_missed_call` con `entry_id`, `alias`,
`device_name`, `location_name`, `city` e `occurred_at` (secondi epoch),
memorizzato per non ripeterlo dopo un riavvio. I motori precedenti omettono
questi campi e il comportamento non cambia.
