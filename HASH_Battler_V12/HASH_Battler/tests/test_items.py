"""Regression tests for V11 build validation and combat behaviors."""
import math
import unittest
from items import ItemBuild, STATS, ELEMENTS
from combat import World


def build(element='Fire', stats=None):
    stats=stats or {'Damage':3,'Attack Speed':2,'Effect Power':2,
                    'Knockback':1,'Reach':1,'Dash Speed':1}
    item=ItemBuild(element=element,stats=stats)
    assert item.valid()
    return item


class ItemTests(unittest.TestCase):
    def test_budget_and_limits(self):
        b=ItemBuild()
        for _ in range(7):self.assertTrue(b.change('Damage',1))
        self.assertFalse(b.change('Damage',1))
        for _ in range(3):self.assertTrue(b.change('Reach',1))
        self.assertEqual(b.remaining,0)
        self.assertFalse(b.change('Poison',1))
        self.assertFalse(b.change('Effect Power',1))
        self.assertTrue(b.valid())

    def test_invalid_configuration_does_not_validate(self):
        self.assertFalse(ItemBuild().valid())
        self.assertFalse(ItemBuild.from_dict({'element':'not real'}).valid())

    def test_serialization_round_trip(self):
        b=build('Air')
        self.assertEqual(ItemBuild.from_dict(b.to_dict()).to_dict(),b.to_dict())

    def test_corrupt_save_is_rejected(self):
        b=ItemBuild.from_dict({'name':'Lance','element':'Fire',
             'stats': {stat:'broken' for stat in STATS}})
        self.assertEqual(b.spent,0)

    def test_dash_speed_makes_lunge_faster(self):
        slow=build(stats={'Damage':3,'Attack Speed':2,'Effect Power':2,
                          'Knockback':1,'Reach':2,'Dash Speed':0})
        fast=build(stats={'Damage':3,'Attack Speed':2,'Effect Power':2,
                          'Knockback':1,'Reach':1,'Dash Speed':1})
        self.assertLess(fast.lance_stats()['dash_duration'], slow.lance_stats()['dash_duration'])

    def test_old_build_stats_migrate_to_melee_names(self):
        old=ItemBuild.from_dict({'name':'Lance','element':'Fire','stats':{
            'Damage':3,'Attack Speed':2,'Effect Power':2,'Knockback':1,
            'Range':1,'Projectile Speed':1}})
        self.assertTrue(old.valid())
        self.assertEqual(old.stats['Reach'],1)
        self.assertEqual(old.stats['Dash Speed'],1)

    def test_training_starts_with_three_dummies_and_no_boss(self):
        w=World();w.start_training(build())
        self.assertTrue(w.training)
        self.assertEqual(len(w.training_targets),3)
        self.assertEqual(w.stage,'training')
        self.assertEqual(w.dummy_hp,0)

    def test_lance_out_of_range_no_cooldown(self):
        w=World();w.start_training(build())
        self.assertFalse(w.activate('Item 1'))
        self.assertEqual(w.cooldowns['Item 1'],0)
        self.assertIn('CLOSER',w.message)

    def test_lance_dash_nearest_target_and_hit(self):
        w=World();w.start_training(build('Thunder'))
        w.x=0;w.y=0
        near=w.training_targets[0]
        far=w.training_targets[1]
        before_x=w.x
        self.assertTrue(w.activate('Item 1'))
        self.assertEqual(near.hp,near.max_hp)
        self.assertEqual(far.hp,far.max_hp)
        self.assertGreater(w.lance_animation,0)
        self.assertGreater(w.cooldowns['Item 1'],0)
        self.assertFalse(w.activate('Item 1'))
        for _ in range(10):w.update(.02)
        self.assertLess(near.hp,near.max_hp)
        self.assertEqual(far.hp,far.max_hp)
        self.assertGreater(w.x,before_x)
        self.assertGreater(near.stun,0)

    def test_lance_fire_burst(self):
        a=World();a.start_training(build('Fire'));a.x=0;a.activate('Item 1');a.update(.2)
        b=World();b.start_training(build('Thunder'));b.x=0;b.activate('Item 1');b.update(.2)
        self.assertLess(a.training_targets[0].hp,b.training_targets[0].hp)

    def test_lance_ice_slow(self):
        w=World();w.start_training(build('Ice'));w.x=0
        w.activate('Item 1');w.update(.2)
        self.assertGreater(w.training_targets[0].slow,0)
        w.update(.2)
        self.assertLess(w.training_targets[0].slow,3)

    def test_lance_poison_damage_over_time(self):
        w=World();w.start_training(build('Poison'));w.x=0
        w.activate('Item 1');w.update(.2)
        target=w.training_targets[0]
        after=target.hp
        w.update(.4)
        self.assertLess(target.hp,after)

    def test_lance_air_knockback(self):
        w=World();w.start_training(build('Air'));w.x=0
        w.activate('Item 1');w.update(.2)
        self.assertGreater(w.training_targets[0].vx,50)

    def test_targets_respawn(self):
        w=World();w.start_training(build());t=w.training_targets[0]
        t.hp=0;t.respawn=.1
        w.update(.15)
        self.assertEqual(t.hp,t.max_hp)
        self.assertEqual(t.respawn,0)

    def test_hash_pickups_are_more_frequent(self):
        w=World()
        self.assertGreaterEqual(w.pickup_spawn_timer,6)
        self.assertLessEqual(w.pickup_spawn_timer,9)
        w.lives=2
        w._spawn_health_pickup()
        self.assertIsNotNone(w.health_pickup)
        w.health_pickup.x,w.health_pickup.y=w.x,w.y
        w._update_health_pickup(.02)
        self.assertGreaterEqual(w.pickup_spawn_timer,11)
        self.assertLessEqual(w.pickup_spawn_timer,16)

    def test_normal_shot_hits_training_target(self):
        w=World();w.start_training(build());w.x=0;w.y=0
        t=w.training_targets[0]
        w.shot_cycle=w.shot_zone_center*w.shot_period
        self.assertTrue(w.attempt_shot((1,0),210))
        for _ in range(13):w.update(.02)
        self.assertLess(t.hp,t.max_hp)

if __name__=='__main__':unittest.main()
