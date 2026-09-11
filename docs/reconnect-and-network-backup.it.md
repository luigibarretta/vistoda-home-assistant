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
vengono adottate soltanto per lo stesso endpoint e alias, mantenendo i binding.
Un device ID fisico già noto che cambia interrompe l’adozione. I nuovi citofoni
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

Verifica: `python -m pytest -q tests/test_release_*.py`. I test eseguono i flussi,
la migrazione, il controllo dei mount e il backup con sostituti isolati del
framework HA e file temporanei. Non contattano i produttori, montano
condivisioni, ricollegano account di produzione o aprono ingressi.
