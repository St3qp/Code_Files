"""All Turtle drawing, including the responsive 16:9 arena and sidebars."""
import math
import turtle
from items import STATS, ELEMENTS, POINT_BUDGET
from config import (BG, PANEL, PANEL_DARK, BUTTON, BORDER, TEXT, MUTED,
                    CYAN, RED, GOLD, GREEN, PURPLE, WORLD_W, WORLD_H,
                    PLAYER_RADIUS, DUMMY_RADIUS, pretty_key)


class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.base = self._pen()
        self.hud = self._pen()
        self.effects = self._pen()
        self.player = turtle.Turtle(visible=False)
        self.player.penup()
        self.player.speed(0)
        self.player.shape("square")
        self.player.color(CYAN)
        self.dummy = turtle.Turtle(visible=False)
        self.dummy.penup()
        self.dummy.speed(0)
        self.dummy.shape("circle")
        self.dummy.color(PURPLE)
        self.buttons = []
        self.move_hitboxes = []
        self.selected_move = None
        self.move_scroll = 0
        # Four persistent Tk canvas strokes for the yellow # cursor. Updating
        # their coordinates does NOT invoke Turtle.clear() or Tk.update(), so
        # fast mouse motion cannot recursively enter Tk callbacks.
        self.cursor_canvas = self.screen.getcanvas()
        self.cursor_items = [self.cursor_canvas.create_line(0,0,0,0,
            fill='#ffdf00', width=3, capstyle='round', tags='hash_cursor',
            state='hidden') for _ in range(4)]
        self.shot_pen = self._pen()
        self.tutorial_pen = self._pen()
        self.width, self.height = 1200, 800
        self.layout = {}
        self.rendered_state = ""

    @staticmethod
    def _pen():
        pen = turtle.Turtle(visible=False)
        pen.penup()
        pen.speed(0)
        return pen

    def dimensions(self):
        w = max(740, self.screen.window_width())
        h = max(520, self.screen.window_height())
        return w, h

    def set_dimensions(self):
        self.width, self.height = self.dimensions()
        w, h = self.width, self.height
        margin = max(12, min(25, w * .016))
        sidebar = min(245, max(145, w * .145))
        gap = max(10, min(22, w * .014))
        available_width = max(390, w - 2*sidebar - 2*margin - 2*gap)
        # Timing is now around the player, freeing vertical space for the arena.
        available_height = max(220, h - 245)
        scale = min(available_width/WORLD_W, available_height/WORLD_H, 2.8)
        arena_w, arena_h = WORLD_W*scale, WORLD_H*scale
        # Anchor near the top, leaving an independent lower ability strip.
        top = h/2 - 65
        bottom = top-arena_h
        self.layout = {
            "scale": scale, "arena_left": -arena_w/2,
            "arena_right": arena_w/2, "arena_top": top,
            "arena_bottom": bottom, "arena_w": arena_w, "arena_h": arena_h,
            "arena_cy": (top+bottom)/2,
            "side_left": -w/2+margin, "side_width": sidebar,
            "side_right": w/2-margin-sidebar,
            "panel_bottom": bottom,
            "ability_y": -h/2 + 76,
            "ability_h": 130,
        }

    def pt(self, world_x, world_y):
        k = self.layout["scale"]
        return world_x*k, self.layout["arena_cy"] + world_y*k

    def in_arena(self, x, y):
        a = self.layout
        return (a["arena_left"] <= x <= a["arena_right"] and
                a["arena_bottom"] <= y <= a["arena_top"])

    def world_from_screen(self, x, y):
        k = self.layout["scale"]
        return x/k, (y - self.layout["arena_cy"])/k

    def rect(self, pen, x, y, w, h, fill, border=None, thickness=1):
        pen.setheading(0)
        pen.pensize(thickness)
        pen.color(border or fill, fill)
        pen.goto(x, y)
        pen.pendown()
        pen.begin_fill()
        for side in (w, h, w, h):
            pen.forward(side)
            pen.left(90)
        pen.end_fill()
        pen.penup()

    def line(self, pen, x1, y1, x2, y2, color, width=2):
        pen.pensize(width)
        pen.pencolor(color)
        pen.goto(x1, y1)
        pen.pendown()
        pen.goto(x2, y2)
        pen.penup()

    def text(self, pen, content, x, y, size=12, color=TEXT, bold=False, align="left"):
        pen.goto(x, y)
        pen.pencolor(color)
        pen.write(str(content), align=align,
                  font=("Arial", max(8, int(size)), "bold" if bold else "normal"))

    def button(self, label, cx, cy, w, h, callback, accent=False):
        self.rect(self.base, cx-w/2, cy-h/2, w, h, TEXT if accent else BUTTON, BORDER)
        self.text(self.base, label, cx, cy-5, 12, BG if accent else TEXT, True, "center")
        self.buttons.append((cx-w/2, cy-h/2, cx+w/2, cy+h/2, callback))

    def click(self, x, y):
        for x1,y1,x2,y2,name in self.move_hitboxes:
            if x1<=x<=x2 and y1<=y<=y2:
                if name=='_PREV': self.move_scroll=max(0,self.move_scroll-1)
                elif name=='_NEXT':self.move_scroll+=1
                else:self.selected_move=None if self.selected_move==name else name
                return True
        for x1, y1, x2, y2, callback in reversed(self.buttons):
            if x1 <= x <= x2 and y1 <= y <= y2:
                callback()
                return True
        return False

    def reset(self):
        self.base.clear()
        self.hud.clear()
        self.effects.clear()
        self.shot_pen.clear()
        self.tutorial_pen.clear()
        self.player.hideturtle()
        self.dummy.hideturtle()
        self.buttons.clear()
        self.move_hitboxes.clear()
        self.set_dimensions()
        w,h = self.width,self.height
        self.rect(self.base, -w/2, -h/2, w, h, BG)

    def menu(self, game):
        self.reset()
        w,h = self.width,self.height
        self.text(self.base, "#HASH#", 0, h*.23, 47, TEXT, True, "center")
        self.text(self.base, "BOSS-BATTLER  /  ROGUELIKE", 0, h*.17, 13, MUTED, False, "center")
        from config import SAVE_FILE
        has_save = SAVE_FILE.exists()
        if has_save:
            self.button("CONTINUE", 0, 110, 285, 48, game.continue_run, accent=True)
        self.button("NEW RUN", 0, 44 if has_save else 85, 285, 48, game.new_run)
        self.button("SETTINGS", 0, -22 if has_save else 18, 285, 48, game.open_settings)
        self.button("QUIT", 0, -88 if has_save else -49, 285, 48, game.close)
        self.text(self.base, "CHOOSE YOUR BOSS. SURVIVE THE HASH.", 0, -h*.28, 12, MUTED, False, "center")
        self.text(self.base, "P PAUSE   |   F11 FULLSCREEN",
                  0, -h*.34, 11, MUTED, False, "center")
        self.screen.update()

    def map_screen(self, game):
        self.reset()
        self.text(self.base, "#HASH# / BOSS MAP", 0, self.height/2-90, 27, TEXT, True, "center")
        nodes = [(-240,0), (0,0), (240,0)]
        for (x,y),(xx,yy) in zip(nodes,nodes[1:]):
            self.line(self.base,x+26,y,xx-26,yy,TEXT,3)
        for i,(x,y) in enumerate(nodes):
            self.rect(self.base,x-26,y-26,52,52,BG,TEXT,3)
            if i == 0:
                self.text(self.base,"0",x,y-6,14,TEXT,True,"center")
                self.buttons.append((x-26,y-26,x+26,y+26,game.select_boss))
            elif i==1:
                self.text(self.base,"1",x,y-6,14,CYAN,True,"center")
                self.buttons.append((x-26,y-26,x+26,y+26,game.select_level_one))
            else:
                self.text(self.base,"?",x,y-6,14,MUTED,True,"center")
        self.text(self.base,"LEVEL 0: THE GREETER     /     LEVEL 1: TRAINING",0,-110,12,MUTED,False,"center")
        self.button("BACK",0,-self.height/2+75,190,43,game.show_menu)
        self.screen.update()

    def map_hover(self, game, x, y):
        self.hud.clear()
        if -266 <= x <= -214 and -26 <= y <= 26:
            self.text(self.hud,"LEVEL 0  /  THE GREETER",0,-155,16,TEXT,True,"center")
            self.text(self.hud,"CLICK THE FIRST SQUARE TO FIGHT",0,-181,11,MUTED,False,"center")
        elif -26<=x<=26 and -26<=y<=26:
            self.text(self.hud,"LEVEL 1  /  ITEM SELECTION + TRAINING",0,-155,14,CYAN,True,"center")
            self.text(self.hud,"CLICK TO CHOOSE YOUR ITEM",0,-181,11,MUTED,False,"center")
        elif 214<=x<=266 and -26<=y<=26:
            self.text(self.hud,"UNKNOWN BOSS / LOCKED",0,-155,15,TEXT,True,"center")

    def item_select(self,game):
        """Three item choices, with only Lance enabled this version."""
        self.reset()
        h,w=self.height,self.width
        self.text(self.base,'LEVEL 1  /  CHOOSE YOUR ITEM',0,h/2-85,28,TEXT,True,'center')
        self.text(self.base,'EQUIP AN ITEM BEFORE ENTERING THE TRAINING ROOM',0,h/2-122,11,MUTED,False,'center')
        box_w=min(245,(w-100)/3.6)
        centers=(-box_w-23,0,box_w+23)
        card_h=min(295,h*.45)
        for i,cx in enumerate(centers):
            available=i==0
            cy=-5
            self.rect(self.base,cx-box_w/2,cy-card_h/2,box_w,card_h,
                      '#18170a' if available else '#101010',CYAN if available else '#454545',2)
            self.text(self.base,'01' if available else f'0{i+1}',cx,cy+card_h*.29,18,CYAN if available else MUTED,True,'center')
            if available:
                self.line(self.base,cx-28,cy-7,cx+25,cy+47,CYAN,6)
                self.polygon(self.base,[(cx+15,cy+33),(cx+33,cy+55),(cx+37,cy+25)],TEXT)
                self.text(self.base,'LANCE',cx,cy-50,19,TEXT,True,'center')
                self.text(self.base,'DASH STRIKE',cx,cy-77,10,MUTED,False,'center')
                self.button('SELECT',cx,cy-card_h/2+32,box_w-32,38,game.select_lance,True)
            else:
                self.text(self.base,'?',cx,cy+3,50,'#5d5d5d',True,'center')
                self.text(self.base,'LOCKED',cx,cy-50,17,MUTED,True,'center')
                self.text(self.base,'COMING SOON',cx,cy-77,10,MUTED,False,'center')
        self.text(self.base,'LANCE: dash toward the nearest target and strike.',0,-h/2+108,12,TEXT,False,'center')
        self.button('BACK TO MAP',0,-h/2+49,210,40,game.show_map)
        self.screen.update()

    def item_config(self,game):
        """Live 10-point allocation and single-element selection."""
        self.reset()
        h,w=self.height,self.width
        build=game.item_build
        compact=h<670
        title_y=h/2-58
        self.text(self.base,'LANCE  /  CONFIGURATION',0,title_y,24,TEXT,True,'center')
        self.text(self.base,'10 POINTS TOTAL    /    7 MAX PER STAT',0,title_y-29,11,MUTED,False,'center')
        self.text(self.base,f'{build.remaining} POINTS LEFT',0,title_y-52,14,CYAN,True,'center')
        left_x=-min(w*.40,465)
        right_x=min(w*.055,70)
        stat_w=min(w*.46,500)
        gap=41 if compact else 53
        start=h/2-(159 if compact else 182)
        self.text(self.base,'STATS',left_x,start+27,14,TEXT,True)
        for i,name in enumerate(STATS):
            y=start-i*gap
            self.text(self.base,name.upper(),left_x,y,10,TEXT,True)
            button_start=left_x+stat_w-115
            self.rect(self.base,button_start-8,y-11,122,29,'#111111','#565656')
            def stat_button(symbol,cx,delta,enabled):
                col=CYAN if enabled else '#333333'
                self.rect(self.base,cx-14,y-10,28,27,BUTTON,col)
                self.text(self.base,symbol,cx,y-2,13,col,True,'center')
                if enabled:
                    self.buttons.append((cx-14,y-10,cx+14,y+17,
                                         lambda n=name,d=delta:game.change_item_stat(n,d)))
            stat_button('-',button_start+8,-1,build.stats[name]>0)
            self.text(self.base,str(build.stats[name]),button_start+52,y-2,14,CYAN,True,'center')
            stat_button('+',button_start+92,1,build.stats[name]<7 and build.remaining>0)
        self.text(self.base,'DASH SPEED MAKES THE LUNGE FASTER',
                  left_x,start-gap*6+14,9,MUTED)
        self.text(self.base,'ELEMENT',right_x,start+27,14,TEXT,True)
        self.text(self.base,'Choose one effect for your Lance.',right_x,start+6,10,MUTED)
        effect_desc={
            'Fire':'Bonus damage on impact',
            'Thunder':'Stuns your target',
            'Ice':'Slows its movement',
            'Poison':'Damage over time',
            'Air':'Extra knockback',
        }
        elem_w=min(320,w*.37)
        for i,name in enumerate(ELEMENTS):
            y=start-44-i*(41 if compact else 48)
            chosen=build.element==name
            self.rect(self.base,right_x,y-9,elem_w,34,'#302b0e' if chosen else BUTTON,
                      CYAN if chosen else BORDER,2 if chosen else 1)
            self.text(self.base,('● ' if chosen else '○ ')+name.upper(),right_x+12,y+3,11,
                      CYAN if chosen else TEXT,True)
            self.text(self.base,effect_desc[name],right_x+12,y-9,9,MUTED)
            self.buttons.append((right_x,y-9,right_x+elem_w,y+25,
                                 lambda e=name:game.change_item_element(e)))
        bottom=-h/2+55
        self.button('BACK',-min(w*.31,345),bottom,130,40,game.select_level_one)
        self.button('RESET POINTS',0,bottom,167,40,game.reset_item_stats)
        self.button('ENTER TRAINING',min(w*.31,345),bottom,180,40,game.start_training,
                    accent=build.valid())
        if game.item_message:
            self.text(self.base,game.item_message[:67],0,bottom+51,10,CYAN,True,'center')
        else:
            stats=build.lance_stats()
            self.text(self.base,f'DASH STRIKE {stats["damage"]:.0f} DMG   /   {stats["reach"]:.0f} REACH   /   {stats["cooldown"]:.2f}s CD',
                      0,bottom+51,11,CYAN,True,'center')
        self.screen.update()

    def dialogue(self, game):
        # Keep the combat arena visible behind the conversation.
        self.arena(game)
        self.display_live(game,force=True)
        a=self.layout
        self.rect(self.base,a["arena_left"]+12,a["arena_bottom"]+12,
                  a["arena_w"]-24,112,BG,TEXT,2)
        is_player=game.dialogue_step==0
        px=a["arena_left"]+51
        py=a["arena_bottom"]+68
        if is_player:
            self.rect(self.base,px-12,py-12,24,24,PANEL,CYAN,2)
            self.health_hash(self.base,px,py,4,.18,CYAN)
        else:
            self.base.goto(px,py)
            self.base.dot(34,TEXT)
            self.base.goto(px-7,py+4);self.base.dot(9,"#ff243c")
            self.base.goto(px+7,py+4);self.base.dot(9,"#ff243c")
        self.text(self.base,"PLAYER" if is_player else "THE GREETER",
                  px+35,py+10,13,TEXT,True)
        if game.state=='victory_dialogue':
            line=('That was The Greeter. What comes next?' if is_player else
                  'You beat the welcome. The real trial begins now.')
        else:
            line=('So... you are The Greeter?' if is_player else
                  'Welcome to #HASH#. Show me what you can do.')
        self.text(self.base,line,px+35,py-16,12,TEXT)
        self.text(self.base,"PRESS ENTER TO CONTINUE",a["arena_right"]-28,
                  a["arena_bottom"]+26,10,MUTED,False,"right")
        self.screen.update()

    def settings(self, game):
        self.reset()
        w, h = self.width, self.height
        paused = game.settings_origin == "arena"
        self.text(self.base, "PAUSED  /  SETTINGS" if paused else "SETTINGS",
                  0, h/2-74, 29, TEXT, True, "center")
        self.text(self.base, "CLICK A BINDING, THEN PRESS A KEY OR MOUSE BUTTON",
                  0, h/2-106, 11, MUTED, False, "center")
        toggles_y = h/2-148
        self.button("SOUND: " + ("ON" if game.settings["sound"] else "OFF"),
                    -w*.17, toggles_y, min(192, w*.25), 37, game.toggle_sound)
        self.button("FULLSCREEN: " + ("ON" if game.settings["fullscreen"] else "OFF"),
                    w*.17, toggles_y, min(192, w*.25), 37, game.toggle_fullscreen)
        actions = list(game.settings["bindings"].items())
        box_w = min(480, w*.435)
        left_cx, right_cx = -w*.25, w*.25
        gap = max(46, min(68, (h-305)/6))
        for index, (action, key) in enumerate(actions):
            col, row = divmod(index, 6)
            cx = left_cx if col == 0 else right_cx
            cy = h/2 - 216 - row*gap
            selected = game.waiting_for == action
            self.rect(self.base, cx-box_w/2, cy-22, box_w, 44,
                      BUTTON if selected else PANEL, TEXT if selected else BORDER)
            fs = 10 if w<1150 else 12
            self.text(self.base, action.upper(), cx-box_w/2+12, cy-5, fs, TEXT, True)
            self.text(self.base, "PRESS KEY..." if selected else pretty_key(key),
                      cx+box_w/2-12, cy-5, fs-1, TEXT, True, "right")
            self.buttons.append((cx-box_w/2, cy-22, cx+box_w/2, cy+22,
                                 lambda name=action: game.start_rebind(name)))
        msg = (f"PRESS NEW KEY FOR {game.waiting_for}  |  ESC TO CANCEL"
               if game.waiting_for else
               game.settings_message or "ESC TO CANCEL A REBIND; P TO PAUSE")
        self.text(self.base, msg[:95], 0, -h/2+122, 11, GOLD if game.waiting_for else MUTED,
                  False, "center")
        self.button("RESUME" if paused else "BACK", -w*.155, -h/2+66,
                    min(240,w*.27), 43, game.exit_settings, accent=True)
        self.button("RESET BINDS", w*.155, -h/2+66,
                    min(240,w*.27), 43, game.reset_bindings)
        if paused:
            self.button("RETURN TO MENU",0,-h/2+22,260,34,game.return_to_menu)
        self.screen.update()

    def arena(self, game):
        self.reset()
        a = self.layout
        w,h = self.width, self.height
        self.text(self.base, "#HASH#", -w/2+23, h/2-42, 26, TEXT, True)
        self.text(self.base, "TRAINING ROOM / LEVEL 1" if game.world.training else "THE GREETER",
                  0, h/2-41, 21, TEXT, True, "center")
        if game.world.training:
            self.button('MAP',w/2-70,h/2-41,64,31,game.show_map)
        if not game.world.training:
            self.text(self.base, "P : PAUSE", w/2-23, h/2-40, 11, MUTED, True, "right")
        self.rect(self.base, a["side_left"], a["panel_bottom"],
                  a["side_width"], a["arena_h"], PANEL_DARK, BORDER)
        self.rect(self.base, a["side_right"], a["panel_bottom"],
                  a["side_width"], a["arena_h"], PANEL_DARK, BORDER)
        self.rect(self.base, a["arena_left"], a["arena_bottom"],
                  a["arena_w"], a["arena_h"], PANEL, BORDER, 2)
        # Subtle floor marker cross: training area stays empty and uncluttered.
        ax, ay = self.pt(0, 0)
        self.line(self.base, ax-8, ay, ax+8, ay, BORDER, 1)
        self.line(self.base, ax, ay-8, ax, ay+8, BORDER, 1)
        self.text(self.base, "PLAYER", a["side_left"]+14, a["arena_top"]-29,
                  15, TEXT, True)
        if game.settings["debug"]:
            self.text(self.base, "SYSTEM MONITOR", a["side_right"]+14,
                      a["arena_top"]-29, 13, GOLD, True)
        else:
            self.text(self.base, "TARGETS" if game.world.training else "THE GREETER",
                      a["side_right"]+14,a["arena_top"]-29,13,TEXT,True)
        # Bottom ability panel separate from gameplay, fixed screen placement.
        if game.hud_unlocked:
            bottom_panel_left = -min(590,w*.46)
            bottom_panel_w = -2*bottom_panel_left
            self.rect(self.base, bottom_panel_left, -h/2+13, bottom_panel_w,
                      130, PANEL_DARK, BORDER)
            self.text(self.base, "ABILITIES", bottom_panel_left+18,
                      -h/2+119, 12, TEXT, True)
            self.text(self.base,
                      "WASD MOVE  |  1 LANCE  |  L-CLICK TIMED SHOT  |  SHIFT DASH  |  CTRL GUARD"
                      if game.world.training else
                      "WASD MOVE  |  SHIFT DASH  |  L-CLICK TIMED SHOT  |  CTRL GUARD",
                      0, a["arena_bottom"]-13, 9, MUTED, False, "center")
        self.draw_dynamic(game)
        self.draw_timing_ring(game)
        self.screen.update()

    def draw_timing_ring(self, game):
        """Draw the shot window around the moving player, not in a separate HUD.

        Both arc and white marker use the same normalized timing values as
        World.attempt_shot. The ring deliberately OVERFLOWS the arena so it
        stays visible when the player hugs a wall or corner.
        """
        from combat import YELLOW
        p=self.shot_pen
        p.clear()
        if game.state not in ('arena','tutorial'):
            return
        if not game.hud_unlocked and not (game.state=='tutorial' and game.tutorial_step in (1,2,3)):
            return
        w=game.world
        k=self.layout['scale']
        radius=67.0
        n=56
        lo,hi=w.shot_zone()
        locked=w.cooldowns['Shoot']>0
        for i in range(n):
            a=i/n
            b=(i+1)/n
            angle_a=math.pi/2-math.tau*a
            angle_b=math.pi/2-math.tau*b
            # Clockwise from top: x=cos(theta), y=sin(theta).
            xa=w.x+radius*math.cos(angle_a)
            ya=w.y+radius*math.sin(angle_a)
            xb=w.x+radius*math.cos(angle_b)
            yb=w.y+radius*math.sin(angle_b)
            in_target=(a+b)/2>=lo and (a+b)/2<=hi
            color=('#8c7615' if locked else YELLOW) if in_target else '#595959'
            x1,y1=self.pt(xa,ya)
            x2,y2=self.pt(xb,yb)
            self.line(p,x1,y1,x2,y2,color,4 if in_target else 2)
        angle=math.pi/2-math.tau*w.shot_marker
        mx=w.x+radius*math.cos(angle)
        my=w.y+radius*math.sin(angle)
        sx,sy=self.pt(mx,my)
        p.goto(sx,sy)
        p.dot(8 if not locked else 6,'#ffffff' if not locked else '#8a8a8a')
        if locked:
            # Keep the recovery unobtrusive but legible near the character.
            px,py=self.pt(w.x,w.y)
            label='MISS' if w.shot_miss_flash>0 else f'{w.cooldowns["Shoot"]:.1f}s'
            self.text(p,label,px,py-85*k,9,YELLOW if w.shot_miss_flash>0 else MUTED,True,'center')

    def tutorial(self,game):
        """Game remains visibly frozen under a centered instruction panel."""
        from combat import YELLOW
        self.arena(game)
        self.display_live(game,force=True)
        self.draw_timing_ring(game)
        p=self.tutorial_pen
        p.clear()
        a=self.layout
        cy=a['arena_cy']
        width=min(a['arena_w']-30,530)
        height=min(245,a['arena_h']-15)
        bottom=cy-height/2
        self.rect(p,-width/2,bottom,width,height,BG,TEXT,2)
        # Keep each card readable at a glance, even during a busy boss fight.
        pages={
            1:('HOW TO SHOOT',
               ('Watch the ring around your #.',
                'LEFT CLICK when white meets YELLOW.',
                'Missed clicks briefly lock your shot.')),
            2:('YOUR HUD',
               ('Four # lines = four hits.',
                'Right panel: boss health.',
                'SHIFT to dash. CTRL to guard.')),
            3:('BOSS MOVES',
               ('Phase 1 complete. Boss intel unlocked!',
                'Click a move in the right panel',
                'to learn its attack pattern.')),
            4:('DASH THROUGH WAVES',
               ('SHIFT to dash through the expanding rings.',
                'You cannot be hit during your dash.',
                'Your dash recharges before the next wave.')),
            5:('HASH PICKUP',
               ('A floating yellow # restores ONE life line.',
                'Walk into it to collect it.',
                'Grab it before it disappears!')),
        }
        title,lines=pages.get(game.tutorial_step,('TIP',()))
        # A compact, high-contrast card with large type and generous spacing.
        width=min(a['arena_w']-22,525)
        height=min(208,a['arena_h']-16)
        bottom=cy-height/2
        p.clear()
        self.rect(p,-width/2,bottom,width,height,BG,'#aaaaaa',2)
        self.text(p,'QUICK TIP',0,cy+height/2-25,10,MUTED,True,'center')
        self.text(p,title,0,cy+height/2-57,18,YELLOW,True,'center')
        start=cy+height/2-92
        gap=min(30,max(21,(height-120)/max(1,len(lines)-1)))
        for index,line in enumerate(lines):
            self.text(p,line,0,start-index*gap,12,TEXT,False,'center')
        self.text(p,'PRESS ENTER TO CONTINUE  >',0,bottom+15,11,YELLOW,True,'center')
        self.screen.update()

    def health_hash(self, pen, cx, cy, strokes, scale=1.0,
                    color=TEXT, dim_missing=False):
        """4 independent # strokes; missing lines actually disappear."""
        segments = [(-13,-37,-13,37), (13,-37,13,37),
                    (-35,-13,35,-13), (-35,13,35,13)]
        for n, (x1,y1,x2,y2) in enumerate(segments):
            if n >= strokes and not dim_missing:
                continue
            self.line(pen, cx+x1*scale, cy+y1*scale,
                      cx+x2*scale, cy+y2*scale,
                      color if n<strokes else '#343434', max(1,4*scale))

    def draw_dynamic(self, game):
        self.hud.clear()
        a = self.layout
        world = game.world
        lx = a["side_left"]+13
        rx = a["side_right"]+13
        top = a["arena_top"]
        sw = a["side_width"]
        k = min(1.4, a["arena_h"]/450)
        compact = sw < 195
        big = 11 if compact else 13
        small = 9 if compact else 11
        self.health_hash(self.hud, lx+sw/2-13, top-117*k, world.lives, k)
        self.text(self.hud, "CHEST", lx, top-207*k, big, TEXT, True)
        guard = world.guard_timer
        guard_cd = world.cooldowns["Chestplate"]
        guard_label = ("ACTIVE  %.1fs" % guard if guard>0 else
                       "COOLDOWN  %.1fs" % guard_cd if guard_cd>0 else "READY")
        self.text(self.hud, guard_label, lx, top-232*k, small,
                  GREEN if guard>0 else GOLD if guard_cd>0 else MUTED)
        self.text(self.hud, "BOOTS", lx, top-270*k, big, TEXT, True)
        self.text(self.hud, "MOVEMENT ACTIVE", lx, top-293*k,
                  small, GREEN)
        self.text(self.hud, "DASH", lx, top-341*k, big, TEXT, True)
        dash = world.cooldowns["Dash"]
        self.text(self.hud, ("PROTECTED" if world.dash_iframes>0 else
                             f"{dash:.1f}s" if dash>0 else "READY"),
                  lx, top-364*k, small, TEXT if dash<=0 else GOLD)
        self.text(self.hud, "LANCE" if world.training else "HASH PICKUP", lx, top-410*k, big, TEXT, True)
        self.text(self.hud,
                  f"{world.lance_build.element.upper()} / SLOT 1" if world.training else
                  ("ON FIELD" if world.health_pickup else "NONE"),
                  lx, top-434*k, small, CYAN if (world.training or world.health_pickup) else MUTED)
        if game.settings["debug"]:
            self.move_hitboxes=[]
            self.draw_debug(game)
        else:
            if game.hud_unlocked:
                if world.training:
                    self.draw_training_info(game,rx,top,sw,small,big)
                else:
                    self.draw_boss_info(game,rx,top,sw,small,big)
            else:
                self.move_hitboxes=[]

        if game.hud_unlocked:
            self._ability_hud(world, a)
        if world.message_timer>0:
            self.text(self.hud, world.message, 0, a["arena_top"]-31,
                      10, GOLD, True, "center")

    def draw_training_info(self,game,rx,top,sw,small,big):
        w=game.world
        self.move_hitboxes=[]
        scale=min(1.0,self.layout['arena_h']/450)
        label_size=max(8,small-1) if scale<.8 else small
        self.text(self.hud,'LANCE BUILD',rx,top-56*scale,big,CYAN,True)
        self.text(self.hud,'ELEMENT: '+w.lance_build.element.upper(),rx,top-89*scale,label_size,TEXT)
        self.text(self.hud,'HITS: '+str(w.training_hits),rx,top-123*scale,label_size,MUTED)
        self.text(self.hud,'TARGETS DOWN: '+str(w.training_kills),rx,top-151*scale,label_size,MUTED)
        self.text(self.hud,'PRACTICE TARGETS',rx,top-199*scale,max(8,small-1),TEXT,True)
        for i,target in enumerate(w.training_targets):
            label=f'DUMMY {i+1}: '+('RESET...' if target.respawn>0 else f'{target.hp:.0f} HP')
            self.text(self.hud,label,rx,top-(227+i*29)*scale,max(8,small-1),
                      CYAN if target.respawn>0 else MUTED)
        self.text(self.hud,'PRESS 1 TO DASH',rx,top-345*scale,label_size,CYAN,True)
        self.text(self.hud,'AUTO-LOCKS ON TARGET',rx,top-370*scale,max(8,small-1),MUTED)
        self.text(self.hud,'MAP TO REBUILD',rx,top-395*scale,max(8,small-1),MUTED)

    def draw_boss_info(self,game,rx,top,sw,small,big):
        w=game.world
        self.move_hitboxes=[]
        self.text(self.hud,"BOSS HEALTH",rx,top-49,small,MUTED,True)
        bar_w=sw-26
        self.rect(self.hud,rx,top-70,bar_w,12,'#313131')
        if w.dummy_hp>0:
            self.rect(self.hud,rx,top-70,max(0,bar_w*w.dummy_hp/w.dummy_max_hp),12,TEXT)
        self.text(self.hud,f"{int(w.dummy_hp)} / {int(w.dummy_max_hp)}",rx,top-91,
                  max(8,small-1),MUTED)
        self.text(self.hud,w.dummy_phase,rx,top-117,big,TEXT,True)
        if not game.right_panel_unlocked:
            self.text(self.hud,'MOVE INTEL LOCKED',rx,top-153,small,MUTED,True)
            return
        self.text(self.hud,"DISCOVERED MOVES",rx,top-145,big,TEXT,True)
        if not w.discovered_moves:
            self.text(self.hud,"NONE YET",rx,top-166,small,MUTED)
            return
        visible=4
        self.move_scroll=max(0,min(self.move_scroll,len(w.discovered_moves)-visible))
        shows=w.discovered_moves[self.move_scroll:self.move_scroll+visible]
        for i,name in enumerate(shows):
            y=top-169-i*25
            active=self.selected_move==name
            self.rect(self.hud,rx,y-7,sw-24,22,'#1b1b1b' if active else '#090909',BORDER)
            self.text(self.hud,('v ' if active else '> ')+name,rx+4,y,
                      max(8,small-1),TEXT if active else MUTED)
            self.move_hitboxes.append((rx,y-7,rx+sw-24,y+15,name))
        if len(w.discovered_moves)>visible:
            y=top-169-25*len(shows)-6
            self.text(self.hud,'< PREV' if self.move_scroll else '  PREV',rx,y,small,
                      TEXT if self.move_scroll else MUTED)
            self.text(self.hud,'NEXT >' if self.move_scroll+visible<len(w.discovered_moves)
                      else '  NEXT',rx+sw-24,y,small,
                      TEXT if self.move_scroll+visible<len(w.discovered_moves) else MUTED,
                      False,'right')
            if self.move_scroll:self.move_hitboxes.append((rx,y-10,rx+sw/2,y+8,'_PREV'))
            if self.move_scroll+visible<len(w.discovered_moves):
                self.move_hitboxes.append((rx+sw/2,y-10,rx+sw-24,y+8,'_NEXT'))
        selected=self.selected_move
        if selected and selected in w.discovered_moves:
            iy=top-169-25*len(shows)-(43 if len(w.discovered_moves)>visible else 19)
            short=self.layout['arena_h']<395
            self.draw_move_icon(self.hud,selected,rx+bar_w/2,iy,bar_w,short)
            lines=w.MOVE_DESCRIPTIONS.get(selected,())
            if short: lines=lines[:2]
            for j,line in enumerate(lines):
                self.text(self.hud,line,rx+3,iy-(40 if short else 47)-j*15,
                          max(8,small-2),MUTED)

    def draw_move_icon(self,p,name,cx,cy,width,short=False):
        """Each unlocked move has a tiny vector illustration, no art assets needed."""
        from combat import NEON
        left=cx-width/2+7
        self.rect(p,left,cy-(28 if short else 32),width-14,
                  56 if short else 61,'#050505','#545454')
        if name=='BOUNCY BALLS':
            for dx,dy in ((-40,10),(-8,-14),(30,14)):
                p.goto(cx+dx,cy+dy);p.dot(12,NEON)
            self.line(p,cx-57,cy-27,cx+54,cy+26,TEXT,1)
        elif name=='RED DOTS':
            for dx in (-30,0,30):
                for dy in (-22,0,22):
                    p.goto(cx+dx,cy+dy);p.dot(8,NEON)
        elif name=='EYE LASERS':
            self.line(p,cx-53,cy+24,cx+42,cy-27,NEON,3)
            self.line(p,cx+42,cy-27,cx+43,cy+26,NEON,3)
            self.line(p,cx+43,cy+26,cx-53,cy+24,NEON,3)
        elif name=='SPIKE RAIN':
            for dx in (-33,0,33):
                self.line(p,cx+dx,cy+25,cx+dx-12,cy-25,NEON,3)
        elif name=='SLAM':
            p.goto(cx,cy+4);p.dot(37,TEXT)
            self.line(p,cx-55,cy-25,cx+55,cy-25,NEON,4)
        elif name=='PULSE':
            for radius in (12,23,32):self._circle_outline(p,cx,cy,radius,NEON,2)
        elif name=='TRACKING LASERS':
            for dx in (-14,14):
                p.goto(cx+dx,cy+15);p.dot(9,NEON)
                self.line(p,cx+dx,cy+15,cx+dx*3,cy-27,NEON,3)
        else:
            self.line(p,cx-25,cy-25,cx+26,cy-25,TEXT,2)
            self.line(p,cx+26,cy-25,cx,cy+25,TEXT,2)
            self.line(p,cx,cy+25,cx-25,cy-25,TEXT,2)
            p.goto(cx+43,cy+15);p.dot(9,NEON)

    def _ability_hud(self, world, a):
        y = -self.height/2+36
        panel_half = min(590, self.width*.46)
        usable = 2*panel_half-45
        slot_w = usable/4
        for n in range(4):
            name = f"Item {n+1}"
            x = -panel_half+18+n*slot_w
            remaining = world.cooldowns[name]
            active = world.active[name]>0
            self.rect(self.hud, x, y, slot_w-9, 54,
                      "#234957" if active else PANEL, GREEN if active else BORDER)
            label = str(n+1)+(f"  LANCE [{world.lance_build.element.upper()}]" if n==0 and world.training else "  EMPTY SLOT")
            self.text(self.hud, label, x+8, y+33,10, CYAN if n==0 and world.training else TEXT, True)
            status = "ACTIVE" if active else f"{remaining:.1f}s" if remaining>0 else "READY"
            self.text(self.hud, status, x+8, y+12,
                      11, GREEN if active else GOLD if remaining>0 else MUTED)

    def draw_debug(self, game):
        # This completely replaces the right boss sidebar, not overlays it.
        a=self.layout
        pen=self.hud
        x=a["side_right"]+12
        top=a["arena_top"]
        world=game.world
        small=9 if a["side_width"]<210 else 11
        data=[
            ("FPS", f"{game.fps:.0f}"),
            ("X", f"{world.x:.1f}"),
            ("Y", f"{world.y:.1f}"),
            ("VX", f"{world.velocity[0]:.0f}"),
            ("VY", f"{world.velocity[1]:.0f}"),
            ("FACING", f"{world.facing[0]:.2f},{world.facing[1]:.2f}"),
            ("LINES", f"{world.lives}/4"),
            ("BOSS HP", f"{world.dummy_hp:.0f}"),
            ("SHOT POS", f"{world.shot_marker:.2f}"),
            ("SHOT ZONE", f"{world.shot_zone_center:.2f}"),
            ("STAGE", world.stage),
            ("BALLS", str(len(world.enemy_balls))),
            ("DOTS", str(len(world.dots))),
            ("HUNTERS", str(len(world.triangles))),
            ("SPIKES", str(len(world.spikes))),
            ("PULSES", str(len(world.pulses))),
            ("PARTICLES", str(len(world.particles))),
            ("LAST", world.last_action),
            ("DASH CD", f"{world.cooldowns['Dash']:.2f}s"),
            ("SHOT CD", f"{world.cooldowns['Shoot']:.2f}s"),
            ("PICKUP", str(world.health_pickup is not None)),
            ("MOVING", str(bool(game.pressed))),
            ("SCALE", f"{a['scale']:.2f}"),
        ]
        gap = min(24, max(11, (a["arena_h"]-65)/len(data)))
        for index, (name,val) in enumerate(data):
            self.text(pen, f"{name}: {val}"[:32], x, top-59-index*gap, small,
                      TEXT if index%2 == 0 else MUTED)

    def polygon(self,pen,points,fill,border=None,width=1):
        if len(points)<3:
            return
        pen.pensize(width)
        pen.color(border or fill,fill)
        pen.goto(*points[0]);pen.pendown();pen.begin_fill()
        for xy in points[1:]: pen.goto(*xy)
        pen.goto(*points[0]);pen.end_fill();pen.penup()

    @staticmethod
    def clip_polygon(points,xmin,xmax,ymin,ymax):
        """Clip giant boss circle to arena, even while half off-screen."""
        def clip(poly,axis,limit,keep_greater):
            out=[]
            for a,b in zip(poly,poly[1:]+poly[:1]):
                aa=a[axis]-limit
                bb=b[axis]-limit
                ina=aa>=0 if keep_greater else aa<=0
                inb=bb>=0 if keep_greater else bb<=0
                if ina!=inb:
                    t=aa/(aa-bb) if aa!=bb else 0
                    out.append((a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])))
                if inb: out.append(b)
            return out
        for axis,limit,greater in ((0,xmin,True),(0,xmax,False),
                                   (1,ymin,True),(1,ymax,False)):
            if not points:break
            points=clip(points,axis,limit,greater)
        return points

    def draw_boss(self,w,p):
        if w.dummy_hp<=0:return
        from combat import NEON
        a=self.layout
        bx,by=self.pt(w.dummy_x,w.dummy_y)
        r=DUMMY_RADIUS*a['scale']
        vertices=[(bx+r*math.cos(i*math.tau/52),
                   by+r*math.sin(i*math.tau/52)) for i in range(52)]
        vertices=self.clip_polygon(vertices,a['arena_left']+2,a['arena_right']-2,
                                   a['arena_bottom']+2,a['arena_top']-2)
        boss_color=NEON if w.phase3 else '#ffffff'
        self.polygon(p,vertices,boss_color,boss_color,1)
        # Bold slanted angry red eyes and black inner pupils.
        eye_y=by+(r*.31 if w.phase3 else -r*.31)
        for sign in (-1,1):
            ex=bx+sign*r*.26
            ey=eye_y
            size=max(15,r*.18)
            # Outer corners are raised and inner corners point downward,
            # making angry eyes rather than tiny red dots.
            eye=[(ex+sign*size,ey+size*.48),
                 (ex-sign*size*.94,ey-size*.18),
                 (ex-sign*size*.57,ey-size*.65),
                 (ex+sign*size*.83,ey-size*.36)]
            if all(self.in_arena(*q) for q in eye):
                self.polygon(p,eye,'#ffffff' if w.phase3 else NEON,
                             '#ffffff' if w.phase3 else NEON,2)
                p.goto(ex-sign*size*.25,ey-size*.28)
                p.dot(max(4,int(9*a['scale'])),'#170001')
        # Small scowl below the eyes.
        mouth_y=by+(r*.53 if w.phase3 else -r*.53)
        if self.in_arena(bx,mouth_y):
            self.line(p,bx-24*a['scale'],mouth_y,bx+24*a['scale'],mouth_y,'#111111',3)

    def draw_trail(self,w,p):
        """Six stages: .90, .70, .50, .25, .10, invisible."""
        from combat import YELLOW
        multipliers=(.90,.70,.50,.25,.10,0.0)
        fade_colors=('#c1a900','#988500','#756500','#4b4200','#302b00')
        full_size=PLAYER_RADIUS*2*self.layout['scale']
        for mark in w.trail:
            index=min(5,int(mark.age/mark.lifetime*6))
            multiplier=multipliers[index]
            if multiplier<=0: continue
            side=full_size*multiplier
            x,y=self.pt(mark.x,mark.y)
            self.rect(p,x-side/2,y-side/2,side,side,PANEL,
                      fade_colors[index],1)

    def draw_character(self,w,p):
        from combat import YELLOW
        x,y=self.pt(w.x,w.y)
        if w.player_invulnerable>0 and int(w.time_alive*14)%2:
            return
        side=PLAYER_RADIUS*2*self.layout['scale']
        self.rect(p,x-side/2,y-side/2,side,side,PANEL,YELLOW,2)
        # Same collision dimensions as the drawn square; no wall clipping.
        self.health_hash(p,x,y,w.lives,side/110,YELLOW)

    def draw_training_targets(self,w,p):
        """Training-only mannequins with health bars and effect indicators."""
        k=self.layout['scale']
        t=w.time_alive
        for target in w.training_targets:
            if target.respawn>0:
                continue
            sx,sy=self.pt(target.x,target.y)
            if not self.in_arena(sx,sy):continue
            color='#ffdf00' if target.flash else '#eeeeee'
            r=39*k
            self._circle_outline(p,sx,sy,r,color,3)
            self.rect(p,sx-10*k,sy-10*k,20*k,20*k,'#1a1a1a',color,2)
            self.line(p,sx-7*k,sy,sx+7*k,sy,'#aaaaaa',2)
            self.line(p,sx,sy-7*k,sx,sy+7*k,'#aaaaaa',2)
            self.rect(p,sx-r,sy+r+11*k,2*r,7*k,'#292929')
            self.rect(p,sx-r,sy+r+11*k,max(0,2*r*target.hp/target.max_hp),7*k,CYAN)
            statuses=[]
            if target.stun>0:statuses.append('STUN')
            if target.slow>0:statuses.append('SLOW')
            if target.poison>0:statuses.append('POISON')
            if statuses:
                self.text(p,' / '.join(statuses),sx,sy-r-20*k,9,CYAN,True,'center')

    def draw_lance(self,w,p):
        """Show a compact spear only during the Lance dash-strike animation."""
        if w.lance_animation<=0:
            return
        k=self.layout['scale']
        fx,fy=w.lance_direction
        m=math.hypot(fx,fy) or 1
        fx,fy=fx/m,fy/m
        nx,ny=-fy,fx
        progress=1-w.lance_animation/.34
        thrust=max(0,math.sin(max(0,min(1,progress))*math.pi))*22
        centerx=w.x+fx*3+nx*2
        centery=w.y+fy*3+ny*2
        tail=(centerx-fx*20,centery-fy*20)
        tip=(centerx+fx*(42+thrust),centery+fy*(42+thrust))
        self.world_line(p,*tail,*tip,'#d6c583',max(2,int(4*k)))
        head=(tip[0]+fx*17,tip[1]+fy*17)
        self.polygon(p,[(self.pt(head[0],head[1])),
                        (self.pt(tip[0]-fx*5+nx*6,tip[1]-fy*5+ny*6)),
                        (self.pt(tip[0]-fx*5-nx*6,tip[1]-fy*5-ny*6))],
                     CYAN,CYAN,1)
        hx,hy=self.pt(*w.lance_contact)
        self._circle_outline(p,hx,hy,12*k,CYAN,2)

    def hash_glyph(self,pen,x,y,side,color,width=2):
        """Four orthogonal strokes, no enclosing square."""
        scale=side/100.0
        self.health_hash(pen,x,y,4,scale,color)

    def draw_cursor(self,x,y,visible=True,refresh=True):
        """Move four persistent Tk Canvas strokes without re-entering Tk's loop.

        x,y are Turtle screen coordinates. Convert to Canvas pixel positions,
        respecting the canvas scroll offset. `refresh` remains for compatibility
        but deliberately never calls screen.update() from mouse events.
        """
        canvas=self.cursor_canvas
        if not visible:
            for item in self.cursor_items:
                canvas.itemconfigure(item,state='hidden')
            return
        cx=canvas.canvasx(x+canvas.winfo_width()/2)
        cy=canvas.canvasy(canvas.winfo_height()/2-y)
        # A crisp # with four aligned strokes; 80% larger than the old cursor.
        segments=((cx-6,cy-15,cx-6,cy+15),
                  (cx+6,cy-15,cx+6,cy+15),
                  (cx-15,cy-6,cx+15,cy-6),
                  (cx-15,cy+6,cx+15,cy+6))
        for item,coords in zip(self.cursor_items,segments):
            canvas.coords(item,*coords)
            canvas.itemconfigure(item,state='normal')
        canvas.tag_raise('hash_cursor')

    def clip_segment(self,x1,y1,x2,y2):
        """Clip segments in WORLD units to the rectangular battle viewport."""
        xmin,xmax=-WORLD_W/2+2,WORLD_W/2-2
        ymin,ymax=-WORLD_H/2+2,WORLD_H/2-2
        dx,dy=x2-x1,y2-y1
        p=(-dx,dx,-dy,dy)
        q=(x1-xmin,xmax-x1,y1-ymin,ymax-y1)
        u0,u1=0.0,1.0
        for pi,qi in zip(p,q):
            if abs(pi)<1e-10:
                if qi<0:return None
            else:
                t=qi/pi
                if pi<0:u0=max(u0,t)
                else:u1=min(u1,t)
        if u0>u1:return None
        return x1+u0*dx,y1+u0*dy,x1+u1*dx,y1+u1*dy

    def world_line(self,pen,x1,y1,x2,y2,color,width):
        segment=self.clip_segment(x1,y1,x2,y2)
        if segment:
            ax,ay=self.pt(segment[0],segment[1])
            bx,by=self.pt(segment[2],segment[3])
            self.line(pen,ax,ay,bx,by,color,width)

    def display_live(self,game,force=False):
        w=game.world
        if game.state not in ('arena','dialogue','victory_dialogue') and not force:return
        from combat import NEON,YELLOW
        WHITE = "#ffffff"
        self.player.hideturtle();self.dummy.hideturtle()
        self.effects.clear()
        p=self.effects
        k=self.layout['scale']
        if w.stage=='slam_prepare':
            # Warning overlay for the broad center-of-stage crash.
            x1,y1=self.pt(-WORLD_W*.37,-WORLD_H/2)
            x2,y2=self.pt(WORLD_W*.37,WORLD_H/2)
            self.line(p,x1,y1,x1,y2,'#9c2635',3)
            self.line(p,x2,y1,x2,y2,'#9c2635',3)
            self.text(p,'SLAM INCOMING - GET TO THE SIDES!',0,self.layout['arena_cy'],11,NEON,True,'center')
        if w.training:
            self.draw_training_targets(w,p)
        else:
            self.draw_boss(w,p)
        self.draw_trail(w,p)
        for ball in w.enemy_balls:
            sx,sy=self.pt(ball.x,ball.y)
            if self.in_arena(sx,sy):
                flash=ball.age>=ball.fuse-1 and int(ball.age*11)%2==0
                p.goto(sx,sy);p.dot(max(8,int(ball.radius*2*k)),WHITE if flash else NEON)
        for dot in w.dots:
            sx,sy=self.pt(dot.x,dot.y)
            if self.in_arena(sx,sy):
                flash=dot.age>dot.fuse-.55 and int(dot.age*12)%2==0
                p.goto(sx,sy);p.dot(PLAYER_RADIUS*4*k,WHITE if flash else NEON)
        for ex in w.explosions:
            sx,sy=self.pt(ex.x,ex.y)
            self._circle_outline(p,sx,sy,ex.radius*k*min(1,ex.age/.12),NEON,3)
        for spike in w.spikes:
            sx,sy=self.pt(spike.x,spike.y)
            if self.in_arena(sx,sy):
                self.polygon(p,[(sx,sy-20*k),(sx-10*k,sy+14*k),(sx+10*k,sy+14*k)],NEON)
        for pulse in w.pulses:
            n=36
            for index in range(n):
                a1=index*math.tau/n;a2=(index+1)*math.tau/n
                self.world_line(p,w.dummy_x+math.cos(a1)*pulse.radius,
                                w.dummy_y+math.sin(a1)*pulse.radius,
                                w.dummy_x+math.cos(a2)*pulse.radius,
                                w.dummy_y+math.sin(a2)*pulse.radius,
                                NEON,max(3,int(pulse.width*k)))
        if w.laser_paths:
            for path in w.laser_paths:
                for (x1,y1),(x2,y2) in zip(path,path[1:]):
                    self.world_line(p,x1,y1,x2,y2,NEON if w.laser_active else '#74313a',
                                    max(5,int(22*k)) if w.laser_active else 2)
        if w.health_pickup is not None:
            self.draw_health_pickup(w,p)
        for hunter in w.triangles:
            tx,ty=self.pt(hunter.x,hunter.y)
            side=PLAYER_RADIUS*4*k
            self.line(p,tx-side,ty-side*.7,tx+side,ty-side*.7,WHITE,3)
            self.line(p,tx+side,ty-side*.7,tx,ty+side,WHITE,3)
            self.line(p,tx,ty+side,tx-side,ty-side*.7,WHITE,3)
            for n in range(hunter.hp):
                hx=tx+(n-1.5)*13
                hy=ty-side-14
                heart=[(hx-5,hy+2),(hx-3,hy+5),(hx,hy+2),
                       (hx+3,hy+5),(hx+5,hy+2),(hx,hy-5)]
                self.polygon(p,heart,NEON)
        for shot in w.hunter_shots:
            px,py=self.pt(shot.x,shot.y)
            if self.in_arena(px,py):p.goto(px,py);p.dot(max(6,shot.radius*2*k),NEON)
        for part in w.particles:
            px,py=self.pt(part.x,part.y)
            if self.in_arena(px,py):
                if part.hash_shape:
                    self.health_hash(p,px,py,4,max(.075,part.radius*k/35),part.color)
                else:p.goto(px,py);p.dot(max(2,int(part.radius*k)),part.color)
        self.draw_character(w,p)
        if w.training:
            self.draw_lance(w,p)
        # Red warning target follows the player before the eye lasers fire.
        # Does not change normal ricochet geometry, count, or thickness.
        warning = ((w.stage in ('lasers_right', 'lasers_left') and
                    w.stage_time < .85*(.68 if w.phase3 else 1.0)) or
                   (w.stage == 'tracking' and w.stage_time < 1.2))
        if warning:
            tx,ty=self.pt(w.x,w.y)
            if self.in_arena(tx,ty):
                p.goto(tx,ty)
                p.dot(max(12,int(17*k)),NEON)
                self._circle_outline(p,tx,ty,22*k,NEON,2)
        x,y=self.pt(w.x,w.y)
        if w.guard_timer>0:self._circle_outline(p,x,y,28*k,WHITE,2)
        for shot in w.projectiles:
            sx,sy=self.pt(shot.x,shot.y)
            if self.in_arena(sx,sy):p.goto(sx,sy);p.dot(max(7,int(shot.radius*2*k)),YELLOW)

    def draw_health_pickup(self,w,p):
        """Floating, softly pulsing yellow HASH with a grounded shadow."""
        from combat import YELLOW
        pickup=w.health_pickup
        if pickup is None:return
        k=self.layout['scale']
        x,y=self.pt(pickup.x,pickup.y)
        bob=math.sin(w.time_alive*3.2)*11*k
        pulse=1+math.sin(w.time_alive*4.8)*.09
        # Shadow stays still, while the collectible rises and falls above it.
        p.goto(x,y-24*k)
        p.dot(max(5,20*k),'#393315')
        self._circle_outline(p,x,y+bob,35*k*pulse,'#897520',2)
        self.health_hash(p,x,y+bob,4,.68*k,YELLOW)
        # Four tiny glints indicate this is a pickup, not a projectile.
        for dx,dy in ((-34,0),(34,0),(0,-34),(0,34)):
            p.goto(x+dx*k,y+bob+dy*k)
            p.dot(max(2,4*k),YELLOW)

    def _clip_ray(self,x,y,ex,ey):
        dx,dy=ex-x,ey-y
        fraction=1.0
        if dx>0:
            fraction=min(fraction,(WORLD_W/2-3-x)/dx)
        elif dx<0:
            fraction=min(fraction,(-WORLD_W/2+3-x)/dx)
        if dy>0:
            fraction=min(fraction,(WORLD_H/2-3-y)/dy)
        elif dy<0:
            fraction=min(fraction,(-WORLD_H/2+3-y)/dy)
        return x+dx*max(0,fraction), y+dy*max(0,fraction)

    def _circle_outline(self,pen,x,y,r,color,width):
        pen.color(color)
        pen.pensize(width)
        pen.goto(x,y-r)
        pen.setheading(0)
        pen.pendown()
        pen.circle(r,steps=18)
        pen.penup()

    def game_over(self,game):
        self.reset()
        self.text(self.base,"#HASH#",0,105,42,RED,True,"center")
        self.text(self.base,"ALL FOUR LINES LOST",0,55,20,TEXT,True,"center")
        self.text(self.base,"PRESS NEW RUN TO RESTORE THE HASH",0,15,12,MUTED,False,"center")
        self.button("NEW RUN",0,-62,240,50,game.new_run,accent=True)
        self.button("MAIN MENU",0,-123,240,48,game.show_menu)
        self.screen.update()
