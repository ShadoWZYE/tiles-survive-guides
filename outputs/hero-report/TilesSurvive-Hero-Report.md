# Tiles Survive hero asset report

Source: local installed client configuration pack, client `2.6.0.235`.

This report contains 28 independently playable base heroes. Chief avatars, monsters, and six `_orange` awakening/rarity-up replacement records are excluded from the ranking. Account power is intentionally not used as a release or identity key because it changes frequently. Rarity labels use the verified in-game mapping: code 4 is SSR, 3 is SR, and 2 is R.

## Important limits

The ranking is a reproducible **configuration comparison**, not a combat simulation or a claim about the live meta. It excludes team synergy, targeting, crowd control, healing, exclusive gear, awakening replacements, mode-specific AI, and any server-side balance override. A hero with a low offense index may be an excellent support.

The composite index uses max-level values from this client: 40% configured battle power, 35% offense, and 25% durability. Offense is 65% hero attack and 35% the largest non-basic `DamageParam[0]`; durability is 70% health and 30% defense. Every input is min-max normalized across the extracted roster. Ties are left visible rather than broken with invented precision.

## Configuration ranking

| # | Hero | Faction | Role | Rarity | Index | Off. # | Dur. # | Server week | Client gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Dave | Sea | Mid | SSR | 100.0 | 1 | 1 | 34-36 | 2.5.500 |
| 2 | Knotty | Sea | Range | SSR | 94.26 | 2 | 1 | 30-32 | 2.4.200 |
| 3 | Tony | Sky | Melee | SSR | 90.93 | 3 | 1 | 22-24 | - |
| 3 | Nikola | Mountain | Melee | SSR | 90.93 | 3 | 1 | 6-8 | - |
| 3 | Becca | Wasteland | Range | SSR | 90.93 | 3 | 1 | 4-5 | 1.13.0 |
| 3 | Wright | Sky | Mid | SSR | 90.93 | 3 | 1 | 20-22 | - |
| 3 | Kiki | Sky | Range | SSR | 90.93 | 3 | 1 | 18-20 | - |
| 3 | Tara | Mountain | Mid | SSR | 90.93 | 3 | 1 | 10-12 | - |
| 3 | Jacob | Wasteland | Melee | SSR | 90.93 | 3 | 1 | 14-16 | - |
| 3 | Tarzan | Mountain | Melee | SSR | 90.93 | 3 | 1 | 8-10 | - |
| 3 | Chiron | Wasteland | Mid | SSR | 90.93 | 3 | 1 | 16-18 | - |
| 3 | Undine | Sea | Mid | SSR | 90.93 | 3 | 1 | 32-34 | 2.4.500 |
| 13 | Ray | Mountain | Range | SSR | 90.39 | 13 | 1 | - | - |
| 14 | Shark | Sea | Melee | SSR | 89.12 | 14 | 1 | 26-28 | 2.3.800 |
| 14 | Ragnar | Sea | Melee | SSR | 89.12 | 14 | 1 | 28-30 | 2.4.000 |
| 16 | Maddie | Sky | Range | SSR | 88.21 | 16 | 1 | - | - |
| 16 | Rosie | Mountain | Melee | SSR | 88.21 | 16 | 1 | - | - |
| 16 | Layla | Wasteland | Mid | SSR | 88.21 | 16 | 1 | 2-3 | - |
| 16 | Candy | Wasteland | Mid | SSR | 88.21 | 16 | 1 | 12-14 | 1.8.70 |
| 16 | Mike | Sky | Melee | SSR | 88.21 | 16 | 1 | 24-26 | - |
| 21 | Lucky | Sky | Range | SR | 55.32 | 21 | 21 | - | - |
| 21 | Sarge | Sky | Range | SR | 55.32 | 21 | 21 | - | - |
| 21 | Freja | Mountain | Mid | SR | 55.32 | 21 | 21 | - | - |
| 21 | Travis | Wasteland | Mid | SR | 55.32 | 21 | 21 | - | - |
| 21 | Eva | Wasteland | Melee | SR | 55.32 | 21 | 21 | - | - |
| 26 | Chef | Mountain | Melee | SR | 53.06 | 26 | 21 | - | - |
| 27 | Rusty | Mountain | Melee | R | 0.84 | 27 | 27 | - | - |
| 27 | Ghost | Wasteland | Mid | R | 0.84 | 27 | 27 | - | - |

## Release-planning signals

`Server week` is the min-max `GroupWeek` found in `hero_control_server`; it varies by server group. `Client gate` and `minimum server` are copied verbatim from the hero record. A configured future week means the client contains a rollout rule, but does not prove the publisher will release it unchanged.

| Hero | Asset ID | Faction | Role | Server week | Client gate | Minimum server | Rank |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Layla | layla | Wasteland | Mid | 2-3 | - | - | 16 |
| Becca | becca | Wasteland | Range | 4-5 | 1.13.0 | - | 3 |
| Nikola | nikola | Mountain | Melee | 6-8 | - | - | 3 |
| Tarzan | tarzan | Mountain | Melee | 8-10 | - | 2.2.800 | 3 |
| Tara | tara | Mountain | Mid | 10-12 | - | - | 3 |
| Candy | candy | Wasteland | Mid | 12-14 | 1.8.70 | - | 16 |
| Jacob | jacob | Wasteland | Melee | 14-16 | - | - | 3 |
| Chiron | chiron | Wasteland | Mid | 16-18 | - | 2.2.800 | 3 |
| Kiki | tithi | Sky | Range | 18-20 | - | - | 3 |
| Wright | wright | Sky | Mid | 20-22 | - | - | 3 |
| Tony | tony | Sky | Melee | 22-24 | - | - | 3 |
| Mike | mike | Sky | Melee | 24-26 | - | - | 16 |
| Shark | shark | Sea | Melee | 26-28 | 2.3.800 | 2.3.800 | 14 |
| Ragnar | ragnar | Sea | Melee | 28-30 | 2.4.000 | 2.4.000 | 14 |
| Knotty | knotty | Sea | Range | 30-32 | 2.4.200 | 2.4.200 | 2 |
| Undine | undine | Sea | Mid | 32-34 | 2.4.500 | - | 3 |
| Dave | dave | Sea | Mid | 34-36 | 2.5.500 | - | 1 |

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
| Lucky | Acquisition route unknown | low | no | no | no |

## Files

- `TilesSurvive-Hero-Data.json`: complete extracted hero records plus skill coefficients and max-level skill benefits.
- `TilesSurvive-Hero-Ranking.csv`: spreadsheet-friendly summary.
- This Markdown report: human-readable overview and methodology.
