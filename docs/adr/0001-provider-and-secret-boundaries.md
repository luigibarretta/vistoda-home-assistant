# ADR-0001: Provider and secret boundaries

## Context

EZVIZ and Ring require different proprietary cloud protocols, session formats
and media lifecycles. Home Assistant needs a coherent setup experience and
native entities without becoming a second owner of rotating vendor sessions.

## Decision

Provider protocols remain in separate Rust bridge repositories. This private
custom integration is one thin provider-neutral adapter with one config entry
per bridge device. Its layout is HACS-compatible for a possible future public
release, while the current private deployment remains SHA-pinned through
Ansible. It stores only:

- provider and private bridge URL;
- independent bridge API token;
- configured non-secret alias.

The Ring Config Flow passes password and SMS code from the HA backend to the
private bridge but never adds them to config-entry data. The Rust bridge owns
challenge expiry, single-use verification and atomic rotating-session storage.
The EZVIZ flow consumes the already enrolled bridge and does not copy or rotate
its vendor session. EZVIZ vendor re-enrollment remains bridge-owned until the
Rust runtime can atomically replace its live transport without a stale client.

Only capabilities with a verified bridge contract produce entities. EZVIZ gets
a camera and connectivity entity. Ring gets connectivity and enrollment now;
media entities remain absent while its capability response is fail-closed.
Neither provider exposes unlock through this adapter.

## Consequences

- one consistent UI does not merge provider implementations or credentials;
- removing or reloading the HA entry cannot invalidate a vendor session;
- a compromised HA config entry grants private bridge access, not the vendor
  password, OTP or refresh token;
- bridge listeners must stay private and source-filtered;
- vendor enrollment progress is not durable in HA and safely expires on loss.
