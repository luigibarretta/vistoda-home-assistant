# EZVIZ controls

From Vistoda 0.41 with the Vistoda EZVIZ app 0.10 or later, EZVIZ settings,
arming, PTZ and camera connectivity use the app's own EZVIZ login. The official
Home Assistant `ezviz` integration becomes optional: its separate login can
expire without blocking settings or arming. When the app's EZVIZ session is
revoked, Vistoda opens the standard **Reconnect account** flow for that entry
(the same EZVIZ credentials step used during setup).

## Feature detection and fallback

Every EZVIZ entry polls `GET /v1/cameras/{camera}/controls` once a minute, in
the background and only while the bridge health and camera binding are
verified. Setup never waits for it.

- **App 0.10+** (`/controls` answers): the details page, the PTZ pad, the
  account alarm panel, the battery sensor and the camera connection sensor all
  read and write through the app.
- **Older app** (`/controls` answers HTTP 404): the previous native path stays
  in use: settings and PTZ through Home Assistant's `ezviz` integration,
  matched by camera serial. The `ezviz_core_unavailable` repair is raised only
  in this case, while that native integration is not loaded.

An app that supports `/controls` but is temporarily failing is reported as
unavailable; Vistoda never silently switches to the native session for it.

## Details page

The page keeps the stage → confirm → apply flow. Each write sends the value
together with the value the page last read; the app compares, writes and reads
back before answering:

| Answer | Panel message |
| --- | --- |
| success | new values are shown at once |
| 409 conflict | the setting changed meanwhile; check and retry |
| 502 `unconfirmed` | EZVIZ did not confirm; the app restored the old value |

Only items the app reports are shown. Existing keys keep their meaning:
`camera_defence` ↔ `defence_enabled`, `detection_mode`, `detection_sensitivity`
↔ `sensitivity` (slider within the reported range), and switches such as
`human_detection`, `wide_dynamic_range` (`wdr`), `distortion_correction`,
`logo_watermark` (`logo`), `privacy_mode`, `sleep_mode`, `status_light` and
`infrared_light`. Unknown switches appear under **Other settings**. The alarm
schedule, battery and firmware are read-only. Notification settings exist only
on the native path.

## Account alarm panel

One `alarm_control_panel` per Vistoda EZVIZ app reads and sets
`/v1/account/defence`, with the same mapping as Home Assistant core:

| Service | EZVIZ mode | State |
| --- | --- | --- |
| `alarm_disarm` | `home` | `disarmed` |
| `alarm_arm_home` | `sleep` | `armed_home` |
| `alarm_arm_away` | `away` | `armed_away` |

Several camera entries can share one app (one EZVIZ login). To avoid
duplicates, the panel belongs to the enabled EZVIZ entry with the smallest
entry ID among those with the same app URL. Its unique ID is
`ezviz-<owner entry_id>-account-defence` on the device
**Vistoda · EZVIZ · Account**, so the entity ID is normally
`alarm_control_panel.vistoda_ezviz_account`. If the owner entry is removed or
disabled, the next entry takes over after a reload with a new unique ID. Older
apps (HTTP 404) get no panel; the EZVIZ page then uses the native one.

## Entities per camera

| Entity | Unique ID | Source |
| --- | --- | --- |
| Camera connection | `ezviz-<entry_id>-camera-connectivity` | `online`, else native status |
| Battery | `ezviz-<entry_id>-battery` | `battery.percent`, created only when reported |
