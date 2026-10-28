"""Main controller: screen transitions, controls, pause, sound, game loop."""
import math
import sys
import threading
import time
import turtle

from config import (BG, ACTION_NAMES, DEFAULT_BINDINGS, FIXED_KEYS,
                    pretty_key)
from combat import World
from items import ItemBuild
from storage import load_run, load_settings, save_run, save_settings
from pathlib import Path
from config import SAVE_FILE
from visuals import Renderer


class HashGame:
    def __init__(self):
        self.settings = load_settings()
        self.screen = turtle.Screen()
        self.screen.setup(1180, 790)
        self.screen.title("#HASH# - Turtle Boss-Battler")
        self.screen.bgcolor(BG)
        self.screen.tracer(0)
        self.root = self.screen.getcanvas().winfo_toplevel()
        self.canvas = self.screen.getcanvas()
        self.renderer = Renderer(self.screen)
        self.world = World()
        self.item_build=ItemBuild()
        self.equipped_build=None
        self.item_message='' 
        self.state = "menu"
        self.dialogue_step = 0
        self.tutorial_step = 0
        self.tutorial_seen = set()
        self.hud_unlocked = False
        self.right_panel_unlocked = False
        self.settings_origin = "menu"
        self.settings_message = ""
        self.waiting_for = None
        self.pressed = set()
        self.aim = None
        self.cursor_position = (0, 0)
        self.pointer_in_canvas = False
        self._windows_cursor_hide_count = 0
        self.fps = 60.0
        self.last_tick = time.monotonic()
        self.hud_clock = 0.0
        self.save_clock = 0.0
        self.last_dimensions = (0, 0)
        self.closed = False
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Destroy>", self.on_window_destroyed, add="+")
        # Listen on the whole game window, not just the canvas.
        # Turtle buttons can steal keyboard focus from the canvas.
        self.root.bind("<KeyPress>", self.on_key_down)
        self.root.bind("<KeyRelease>", self.on_key_up)
        self.root.bind("<FocusOut>", self.on_focus_lost)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Enter>", self.on_pointer_enter, add="+")
        self.canvas.bind("<Leave>", self.on_pointer_leave, add="+")
        self.root.bind("<FocusIn>", self.on_focus_gained, add="+")
        # Turtle's canvas sits inside a ScrolledCanvas/Frame. Hide the native
        # cursor on every widget in the window, not just on Turtle's canvas.
        for widget in (self.root, self.canvas.master, self.canvas):
            try:
                widget.configure(cursor="none")
            except Exception:
                pass
        # Windows Tk can still show its arrow despite cursor='none'. While
        # the pointer is in the game, hide it with the native OS cursor API.
        # Every ShowCursor(False) is paired with a ShowCursor(True) on leave,
        # loss of focus, and exit so other applications remain unaffected.
        self.screen.onscreenclick(self.on_left_click, btn=1)
        self.screen.onscreenclick(self.on_middle_click, btn=2)
        self.screen.onscreenclick(self.on_right_click, btn=3)
        self.set_fullscreen(self.settings["fullscreen"])
        self.show_menu()
        self.root.after_idle(self.restore_keyboard_focus)
        self.screen.ontimer(self.tick, 16)

    def restore_keyboard_focus(self):
        """Return focus to gameplay after a menu click or screen change."""
        try:
            self.canvas.focus_force()
        except Exception:
            pass

    def run(self):
        self.screen.mainloop()

    def set_fullscreen(self, enabled):
        try:
            if enabled:
                # Also set the real monitor geometry: some Tk environments
                # ignore the fullscreen attribute until a window manager runs.
                monitor_w = self.root.winfo_screenwidth()
                monitor_h = self.root.winfo_screenheight()
                self.root.geometry(f"{monitor_w}x{monitor_h}+0+0")
            self.root.attributes("-fullscreen", bool(enabled))
            if not enabled:
                monitor_w = self.root.winfo_screenwidth()
                monitor_h = self.root.winfo_screenheight()
                w = min(1180, max(760, monitor_w-80))
                h = min(790, max(570, monitor_h-95))
                self.root.geometry(f"{w}x{h}+40+30")
        except Exception:
            # On some Linux desktops fullscreen window attributes are unavailable.
            self.settings["fullscreen"] = False
        self.last_dimensions = (0, 0)

    def persist_settings(self):
        try:
            save_settings(self.settings)
        except OSError:
            self.settings_message = "UNABLE TO SAVE SETTINGS - CHECK FOLDER PERMISSIONS"

    def persist_run(self):
        try:
            save = self.world.to_save()
            if self.equipped_build is not None:
                save['equipped_item']=self.equipped_build.to_dict()
            save['greeter_defeated']=getattr(self,'greeter_defeated',False)
            save_run(save)
        except OSError:
            self.world.message = "WARNING: SAVE COULD NOT BE WRITTEN"
            self.world.message_timer = 2.0

    def beep(self, frequency=700, duration_ms=38):
        if not self.settings["sound"]:
            return
        try:
            import winsound
            threading.Thread(target=self._beep_thread,
                             args=(winsound,frequency,duration_ms),daemon=True).start()
        except ImportError:
            pass  # Windows-only built-in; game remains functional everywhere.

    @staticmethod
    def _beep_thread(winsound, frequency, duration):
        try:
            winsound.Beep(frequency, duration)
        except (OSError, RuntimeError):
            pass

    def show_menu(self):
        if self.state == "arena":
            self.persist_run()
        self.state = "menu"
        self.settings_origin = "menu"
        self.waiting_for = None
        self.pressed.clear()
        self.renderer.menu(self)
        self.last_dimensions = self.renderer.dimensions()
        self.beep(550)
        self.update_cursor()

    def return_to_menu(self):
        self.persist_run()
        self.show_menu()

    def update_cursor(self):
        x,y=self.cursor_position
        visible=self.pointer_in_canvas
        self.renderer.draw_cursor(x,y,visible)

    def enter_arena(self):
        self.state = "arena"
        self.waiting_for = None
        self.pressed.clear()
        self.hud_clock = 0
        self.renderer.arena(self)
        self.last_dimensions = self.renderer.dimensions()
        self.root.after_idle(self.restore_keyboard_focus)
        self.beep(850)
        self.update_cursor()

    def new_run(self):
        self.world.reset()
        self.persist_run()
        self.equipped_build=None
        self.item_build=ItemBuild()
        self.greeter_defeated=False
        self.state = "map"
        self.renderer.map_screen(self)
        self.last_dimensions = self.renderer.dimensions()
        self.root.after_idle(self.restore_keyboard_focus)
        self.update_cursor()

    def show_map(self):
        if self.state=='arena':
            self.persist_run()
        self.state='map'
        self.pressed.clear()
        self.renderer.map_screen(self)
        self.last_dimensions=self.renderer.dimensions()
        self.update_cursor()

    def select_level_one(self):
        """Second map square opens the three-card item selection."""
        self.state='item_select'
        self.item_message=''
        self.pressed.clear()
        self.renderer.item_select(self)
        self.last_dimensions=self.renderer.dimensions()
        self.update_cursor()

    def select_lance(self):
        self.item_build=ItemBuild.from_dict(self.equipped_build.to_dict()) if self.equipped_build else ItemBuild()
        self.item_message='DISTRIBUTE ALL 10 POINTS'
        self.state='item_config'
        self.pressed.clear()
        self.renderer.item_config(self)
        self.last_dimensions=self.renderer.dimensions()
        self.update_cursor()

    def change_item_stat(self, stat, delta):
        if self.state!='item_config':return
        if self.item_build.change(stat,delta):
            self.item_message=''
        else:
            self.item_message='10 TOTAL POINTS  /  MAX 7 PER STAT'
        self.renderer.item_config(self)
        self.update_cursor()

    def change_item_element(self, element):
        if self.state!='item_config':return
        self.item_build.set_element(element)
        self.item_message=''
        self.renderer.item_config(self)
        self.update_cursor()

    def reset_item_stats(self):
        if self.state!='item_config':return
        self.item_build.stats={key:0 for key in self.item_build.stats}
        self.item_message='POINTS RESET'
        self.renderer.item_config(self)
        self.update_cursor()

    def start_training(self):
        if self.state!='item_config':return
        if not self.item_build.valid():
            self.item_message=f'SPEND ALL {self.item_build.remaining} REMAINING POINTS FIRST'
            self.renderer.item_config(self)
            self.update_cursor()
            return
        self.equipped_build=ItemBuild.from_dict(self.item_build.to_dict())
        self.world.start_training(self.equipped_build)
        self.hud_unlocked=True
        self.right_panel_unlocked=False
        self.persist_run()
        self.enter_arena()

    def select_boss(self):
        self.world.reset()
        self.persist_run()
        self.pressed.clear()
        self.state = "dialogue"
        self.dialogue_step = 0
        self.tutorial_step = 0
        self.tutorial_seen = set()
        self.hud_unlocked = False
        self.right_panel_unlocked = False
        self.renderer.dialogue(self)
        self.last_dimensions = self.renderer.dimensions()
        self.root.after_idle(self.restore_keyboard_focus)
        self.screen.update()
        self.update_cursor()

    def advance_dialogue(self):
        self.dialogue_step += 1
        if self.dialogue_step >= 2:
            self.begin_tutorial(1)
        else:
            self.renderer.dialogue(self)
            self.screen.update()
            self.update_cursor()

    def begin_tutorial(self,step):
        """Freeze the boss, hazards and player until the instruction is read."""
        self.tutorial_step = step
        self.tutorial_seen.add(step)
        self.state = 'tutorial'
        self.pressed.clear()
        self.renderer.tutorial(self)
        self.last_dimensions = self.renderer.dimensions()
        self.update_cursor()

    def advance_tutorial(self):
        if self.state != 'tutorial':return
        if self.tutorial_step==1:
            self.begin_tutorial(2)
            return
        if self.tutorial_step==2:
            self.hud_unlocked=True
        if self.tutorial_step==3:
            self.right_panel_unlocked=True
        self.enter_arena()

    def check_tutorial_triggers(self):
        if 3 not in self.tutorial_seen and self.world.stage == 'exit_for_spikes':
            self.begin_tutorial(3)
            return True
        if 4 not in self.tutorial_seen and self.world.stage == 'pulses':
            self.begin_tutorial(4)
            return True
        if 5 not in self.tutorial_seen and self.world.health_pickup is not None:
            self.begin_tutorial(5)
            return True
        return False

    def start_victory_dialogue(self):
        self.greeter_defeated=True
        self.state='victory_dialogue'
        self.dialogue_step=0
        self.persist_run()
        self.renderer.dialogue(self)
        self.update_cursor()

    def advance_victory_dialogue(self):
        self.dialogue_step+=1
        if self.dialogue_step>=2:
            self.state='map'
            self.renderer.map_screen(self)
        else:
            self.renderer.dialogue(self)
        self.update_cursor()

    def continue_run(self):
        """Saved runs return to boss selection, never directly to combat."""
        if not SAVE_FILE.exists():
            return
        saved=load_run()
        self.world.restore(saved)
        self.greeter_defeated=saved.get('greeter_defeated',False) is True
        self.equipped_build=ItemBuild.from_dict(saved['equipped_item']) if isinstance(saved.get('equipped_item'),dict) else None
        self.item_build=ItemBuild.from_dict(self.equipped_build.to_dict()) if self.equipped_build else ItemBuild()
        self.state = "map"
        self.pressed.clear()
        self.renderer.map_screen(self)
        self.last_dimensions = self.renderer.dimensions()
        self.root.after_idle(self.restore_keyboard_focus)
        self.update_cursor()

    def open_settings(self):
        self.settings_origin = "arena" if self.state == "arena" else "menu"
        self.state = "settings"
        self.pressed.clear()
        self.waiting_for = None
        self.settings_message = ""
        self.renderer.settings(self)
        self.last_dimensions = self.renderer.dimensions()
        self.beep()
        self.update_cursor()

    def pause(self):
        if self.state == "arena":
            self.open_settings()  # The pause menu IS the regular Settings UI.
        elif self.state == "settings" and self.settings_origin == "arena":
            if not self.waiting_for:
                self.exit_settings()

    def exit_settings(self):
        self.waiting_for = None
        self.settings_message = ""
        if self.settings_origin == "arena":
            self.enter_arena()
        else:
            self.show_menu()

    def refresh_settings(self):
        if self.state == "settings":
            self.renderer.settings(self)
            self.last_dimensions = self.renderer.dimensions()
            self.root.after_idle(self.restore_keyboard_focus)

    def toggle_sound(self):
        self.settings["sound"] = not self.settings["sound"]
        self.persist_settings()
        self.beep(850)
        self.refresh_settings()

    def toggle_debug(self):
        self.settings["debug"] = not self.settings["debug"]
        self.persist_settings()
        if self.state == "settings":
            self.refresh_settings()
        elif self.state == "arena":
            self.renderer.arena(self)

    def toggle_fullscreen(self):
        self.settings["fullscreen"] = not self.settings["fullscreen"]
        self.set_fullscreen(self.settings["fullscreen"])
        self.persist_settings()
        self.redraw()

    def start_rebind(self, action):
        self.waiting_for = action
        self.settings_message = ""
        self.refresh_settings()
        self.beep(940)

    def reset_bindings(self):
        self.settings["bindings"] = DEFAULT_BINDINGS.copy()
        self.waiting_for = None
        self.settings_message = "DEFAULT CONTROLS RESTORED"
        self.persist_settings()
        self.refresh_settings()
        self.beep(900)

    def rebind(self, key):
        action = self.waiting_for
        if action is None:
            return
        if key == "Escape":
            self.waiting_for = None
            self.settings_message = "REBIND CANCELLED"
            self.refresh_settings()
            return
        if key in FIXED_KEYS:
            self.settings_message = f"{pretty_key(key)} IS RESERVED FOR SYSTEM CONTROLS"
            self.refresh_settings()
            return
        if action.startswith("Move ") and key.startswith("Mouse"):
            self.settings_message = "MOVEMENT MUST USE A KEYBOARD KEY"
            self.refresh_settings()
            return
        bindings = self.settings["bindings"]
        old_key = bindings[action]
        conflict = next((name for name, other in bindings.items()
                         if name != action and other == key), None)
        if conflict:
            if conflict.startswith("Move ") and old_key.startswith("Mouse"):
                self.settings_message = "CAN'T SWAP A MOUSE KEY INTO MOVEMENT"
                self.refresh_settings()
                return
            bindings[conflict] = old_key
            self.settings_message = f"SWAPPED {action} AND {conflict}"
        else:
            self.settings_message = f"{action} SET TO {pretty_key(key)}"
        bindings[action] = key
        self.waiting_for = None
        self.persist_settings()
        self.refresh_settings()
        self.beep(900)

    @staticmethod
    def normalize_key(key):
        return key.lower() if len(key)==1 else key

    def on_key_down(self, event):
        key = self.normalize_key(event.keysym)
        if self.state == "settings" and self.waiting_for:
            if key not in self.pressed:
                self.rebind(key)
            return
        if key in self.pressed:
            return
        self.pressed.add(key)
        if key == "F11":
            self.toggle_fullscreen()
            return
        if key == "F3":
            self.toggle_debug()
            return
        if self.state == "arena":
            if key in ("p", "Escape"):
                self.pause()
                return
            if key == "j" and self.settings["debug"]:
                if self.world.take_debug_hit():
                    self.state = "gameover"
                    self.persist_run()
                    self.renderer.game_over(self)
                else:
                    self.beep(230, 110)
                return
            for name, binding in self.settings["bindings"].items():
                if key == binding and name in ACTION_NAMES:
                    self.trigger(name)
                    break
        elif self.state == "tutorial":
            if key == "Return":
                self.advance_tutorial()
        elif self.state == "dialogue":
            if key == "Return":
                self.advance_dialogue()
        elif self.state == "victory_dialogue":
            if key == "Return":
                self.advance_victory_dialogue()
        elif self.state == "map":
            if key == "Escape":
                self.show_menu()
        elif self.state == 'item_select':
            if key=='Escape':self.show_map()
        elif self.state == 'item_config':
            if key=='Escape':self.select_level_one()
        elif self.state == "settings":
            if key in ("Escape", "p") and self.settings_origin == "arena":
                self.exit_settings()
            elif key == "Escape":
                self.show_menu()

    def on_key_up(self, event):
        self.pressed.discard(self.normalize_key(event.keysym))

    def _hide_native_cursor(self):
        """Hide Windows system arrow while hovering inside the game window."""
        if sys.platform != 'win32' or self._windows_cursor_hide_count:
            return
        try:
            import ctypes
            user32=ctypes.windll.user32
            # ShowCursor uses an internal counter; hide until negative.
            for _ in range(32):
                self._windows_cursor_hide_count+=1
                if user32.ShowCursor(False)<0:
                    break
        except (AttributeError, OSError):
            self._windows_cursor_hide_count=0

    def _restore_native_cursor(self):
        if not self._windows_cursor_hide_count:
            return
        try:
            import ctypes
            for _ in range(self._windows_cursor_hide_count):
                ctypes.windll.user32.ShowCursor(True)
        except (AttributeError, OSError):
            pass
        self._windows_cursor_hide_count=0

    def on_window_destroyed(self,event):
        if event.widget is self.root:
            self._restore_native_cursor()

    def on_pointer_enter(self,event):
        self.pointer_in_canvas=True
        self._hide_native_cursor()
        self.update_cursor()

    def on_pointer_leave(self,event):
        self.pointer_in_canvas=False
        self._restore_native_cursor()
        self.update_cursor()

    def on_focus_gained(self,event):
        # FocusIn also fires for children; only hide if pointer is inside.
        if self.pointer_in_canvas:
            self._hide_native_cursor()

    def on_focus_lost(self, event):
        self.pressed.clear()
        self._restore_native_cursor()

    def _canvas_to_screen(self, event):
        # Screen origin is centered; canvas handles pixel translation.
        return event.x-self.canvas.winfo_width()/2, self.canvas.winfo_height()/2-event.y

    def on_mouse_move(self, event):
        x,y=self._canvas_to_screen(event)
        self.cursor_position=x,y
        self.pointer_in_canvas=True
        self._hide_native_cursor()
        if self.state=='arena' and self.renderer.in_arena(x,y):
            self.aim=(x,y)
            tx,ty=self.renderer.world_from_screen(x,y)
            self.world.shot_aim_distance=math.hypot(tx-self.world.x,ty-self.world.y)
        if self.state=='map':
            self.renderer.map_hover(self,x,y)
        # Tk cursor items update directly: no screen.update() inside a Motion
        # callback. Re-entering Tk's event loop here caused RecursionError.
        self.update_cursor()

    def on_left_click(self, x, y):
        self.mouse_click(x, y, "Mouse1")

    def on_middle_click(self, x, y):
        self.mouse_click(x, y, "Mouse2")

    def on_right_click(self, x, y):
        self.mouse_click(x, y, "Mouse3")

    def mouse_click(self, x, y, key):
        self.root.after_idle(self.restore_keyboard_focus)
        if self.state == "settings" and self.waiting_for:
            self.rebind(key)
            return
        # Dialogue and Quick Tips advance with Enter only. Mouse clicks do
        # not dismiss them (or leak through into an attack).
        if self.state in ('dialogue','victory_dialogue','tutorial'):
            return
        if key == "Mouse1" and self.renderer.click(x, y):
            return
        if self.state != "arena" or not self.renderer.in_arena(x,y):
            return
        self.aim=(x,y)
        tx,ty=self.renderer.world_from_screen(x,y)
        self.world.shot_aim_distance=math.hypot(tx-self.world.x,ty-self.world.y)
        for action, binding in self.settings["bindings"].items():
            if action in ACTION_NAMES and key == binding:
                self.trigger(action)
                break

    def direction_pressed(self):
        b = self.settings["bindings"]
        dx = int(b["Move Right"] in self.pressed)-int(b["Move Left"] in self.pressed)
        dy = int(b["Move Up"] in self.pressed)-int(b["Move Down"] in self.pressed)
        magnitude = math.hypot(dx,dy)
        return (dx/magnitude,dy/magnitude) if magnitude else (0.0,0.0)

    def attack_direction(self):
        if self.aim and self.renderer.in_arena(*self.aim):
            tx,ty = self.renderer.world_from_screen(*self.aim)
            dx,dy = tx-self.world.x,ty-self.world.y
            size=math.hypot(dx,dy)
            if size>.001:
                return dx/size,dy/size
        return self.world.facing

    def trigger(self, action):
        if self.state != "arena":
            return
        if action=="Dash":
            direction=self.direction_pressed()
            if direction==(0.0,0.0):
                direction=self.world.facing
        elif action=='Shoot':
            direction=self.attack_direction()
            # Keyboard-rebound shots use the live mouse position too.
            if self.aim and self.renderer.in_arena(*self.aim):
                tx,ty=self.renderer.world_from_screen(*self.aim)
                self.world.shot_aim_distance=math.hypot(tx-self.world.x,ty-self.world.y)
        else:
            direction=self.world.facing
        if self.world.activate(action,direction):
            notes={"Dash":950, "Shoot":970,
                   "Chestplate":650, "Item 1":720,"Item 2":790,
                   "Item 3":830,"Item 4":870}
            self.beep(notes[action], 48)

    def redraw(self):
        if self.state == "arena":
            self.renderer.arena(self)
        elif self.state == "tutorial":
            self.renderer.tutorial(self)
        elif self.state == "settings":
            self.renderer.settings(self)
        elif self.state == "menu":
            self.renderer.menu(self)
        elif self.state == "gameover":
            self.renderer.game_over(self)
        elif self.state == "map":
            self.renderer.map_screen(self)
        elif self.state=='item_select':
            self.renderer.item_select(self)
        elif self.state=='item_config':
            self.renderer.item_config(self)
        elif self.state in ("dialogue","victory_dialogue"):
            self.renderer.dialogue(self)
        self.last_dimensions = self.renderer.dimensions()
        self.update_cursor()

    def tick(self):
        if self.closed:
            return
        now=time.monotonic()
        dt=min(.05,max(0,now-self.last_tick))
        self.last_tick=now
        if dt>.0001:
            instant_fps=min(100,1/dt)
            self.fps=.9*self.fps+.1*instant_fps
        current_size=self.renderer.dimensions()
        if current_size!=self.last_dimensions:
            self.redraw()
        if self.state == "arena":
            dx,dy=self.direction_pressed()
            self.world.move(dx,dy,dt)
            if self.aim and self.renderer.in_arena(*self.aim):
                tx,ty=self.renderer.world_from_screen(*self.aim)
                self.world.shot_aim_distance=math.hypot(tx-self.world.x,ty-self.world.y)
            self.world.update(dt)
            if not self.world.training:
                self.world.update_boss(dt)
            if not self.world.training and self.world.dummy_hp<=0:
                self.start_victory_dialogue()
                self.screen.ontimer(self.tick,16)
                return
            if not self.world.training and self.world.lives <= 0:
                self.state = "gameover"
                self.renderer.game_over(self)
                self.update_cursor()
                self.screen.ontimer(self.tick,16)
                return
            if not self.world.training and self.check_tutorial_triggers():
                self.screen.ontimer(self.tick,16)
                return
            self.renderer.display_live(self)
            self.hud_clock+=dt
            self.save_clock+=dt
            if self.hud_clock>=.11:
                self.hud_clock=0
                self.renderer.draw_dynamic(self)
            # Draw after the HUD so the ring remains visible past arena edges.
            self.renderer.draw_timing_ring(self)
            self.renderer.screen.update()
            # Tk Canvas cursor lives above Turtle's rendering layer.
            self.update_cursor()
            if self.save_clock>=7:
                self.save_clock=0
                self.persist_run()
        self.screen.ontimer(self.tick, 16)

    def close(self):
        self.closed=True
        self._restore_native_cursor()
        if self.state == "arena" or (self.state == "settings" and self.settings_origin == "arena"):
            self.persist_run()
        self.persist_settings()
        try:
            self.screen.bye()
        except turtle.Terminator:
            pass
