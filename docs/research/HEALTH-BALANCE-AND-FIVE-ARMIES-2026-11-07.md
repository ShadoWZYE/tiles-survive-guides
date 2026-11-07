# Five armies and report health accounting — 7 November 2026

## Saved armies

Both planner editions now have numbered buttons **1–5 above the formation**. Each army saves its ordered hero formation and battle focus. Hero builds and account settings remain shared. A hero assigned to another army cannot be selected or recommended again; clearing that army releases its heroes. Import normalization also removes duplicate assignments, unknown heroes and excess slots. Browser profiles migrate their existing formation to Army 1. Previous Windows profiles did not save a formation; recorded builds and ownership are retained.

Switching, reload, modes, duplicate rejection, clearing and recommendation exclusions are checked in both editions. This is sequential army planning: recommendations optimize the current army from the remaining pool, not all five armies jointly.

## A useful reduction in unexplained report discrepancy

The recorded battle contains outgoing damage, incoming damage and healing. Treating outgoing damage as identical to incoming damage leaves sizeable differences. Including the **opposing side's displayed healing** explains much of those differences with **zero fitted parameters**:

| Direction | Outgoing damage | Visible incoming damage | Displayed opposing healing | Gap before recovery | Gap after recovery |
|---|---:|---:|---:|---:|---:|
| Friendly outgoing | 37,910,000 | 33,919,480 | 3,976,230 | 3,990,520 (10.53%) | 14,290 (0.038%) |
| Enemy outgoing | 75,400,000 | 71,680,000 | 3,228,170 | 3,720,000 (4.93%) | 491,830 (0.652%) |

Percentages use outgoing damage as denominator. These are arithmetic differences between rounded report totals, **not simulated damage prediction errors**.

The friendly-outgoing residual is inside a conservative display-precision budget of 110,050. The reverse residual exceeds its 140,020 budget. Budgets allow one full shown unit for each displayed value; the game's exact rounding implementation is not assumed. Enemy healing was read from the report at recording second 37. The machine-readable observation retains each value and its displayed unit.

### Interpretation and limits

The evidence supports testing whether the incoming column describes net HP depletion while outgoing damage represents gross pressure. The general health identity is:

`gross post-defence damage = net HP lost + effective healing + shield absorption + overkill`

This identity applies only when the terms cover the same actors and event magnitudes. Displayed healing may include ineffective recovery or recipients outside the visible incoming rows. Shields, overkill, omitted recovery and actor coverage remain possible explanations for the reverse residual. **We have not proved the server's counter definitions or identified the remaining residual's cause.** Local replay animations and report totals share supplied report data and therefore do not independently establish those definitions.

The new health ledger explicitly tracks effective recovery, overhealing, shields and overkill for supplied events. It does not invent targeting, mitigation or revival rules. Existing raw discrepancy measurements remain available alongside this alternative reconciliation.

## What this changes in accuracy claims

It prevents a recoverable accounting difference from being treated as missing hero damage or used to inflate scoring weights. It does **not** improve the measured per-hero reconstruction by itself: the current offense proxy still has about **25.1% fitted weighted absolute error** on this battle, and future-battle accuracy remains unmeasured. No global weight changes were justified by this reconciliation.

- [Health reconciliation data](../../outputs/hero-report/Health-Balance-Reconciliation.json)
- [Measurement report](../../outputs/hero-report/Simulation-Measurement-Report.json)
- [Per-hero retrospective reconstruction](RETROSPECTIVE-RECONSTRUCTION-2026-11-07.md)
- [Replay authority audit](../../outputs/hero-report/Replay-Authority-Audit.json)
