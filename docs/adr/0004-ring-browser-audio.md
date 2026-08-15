# ADR 0004: Ring browser audio boundary

- Status: accepted
- Date: 2026-08-15

## Context

Ring Intercom Audio has no video stream. The provider bridge now supports a
bounded direct WebRTC signaling contract, but its URL and bearer token must not
enter Home Assistant browser state. Native camera entities do not express an
audio-only talk interaction or guarantee that microphone capture follows an
explicit user gesture.

## Decision

Vistoda registers one local panel and three authenticated Home Assistant
WebSocket commands: list loaded Ring entries, create an audio session and
delete it idempotently. The Python backend resolves the config entry, reads the
private client already owned by the integration and proxies only bounded SDP,
ICE and lifecycle data. It never returns bridge URL, token or Ring identity.

The provider-specific **Vistoda · Ring** panel exposes two distinct actions:

- **Ascolta** generates a zero-gain local audio track and never requests a
  microphone;
- **Parla e ascolta** calls `getUserMedia` only inside the click handler and
  applies echo cancellation, noise suppression and automatic gain control.

Both actions create one `sendrecv` PCMU transceiver because that is the Ring
transport proven by the owned-device canary. The panel fully gathers local ICE,
submits the offer through Home Assistant, applies the answer and bounded remote
candidates, and attempts delete after stop, failure, disconnect or expiry. A
session lasts at most 120 seconds.

The user may switch between listen-only and full-duplex conversation inside
the same call. The browser uses `RTCRtpSender.replaceTrack` to replace the
silent track with the microphone, or vice versa, without dropping inbound
audio or negotiating a second Ring session. After an explicit stop, the panel
shows the bounded provider cooldown and re-enables both start controls when it
expires instead of failing an immediate restart opaquely.

The Vistoda Ring device owns a diagnostic **Audio Vistoda** connectivity entity
and links to the provider-specific panel through its configuration URL. It is
kept separate from the official Ring integration device because the two config
entries have different ownership and lifecycle. The interactive microphone
remains correctly owned by the browser panel.

The JavaScript asset is shipped inside the custom component, served by an
async static path and registered through Home Assistant's supported
`panel_custom.async_register_panel` API. No external JavaScript dependency or
public route is added.

## Consequences

- HA authentication remains the browser trust boundary;
- browsers need PCMU, WebRTC and direct ICE reachability;
- microphone permission is visible and revocable in browser controls;
- the first release supports one Ring peer and no call recording;
- future dashboard cards can reuse the same WebSocket commands without gaining
  bridge credentials.
