import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('builder', HERE / 'build_estimate_model.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class EstimateBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder = ROOT / 'outputs/hero-report'
        read = lambda name: json.loads((folder / name).read_text(encoding='utf8'))
        cls.model = builder.build(read('TilesSurvive-Upgrade-Data.json'), read('Hero-Combat-Audit.json'),
                                  {h['asset_slug']: h for h in read('TilesSurvive-Hero-Data.json')})

    def skill(self, hero, slot):
        return next(s for s in self.model['heroes'][hero]['skills'] if s['slot'] == slot)

    def test_ray_delay_damage_depends_on_completed_active_not_own_cooldown(self):
        s=self.skill('ray',2)
        self.assertEqual(s['damage_selection_basis'],'finish_triggered_delayed_effect')
        self.assertEqual(s['finish_trigger']['source_skill_id'],'survivor_ray_skill_1')
        self.assertEqual(s['finish_trigger']['delay_seconds'],0)
        self.assertAlmostEqual(s['levels'][1]['damage'],4/9,places=7)
        self.assertAlmostEqual(s['levels'][30]['damage'],s['levels'][30]['cast_budget']['direct_coefficient']/9,places=7)

    def test_finish_rule_rejects_compound_gates_and_unknown_native_paths(self):
        from copy import deepcopy
        a=json.loads((ROOT/'outputs/hero-report/Hero-Combat-Audit.json').read_text(encoding='utf-8'))
        h=a['heroes']['ray'];s=next(s for s in h['skills'] if s['id']=='survivor_ray_skill_2')
        self.assertIsNone(builder.finish_trigger(s,h,{}))
        modified=deepcopy(s);modified['skill_nodes'][0]['condition']['ConditionAnd']=[123]
        self.assertIsNone(builder.finish_trigger(modified,h,a['native_audit']))
        modified=deepcopy(s);modified['referenced_buffs'][0]['Plus']=1
        self.assertIsNone(builder.finish_trigger(modified,h,a['native_audit']))

    def test_current_native_scope_never_claims_full_runtime_validation(self):
        self.assertEqual(self.model['native_semantics_build'],'2.6.300.293')
        self.assertGreaterEqual(self.model['native_selected_method_count'],43)
        self.assertFalse(self.model['current_native_semantics_reverified'])
        self.assertIn('live_patches_unverified',self.model['native_verification_scope'])

    def test_new_native_rule_preserves_other_hero_curves_and_reference_anchors(self):
        folder=ROOT/'outputs/hero-report'
        read=lambda n:json.loads((folder/n).read_text(encoding='utf-8'))
        audit=read('Hero-Combat-Audit.json');audit.pop('native_audit')
        prior=builder.build(read('TilesSurvive-Upgrade-Data.json'),audit,{h['asset_slug']:h for h in read('TilesSurvive-Hero-Data.json')})
        from copy import deepcopy
        current=deepcopy(self.model)
        for h in current['heroes'].values():
            for s in h['skills']:
                for row in s['levels']:row.pop('healing_budgets',None)
        for slug in self.model['heroes']:
            if slug!='ray':self.assertEqual(current['heroes'][slug],prior['heroes'][slug],slug)
        self.assertEqual(self.model['scales'],prior['scales'])

    def test_raw_healing_keeps_caster_and_recipient_property_sources_separate(self):
        chef=self.skill('ken',1)['levels'][1]['healing_budgets'][0]
        self.assertEqual(chef['property_terms'],[{'owner':'caster','property':'HP','coefficient':.15}])
        self.assertAlmostEqual(self.skill('ken',1)['levels'][30]['healing_budgets'][0]['property_terms'][0]['coefficient'],.15*1.29)
        frank=self.skill('maddie',2)['levels'][1]['healing_budgets'][0]
        self.assertEqual(frank['attack_coefficient'],0)
        self.assertEqual(frank['property_terms'],[{'owner':'recipient','property':'HP','coefficient':.05}])
        self.assertEqual(frank['execution'],'conditional summon-dependent')
        layla=self.skill('layla',1)['levels'][1]['healing_budgets']
        self.assertEqual({b['execution'] for b in layla},{'direct dispatch','periodic tick'})
        self.assertEqual(next(b for b in layla if b['execution']=='direct dispatch')['attack_coefficient'],2.84)
        self.assertTrue(all(not b['effective_healing_verified'] for b in layla))

    def test_raw_healing_rejects_unknown_formulas_and_mismatched_sources(self):
        from copy import deepcopy
        a=json.loads((ROOT/'outputs/hero-report/Hero-Combat-Audit.json').read_text(encoding='utf-8'))
        e=next(s for s in a['heroes']['ken']['skills'] if s['id']=='survivor_ken_skill_1')
        bad=deepcopy(e)
        for effect in bad['dependency_effects']:effect['custom_formula']=True
        self.assertEqual(builder.healing_budgets(bad,[]),[])
        bad=deepcopy(e)
        for effect in bad['dependency_effects']:effect['property_rates_per_mille']=[]
        self.assertEqual(builder.healing_budgets(bad,[]),[])

    def test_placeholder_stat_skill_is_neither_healing_nor_damage(self):
        s = self.skill('rosie', 3)
        self.assertTrue(all(r['utility'] == r['damage'] == 0 for r in s['levels']))
        self.assertFalse(s['uses_generic_pressure_prior'])

    def test_actual_hit_effect_replaces_generic_basic_fallback(self):
        for hero in ['becca', 'maddie', 'layla']:
            s = self.skill(hero, 0)
            self.assertEqual(s['damage_effects'], [f'damage_{hero}_attack'])
            self.assertEqual(s['damage_selection_basis'], 'direct_hit_reference')

    def test_damage_zone_is_not_a_summoned_ally(self):
        for hero, slot in [('ray', 0), ('maddie', 1)]:
            s = self.skill(hero, slot)
            self.assertTrue(s['has_damage_zone'])
            self.assertFalse(s['has_summon_dependency'])
            self.assertTrue(all(r['utility'] == 0 for r in s['levels']))

    def test_lifesteal_and_real_summons_keep_qualitative_utility(self):
        self.assertGreater(self.skill('rosie', 2)['levels'][1]['utility'], 0)
        self.assertTrue(self.skill('maddie', 2)['has_summon_dependency'])
        self.assertGreater(self.skill('maddie', 2)['levels'][1]['utility'], 0)

    def test_incomplete_graphs_are_never_declared_verified(self):
        self.assertTrue(all(s['unresolved_execution'] for h in self.model['heroes'].values() for s in h['skills']))

    def test_rosie_combo_uses_full_bound_clip_chain_not_sum_of_cooldowns(self):
        s=self.skill('rosie',0)
        self.assertEqual(s['sequence_effect_ids'],['damage_rosie_attack_2'])
        self.assertAlmostEqual(s['cadence_assumed_seconds'],1.4+1.7333333,places=6)
        self.assertEqual(s['cadence_model'],'max_cooldown_and_uninterrupted_clip_chain_at_unit_speed')
        self.assertAlmostEqual(s['levels'][1]['damage'],1.88/s['cadence_assumed_seconds'],places=7)
        self.assertFalse(self.skill('ray',2)['sequence_effect_ids'])

    def test_layla_runtime_hp_not_double_value_tooltip_and_locked_zero(self):
        s=self.skill('layla',2)
        self.assertEqual(s['levels'][0]['self_percent'],[0,0,0])
        self.assertAlmostEqual(s['levels'][30]['self_percent'][2],.129)
        self.assertGreater(s['levels'][30]['self_percent'][2],s['levels'][1]['self_percent'][2])
        self.assertFalse(any('_text' in b['id'] for b in s['permanent_stat_sources']))

    def test_tarzan_finish_strike_is_included_but_counterattack_is_not(self):
        s=self.skill('tarzan',0)
        self.assertEqual(s['sequence_effect_ids'],['damage_tarzan_attack_2'])
        self.assertAlmostEqual(s['cadence_assumed_seconds'],1.6,places=6)
        self.assertAlmostEqual(s['levels'][1]['damage'],.42/s['cadence_assumed_seconds'],places=7)
        self.assertFalse(self.skill('tarzan',1)['sequence_effect_ids'])
        # Child has no root skill-level override; do not invent inherited scaling.
        self.assertAlmostEqual(s['levels'][30]['damage'],(.21*1.29+.21)/s['cadence_assumed_seconds'],places=7)

    def test_team_defense_is_exported_separately_from_self(self):
        for hero in ['tara','tony']:
            s=self.skill(hero,2)
            self.assertEqual(s['levels'][30]['self_percent'],[0,0,0])
            self.assertAlmostEqual(s['levels'][30]['team_percent'][1],.129)

    def test_real_support_modifiers_change_utility_but_tooltip_only_does_not(self):
        s=self.skill('layla',1)
        self.assertGreater(s['levels'][30]['utility'],s['levels'][1]['utility'])
        s=self.skill('rosie',2)
        self.assertEqual(s['levels'][30]['utility'],s['levels'][1]['utility'])

    def test_lucky_periodic_damage_counts_ticks_not_one_modifier_row(self):
        s=self.skill('lucky',1)
        self.assertEqual(s['damage_selection_basis'],'periodic_buff_potential')
        self.assertEqual(s['damage_effects'],[])
        self.assertEqual(s['periodic_budgets'][0]['nominal_ticks'],24)
        self.assertAlmostEqual(s['levels'][1]['damage'],24*.2/8)
        self.assertEqual(s['levels'][0]['damage'],0)

    def test_refreshing_burn_and_periodic_healing_are_not_unconditional_damage(self):
        lava=self.skill('lava',0)
        self.assertFalse(any(p['scored'] for p in lava['periodic_budgets']))
        self.assertTrue(lava['periodic_budgets'][0]['overlapping_refresh'])
        self.assertEqual(lava['periodic_budgets'][0]['reapplication_policy'],'replace_same_id_and_restart_tick_timer')
        self.assertEqual(lava['levels'][1]['utility'],0)
        for hero in ['layla','candy']:
            s=self.skill(hero,1)
            self.assertEqual(s['periodic_budgets'][0]['nominal_ticks'],4)
            self.assertFalse(s['periodic_budgets'][0]['scored'])

    def test_nikola_temporary_attack_buff_uses_time_average_and_lock(self):
        s=self.skill('nikola',1)
        self.assertAlmostEqual(s['levels'][1]['self_percent'][0],.2*5/7)
        self.assertEqual(s['levels'][0]['self_percent'],[0,0,0])
        self.assertAlmostEqual(s['temporary_stat_sources'][0]['assumed_uptime'],5/7)

    def test_description_prefix_rows_never_supply_damage_or_progression(self):
        for hero in ['lucky','sarge','ken','freja','travis','eva']:
            s=self.skill(hero,2)
            self.assertEqual(s['damage_effects'],[],hero)
            self.assertTrue(all(r['damage']==0 for r in s['levels']),hero)
            self.assertFalse(s['uses_generic_pressure_prior'],hero)
        # Removing description pressure must preserve genuine stat/support benefits.
        self.assertGreater(self.skill('ken',2)['levels'][1]['self_percent'][2],0)
        self.assertGreater(self.skill('freja',2)['levels'][1]['utility'],0)

    def test_lava_condition_graph_keeps_chance_health_and_compound_state_distinct(self):
        s=self.skill('lava',0)
        conditions={c['InternalId']:c for c in s['condition_dependencies']}
        self.assertEqual(conditions[158000199]['ParamInt'],[200])
        self.assertEqual(conditions[158000200]['ParamInt'],[500])
        self.assertEqual(conditions[158000204]['ConditionAnd'],[158000203,158000202])
        self.assertIn(158000202,conditions)
        self.assertIn('lava_attack_add_burn',{e['id'] for e in s['conditional_effects']})

    def test_all_base_models_have_bound_animation_audit(self):
        data=json.loads((ROOT/'outputs/hero-report/Hero-Animation-Audit.json').read_text(encoding='utf-8'))
        self.assertEqual(set(data['heroes']),set(self.model['heroes']))
        for h in data['heroes'].values():
            self.assertGreater(h['takes']['attack']['duration_seconds'],0)
        for h in self.model['heroes'].values():
            for s in h['skills']:
                if s['cast_duration_at_unit_speed_seconds'] is not None:
                    self.assertGreaterEqual(s['cadence_assumed_seconds'],s['cast_duration_at_unit_speed_seconds'])

    def test_opening_window_honors_first_delay_and_cast_completion(self):
        evidence={'base_pre_cooldown_ms':5000}
        self.assertEqual(builder.opening_pressure(evidence,7,2,3,[],6),0)
        self.assertEqual(builder.opening_pressure(evidence,7,2,3,[],7),round(3/7,8))
        self.assertEqual(builder.opening_pressure(evidence,7,2,3,[],14),round(6/14,8))
        self.assertIsNone(builder.opening_pressure(evidence,7,None,3,[],20))

    def test_opening_periodic_budget_does_not_credit_ticks_after_window(self):
        periodic=[{'scored':True,'nominal_ticks':24,'interval_ms':100,'coefficient_per_tick':.2}]
        # Cast completes at 7s; a window ending at 8s admits only ten ticks.
        self.assertEqual(builder.opening_pressure({'base_pre_cooldown_ms':5600},8,1.4,0,periodic,8),.25)
        periodic[0]['scored']=False
        self.assertEqual(builder.opening_pressure({'base_pre_cooldown_ms':5600},8,1.4,0,periodic,8),0)

    def test_opening_temporary_buff_has_no_pre_activation_credit(self):
        s=self.skill('nikola',1)
        self.assertLess(s['levels'][1]['opening_windows']['10']['self_percent'][0],s['levels'][1]['self_percent'][0])
        self.assertEqual(s['levels'][0]['self_percent'],[0,0,0])
        for h in self.model['heroes'].values():
            for skill in h['skills']:
                for level in skill['levels'][1:]:
                    self.assertEqual(set(level['opening_windows']),{'10','20','30'})

    def test_immediate_multi_hit_potential_scales_per_effect_not_per_dependency(self):
        for hero,counts in [('jacob',{'damage_jacob_attack':3}),('tim',{'damage_tim_attack':4}),
                            ('lava',{'damage_lava_attack':1,'damage_lava_attack_2':1})]:
            s=self.skill(hero,0)
            self.assertEqual(s['direct_hit_counts'],counts)
            self.assertEqual(s['direct_hit_budget_basis'],'unconditional_immediate_timeline_potential')
        # Traveling projectiles are not converted to guaranteed hit counts.
        self.assertEqual(self.skill('sarge',0)['direct_hit_counts'],{})
        self.assertEqual(self.skill('eva',1)['direct_hit_counts'],{})
        lava=self.skill('lava',0)
        self.assertAlmostEqual(lava['levels'][1]['damage'],.7/lava['cadence_assumed_seconds'],places=7)

    def test_timed_budgets_preserve_full_cast_coefficients_and_child_offsets(self):
        for h in self.model['heroes'].values():
            for s in h['skills']:
                for row in s['levels'][1:]:
                    b=row['cast_budget']
                    if not b['direct_events']:continue
                    self.assertAlmostEqual(sum(e['coefficient'] for e in b['direct_events']),b['direct_coefficient'])
                    self.assertTrue(all(0<=e['offset_seconds']<=s['cast_duration_at_unit_speed_seconds'] for e in b['direct_events']))
        rosie=self.skill('rosie',0)['levels'][1]['cast_budget']['direct_events']
        self.assertEqual(len(rosie),2)
        self.assertGreater(rosie[1]['offset_seconds'],1.4)
        self.assertLess(rosie[0]['offset_seconds'],.4)
        self.assertEqual(len(self.skill('tim',0)['levels'][1]['cast_budget']['direct_events']),4)
        self.assertEqual(self.skill('sarge',0)['levels'][1]['cast_budget']['direct_events'],[])
        self.assertAlmostEqual(self.skill('nikola',1)['levels'][1]['cast_budget']['temporary_buffs'][0]['application_offset_seconds'],.5)


if __name__ == '__main__':
    unittest.main()
