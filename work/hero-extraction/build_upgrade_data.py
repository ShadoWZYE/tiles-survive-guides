"""Export only planner progression data; raw tables and paths stay private."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from decode_cfg import decode_table
from decode_language_pack import decode_language_pack, DEFAULT_LANGUAGE_PACK

ROOT = Path(__file__).resolve().parents[2]
STAT_IDS = (301825, 301826, 301827)

def stats(values):
    lookup = {v["benefit_id"]: v["benefit_value"] for v in values}
    return [float(lookup.get(i, 0)) for i in STAT_IDS]

def export(source: Path, roster: list, version: str, localized: dict) -> dict:
    files = {}
    def table(name):
        matches = [path for path in source.glob('*.cfg') if path.name.partition('_')[0].isdigit() and path.name.partition('_')[2] == name + '.cfg']
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one {name} table, found {len(matches)}")
        files[name] = hashlib.sha256(matches[0].read_bytes()).hexdigest()
        return decode_table(matches[0])["rows"]
    heroes = {r["InternalId"]: r for r in table("survivor")}
    ranks, levels = table("survivor_rank_main"), table("survivor_level_main")
    xp = table("survivor_level")
    skill_types = {r["InternalId"]: r for r in table("survivor_skill_type")}
    skill_levels = table("survivor_skill_main")
    timelines = {r["InternalId"]: r for r in table("pve_new_skill")}
    gear_types, gear_levels = table("survivor_equipment_npp"), table("survivor_equipment_level_npp")
    items = {str(r["InternalId"]): localized.get(r["Name"], r["Name"] or r["Id"]) for r in table("itemlist")}
    result = {}
    for entry in roster:
        hero_id = entry["hero_id"]
        hero = heroes[hero_id]  # Refuse mismatched identities rather than a name-based guess.
        costs = {r["Level"]: r for r in xp if r["Rarity"] == hero["Rarity"]}
        stages = []
        for r in sorted((r for r in ranks if r["SurvivorType"] == hero_id), key=lambda r: (r["Rank"], r["RankSmall"])):
            stages.append({"id": r["Id"], "rank": r["Rank"], "step": r["RankSmall"],
                           "cost": r["ItemReqNew"], "stats": stats(r["BenefitTroop"]), "power": r["BattlePower"],
                           "skill_caps": r["SkillLevelMax"], "unlocks": r["UnlockSkills"],
                           "level_required": r["SurvivorLevelReq"], "level_max": r["SurvivorLevelMax"],
                           "building_required": r["BuildingReq"]})
        hero_levels = []
        for r in sorted((r for r in levels if r["SurvivorType"] == hero_id), key=lambda r: r["Level"]):
            c = costs.get(r["Level"], {})
            hero_levels.append({"level": r["Level"], "stats": stats(r["BenefitsTroops"]), "power": r["BattlePower"],
                                "xp_total": c.get("ExpNew"), "building_gate": c.get("NextLevelBuildingCondition")})
        skills = []
        for skill_id in hero["SkillConfig"]:
            s = skill_types[int(skill_id)]
            timeline = timelines.get(s["RaidNewSkill"], {})
            skills.append({"id": s["Id"], "slot": s["SkillNo"], "name": localized.get(s["Name"], s["Id"]),
                           "description": localized.get(s["DescriptionSquad"], ""),
                           "damage_ratio": s["DamageRatio"], "damage_params": s["DamageParam"],
                           "cooldown": timeline.get("Cooldown", 0), "first_cast": timeline.get("PreCooldown", 0),
                           "conditional": bool(timeline.get("Condition")),
                           "effect_type": s["EffectType"], "subskills": bool(timeline.get("SubSkill")),
                           "levels": [{"level": r["Level"], "cost": r["SlgItemReq"],
                                       "power": r["BattlePower"], "params": r["RaidSkillParam_1"],
                                       "overall": r["OverallBenefit"]}
                                      for r in sorted((r for r in skill_levels if r["SkillType"] == s["InternalId"]), key=lambda r: r["Level"])]})
        if len({s["id"] for s in stages}) != len(stages) or not stages or not hero_levels:
            raise ValueError(f"Invalid progression for {entry['name']}")
        result[entry["asset_slug"]] = {"id": hero_id, "name": entry["name"], "stages": stages, "levels": hero_levels, "skills": skills}
    gear = {}
    for r in gear_types:
        if r["Arms"] != 0:  # No unverified profession compatibility conversion.
            continue
        rows = sorted((g for g in gear_levels if g["SurvivorEquipmentId"] == r["InternalId"]), key=lambda g: g["Level"])
        if not rows:
            continue
        gear[r["Id"]] = {"name": localized.get(r["EquipmentName"], r["Id"]), "slot": r["Part"], "quality": r["Quality"],
                         "hero_level_required": r["SurvivorLevel"],
                         "levels": [{"level": g["Level"], "stats": stats(g["BenefitSlg"]), "power": g["Power"], "xp_next": g["ExpNeed"]} for g in rows]}
    used_items = {key for hero in result.values() for stage in hero["stages"] for key in stage["cost"]}
    used_items.update(key for hero in result.values() for skill in hero["skills"] for level in skill["levels"] for key in level["cost"])
    return {"schema": 1, "client_build": version, "source_hashes": files, "heroes": result, "gear": gear,
            "items": {**{key: items.get(key, key) for key in sorted(used_items)}, "hero-xp": "Hero XP", "gear-xp": "Gear XP"},
            "model_notes": "BenefitTroop + BenefitsTroops + recorded BenefitSlg gear. Rank costs use destination ItemReqNew; skill costs use destination SlgItemReq. Direct-output estimates use affine DamageParam growth and configured cooldowns; runtime formula/animation semantics are not verified. Not a win-rate or live damage simulator."}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--client-build", required=True)
    parser.add_argument("--language", type=Path, default=DEFAULT_LANGUAGE_PACK)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/hero-report/TilesSurvive-Upgrade-Data.json")
    parser.add_argument("--targeted-source", type=Path, help="Private extracted Targeted Draft tables")
    args = parser.parse_args()
    roster = json.loads((ROOT / "outputs/hero-report/TilesSurvive-Hero-Data.json").read_text(encoding="utf-8"))
    localized = decode_language_pack(args.language) if args.language.exists() else {}
    data = export(args.source, roster, args.client_build, localized)
    if args.targeted_source:
        data["targeted_draft"] = export_targeted(args.targeted_source, args.source, roster, data["source_hashes"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Exported {len(data['heroes'])} heroes, {len(data['gear'])} universal gear types; {args.output.stat().st_size:,} bytes")

def export_targeted(source, hero_source, roster, hashes):
    def rows(name):
        paths = list(source.glob(f"*_{name}.cfg"))
        if len(paths) != 1:
            raise ValueError(f"Expected one {name} table")
        hashes[name] = hashlib.sha256(paths[0].read_bytes()).hexdigest()
        return decode_table(paths[0])["rows"]
    items = {r["InternalId"]: r for r in rows("itemlist")}
    contrasts = {r["InternalId"]: r for r in rows("survival_up_drop_contrast")}
    up = {r["InternalId"]: r for r in rows("survival_up_card_pool")}
    survivor_rows = decode_table(next(hero_source.glob("*_survivor.cfg")))["rows"]
    names = {r["InternalId"]: r["Id"] for r in survivor_rows}
    by_internal = {names[r["hero_id"]]: r["asset_slug"] for r in roster}
    pools = []
    for r in rows("survival_card_pool"):
        if r["CostItem"] != 208308 or not r["UpCardPool"]:
            continue
        u = up[r["UpCardPool"]]
        choices = []
        for contrast in u["UpHero"]:
            c = contrasts[contrast]
            item = items[c["HeroItemId"]]
            choices.append({"slug": by_internal.get(item["Para1"], ""), "hero_internal": item["Para1"], "shard_item": str(c["HeroChipId"])})
        pools.append({"id": r["Id"], "choices": choices, "single_cost": r["SingleDrawCost"],
                      "pity": r["FloorsTimes"], "unlock_level": r["UnlockLevel"],
                      "selected_hero_chance": u["HeroChanceShow"].split('|')[0],
                      "selected_shard_chance": u["ChipChanceShow"].split('|')[0],
                      "selected_bonus_chance": u["GachaChanceShow"].split('|')[0]})
    return {"card_item": "208308", "pools": pools,
            "notes": "Available pool must be selected from the live in-game choices; server age alone is not inferred. Display probabilities are per reward category, not fragment yields. Pity and duplicate conversion are not simulated. Recommendations compare formation milestone gain per remaining hero-specific fragment, conditional on targeting that eligible hero, not expected return per voucher."}

if __name__ == "__main__":
    main()
