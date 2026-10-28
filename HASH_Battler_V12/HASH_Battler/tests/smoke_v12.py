"""Full Level 1 menu -> Lance config -> training rendering smoke test."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from game import HashGame
from items import STATS
from PIL import ImageGrab

out=Path(__file__).resolve().parents[1]
g=HashGame()
g.settings.update(sound=False,fullscreen=False,debug=False)
g.set_fullscreen(False)
g.root.update_idletasks()

def snap(name):
    g.root.update_idletasks()
    g.renderer.screen.update()
    x,y=g.root.winfo_rootx(),g.root.winfo_rooty()
    w,h=g.root.winfo_width(),g.root.winfo_height()
    ImageGrab.grab(bbox=(x,y,x+w,y+h)).save(out/name)

try:
    g.new_run()
    g.root.update()
    snap('V12_map.png')
    g.select_level_one()
    assert g.state=='item_select'
    snap('V12_item_selection.png')
    g.select_lance()
    assert g.state=='item_config'
    for stat in STATS:
        for _ in range({'Damage':3, 'Attack Speed':2,'Effect Power':2,'Knockback':1,'Reach':1,'Dash Speed':1}[stat]):
            g.change_item_stat(stat,1)
    g.change_item_element('Thunder')
    assert g.item_build.valid()
    snap('V12_lance_config.png')
    g.start_training()
    assert g.state=='arena' and g.world.training
    snap('V12_training_start.png')
    target=g.world.training_targets[0]
    g.world.x=target.x-205
    g.world.y=target.y
    old_hp=target.hp
    start_x=g.world.x
    g.trigger('Item 1')
    assert g.world.training_hits==0
    assert target.hp==old_hp
    assert g.world.lance_animation>0
    assert g.world.cooldowns['Item 1']>0
    g.renderer.display_live(g)
    g.renderer.draw_dynamic(g)
    snap('V12_lance_dash.png')
    for _ in range(8):
        g.world.update(.03)
    assert g.world.training_hits==1
    assert target.hp<old_hp and target.stun>0
    assert g.world.x > start_x
    g.renderer.display_live(g)
    g.renderer.draw_dynamic(g)
    snap('V12_lance_strike.png')
    for _ in range(22):
        g.world.update(.03)
    g.renderer.display_live(g)
    g.renderer.draw_dynamic(g)
    snap('V12_training.png')
    g.show_map();assert g.state=='map'
    g.select_level_one();g.select_lance()
    assert g.item_build.element=='Thunder'
    assert g.item_build.stats['Damage']==3
    print('GUI smoke passed: map, selection, config, dash-strike, cooldown, stun, saving build.')
finally:
    g.close()
