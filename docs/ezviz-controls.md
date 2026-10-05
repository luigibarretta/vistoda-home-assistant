# EZVIZ controls

Each EZVIZ entry explicitly chooses where its controls come from, exactly like
Ring's delegation switch:

- **Standalone (default)**: settings, arming, detection, sensitivity, PTZ,
  camera connectivity and the account alarm panel use the Vistoda EZVIZ app's
  own EZVIZ login (app 0.10 or later). The official Home Assistant `ezviz`
  integration is not needed and its separate login can expire freely. When the
  app's EZVIZ session is revoked, Vistoda opens the standard **Reconnect
  account** flow for that entry.
- **Delegated**: the configuration switch **Delegate controls to the official
  EZVIZ integration** (`ezviz_delegate_controls`, on the camera's
  **Vistoda · EZVIZ · <alias>** device) routes the same controls through Home
  Assistant's `ezviz` integration, matched by camera serial. It can be turned
  on only while that integration's cloud coordinator for the bound camera is
  loaded and healthy (RTSP-only `CAMERA_ACCOUNT` entries never count).

The choice takes effect without a restart: routing follows the option at once
and the entries sharing the same app reload to add or remove the Vistoda
account alarm panel. If the official integration is unavailable when the entry
sets up (checked once Home Assistant has started), the option is switched back
off, as Ring does. The switch stays available while on, so delegation can
always be turned off. The EZVIZ details page shows the current
**Control source** (Vistoda or Official integration) and opens the switch.
The open panel reloads its data when the switch flips, and every PTZ press or
Arm/Disarm re-checks the live switch first, so a stale page never writes to the
other source. Standalone entries show Vistoda data only (no native battery,
alarm panel, entities or encryption sensor).

## Routing matrix

Every EZVIZ entry polls `GET /v1/cameras/{camera}/controls` once a minute, in
the background and only while the bridge health and camera binding are
verified. Setup never waits for it.

| Mode | Official integration | App `/controls` | Settings, arming, PTZ, connectivity |
| --- | --- | --- | --- |
| Standalone | any | answers | Vistoda EZVIZ app |
| Standalone | any | HTTP 404 (older app) | unavailable; update the app to 0.10 or delegate |
| Delegated | loaded and healthy | any | official `ezviz` integration |
| Delegated | unavailable | any | unavailable; restore it or turn delegation off |

Vistoda never silently switches between the two sources: a failing app is
reported as unavailable, and so is a missing official integration. The
`ezviz_core_unavailable` repair is raised only while some enabled entry is
delegated and the official integration is not loaded; standalone entries never
require it.

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
schedule, battery and firmware are read-only. Notification settings and the
official integration's own entities appear only in delegated mode.

## Account alarm panel

One `alarm_control_panel` per Vistoda EZVIZ app reads and sets
`/v1/account/defence`, with the same mapping as Home Assistant core:

| Service | EZVIZ mode | State |
| --- | --- | --- |
| `alarm_disarm` | `home` | `disarmed` |
| `alarm_arm_home` | `sleep` | `armed_home` |
| `alarm_arm_away` | `away` | `armed_away` |

The panel exists only in standalone mode; delegated entries rely on the
official integration's own alarm panel, so no duplicate is created and a panel
left from standalone mode is removed. Several camera entries can share one app
(one EZVIZ login). To avoid duplicates, the panel belongs to the enabled
standalone EZVIZ entry with the smallest entry ID among those with the same app
URL. Its unique ID is
`ezviz-<owner entry_id>-account-defence` on the device
**Vistoda · EZVIZ · Account**, so the entity ID is normally
`alarm_control_panel.vistoda_ezviz_account`. If the owner entry is removed or
disabled, or delegated, the next standalone entry takes over after a reload
with a new unique ID. Older apps (HTTP 404) get no panel.

## Entities per camera

| Entity | Unique ID | Source |
| --- | --- | --- |
| Camera connection | `ezviz-<entry_id>-camera-connectivity` | app `online` (standalone) or native status (delegated) |
| Delegate controls to the official EZVIZ integration | `ezviz-<entry_id>-delegate-controls` | entry option `ezviz_delegate_controls`, default off |
| Battery | `ezviz-<entry_id>-battery` | `battery.percent`, created only when reported |
