# ADR 0026: Atomic bulk provider-list membership

- Status: accepted
- Date: 2026-09-10

## Context

Local Blink and EZVIZ recordings and Blink USB clips already support selection,
but adding them to custom lists was available only one recording at a time.
Repeating the single-membership command for every recording and list could leave
a partially applied result if a later list reached its membership limit.

## Decision

The selection toolbar exposes one compact list action. It opens a mobile-safe
dialog in which the user can choose one or more existing lists. Lists that
already contain every selected recording are identified and disabled; partial
membership is reported without removing it.

Home Assistant accepts one bounded, provider- and config-entry-scoped command
containing up to 100 unique media identifiers and 64 list identifiers. The
persistent model validates every list and every capacity limit before changing
any membership, then saves the complete result once. Repeating the request is
idempotent. The response reports the number of newly created associations.

## Consequences

- One action organizes several local Blink/EZVIZ or Blink USB clips into one or
  more lists.
- Existing memberships are never removed by the bulk-add operation.
- A validation or capacity failure changes no list.
- Selecting a read-only Blink USB clip remains useful for list organization;
  destructive bulk deletion stays disabled when the provider disallows it.
