"""Full regression suite for the Greeter's Level-0 tutorial encounter."""
import math
import random
import unittest
from combat import World, EnemyBall, HashPickup, segment_circle, YELLOW
from config import DUMMY_RADIUS, PLAYER_RADIUS, WORLD_H, WORLD_W


class CombatTests(unittest.TestCase):
    def setUp(self):
        random.seed(31415)

    def advance(self,w,seconds,dt=.05):
        visited=[]
        for _ in range(int(seconds/dt)):
            w.update(dt)
            w.update_boss(dt)
            visited.append(w.stage)
        return visited

    def test_four_player_life_lines(self):
        w=World()
        for expected in (3,2,1,0):
            w.take_debug_hit()
            self.assertEqual(w.lives,expected)

    def test_shot_miss_triggers_only_cooldown(self):
        w=World()
        w.shot_zone_center=.7
        w.shot_cycle=.1
        old_center=w.shot_zone_center
        self.assertFalse(w.attempt_shot((0,1),600))
        self.assertEqual(len(w.projectiles),0)
        self.assertAlmostEqual(w.cooldowns['Shoot'],.45)
        self.assertEqual(w.last_action,'MISSED SHOT')
        self.assertEqual(w.shot_zone_center,old_center)
        self.assertFalse(w.attempt_shot((0,1),600))
        self.assertEqual(len(w.projectiles),0)
        w.update(.46)
        self.assertEqual(w.cooldowns['Shoot'],0)

    def test_shot_zone_moves_after_success(self):
        w=World()
        w.shot_zone_center=.4
        w.shot_cycle=.4*w.shot_period
        self.assertTrue(w.attempt_shot((0,1),600))
        self.assertEqual(len(w.projectiles),1)
        self.assertEqual(w.shot_cycle,0)
        self.assertNotEqual(w.shot_zone_center,.4)
        self.assertFalse(w.attempt_shot((0,1),600))

    def test_marker_rotates_clockwise_without_reversing(self):
        w=World()
        w.shot_cycle=.9*w.shot_period
        self.assertAlmostEqual(w.shot_marker,.9)
        w.update(.2*w.shot_period)
        self.assertAlmostEqual(w.shot_marker,.1)

    def test_distance_reduces_target_size_but_not_too_small(self):
        w=World()
        near=w.shot_zone_width(5)
        far=w.shot_zone_width(1500)
        self.assertGreater(near,far)
        self.assertGreaterEqual(far,.18)

    def test_parry_is_removed_and_guard_still_works(self):
        w=World()
        self.assertNotIn('Parry',w.cooldowns)
        self.assertFalse(w.activate('Parry'))
        self.assertTrue(w.activate('Chestplate'))
        self.assertFalse(w._hurt_player(w.x,w.y,0))
        self.assertEqual(w.lives,4)
        w.update(.7)
        self.assertTrue(w._hurt_player(w.x,w.y,0))
        self.assertEqual(w.lives,3)

    def test_boundary_clamp_player_square(self):
        w=World()
        for x,y in ((-1e6,0),(1e6,0),(0,1e6),(0,-1e6),(1e6,1e6)):
            px,py=w._position_outside_boss(x,y)
            self.assertGreaterEqual(px-PLAYER_RADIUS,-WORLD_W/2)
            self.assertLessEqual(px+PLAYER_RADIUS,WORLD_W/2)
            self.assertGreaterEqual(py-PLAYER_RADIUS,-WORLD_H/2)
            self.assertLessEqual(py+PLAYER_RADIUS,WORLD_H/2)

    def test_boss_is_solid_for_move_and_dash(self):
        w=World()
        w.x=w.dummy_x-DUMMY_RADIUS-PLAYER_RADIUS-30
        w.y=w.dummy_y
        for _ in range(110):w.move(1,0,.016)
        self.assertGreaterEqual(w.dummy_x-w.x,DUMMY_RADIUS+PLAYER_RADIUS)
        self.assertTrue(w.activate('Dash',(1,0)))
        self.assertLess(w.x,w.dummy_x)

    def test_dash_protects_from_pulse_contact(self):
        w=World()
        w.activate('Dash',(-1,0))
        self.assertFalse(w._hurt_player(w.x,w.y,0))
        self.assertEqual(w.lives,4)

    def test_dash_is_longer_and_invulnerability_lasts(self):
        w=World()
        before=w.x
        self.assertTrue(w.activate('Dash',(-1,0)))
        self.assertGreaterEqual(abs(w.x-before),190)
        self.assertGreater(w.dash_iframes,.55)
        w.update(.5)
        w.update_boss(.01)
        self.assertFalse(w._hurt_player(w.x,w.y,0))
        self.assertEqual(w.lives,4)

    def test_projectile_locks_direction_from_click(self):
        w=World()
        w.shot_zone_center=.35
        w.shot_cycle=.35*w.shot_period
        self.assertTrue(w.attempt_shot((0,1),0))
        origin=(w.projectiles[0].x,w.projectiles[0].y)
        w.move(1,0,.1)
        w.update(.12)
        self.assertEqual(len(w.projectiles),1)
        shot=w.projectiles[0]
        self.assertAlmostEqual(shot.x,origin[0])
        self.assertGreater(shot.y,origin[1])

    def test_ball_reflects_off_wall_boss_then_explodes(self):
        w=World()
        w.enemy_balls=[EnemyBall(w.dummy_x-DUMMY_RADIUS-22,0,300,0)]
        w._update_balls(.1)
        self.assertLess(w.enemy_balls[0].vx,0)
        w.enemy_balls=[EnemyBall(-WORLD_W/2+22,0,-200,0)]
        w._update_balls(.1)
        self.assertGreater(w.enemy_balls[0].vx,0)
        w.enemy_balls[0].age=2.79
        w._update_balls(.02)
        self.assertEqual(len(w.explosions),1)
        self.assertFalse(w.enemy_balls)

    def test_opening_has_three_pairs_and_moves_to_top(self):
        w=World();w.player_invulnerable=1000
        visited=self.advance(w,12)
        self.assertIn('leave_right',visited)
        self.assertIn('enter_top',visited)
        self.assertEqual(w.ball_pairs,3)
        self.assertIn('BOUNCY BALLS',w.discovered_moves)

    def test_thirty_dots_detonate_simultaneously(self):
        w=World();w._spawn_dots()
        self.assertEqual(len(w.dots),30)
        self.assertEqual(len(set(round(d.fuse,4) for d in w.dots)),1)
        w._update_dots(1.61)
        self.assertFalse(w.dots)
        self.assertEqual(len(w.explosions),30)

    def test_phase_three_dots_shift_halfway_then_explode_together(self):
        w=World();w.phase3=True;w._spawn_dots(shift=True)
        before=[(d.x,d.y) for d in w.dots]
        w._update_dots(.7)
        self.assertTrue(all(d.shifted for d in w.dots))
        self.assertNotEqual(before,[(d.x,d.y) for d in w.dots])
        w._update_dots(.5)
        self.assertEqual(len(w.explosions),30)

    def test_lasers_reflect_from_walls_not_boss(self):
        w=World()
        for side in ('left','right'):
            paths=w._laser_geometry(side)
            self.assertGreaterEqual(len(paths),5)
            for path in paths:
                self.assertEqual(len(path),5)
                for x,y in path[1:]:
                    self.assertTrue(abs(abs(x)-(WORLD_W/2-9))<.001 or
                                    abs(abs(y)-(WORLD_H/2-9))<.001)
        path=World._wall_reflection_ray(0,0,1,.5,3)
        self.assertAlmostEqual(path[1][0],WORLD_W/2-9)
        self.assertLess(path[2][0],path[1][0])

    def test_pulse_spacing_longer_than_dash_cooldown(self):
        w=World()
        w._begin('pulses')
        times=[];speeds=[]
        for i in range(300):
            w.update(.05);w.update_boss(.05)
            if w.pulse_count>len(times):
                times.append(round((i+1)*.05,2))
                speeds.append(w.pulses[-1].speed)
            if len(times)==4:break
        self.assertEqual(len(times),4)
        self.assertTrue(all(b-a>1.0 for a,b in zip(times,times[1:])))
        self.assertEqual(speeds,sorted(speeds))
        self.assertLess(speeds[0],speeds[-1])

    def test_full_opening_includes_spikes_slam_four_pulses_and_hunters(self):
        w=World();w.player_invulnerable=1000
        visited=self.advance(w,50)
        for stage in ('bouncy','dots','lasers_right','lasers_left',
                      'exit_for_spikes','spikes','slam_prepare','slam','pulses','cycle_summon'):
            self.assertIn(stage,visited)
        self.assertEqual(w.pulse_count,4)
        self.assertEqual(len(w.triangles),1)
        self.assertIn('SPIKE RAIN',w.discovered_moves)
        self.assertIn('SLAM',w.discovered_moves)
        self.assertIn('PULSE',w.discovered_moves)

    def test_hunters_have_one_hp(self):
        w=World();w._summon_hunters(2)
        self.assertEqual(len(w.triangles),1)
        hunter=w.triangles[0]
        self.assertEqual(hunter.hp,1)
        w._damage_hunter(hunter)
        self.assertEqual(len(w.triangles),0)
        self.assertNotIn(hunter,w.triangles)

    def test_repeated_cycles_add_hunters_with_performance_cap(self):
        w=World();w.player_invulnerable=1000
        self.advance(w,75)
        self.assertGreaterEqual(w.cycle_count,4)
        self.assertEqual(len(w.triangles),1)

    def test_tracking_laser_warns_and_locks_before_firing(self):
        w=World();w.phase3=True
        w._begin('tracking')
        w._update_stage(.4)
        self.assertFalse(w.laser_active)
        w.x,w.y=100,100
        w._update_stage(.4)
        self.assertFalse(w.laser_active)
        paths_before=[list(path) for path in w.laser_paths]
        w.x,w.y=-200,-200
        w._update_stage(.4)
        self.assertTrue(w.laser_active)
        self.assertEqual(w.laser_paths,paths_before)
        w._update_stage(.2)
        self.assertEqual(w.laser_paths,paths_before)

    def test_only_one_hunter_can_exist_at_once(self):
        w=World()
        w._summon_hunters(20)
        self.assertEqual(len(w.triangles),1)
        w._summon_hunters(20)
        self.assertEqual(len(w.triangles),1)
        w._damage_hunter(w.triangles[0])
        self.assertEqual(len(w.triangles),0)
        w._summon_hunters(20)
        self.assertEqual(len(w.triangles),1)

    def test_phase_three_at_half_health_red_bottom_tracking_then_dots(self):
        w=World()
        w._hit_dummy(600)
        w.update_boss(.05)
        self.assertTrue(w.phase3)
        self.assertEqual(w.dummy_phase,'PHASE 3')
        self.assertEqual(w.stage,'phase3_glide')
        w.player_invulnerable=1000
        seen=self.advance(w,14)
        self.assertIn('tracking',seen)
        self.assertIn('phase3_dots',seen)
        self.assertIn('TRACKING LASERS',w.discovered_moves)
        self.assertAlmostEqual(w.dummy_y,-WORLD_H/2)

    def test_boss_zero_hp_stops_hazards(self):
        w=World();w._summon_hunters(2)
        w._spawn_three_balls()
        w._hit_dummy(10000)
        self.assertEqual(w.dummy_hp,0)
        self.assertEqual(w.stage,'victory')
        self.assertFalse(w.triangles)
        self.assertFalse(w.enemy_balls)

    def test_ricochet_collision_segment(self):
        self.assertTrue(segment_circle(-100,0,100,0,0,0,10))
        self.assertFalse(segment_circle(-100,0,100,0,0,30,10))

    def test_boss_hp_is_halved(self):
        w=World()
        self.assertEqual(w.dummy_max_hp,1200)
        self.assertEqual(w.dummy_hp,1200)

    def test_bouncy_balls_expire_faster(self):
        w=World();w._spawn_ball_pair()
        self.assertTrue(all(b.fuse<=2.8 for b in w.enemy_balls))
        w._update_balls(2.81)
        self.assertFalse(w.enemy_balls)
        self.assertEqual(len(w.explosions),2)
        w._spawn_three_balls()
        self.assertTrue(all(b.fuse<=2.8 for b in w.enemy_balls))

    def test_health_pickup_only_spawns_when_hurt_and_one_at_a_time(self):
        w=World()
        w.pickup_spawn_timer=0
        w.update(.02)
        self.assertIsNone(w.health_pickup)
        w.lives=2
        w.update(.02)
        self.assertIsNotNone(w.health_pickup)
        self.assertEqual(w.pickup_spawn_count,1)
        p=w.health_pickup
        self.assertGreater(math.hypot(p.x-w.x,p.y-w.y),200)
        w.update(3)
        self.assertIs(w.health_pickup,p)
        self.assertEqual(w.pickup_spawn_count,1)

    def test_health_pickup_restores_exactly_one_line_and_has_cooldown(self):
        w=World();w.lives=2
        w.health_pickup=HashPickup(w.x,w.y)
        w._update_health_pickup(.05)
        self.assertEqual(w.lives,3)
        self.assertIsNone(w.health_pickup)
        self.assertGreaterEqual(w.pickup_spawn_timer,11)
        self.assertLessEqual(w.pickup_spawn_timer,16)
        self.assertEqual(w.last_action,'HASH RESTORED')

    def test_health_pickup_expires_and_can_spawn_again_later(self):
        w=World();w.lives=3
        w.health_pickup=HashPickup(0,380,lifetime=.5)
        w._update_health_pickup(.51)
        self.assertIsNone(w.health_pickup)
        self.assertGreater(w.pickup_spawn_timer,10)
        w.pickup_spawn_timer=0
        w._update_health_pickup(.01)
        self.assertEqual(w.pickup_spawn_count,1)
        self.assertIsNotNone(w.health_pickup)

    def test_laser_collision_matches_thinner_visual(self):
        w=World()
        w.x,w.y=-450,0
        w.laser_paths=[[(-600,50),(-300,50)]]
        w.laser_active=True
        w._update_lasers()
        self.assertEqual(w.lives,4)
        w.y=24
        w._update_lasers()
        self.assertEqual(w.lives,3)

    def test_map_checkpoint_reset(self):
        w=World()
        w.restore({'x':9999,'lives':0,'time_alive':15})
        self.assertEqual(w.lives,4)
        self.assertEqual(w.time_alive,15)


if __name__=='__main__':unittest.main()
