# ADR 0010: Native Apple audio and OAuth boundary

- Status: accepted
- Date: 2026-08-22
- Extends ADR 0004

## Context

Home Assistant Companion mirrors actionable notifications to Apple Watch, but
it does not expose an audio client for custom integrations. The browser path in
ADR 0004 depends on WebRTC, while maintained WebRTC frameworks do not ship a
watchOS target. The Ring bridge now offers a bounded codec-preserving PCMU
relay specifically for native clients.

A native application must authenticate as the Home Assistant user without
embedding a long-lived token, Ring credential or private bridge token. Home
Assistant's OAuth client identifier is a web URL. A redirect URI on the same
host and port needs no pre-registration, while a custom scheme requires an
approved link on that client website.

## Decision

Vistoda registers the authenticated endpoint
`/api/media_bridge/ring/audio/{entry_id}`. It resolves only a loaded Ring config
entry, opens the bridge relay with the config-entry bearer, and proxies bounded
WebSocket text/binary messages for at most 125 seconds. Client binary frames
must be exactly 160 bytes; bridge frames and all text are capped at 2 KiB.
Either side ending closes both. No bridge URL, token, Ring identity, SDP or ICE
is returned to the Apple client.

The iPhone app uses Home Assistant's authorization-code flow. The selected HA
origin is the OAuth `client_id`; the redirect URI is the same-origin
`/api/media_bridge/apple/auth` view. That public, no-store view accepts only a
bounded `code` or `error` plus mandatory `state`, then redirects to
`vistoda://auth`. `ASWebAuthenticationSession` captures the native callback,
the app validates `state`, exchanges the one-time code at `/auth/token`, and
stores refresh/access tokens in Keychain. There is no client secret.

The iPhone transfers the instance, Ring entry identifier, access token and
expiry through WatchConnectivity. The Watch stores them in its Keychain. It
starts muted and uses the authenticated HA relay endpoint; refresh remains an
iPhone responsibility. The first hardware release does not claim background
VoIP delivery: the existing HA notification is the wake-up path until signed
PushKit/APNs can be validated.

## Consequences

- native Apple clients authenticate to HA, never directly to a bridge;
- OAuth state and one-time code bounds are testable without secrets;
- the callback is public by protocol necessity but reflects only whitelisted,
  bounded values into a fixed custom scheme and is never cached;
- Watch audio works without embedding WebRTC or vendor protocol code;
- true incoming CallKit/PushKit ringing remains a separate signed deployment
  gate; mirrored HA notifications remain functional meanwhile.
