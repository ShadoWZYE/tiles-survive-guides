import unittest
import json
from pathlib import Path
from audit_combat_effects import events, effect_summary, condition_dependencies, release_timing, immediate_hit_events, timed_dispatches, summon_inventory, projectile_launch_events


class CombatAuditTests(unittest.TestCase):

    def test_projectile_launches_keep_simultaneous_actions_and_do_not_use_launch_as_impact(self):
        import copy
        r=dict(Id='release',SkillEvent='clip',PreWait=100,AfterWait=0,Speed=1000,LoopTime=0)
        hit=dict(Action='RaidEvent',RaidEventType=1,StringParam0='damage')
        action=dict(Action='Projectile',Type='Line',Config={'Velocity':15,'TimeScale':1,'Acceleration':0},HitActions=[hit])
        timeline=dict(Take='attack',Speed=1,Loop=False,CustomLength=2,Stages=[{'Time':.3,'Actions':[action,copy.deepcopy(action)]}])
        events=projectile_launch_events(r,timeline,{},start=1)
        self.assertEqual(len(events),2);self.assertNotEqual(events[0]['action_index'],events[1]['action_index'])
        self.assertAlmostEqual(events[0]['launch_offset_seconds'],1.4)
        self.assertIsNone(events[0]['impact_offset_seconds']);self.assertEqual(events[0]['hit_target_limit'],1)
        self.assertEqual(projectile_launch_events(r,{**timeline,'Loop':True},{}),[])
        self.assertEqual(projectile_launch_events({**r,'LoopTime':1000},timeline,{}),[])
        self.assertEqual(projectile_launch_events(r,{**timeline,'Speed':2},{}),[])

    def test_timed_dispatches_scale_release_speed_and_preserve_release_start(self):
        r=dict(Id='release',SkillEvent='clip',PreWait=100,AfterWait=0,Speed=2000,LoopTime=0)
        hit=dict(Action='RaidEvent',RaidEventType=1,StringParam0='damage')
        t=dict(Take='attack',Speed=1,Loop=False,CustomLength=0,Stages=[{'Time':.6,'Actions':[
            hit,{'Action':'Projectile','Type':'Immediate','HitActions':[hit]},
            {'Action':'Projectile','Type':'Line','HitActions':[hit]}]}])
        clips={'attack':{'clip_name':'attack','duration_seconds':2}}
        found=timed_dispatches(r,t,clips,start=3)
        self.assertEqual(found,[{'reference':'damage','offset_seconds':3.4}]*2)
        self.assertEqual(timed_dispatches(r,{**t,'Loop':True},clips),[])
        self.assertEqual(timed_dispatches(r,t,{},start=3),[])
        self.assertEqual(timed_dispatches(r,t,clips,start=None),[])

    def test_release_duration_uses_clip_speed_waits_and_explicit_length_precedence(self):
        r=dict(Id='release',SkillEvent='action',PreWait=100,AfterWait=200,Speed=2000,LoopTime=0)
        t=dict(Take='attack',CustomLength=0,Stages=[{'Time':.4}])
        clips={'attack':{'clip_name':'actual_attack','duration_seconds':2}}
        self.assertAlmostEqual(release_timing(r,t,clips)['duration_at_unit_speed_seconds'],1.3)
        self.assertIsNone(release_timing(r,t,{})['duration_at_unit_speed_seconds'])
        self.assertAlmostEqual(release_timing({**r,'LoopTime':400},t,clips)['duration_at_unit_speed_seconds'],.7)
        self.assertAlmostEqual(release_timing(r,{**t,'CustomLength':.6},clips)['duration_at_unit_speed_seconds'],.9)

    def test_immediate_inventory_does_not_count_traveling_or_nested_actions(self):
        event=dict(Action='RaidEvent',RaidEventType=1,StringParam0='damage')
        projectile=dict(Action='Projectile',Type='Immediate',HitActions=[event,event])
        t={'Stages':[{'Time':.2,'Actions':[projectile,{**projectile,'Type':'Line'},
            {'Action':'Branch','Actions':[projectile]}]}]}
        self.assertEqual(immediate_hit_events(t),[{'reference':'damage','stage_time_seconds':.2}]*2)

    def test_condition_graph_handles_cycles_and_shared_conditions(self):
        def row(n, ands, ors):
            return dict(InternalId=n,Id=str(n),Type=100,ParamInt=[],ParamString=[],
                        ConditionAnd=ands,ConditionOr=ors,ConditionTarget=0,ConditionTarget_2=1)
        graph=condition_dependencies([1,1,None],{1:row(1,[2],[3]),2:row(2,[1,3],[]),3:row(3,[],[])})
        self.assertEqual([c['InternalId'] for c in graph],[1,2,3])
        self.assertEqual(graph[0]['ConditionTarget_2'],1)

    def test_projectile_launch_does_not_become_impact_time(self):
        self.assertEqual(events({'Action': 'Projectile', 'HitActions': [
            {'Action': 'RaidEvent', 'StringParam0': 'zone', 'RaidEventType': 1}]}),
            [{'reference': 'zone', 'event_type': 1, 'context': 'projectile_hit'}])

    def test_damage_name_does_not_override_heal_type(self):
        row = effect_summary({'Id': 'damage_heal_text', 'Type': 1,
                              'EffectParam2': 300, 'EffectParam3': 0})
        self.assertEqual(row['type'], 1)
        self.assertNotIn('damage_coefficient', row)

    def test_all_roster_offense_indices_use_attack_not_display_parameters(self):
        path = Path(__file__).resolve().parents[2] / 'outputs/hero-report/TilesSurvive-Hero-Data.json'
        heroes = json.loads(path.read_text(encoding='utf-8'))
        low = min(h['max_level_attack'] for h in heroes)
        high = max(h['max_level_attack'] for h in heroes)
        for hero in heroes:
            self.assertIsNone(hero['best_non_basic_damage_coefficient'], hero['name'])
            expected = round((hero['max_level_attack'] - low) / (high - low) * 1000, 2)
            self.assertEqual(hero['offense_index'], expected, hero['name'])

    def test_child_buffs_and_periodic_effects_are_in_dependency_graph(self):
        path=Path(__file__).resolve().parents[2]/'outputs/hero-report/Hero-Combat-Audit.json'
        data=json.loads(path.read_text(encoding='utf8'))
        layla=data['heroes']['layla']['skills'][1]
        self.assertIn('layla_skill_1_buff_dot',{b['Id'] for b in layla['referenced_buffs']})
        lava=data['heroes']['lava']['skills'][0]
        self.assertIn('lava_attack_burn_dot',{e['id'] for e in lava['dependency_effects']})

    def test_actor_dependencies_have_cycle_protection_and_never_become_scored_hits(self):
        effects={'spawn':{'Id':'spawn','InternalId':1,'Type':7,'EffectParam1':'actor','EffectParam2':0,'EffectParam3':0,'SummonLifeTime':1000}}
        monsters={'actor':{'Id':'actor','Type':3,'SkillConfig':{'10':1}}}
        skills={10:{'Id':'actor_skill','Type':2,'Cooldown':99999,'PreCooldown':0,'AttackTarget':[0],
            'AttackArea':[1,2000],'SkillRelease':[20],'SubSkill':[10]}}
        releases={20:{'SkillNewEffect':[1],'SkillEvent':''}}
        result=summon_inventory(['spawn'],effects,monsters,skills,releases,{})
        self.assertEqual(len(result),1)
        self.assertEqual(len(result[0]['skills']),1)
        self.assertFalse(result[0]['scored_as_executed_damage'])

    def test_ray_and_maddie_actor_templates_resolve_to_actual_skill_effects(self):
        path=Path(__file__).resolve().parents[2]/'outputs/hero-report/Hero-Combat-Audit.json'
        data=json.loads(path.read_text(encoding='utf8'))
        ray=data['heroes']['ray']['skills'][0]['summoned_actors'][0]
        self.assertEqual(ray['template_id'],'ray_attack_summon_damagezone')
        self.assertEqual(ray['stat_rates_per_mille'],[1000,1000,1000])
        self.assertEqual(ray['missing_references'],[])
        self.assertEqual(ray['skills'][0]['effects'][0]['id'],'damage_ray_attack')
        self.assertFalse(ray['scored_as_executed_damage'])
        maddie=data['heroes']['maddie']['skills'][1]['summoned_actors'][0]
        self.assertEqual(maddie['template_id'],'maddie_skill_1_summon')
        self.assertEqual(maddie['lifetime_ms'],2000)


if __name__ == '__main__':
    unittest.main()
