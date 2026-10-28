"""Measure dense frames under desktop/Xvfb, outside the unittest suite."""
from pathlib import Path
import sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from game import HashGame

g=HashGame()
g.settings['sound']=False
g.settings['fullscreen']=False
g.set_fullscreen(False)
try:
    g.new_run();g.select_boss();g.advance_dialogue();g.advance_dialogue()
    for _ in range(3):g.advance_tutorial()
    g.world._begin('dots');g.world._update_dots(1.62)
    start=time.monotonic()
    for i in range(12):
        g.renderer.display_live(g)
        g.renderer.draw_timing_ring(g)
        g.screen.update()
    print('12 dense-explosion frames:',round(time.monotonic()-start,2),'seconds')
finally:
    g.closed=True
    try:g.screen.bye()
    except Exception:pass
