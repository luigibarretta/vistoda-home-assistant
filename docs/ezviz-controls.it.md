# Controlli EZVIZ

Da Vistoda 0.41 con l'app Vistoda EZVIZ 0.10 o successiva, impostazioni EZVIZ,
inserimento, PTZ e connessione delle telecamere usano l'accesso EZVIZ
dell'app. L'integrazione ufficiale `ezviz` di Home Assistant diventa
facoltativa: la sua sessione separata può scadere senza bloccare impostazioni o
inserimento. Se la sessione EZVIZ dell'app viene revocata, Vistoda apre il
normale flusso **Ricollega account** per quella entry (lo stesso passaggio con
le credenziali EZVIZ usato in configurazione).

## Rilevamento e ripiego

Ogni entry EZVIZ interroga `GET /v1/cameras/{camera}/controls` una volta al
minuto, in background e solo mentre salute del bridge e associazione della
telecamera sono verificate. La configurazione non la attende mai.

- **App 0.10+** (`/controls` risponde): pagina dei dettagli, comandi PTZ,
  pannello d'allarme dell'account, sensore batteria e sensore di connessione
  leggono e scrivono tramite l'app.
- **App precedente** (`/controls` risponde HTTP 404): resta il percorso nativo:
  impostazioni e PTZ tramite l'integrazione `ezviz` di Home Assistant,
  associata per numero di serie. La riparazione `ezviz_core_unavailable` viene
  segnalata solo in questo caso, finché l'integrazione nativa non è caricata.

Un'app che supporta `/controls` ma è temporaneamente in errore risulta non
disponibile; Vistoda non passa mai in silenzio alla sessione nativa.

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
firmware sono in sola lettura. Le notifiche esistono solo nel percorso nativo.

## Pannello d'allarme dell'account

Un `alarm_control_panel` per ogni app Vistoda EZVIZ legge e imposta
`/v1/account/defence`, con la stessa corrispondenza di Home Assistant core:

| Servizio | Modalità EZVIZ | Stato |
| --- | --- | --- |
| `alarm_disarm` | `home` | `disarmed` |
| `alarm_arm_home` | `sleep` | `armed_home` |
| `alarm_arm_away` | `away` | `armed_away` |

Più entry di telecamere possono condividere un'app (un solo accesso EZVIZ).
Per evitare duplicati, il pannello appartiene alla entry EZVIZ attiva con
l'entry ID minore tra quelle con lo stesso URL dell'app. Lo unique ID è
`ezviz-<entry_id proprietaria>-account-defence` sul dispositivo
**Vistoda · EZVIZ · Account**, quindi l'entity ID è normalmente
`alarm_control_panel.vistoda_ezviz_account`. Se la entry proprietaria viene
rimossa o disattivata, la successiva subentra dopo un ricaricamento con un
nuovo unique ID. Le app precedenti (HTTP 404) non hanno il pannello; la pagina
EZVIZ usa allora quello nativo.

## Entità per telecamera

| Entità | Unique ID | Origine |
| --- | --- | --- |
| Connessione telecamera | `ezviz-<entry_id>-camera-connectivity` | `online`, altrimenti stato nativo |
| Batteria | `ezviz-<entry_id>-battery` | `battery.percent`, creata solo se riportata |
