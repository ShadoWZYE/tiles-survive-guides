# Tiles Survive hero asset report

Source: local installed client configuration pack, client `2.6.200.276`.

This report contains 29 independently playable base heroes. Chief avatars, monsters, and six `_orange` awakening/rarity-up replacement records are excluded from the ranking. Account power is intentionally not used as a release or identity key because it changes frequently. Rarity labels use the verified in-game mapping: code 4 is SSR, 3 is SR, and 2 is R.

## Important limits

The ranking is a reproducible **configuration comparison**, not a combat simulation or a claim about the live meta. It excludes team synergy, targeting, crowd control, healing, exclusive gear, awakening replacements, mode-specific AI, and any server-side balance override. A hero with a low offense index may be an excellent support.

The composite index uses max-level values from this client: 40% configured battle power, 35% offense, and 25% durability. Offense is the normalized hero ATK stat only; durability is 70% health and 30% defense. The offline native audit invalidated the old display-DamageParam proxy, which has been removed. These weights remain planning heuristics, not game combat formulas. Every input is min-max normalized across the extracted roster. Ties are left visible rather than broken with invented precision.

## Configuration ranking

| # | Hero | Faction | Role | Rarity | Index | Off. # | Dur. # | Server week | Client gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Tony | Sky | Melee | SSR | 100.0 | 1 | 1 | 22-24 | - |
| 1 | Maddie | Sky | Range | SSR | 100.0 | 1 | 1 | - | - |
| 1 | Rosie | Mountain | Melee | SSR | 100.0 | 1 | 1 | - | - |
| 1 | Nikola | Mountain | Melee | SSR | 100.0 | 1 | 1 | 6-8 | - |
| 1 | Ray | Mountain | Range | SSR | 100.0 | 1 | 1 | - | - |
| 1 | Becca | Wasteland | Range | SSR | 100.0 | 1 | 1 | 4-5 | 1.13.0 |
| 1 | Layla | Wasteland | Mid | SSR | 100.0 | 1 | 1 | 2-3 | - |
| 1 | Candy | Wasteland | Mid | SSR | 100.0 | 1 | 1 | 12-14 | 1.8.70 |
| 1 | Mike | Sky | Melee | SSR | 100.0 | 1 | 1 | 24-26 | - |
| 1 | Wright | Sky | Mid | SSR | 100.0 | 1 | 1 | 20-22 | - |
| 1 | Kiki | Sky | Range | SSR | 100.0 | 1 | 1 | 18-20 | - |
| 1 | Tara | Mountain | Mid | SSR | 100.0 | 1 | 1 | 10-12 | - |
| 1 | Jacob | Wasteland | Melee | SSR | 100.0 | 1 | 1 | 14-16 | - |
| 1 | Tarzan | Mountain | Melee | SSR | 100.0 | 1 | 1 | 8-10 | - |
| 1 | Chiron | Wasteland | Mid | SSR | 100.0 | 1 | 1 | 16-18 | - |
| 1 | Shark | Sea | Melee | SSR | 100.0 | 1 | 1 | 26-28 | 2.3.800 |
| 1 | Ragnar | Sea | Melee | SSR | 100.0 | 1 | 1 | 28-30 | 2.4.000 |
| 1 | Knotty | Sea | Range | SSR | 100.0 | 1 | 1 | 30-32 | 2.4.200 |
| 1 | Undine | Sea | Mid | SSR | 100.0 | 1 | 1 | 32-34 | 2.4.500 |
| 1 | Dave | Sea | Mid | SSR | 100.0 | 1 | 1 | 34-36 | 2.5.500 |
| 1 | Lava | Mountain | Melee | SSR | 100.0 | 1 | 1 | 36-38 | 2.6.200 |
| 22 | Lucky | Sky | Range | SR | 60.47 | 22 | 22 | - | - |
| 22 | Sarge | Sky | Range | SR | 60.47 | 22 | 22 | - | - |
| 22 | Chef | Mountain | Melee | SR | 60.47 | 22 | 22 | - | - |
| 22 | Freja | Mountain | Mid | SR | 60.47 | 22 | 22 | - | - |
| 22 | Travis | Wasteland | Mid | SR | 60.47 | 22 | 22 | - | - |
| 22 | Eva | Wasteland | Melee | SR | 60.47 | 22 | 22 | - | - |
| 28 | Rusty | Mountain | Melee | R | 0.0 | 28 | 28 | - | - |
| 28 | Ghost | Wasteland | Mid | R | 0.0 | 28 | 28 | - | - |

## Release-planning signals

`Server week` is the min-max `GroupWeek` found in `hero_control_server`; it varies by server group. `Client gate` and `minimum server` are copied verbatim from the hero record. A configured future week means the client contains a rollout rule, but does not prove the publisher will release it unchanged.

| Hero | Asset ID | Faction | Role | Server week | Client gate | Minimum server | Rank |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Layla | layla | Wasteland | Mid | 2-3 | - | - | 1 |
| Becca | becca | Wasteland | Range | 4-5 | 1.13.0 | - | 1 |
| Nikola | nikola | Mountain | Melee | 6-8 | - | - | 1 |
| Tarzan | tarzan | Mountain | Melee | 8-10 | - | 2.2.800 | 1 |
| Tara | tara | Mountain | Mid | 10-12 | - | - | 1 |
| Candy | candy | Wasteland | Mid | 12-14 | 1.8.70 | - | 1 |
| Jacob | jacob | Wasteland | Melee | 14-16 | - | - | 1 |
| Chiron | chiron | Wasteland | Mid | 16-18 | - | 2.2.800 | 1 |
| Kiki | tithi | Sky | Range | 18-20 | - | - | 1 |
| Wright | wright | Sky | Mid | 20-22 | - | - | 1 |
| Tony | tony | Sky | Melee | 22-24 | - | - | 1 |
| Mike | mike | Sky | Melee | 24-26 | - | - | 1 |
| Shark | shark | Sea | Melee | 26-28 | 2.3.800 | 2.3.800 | 1 |
| Ragnar | ragnar | Sea | Melee | 28-30 | 2.4.000 | 2.4.000 | 1 |
| Knotty | knotty | Sea | Range | 30-32 | 2.4.200 | 2.4.200 | 1 |
| Undine | undine | Sea | Mid | 32-34 | 2.4.500 | - | 1 |
| Dave | dave | Sea | Mid | 34-36 | 2.5.500 | - | 1 |
| Lava | lava | Mountain | Melee | 36-38 | 2.6.200 | 2.6.200 | 1 |

## Acquisition evidence

`F2P confirmed` means the hero's chip appears in the normal or rare recruitment preview. `Event/turntable + paid acceleration` means both event rewards and IAP offers reference the chip; it is not proof of a paid-only hero. The client does not provide enough evidence to label any hero paid-only with confidence.

| Hero | Classification | Confidence | Recruit | Event | IAP |
| --- | --- | --- | --- | --- | --- |
| Becca | Event/turntable + paid acceleration | medium | no | yes | yes |
| Chiron | Event/turntable + paid acceleration | medium | no | yes | yes |
| Dave | Event/turntable + paid acceleration | medium | no | yes | yes |
| Jacob | Event/turntable + paid acceleration | medium | no | yes | yes |
| Kiki | Event/turntable + paid acceleration | medium | no | yes | yes |
| Knotty | Event/turntable + paid acceleration | medium | no | yes | yes |
| Ragnar | Event/turntable + paid acceleration | medium | no | yes | yes |
| Ray | Event/turntable + paid acceleration | medium | no | yes | yes |
| Shark | Event/turntable + paid acceleration | medium | no | yes | yes |
| Tara | Event/turntable + paid acceleration | medium | no | yes | yes |
| Tarzan | Event/turntable + paid acceleration | medium | no | yes | yes |
| Undine | Event/turntable + paid acceleration | medium | no | yes | yes |
| Wright | Event/turntable + paid acceleration | medium | no | yes | yes |
| Candy | Recruitable (F2P confirmed) | high | yes | yes | yes |
| Chef | Recruitable (F2P confirmed) | high | yes | no | no |
| Eva | Recruitable (F2P confirmed) | high | yes | no | no |
| Freja | Recruitable (F2P confirmed) | high | yes | no | no |
| Ghost | Recruitable (F2P confirmed) | high | yes | no | no |
| Layla | Recruitable (F2P confirmed) | high | yes | yes | yes |
| Maddie | Recruitable (F2P confirmed) | high | yes | yes | yes |
| Mike | Recruitable (F2P confirmed) | high | yes | yes | yes |
| Nikola | Recruitable (F2P confirmed) | high | yes | yes | yes |
| Rosie | Recruitable (F2P confirmed) | high | yes | no | yes |
| Rusty | Recruitable (F2P confirmed) | high | yes | no | no |
| Sarge | Recruitable (F2P confirmed) | high | yes | no | no |
| Tony | Recruitable (F2P confirmed) | high | yes | yes | yes |
| Travis | Recruitable (F2P confirmed) | high | yes | no | no |
| Lava | IAP-linked; free route unconfirmed | medium | no | no | yes |
| Lucky | Acquisition route unknown | low | no | no | no |

## Files

- `TilesSurvive-Hero-Data.json`: complete extracted hero records plus skill coefficients and max-level skill benefits.
- `TilesSurvive-Hero-Ranking.csv`: spreadsheet-friendly summary.
- This Markdown report: human-readable overview and methodology.
