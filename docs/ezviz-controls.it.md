# Controlli EZVIZ

Ogni entry EZVIZ sceglie esplicitamente da dove arrivano i suoi comandi,
esattamente come l'interruttore di delega di Ring:

- **Autonoma (predefinita)**: impostazioni, inserimento, rilevamento,
  sensibilità, PTZ, connessione della telecamera e pannello d'allarme
  dell'account usano l'accesso EZVIZ dell'app Vistoda EZVIZ (app 0.10 o
  successiva). L'integrazione ufficiale `ezviz` di Home Assistant non serve e la
  sua sessione separata può scadere liberamente. Se la sessione EZVIZ dell'app
  viene revocata, Vistoda apre il normale flusso **Ricollega account** per
  quella entry.
- **Delegata**: l'interruttore di configurazione **Delega comandi
  all'integrazione EZVIZ ufficiale** (`ezviz_delegate_controls`, sul
  dispositivo **Vistoda · EZVIZ · <alias>** della telecamera) affida i comandi
  della telecamera all'integrazione `ezviz` di Home Assistant. Vistoda trova il
  dispositivo della telecamera nel registro dispositivi tramite il numero di
  serie e usa solo l'interfaccia pubblica di quell'integrazione: le sue entità
  (elencate nella pagina dei dettagli), i loro stati pubblicati e i servizi
  `camera.enable_motion_detection` / `camera.disable_motion_detection`
  dell'entità camera ufficiale per l'armamento. Non legge né chiama mai gli
  oggetti di runtime dell'integrazione ufficiale o il suo client EZVIZ. Si può
  attivare solo mentre la entry ufficiale che ha registrato la telecamera è
  caricata e ha un'entità camera per essa.

La scelta ha effetto senza riavvio: l'instradamento segue subito l'opzione e
le entry che condividono la stessa app si ricaricano per aggiungere o togliere
il pannello d'allarme dell'account Vistoda. Se l'integrazione ufficiale non è
disponibile quando la entry si configura (verificato dopo l'avvio di Home
Assistant), l'opzione viene riportata a disattivata, come fa Ring.
L'interruttore resta disponibile mentre è attivo, così la delega si può sempre
disattivare. La pagina dei dettagli EZVIZ mostra l'**Origine dei comandi**
attuale (Vistoda o Integrazione ufficiale) e apre l'interruttore.
Il pannello aperto ricarica i dati quando l'interruttore cambia, e ogni comando
PTZ o Arma/Disarma ricontrolla prima l'interruttore attuale, così una pagina non
aggiornata non scrive mai sull'altra fonte. Le entry autonome mostrano solo dati
Vistoda (nessuna batteria, pannello d'allarme, entità o sensore di crittografia
nativi).

## Matrice di instradamento

Ogni entry EZVIZ interroga `GET /v1/cameras/{camera}/controls` una volta al
minuto, in background e solo mentre salute del bridge e associazione della
telecamera sono verificate. La configurazione non la attende mai.

| Modalità | Integrazione ufficiale | `/controls` dell'app | Impostazioni, inserimento, PTZ, connessione |
| --- | --- | --- | --- |
| Autonoma | qualsiasi | risponde | app Vistoda EZVIZ |
| Autonoma | qualsiasi | HTTP 404 (app precedente) | non disponibili; aggiorna l'app alla 0.10 o attiva la delega |
| Delegata | caricata, telecamera registrata | qualsiasi | entità e servizi camera dell'integrazione ufficiale `ezviz` |
| Delegata | non disponibile | qualsiasi | non disponibili; ripristinala o disattiva la delega |

Vistoda non passa mai in silenzio da una fonte all'altra: un'app in errore
risulta non disponibile, e così un'integrazione ufficiale assente. La
riparazione `ezviz_core_unavailable` viene segnalata solo finché una entry
attiva è delegata e l'integrazione ufficiale non è caricata; le entry autonome
non la richiedono mai.

## Pagina dei dettagli

La pagina mantiene il flusso modifica → conferma → applica. Ogni scrittura
invia il valore insieme a quello letto dalla pagina; l'app confronta, scrive e
rilegge prima di rispondere:

| Risposta | Messaggio del pannello |
| --- | --- |
| successo | i nuovi valori compaiono subito |
| 409 conflitto | l'impostazione è cambiata nel frattempo; controlla e riprova |
| 502 `unconfirmed` | EZVIZ non ha confermato; l'app ha ripristinato il valore |

Compaiono solo le voci riportate dall'app. Le chiavi esistenti mantengono il
loro significato: `camera_defence` ↔ `defence_enabled`, `detection_mode`,
`detection_sensitivity` ↔ `sensitivity` (cursore nell'intervallo riportato) e
interruttori come `human_detection`, `wide_dynamic_range` (`wdr`),
`distortion_correction`, `logo_watermark` (`logo`), `privacy_mode`,
`sleep_mode`, `status_light` e `infrared_light`. Gli interruttori sconosciuti
compaiono in **Altre impostazioni**. Programmazione allarme, batteria e
firmware sono in sola lettura.

In modalità delegata la pagina elenca le entità proprie dell'integrazione
ufficiale e aggiunge una sola riga Vistoda, **Telecamera armata**, letta
dall'attributo `motion_detection` dell'entità camera ufficiale. L'armamento
chiama il servizio camera ufficiale, poi chiede a quell'entità un nuovo
aggiornamento (`homeassistant.update_entity`) e attende fino a 20 s che il suo
stato mostri il nuovo valore; altrimenti il pannello segnala `unconfirmed` e
non annulla nulla. Le impostazioni che l'integrazione ufficiale non espone
(notifiche, WDR, correzione distorsione, logo, rilevamento sagoma umana,
modalità di rilevamento) sono disponibili solo in modalità autonoma.

## Pannello d'allarme dell'account

Un `alarm_control_panel` per ogni app Vistoda EZVIZ legge e imposta
`/v1/account/defence`, con la stessa corrispondenza di Home Assistant core:

| Servizio | Modalità EZVIZ | Stato |
| --- | --- | --- |
| `alarm_disarm` | `home` | `disarmed` |
| `alarm_arm_home` | `sleep` | `armed_home` |
| `alarm_arm_away` | `away` | `armed_away` |

Il pannello esiste solo in modalità autonoma; le entry delegate usano il
pannello d'allarme dell'integrazione ufficiale, quindi non si crea alcun
duplicato e un pannello rimasto dalla modalità autonoma viene rimosso. Più
entry di telecamere possono condividere un'app (un solo accesso EZVIZ). Per
evitare duplicati, il pannello appartiene alla entry EZVIZ autonoma attiva con
l'entry ID minore tra quelle con lo stesso URL dell'app. Lo unique ID è
`ezviz-<entry_id proprietaria>-account-defence` sul dispositivo
**Vistoda · EZVIZ · Account**, quindi l'entity ID è normalmente
`alarm_control_panel.vistoda_ezviz_account`. Se la entry proprietaria viene
rimossa, disattivata o delegata, la successiva entry autonoma subentra dopo un
ricaricamento con un nuovo unique ID. Le app precedenti (HTTP 404) non hanno il
pannello.

## Entità per telecamera

| Entità | Unique ID | Origine |
| --- | --- | --- |
| Connessione telecamera | `ezviz-<entry_id>-camera-connectivity` | `online` dell'app (autonoma) o stato nativo (delegata) |
| Delega comandi all'integrazione EZVIZ ufficiale | `ezviz-<entry_id>-delegate-controls` | opzione della entry `ezviz_delegate_controls`, disattivata per impostazione predefinita |
| Batteria | `ezviz-<entry_id>-battery` | `battery.percent`, creata solo se riportata |
| In carica (sensore binario) | `ezviz-<entry_id>-charging` | `battery.charging` (app 0.13+), creato solo se riportato; attributi `power_source` (esterna/batteria) e `power_status` grezzo |
