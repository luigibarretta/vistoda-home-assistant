# Ring cameras (experimental)

Vistoda Home Assistant 0.30.2 and the Ring app 0.14.0 add a native camera
inventory and browser live viewer. No official Home Assistant Ring integration
is required. `/vistoda/ring` displays a camera selector when the enrolled Ring
account reports supported cameras; an account with only an Intercom has no empty
camera card. Camera-only accounts can complete enrollment without a fabricated
Intercom device. The existing Intercom controls and history remain separate.

An administrator explicitly opens a selected camera. The viewer starts in
listen-only mode, supports rotation, speaker mute and opt-in microphone access,
and releases its session on close, page hiding, disconnect or expiry. Sessions
last at most two minutes. Camera access currently requires a Home Assistant
administrator; delegated Intercom control does not grant camera access.

This is a protocol-tested preview, not a claim of hardware compatibility. No Ring
camera was available for acceptance testing. The UI marks this limitation.
H264 video and PCMU audio are negotiated directly between Ring and the browser;
the provider only forwards authenticated signaling. Camera recordings, snapshots,
settings and Ring Edge are not supported by this path. Existing Intercom
recording and unlock functionality is unchanged.

Use HTTPS and grant microphone access only when you intend to talk. If the
provider is busy, close the previous viewer and wait for its cooldown. Closing
another person's session is not permitted by the HA connection ownership check.

Tests cover exact string device IDs, cross-device/connection isolation, pending
session cancellation, account unload, expiry, camera-only enrollment, receiving
audio/video track aggregation and UI rotation on Chromium, Firefox and WebKit.
They do not substitute for a real-device network/audio/video acceptance test.
The provider's `docs/NATIVE_CAMERAS.md` records protocol provenance and limits.
