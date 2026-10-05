from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from decode_cfg import decode_table
from decode_language_pack import DEFAULT_LANGUAGE_PACK, decode_language_pack


TABLE_FILES = {
    "heroes": "1824_survivor.cfg",
    "levels": "1853_survivor_level_main.cfg",
    "skill_levels": "1874_survivor_skill_main.cfg",
    "skill_types": "1876_survivor_skill_type.cfg",
    "benefits": "0754_benefits.cfg",
    "release_control": "1170_hero_control_server.cfg",
    "recruit": "1872_survivor_recuit.cfg",
    "iap_daily": "1197_iap_daily_recharge.cfg",
    "iap_packages": "1225_iap_package.cfg",
    "turntable": "0487_activity_turntable.cfg",
    "drops": "0984_drop_main.cfg",
}

FACTIONS = {1: "Mountain", 2: "Wasteland", 3: "Sky", 4: "Sea"}
ROLES = {"zealots": "Melee", "assault": "Mid", "sniper": "Range"}
RARITIES = {2: "R", 3: "SR", 4: "SSR"}

# Names visible in the English UI differ from a few internal asset IDs.  Keep the
# internal ID in every export so the mapping remains auditable.
DISPLAY_NAMES = {
    "ken": "Chef",
    "tim": "Ghost",
    "tithi": "Kiki",
}

BENEFIT_IDS = {
    "march_capacity": 300332,
    "attack": 301825,
    "defense": 301826,
    "health": 301827,
}


def base_slug(row: dict[str, Any]) -> str:
    return row["Id"].removeprefix("survivor_")


def is_base_playable(row: dict[str, Any]) -> bool:
    identifier = row.get("Id", "")
    return (
        identifier.startswith("survivor_")
        and "monster" not in identifier
        and not identifier.endswith("_orange")
        and identifier not in {"survivor_chief_female", "survivor_chief_male"}
        and row.get("Faction") in FACTIONS
        and bool(row.get("SkillConfig"))
    )


def rows(table: dict[str, Any]) -> list[dict[str, Any]]:
    return table["rows"]


def benefit_map(items: list[dict[str, Any]]) -> dict[int, float]:
    return {item["benefit_id"]: float(item["benefit_value"]) for item in items}


def contains_item(items: list[dict[str, Any]], wanted: set[int]) -> bool:
    return any(item.get("i_id") in wanted for item in items)


def minmax(values: list[float], value: float) -> float:
    low, high = min(values), max(values)
    return 1.0 if math.isclose(low, high) else (value - low) / (high - low)


def markdown_table(headers: list[str], body: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in body)
    return "\n".join(lines)


def clean_game_text(value: str) -> str:
    return re.sub(r"</?color(?:=[^>]+)?>", "", value).strip()


def build(source: Path, language_pack: Path | None = DEFAULT_LANGUAGE_PACK) -> list[dict[str, Any]]:
    decoded = {}
    for name, filename in TABLE_FILES.items():
        table_name = filename.split('_', 1)[1]
        matches = [path for path in source.glob('*.cfg') if path.name.partition('_')[0].isdigit() and path.name.partition('_')[2] == table_name]
        if len(matches) != 1:
            raise ValueError(f"Expected one {table_name}, found {len(matches)}")
        decoded[name] = decode_table(matches[0])
    localized = decode_language_pack(language_pack) if language_pack and language_pack.exists() else {}

    benefit_names = {
        row["InternalId"]: row["Id"] for row in rows(decoded["benefits"])
    }
    levels_by_hero: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows(decoded["levels"]):
        levels_by_hero[row["SurvivorType"]].append(row)

    skill_types = {row["InternalId"]: row for row in rows(decoded["skill_types"])}
    skill_levels: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows(decoded["skill_levels"]):
        skill_levels[row["SkillType"]].append(row)

    controls: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows(decoded["release_control"]):
        controls[row["HeroId"]].append(row)

    recruit_rows = rows(decoded["recruit"])
    daily_rows = rows(decoded["iap_daily"])
    package_rows = rows(decoded["iap_packages"])
    turntable_rows = rows(decoded["turntable"])
    drop_item_ids = {row["ItemId"] for row in rows(decoded["drops"])}

    result: list[dict[str, Any]] = []
    for hero in filter(is_base_playable, rows(decoded["heroes"])):
        hero_id = hero["InternalId"]
        slug = base_slug(hero)
        hero_levels = levels_by_hero[hero_id]
        chip_ids = {int(item_id) for item_id in hero.get("ChipNumber", {})}
        recruitable = any(
            bool(chip_ids.intersection(row["ChestNormalPreview"] + row["ChestRarePerview"]))
            for row in recruit_rows
        )
        turntable = any(contains_item(row.get("RewardItem", []), chip_ids) for row in turntable_rows)
        iap_daily = any(
            contains_item(row.get("Rewards", []), chip_ids)
            or contains_item(row.get("RewardsDisplay", []), chip_ids)
            for row in daily_rows
        )
        iap_package = any(contains_item(row.get("RewardItem", []), chip_ids) for row in package_rows)
        generic_drop = bool(chip_ids.intersection(drop_item_ids))
        direct_iap = hero.get("HeroCompletionIap") is not None
        if recruitable:
            acquisition_class = "f2p_confirmed"
            acquisition_label = "Recruitable (F2P confirmed)"
            acquisition_confidence = "high"
        elif turntable:
            acquisition_class = "event_mixed"
            acquisition_label = "Event/turntable + paid acceleration"
            acquisition_confidence = "medium"
        elif direct_iap or iap_daily or iap_package:
            acquisition_class = "iap_linked"
            acquisition_label = "IAP-linked; free route unconfirmed"
            acquisition_confidence = "medium"
        else:
            acquisition_class = "unknown"
            acquisition_label = "Acquisition route unknown"
            acquisition_confidence = "low"
        max_level = max(hero_levels, key=lambda row: row["Level"])
        base_benefits = benefit_map(max_level["BenefitsTroops"])

        skills = []
        damage_coefficients = []
        for skill_id_text in hero["SkillConfig"]:
            skill_id = int(skill_id_text)
            skill_type = skill_types.get(skill_id)
            if not skill_type:
                continue
            configured_levels = skill_levels.get(skill_id, [])
            max_skill = max(configured_levels, key=lambda row: row["Level"]) if configured_levels else None
            damage_params = [float(value) for value in skill_type.get("DamageParam", [])]
            if not skill_type.get("NormalAttack") and damage_params:
                damage_coefficients.append(damage_params[0])
            overall = []
            if max_skill:
                for item in max_skill.get("OverallBenefit", []):
                    benefit_id = item["benefit_id"]
                    overall.append({
                        "id": benefit_id,
                        "name": benefit_names.get(benefit_id, f"benefit_{benefit_id}"),
                        "value": float(item["benefit_value"]),
                    })
            skills.append({
                "id": skill_id,
                "internal_name": skill_type["Id"],
                "display_name": clean_game_text(localized.get(skill_type.get("Name", ""), "")),
                "game_description": clean_game_text(localized.get(skill_type.get("DescriptionSquad", ""), "")),
                "name_key": skill_type.get("Name", ""),
                "description_key": skill_type.get("DescriptionSquad", ""),
                "icon_asset": skill_type.get("Icon", ""),
                "slot": skill_type["SkillNo"],
                "normal_attack": bool(skill_type["NormalAttack"]),
                "damage_ratio": float(skill_type["DamageRatio"]),
                "damage_params": damage_params,
                "skill_value": skill_type["SkillValue"],
                "classification": skill_type.get("SkillClassification", 0),
                "effect_type": skill_type.get("EffectType", 0),
                "effect_description_key": skill_type.get("SkillEffectTypeDesc", ""),
                "squad_parameter_map": skill_type.get("ParamSquad", ""),
                "raid_level_parameters": max_skill.get("RaidSkillParam_1", []) if max_skill else [],
                "configured_max_level": max_skill["Level"] if max_skill else None,
                "max_level_overall_benefits": overall,
            })

        release_rows = controls.get(hero_id, [])
        weeks = [row["GroupWeek"] for row in release_rows]
        display_name = DISPLAY_NAMES.get(slug, slug.replace("_", " ").title())
        result.append({
            "name": display_name,
            "asset_slug": slug,
            "hero_id": hero_id,
            "faction": FACTIONS[hero["Faction"]],
            "role": ROLES.get(hero["Profession"], hero["Profession"]),
            "rarity": RARITIES.get(hero["Rarity"], f'Code {hero["Rarity"]}'),
            "rarity_code": hero["Rarity"],
            "hero_generation": hero.get("HeroGen", ""),
            "real_generation": hero.get("SurvivorRealGeneration", 0),
            "client_version": hero.get("ClientVersion", ""),
            "minimum_server_version": hero.get("MinServerVersion", ""),
            "display_priority": hero.get("Priority", 0),
            "portrait_asset": hero.get("ImageBig", ""),
            "small_portrait_asset": hero.get("ImageSmall", ""),
            "ascension_hero_id": hero.get("SurvivorRarityUp"),
            "has_ascension": hero.get("SurvivorRarityUp") is not None,
            "acquisition_class": acquisition_class,
            "acquisition_label": acquisition_label,
            "acquisition_confidence": acquisition_confidence,
            "recruit_pool": recruitable,
            "turntable_event": turntable,
            "iap_linked": direct_iap or iap_daily or iap_package,
            "generic_drop_table": generic_drop,
            "release_week_min": min(weeks) if weeks else None,
            "release_week_max": max(weeks) if weeks else None,
            "release_rule_count": len(release_rows),
            "max_level": max_level["Level"],
            "max_level_battle_power": max_level["BattlePower"],
            "max_level_attack": base_benefits.get(BENEFIT_IDS["attack"], 0.0),
            "max_level_defense": base_benefits.get(BENEFIT_IDS["defense"], 0.0),
            "max_level_health": base_benefits.get(BENEFIT_IDS["health"], 0.0),
            "max_level_march_capacity": base_benefits.get(BENEFIT_IDS["march_capacity"], 0.0),
            "best_non_basic_damage_coefficient": max(damage_coefficients, default=0.0),
            "skills": skills,
        })

    # These are transparent comparative indices, not simulated tier-list scores.
    attack_values = [row["max_level_attack"] for row in result]
    defense_values = [row["max_level_defense"] for row in result]
    health_values = [row["max_level_health"] for row in result]
    power_values = [row["max_level_battle_power"] for row in result]
    coefficient_values = [row["best_non_basic_damage_coefficient"] for row in result]
    for row in result:
        offense = (
            minmax(attack_values, row["max_level_attack"]) * 0.65
            + minmax(coefficient_values, row["best_non_basic_damage_coefficient"]) * 0.35
        )
        durability = (
            minmax(health_values, row["max_level_health"]) * 0.70
            + minmax(defense_values, row["max_level_defense"]) * 0.30
        )
        composite = (
            minmax(power_values, row["max_level_battle_power"]) * 0.40
            + offense * 0.35
            + durability * 0.25
        )
        row["offense_index"] = round(offense * 100, 2)
        row["durability_index"] = round(durability * 100, 2)
        row["composite_index"] = round(composite * 100, 2)

    for field, rank_field in (
        ("offense_index", "offense_rank"),
        ("durability_index", "durability_rank"),
        ("composite_index", "composite_rank"),
    ):
        ordered = sorted(result, key=lambda row: (-row[field], row["name"]))
        previous_value = None
        shared_rank = 0
        for position, row in enumerate(ordered, 1):
            if previous_value is None or row[field] != previous_value:
                shared_rank = position
            row[rank_field] = shared_rank
            previous_value = row[field]
    return sorted(result, key=lambda row: row["composite_rank"])


def write_outputs(heroes: list[dict[str, Any]], output: Path, client_version: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "TilesSurvive-Hero-Data.json"
    csv_path = output / "TilesSurvive-Hero-Ranking.csv"
    report_path = output / "TilesSurvive-Hero-Report.md"
    json_path.write_text(json.dumps(heroes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    csv_fields = [field for field in heroes[0] if field != "skills"]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        writer.writerows({field: row[field] for field in csv_fields} for row in heroes)

    ranking_rows = []
    for hero in heroes:
        week = (
            "-"
            if hero["release_week_min"] is None
            else str(hero["release_week_min"])
            if hero["release_week_min"] == hero["release_week_max"]
            else f'{hero["release_week_min"]}-{hero["release_week_max"]}'
        )
        ranking_rows.append([
            hero["composite_rank"], hero["name"], hero["faction"], hero["role"],
            hero["rarity"], hero["composite_index"], hero["offense_rank"],
            hero["durability_rank"], week, hero["client_version"] or "-",
        ])

    future = sorted(
        [hero for hero in heroes if hero["client_version"] or hero["release_week_min"]],
        key=lambda row: (row["release_week_min"] is None, row["release_week_min"] or 999, row["name"]),
    )
    future_rows = []
    for hero in future:
        week = "-" if hero["release_week_min"] is None else (
            str(hero["release_week_min"])
            if hero["release_week_min"] == hero["release_week_max"]
            else f'{hero["release_week_min"]}-{hero["release_week_max"]}'
        )
        future_rows.append([
            hero["name"], hero["asset_slug"], hero["faction"], hero["role"],
            week, hero["client_version"] or "-", hero["minimum_server_version"] or "-",
            hero["composite_rank"],
        ])

    acquisition_rows = [[
        hero["name"], hero["acquisition_label"], hero["acquisition_confidence"],
        "yes" if hero["recruit_pool"] else "no",
        "yes" if hero["turntable_event"] else "no",
        "yes" if hero["iap_linked"] else "no",
    ] for hero in sorted(heroes, key=lambda row: (row["acquisition_class"], row["name"]))]

    report = f"""# Tiles Survive hero asset report

Source: local installed client configuration pack, client `{client_version}`.

This report contains {len(heroes)} independently playable base heroes. Chief avatars, monsters, and six `_orange` awakening/rarity-up replacement records are excluded from the ranking. Account power is intentionally not used as a release or identity key because it changes frequently. Rarity labels use the verified in-game mapping: code 4 is SSR, 3 is SR, and 2 is R.

## Important limits

The ranking is a reproducible **configuration comparison**, not a combat simulation or a claim about the live meta. It excludes team synergy, targeting, crowd control, healing, exclusive gear, awakening replacements, mode-specific AI, and any server-side balance override. A hero with a low offense index may be an excellent support.

The composite index uses max-level values from this client: 40% configured battle power, 35% offense, and 25% durability. Offense is 65% hero attack and 35% the largest non-basic `DamageParam[0]`; durability is 70% health and 30% defense. Every input is min-max normalized across the extracted roster. Ties are left visible rather than broken with invented precision.

## Configuration ranking

{markdown_table(["#", "Hero", "Faction", "Role", "Rarity", "Index", "Off. #", "Dur. #", "Server week", "Client gate"], ranking_rows)}

## Release-planning signals

`Server week` is the min-max `GroupWeek` found in `hero_control_server`; it varies by server group. `Client gate` and `minimum server` are copied verbatim from the hero record. A configured future week means the client contains a rollout rule, but does not prove the publisher will release it unchanged.

{markdown_table(["Hero", "Asset ID", "Faction", "Role", "Server week", "Client gate", "Minimum server", "Rank"], future_rows)}

## Acquisition evidence

`F2P confirmed` means the hero's chip appears in the normal or rare recruitment preview. `Event/turntable + paid acceleration` means both event rewards and IAP offers reference the chip; it is not proof of a paid-only hero. The client does not provide enough evidence to label any hero paid-only with confidence.

{markdown_table(["Hero", "Classification", "Confidence", "Recruit", "Event", "IAP"], acquisition_rows)}

## Files

- `TilesSurvive-Hero-Data.json`: complete extracted hero records plus skill coefficients and max-level skill benefits.
- `TilesSurvive-Hero-Ranking.csv`: spreadsheet-friendly summary.
- This Markdown report: human-readable overview and methodology.
"""
    report_path.write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a hero roster and ranking from extracted CFG tables")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(__file__).resolve().parent / "generated-v2",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "outputs" / "hero-report",
    )
    parser.add_argument("--client-version", default="2.6.0.235")
    parser.add_argument("--language-pack", type=Path, default=DEFAULT_LANGUAGE_PACK)
    args = parser.parse_args()
    heroes = build(args.source, args.language_pack)
    write_outputs(heroes, args.output, args.client_version)
    print(f"heroes={len(heroes)} output={args.output}")


if __name__ == "__main__":
    main()
