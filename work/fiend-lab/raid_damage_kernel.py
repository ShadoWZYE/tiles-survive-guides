"""Translation of the inspected 2.6.400.304 static Raid base-damage helper.

This is NOT established as the field/Lite fiend formula. It excludes the caller's
crit, floating roll, contextual modifiers, power correction and live patches.
Keeping it separate prevents an unverified engine bridge entering predictions.
"""
import math


def base_damage(attack, defense, coefficient, *, flat_penetration=0,
                percent_penetration=0, flat_damage=0, property_source=0,
                custom_formula=0, external_additive=0, defense_parameter=2.5):
    values = (attack, defense, coefficient, flat_penetration, percent_penetration,
              flat_damage, property_source, custom_formula, external_additive,
              defense_parameter)
    if not all(isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v) for v in values):
        raise ValueError('Inputs must be finite numeric values.')
    if attack <= 0 or defense_parameter < 0:
        raise ValueError('This helper requires positive ATK and a nonnegative defense parameter.')
    effective_defense = max(0, defense - flat_penetration) * max(0, 1 - percent_penetration)
    physical = attack * attack / (attack + defense_parameter * effective_defense)
    return physical * coefficient + flat_damage + property_source + custom_formula + external_additive
