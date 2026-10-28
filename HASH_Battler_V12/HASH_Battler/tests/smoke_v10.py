"""V10 graphical integration and regression: tutorial, cursor, pickups, stages."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from game import HashGame
from combat import HashPickup
from PIL import ImageGrab

project=Path(__file__).resolve().parents[1]
g=HashGame()
g.settings['sound']=False
g.settings['fullscreen']=False
g.settings['debug']=False
g.set_fullscreen(False)

def snap(name):
    g.root.update_idletasks()
    g.renderer.screen.update()
    x,y=g.root.winfo_rootx(),g.root.winfo_rooty()
    w,h=g.root.winfo_width(),g.root.winfo_height()
    ImageGrab.grab(bbox=(x,y,x+w,y+h)).save(project/name)

class Key:
    def __init__(self,keysym):self.keysym=keysym

def press(key):
    g.on_key_down(Key(key));g.on_key_up(Key(key))

try:
    g.new_run();assert g.state=='map'
    g.select_boss();assert g.state=='dialogue'
    g.mouse_click(0,0,'Mouse1');assert g.dialogue_step==0
    press('space');assert g.dialogue_step==0
    press('Return');assert g.dialogue_step==1
    g.mouse_click(0,0,'Mouse1');assert g.dialogue_step==1
    press('Return');assert g.state=='tutorial' and g.tutorial_step==1
    snap('V10_tutorial_shoot.png')
    t=g.world.stage_time
    g.tick();assert g.world.stage_time==t
    g.mouse_click(0,0,'Mouse1');press('space');assert g.tutorial_step==1
    press('Return');assert g.tutorial_step==2
    press('Return');assert g.state=='arena' and g.hud_unlocked
    # Mouse movement must not call Turtle.clear()/screen.update() recursively.
    g.pointer_in_canvas=True
    x,y=g.renderer.pt(100,-140)
    class Event:
        def __init__(self,x,y):self.x=x;self.y=y
    for i in range(350):
        sx=150+i%80;sy=120+i%65
        g.on_mouse_move(Event(sx,sy))
    assert all(g.renderer.cursor_canvas.itemcget(item,'state')=='normal' for item in g.renderer.cursor_items)
    assert len(g.renderer.cursor_items)==4
    # Test real mouse aimed shot and cooldown.
    g.world.shot_zone_center=.4
    g.world.shot_cycle=.4*g.world.shot_period
    tx,ty=g.renderer.pt(g.world.dummy_x,g.world.dummy_y)
    g.mouse_click(tx,ty,'Mouse1')
    assert len(g.world.projectiles)==1
    g.world.cooldowns['Shoot']=0
    g.world.shot_zone_center=.7
    g.world.shot_cycle=.1*g.world.shot_period
    g.mouse_click(tx,ty,'Mouse1')
    assert len(g.world.projectiles)==1
    assert g.world.cooldowns['Shoot']>.4
    # Removed parry cannot be triggered.
    g.mouse_click(tx,ty,'Mouse3')
    assert 'Parry' not in g.world.cooldowns
    # Ring must extend OUTSIDE the arena when near the top-left corner.
    g.world.x=-800+18+1
    g.world.y=450-18-1
    g.renderer.draw_timing_ring(g)
    assert len(g.renderer.shot_pen.undobufferentries().__str__())>0
    snap('V10_corner_ring.png')
    # Spawn one floating HASH pickup and show the one-time tutorial.
    g.world.x=-570;g.world.y=0
    g.world.lives=2
    g.world.pickup_spawn_timer=0
    g.world.update(.02)
    assert g.world.health_pickup is not None
    g.check_tutorial_triggers()
    assert g.state=='tutorial' and g.tutorial_step==5
    snap('V10_hash_tutorial.png')
    g.mouse_click(0,0,'Mouse1');assert g.state=='tutorial'
    press('Return');assert g.state=='arena'
    snap('V10_hash_pickup.png')
    pickup=g.world.health_pickup
    g.world.x,g.world.y=pickup.x,pickup.y
    g.world.update(.03)
    assert g.world.lives==3 and g.world.health_pickup is None
    # Phase 1 transition -> intel tip.
    g.world._begin('lasers_left')
    g.renderer.display_live(g)
    g.renderer.draw_dynamic(g)
    snap('V10_thin_lasers.png')
    g.world._begin('exit_for_spikes')
    assert g.check_tutorial_triggers() and g.tutorial_step==3
    press('Return');assert g.right_panel_unlocked
    g.world._begin('pulses')
    assert g.check_tutorial_triggers() and g.tutorial_step==4
    press('Return');assert g.state=='arena'
    g.world.player_invulnerable=100
    for _ in range(24):g.world.update(.05);g.world.update_boss(.05)
    g.renderer.display_live(g);g.renderer.draw_timing_ring(g)
    snap('V10_pulses.png')
    g.world._hit_dummy(600)
    g.world.update_boss(.05)
    assert g.world.phase3
    g.renderer.arena(g)
    snap('V10_phase3.png')
    g.world._hit_dummy(1200)
    g.start_victory_dialogue()
    assert g.state=='victory_dialogue'
    g.mouse_click(0,0,'Mouse1');assert g.dialogue_step==0
    press('Return');press('Return');assert g.state=='map'
    g.show_menu();assert g.state=='menu'
    g.on_pointer_leave(None)
    assert not g.pointer_in_canvas
    assert all(g.renderer.cursor_canvas.itemcget(item,'state')=='hidden' for item in g.renderer.cursor_items)
    print('PASS: enter-only dialogue/tips, no-recursion cursor stress, ring overflow, HASH pickup, thin lasers, phases, victory')
finally:
    g.closed=True
    g._restore_native_cursor()
    try:g.screen.bye()
    except Exception:pass
