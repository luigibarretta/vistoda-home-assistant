# ADR 0006: Official Ring entity facade

- Status: accepted
- Date: 2026-08-22
- Supersedes: the no-unlock scope in ADR 0001

## Context

Vistoda adds Ring Intercom answering, full-duplex audio and private recording,
but its Home Assistant device exposed fewer controls than the official Ring
integration. Owning another Ring cloud session for door opening, volume and
telemetry would create competing authentication, refresh and command paths.
Moving official entities to the Vistoda device would also violate Home
Assistant registry ownership because one entity has one device owner.

## Decision

Vistoda exposes native proxy entities on its Ring device for every enabled
official Ring Intercom capability: door opening, three volume levels, battery,
last activity, ding and unlock. Each proxy resolves exactly one entity whose
registry platform is `ring` and whose device is manufactured by Ring with model
`Intercom`. Translation keys identify capabilities; Battery uses its official
original name because the provider supplies no translation key.

Reads mirror Home Assistant state and subscribe to state changes without
polling Ring. Writes call the official entity service with `blocking=True`.
The door button performs exactly one delegated press and never retries. Events
forward only future source transitions; startup never synthesizes or replays a
historical ding or unlock. Missing or ambiguous sources remain unavailable.

The two official diagnostics disabled by default are not duplicated. Vistoda
tracks the enabled public contract and its deployment audit records the complete
official device inventory, including disabled entities, so provider drift is
visible before a release.

## Consequences

- the official integration remains the only Ring cloud control owner;
- Vistoda's device page offers Ring parity plus the additional audio workflow;
- existing automations may keep using official entities without migration;
- proxy entities add a small amount of low-frequency recorder state;
- an official entity contract change requires review instead of guesswork.
