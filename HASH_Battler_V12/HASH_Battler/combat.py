"""#HASH# combat engine: no graphical dependencies, deterministic update stages.

The Greeter is a complete Level-0 fight. The UI owns no attack state: it reads
these objects, draws telegraphs, and sends movement/ability input.
"""
from dataclasses import dataclass
from items import ItemBuild
import math
import random
from config import (WORLD_W, WORLD_H, DUMMY_RADIUS, PLAYER_RADIUS,
                    MOVE_SPEED, DASH_LENGTH, ABILITY_COOLDOWN, ACTION_NAMES)

YELLOW = '#ffdf00'
NEON = '#ff243c'
WHITE = '#ffffff'


def clamp(value, low, high):
    return min(high, max(low, value))


def normalized(x, y):
    m=math.hypot(x,y)
    return (x/m,y/m) if m else (0.0,0.0)


def segment_circle(x1,y1,x2,y2,cx,cy,radius):
    dx,dy=x2-x1,y2-y1
    t=clamp(((cx-x1)*dx+(cy-y1)*dy)/(dx*dx+dy*dy),0,1) if dx or dy else 0
    return math.hypot(x1+t*dx-cx,y1+t*dy-cy)<=radius


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    lifetime: float
    maximum: float
    color: str
    radius: float=4.0
    hash_shape: bool=False


@dataclass
class TrailSquare:
    x: float
    y: float
    age: float=0.0
    lifetime: float=.42


@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    lifetime: float=2.5
    radius: float=7.0


@dataclass
class EnemyBall:
    x: float
    y: float
    vx: float
    vy: float
    radius: float=20.0
    age: float=0.0
    fuse: float=2.8


@dataclass
class BombDot:
    x: float
    y: float
    age: float=0.0
    fuse: float=1.55
    radius: float=PLAYER_RADIUS*2
    shift_time: float=-1.0
    shifted: bool=False


@dataclass
class Explosion:
    x: float
    y: float
    radius: float
    age: float=0.0
    lifetime: float=.30


@dataclass
class HunterShot:
    x: float
    y: float
    vx: float
    vy: float
    lifetime: float=4.2
    radius: float=11.0


@dataclass
class Hunter:
    x: float
    y: float
    hp: int=1
    fire_timer: float=4.0
    ident: int=0


@dataclass
class HashPickup:
    """One temporary floating life-line pickup on the battlefield."""
    x: float
    y: float
    age: float=0.0
    lifetime: float=14.0


@dataclass
class TrainingTarget:
    x: float
    y: float
    hp: float = 250.0
    max_hp: float = 250.0
    respawn: float = 0.0
    stun: float = 0.0
    slow: float = 0.0
    poison: float = 0.0
    poison_dps: float = 0.0
    flash: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    home_x: float = 0.0
    home_y: float = 0.0


@dataclass
class Spike:
    x: float
    y: float
    vx: float
    vy: float
    radius: float=15.0


@dataclass
class Pulse:
    radius: float=0.0
    speed: float=240.0
    width: float=17.0
    hit: bool=False


class World:
    MOVES=('BOUNCY BALLS','RED DOTS','EYE LASERS','HUNTER TRIANGLE',
           'SPIKE RAIN','SLAM','PULSE','TRACKING LASERS')
    MOVE_DESCRIPTIONS={
        'BOUNCY BALLS':('The Greeter fires bouncing', 'neon orbs. They flash', 'before exploding.'),
        'RED DOTS':('30 flashing markers explode','all at once. In Phase 3,','they move midway through.'),
        'EYE LASERS':('Thin beams ricochet across','the arena. Watch the','warning lines for safe gaps.'),
        'HUNTER TRIANGLE':('One hit destroys a hunter.','Watch for the red shots','they fire at you.'),
        'SPIKE RAIN':('The boss leaves the arena.','Avoid spikes falling','from above.'),
        'SLAM':('The boss crashes into the','center. Retreat to the','sides before impact.'),
        'PULSE':('Four expanding shockwaves.','Use your dash to pass','through each ring.'),
        'TRACKING LASERS':('Eyes slowly turn to follow','your movements. Keep moving','until the beams stop.'),
    }
    def __init__(self): self.reset()

    def reset(self):
        self.x,self.y=-570.0,0.0
        self.facing=(1.0,0.0)
        self.velocity=(0.0,0.0)
        self.lives=4
        self.dummy_x,self.dummy_y=300.0,0.0
        self.dummy_max_hp=1200.0
        self.dummy_hp=self.dummy_max_hp
        self.dummy_phase='PHASE 1'
        self.discovered_moves=[]
        self.cooldowns={name:0.0 for name in ACTION_NAMES}
        self.active={name:0.0 for name in ACTION_NAMES}
        self.particles=[];self.trail=[];self.last_trail_position=(self.x,self.y)
        self.projectiles=[];self.enemy_balls=[];self.dots=[];self.explosions=[]
        self.hunter_shots=[];self.triangles=[];self.next_hunter_id=0
        self.spikes=[];self.pulses=[]
        self.laser_paths=[];self.laser_active=False
        self.stage='bouncy';self.stage_time=0.0
        self.ball_pairs=0;self.dot_waves=0
        self.cycle_count=0;self.phase3=False;self.hunters_per_cycle=2
        self.player_invulnerable=0.0;self.dash_iframes=0.0
        # Timing ring: white marker rotates clockwise; the yellow arc moves on hits.
        self.shot_cycle=0.0
        self.shot_period=1.45  # one complete revolution in seconds
        self.shot_zone_center=random.uniform(.19,.81)
        self.shot_aim_distance=0.0
        self.shot_miss_flash=0.0
        self.projectile_origin=(self.x,self.y)
        self.guard_timer=0.0
        # At most one floating HASH at a time. Spawn only if a line is missing.
        self.health_pickup=None
        self.pickup_spawn_timer=random.uniform(6.0,9.0)
        self.pickup_spawn_count=0
        self.message='THE GREETER';self.message_timer=2.0
        self.damage_dealt=0.0;self.hits=0;self.time_alive=0.0
        self.last_action='NONE'
        self.stage_origin=(self.dummy_x,self.dummy_y)
        self.spike_spawn_timer=0.0
        self.pulse_count=0;self.pulse_spawn_timer=0.0
        self.eye_directions=[(-.8,-.55),(.8,-.55)]
        self.boss_attack_timer=0.0 # compatibility for old saves
        self.training=False
        self.lance_build=None
        self.training_targets=[]
        self.training_hits=0
        self.training_kills=0
        self.lance_animation=0.0
        self.lance_target=None
        self.lance_direction=(1.0,0.0)
        self.lance_contact=(self.x,self.y)
        self.lance_dash_start=(self.x,self.y)
        self.lance_dash_end=(self.x,self.y)
        self.lance_dash_timer=0.0
        self.lance_dash_duration=.18
        self.lance_pending_target=None
        self.lance_pending_values=None

    def start_training(self, build):
        """A safe testing arena with three renewable practice targets."""
        self.reset()
        self.training=True
        self.lance_build=ItemBuild.from_dict(build.to_dict())
        self.x,self.y=-460.0,0.0
        self.last_trail_position=(self.x,self.y)
        self.dummy_hp=0
        self.stage='training'
        self.message='TRAINING ROOM  /  LANCE EQUIPPED'
        self.message_timer=3.0
        self.training_targets=[TrainingTarget(210, 0, home_x=210, home_y=0),
                               TrainingTarget(365, 235, home_x=365, home_y=235),
                               TrainingTarget(365, -235, home_x=365, home_y=-235)]

    @property
    def triangle_hp(self):
        return sum(t.hp for t in self.triangles)

    def to_save(self):
        # Maps are checkpoints, not mid-boss snapshots.
        return {'map_unlocked':True,'time_alive':self.time_alive,
                'damage_dealt':self.damage_dealt,'hits':self.hits}

    def restore(self,data):
        self.reset()
        try:
            self.time_alive=max(0,float(data.get('time_alive',0)))
            self.damage_dealt=max(0,float(data.get('damage_dealt',0)))
            self.hits=max(0,int(data.get('hits',0)))
        except (TypeError,ValueError,OverflowError):
            self.reset()

    def _position_outside_boss(self,x,y):
        half=PLAYER_RADIUS+2
        xmin,xmax=-WORLD_W/2+half,WORLD_W/2-half
        ymin,ymax=-WORLD_H/2+half,WORLD_H/2-half
        x,y=clamp(x,xmin,xmax),clamp(y,ymin,ymax)
        if self.dummy_hp<=0:return x,y
        def touching(px,py):
            qx=clamp(self.dummy_x,px-half,px+half)
            qy=clamp(self.dummy_y,py-half,py+half)
            return (qx-self.dummy_x)**2+(qy-self.dummy_y)**2 < DUMMY_RADIUS**2
        if touching(x,y):
            dx,dy=x-self.dummy_x,y-self.dummy_y
            d=math.hypot(dx,dy)
            if d<.001: dx,dy,d=-1.0,0,1.0
            nx,ny=dx/d,dy/d
            lo,hi=d,DUMMY_RADIUS+math.sqrt(2)*half+4
            for _ in range(18):
                mid=(lo+hi)*.5
                if touching(self.dummy_x+nx*mid,self.dummy_y+ny*mid):lo=mid
                else:hi=mid
            x=clamp(self.dummy_x+nx*(hi+.4),xmin,xmax)
            y=clamp(self.dummy_y+ny*(hi+.4),ymin,ymax)
            if touching(x,y):
                candidates=((clamp(self.dummy_x-DUMMY_RADIUS-half-3,xmin,xmax),y),
                            (clamp(self.dummy_x+DUMMY_RADIUS+half+3,xmin,xmax),y),
                            (x,clamp(self.dummy_y-DUMMY_RADIUS-half-3,ymin,ymax)),
                            (x,clamp(self.dummy_y+DUMMY_RADIUS+half+3,ymin,ymax)))
                valid=[p for p in candidates if not touching(*p)]
                if valid:x,y=min(valid,key=lambda p:(p[0]-x)**2+(p[1]-y)**2)
        return x,y

    def _record_trail(self,old_x,old_y):
        if math.hypot(self.x-self.last_trail_position[0],self.y-self.last_trail_position[1])>=11:
            self.trail.append(TrailSquare(old_x,old_y))
            self.last_trail_position=(self.x,self.y)
            self.trail=self.trail[-36:]

    def move(self,dx,dy,dt):
        dx,dy=normalized(dx,dy)
        self.velocity=dx*MOVE_SPEED,dy*MOVE_SPEED
        if dx or dy:self.facing=(dx,dy)
        ox,oy=self.x,self.y
        self.x,self.y=self._position_outside_boss(self.x+dx*MOVE_SPEED*dt,self.y+dy*MOVE_SPEED*dt)
        if (self.x,self.y)!=(ox,oy):self._record_trail(ox,oy)

    def emit(self,x,y,color,count=12,force=130,lifetime=.35,hash_shape=False):
        for _ in range(min(count,20)):
            a=random.random()*math.tau
            speed=force*random.uniform(.2,1)
            life=lifetime*random.uniform(.55,1.25)
            self.particles.append(Particle(x,y,math.cos(a)*speed,math.sin(a)*speed,
                                           life,life,color,random.uniform(3,6),hash_shape))
        self.particles=self.particles[-110:]

    def _hit_dummy(self,damage):
        if self.dummy_hp<=0:return
        dealt=min(self.dummy_hp,damage)
        self.dummy_hp-=dealt
        self.damage_dealt+=dealt;self.hits+=1
        self.emit(self.dummy_x,self.dummy_y,WHITE,4)
        if self.dummy_hp<=0:
            self.stage='victory';self.dummy_phase='DEFEATED';self.stage_time=0
            self.enemy_balls.clear();self.dots.clear();self.hunter_shots.clear()
            self.triangles.clear();self.spikes.clear();self.pulses.clear()
            self.explosions.clear();self.laser_paths.clear();self.laser_active=False
            self.message='THE GREETER DEFEATED';self.message_timer=4

    def _random_hunter_location(self,avoid=None):
        margin=105
        for _ in range(350):
            x=random.uniform(-WORLD_W/2+margin,WORLD_W/2-margin)
            y=random.uniform(-WORLD_H/2+margin,WORLD_H/2-margin)
            if math.hypot(x-self.dummy_x,y-self.dummy_y)<=DUMMY_RADIUS+95:continue
            if math.hypot(x-self.x,y-self.y)<=135:continue
            if any(math.hypot(x-t.x,y-t.y)<90 and t is not avoid for t in self.triangles):continue
            return x,y
        return -WORLD_W/2+margin, WORLD_H/2-margin

    def _summon_hunters(self,count):
        self.discover_boss_move('HUNTER TRIANGLE')
        # Turtle rendering stays responsive even when a long run repeats.
        count=min(count,max(0,1-len(self.triangles)))
        for _ in range(count):
            x,y=self._random_hunter_location()
            self.next_hunter_id+=1
            self.triangles.append(Hunter(x,y,1,random.uniform(2,4),self.next_hunter_id))
        self.message=(f'{count} HUNTERS SUMMONED' if count else 'HUNTER SWARM AT MAXIMUM')
        self.message_timer=1.2

    def _summon_hunter(self):
        self._summon_hunters(1)

    def _damage_hunter(self,hunter):
        if hunter not in self.triangles:return
        hunter.hp-=1;self.hits+=1
        self.emit(hunter.x,hunter.y,NEON,7)
        if hunter.hp<=0:
            self.triangles.remove(hunter)
            self.emit(hunter.x,hunter.y,WHITE,12)
        else:
            hunter.x,hunter.y=self._random_hunter_location(avoid=hunter)

    def _hit_triangle(self):
        if self.triangles:self._damage_hunter(self.triangles[0])

    @property
    def shot_marker(self):
        """Position on the timing ring, 0..1 clockwise from the top."""
        return (self.shot_cycle/self.shot_period)%1.0

    def shot_zone_width(self,distance):
        """A visible 18-30% arc, narrowing gently for distant mouse aims."""
        return clamp(.30 - .12*clamp(distance/1250.0,0,1), .18, .30)

    def shot_zone(self,distance=None):
        width=self.shot_zone_width(self.shot_aim_distance if distance is None else distance)
        center=self.shot_zone_center
        return center-width*.5, center+width*.5

    def attempt_shot(self,direction=None,aim_distance=0):
        """Only an accurate click fires. A miss incurs a brief retry cooldown."""
        if self.lives<=0 or self.cooldowns['Shoot']>0:
            return False
        self.shot_aim_distance=max(0.0,aim_distance)
        lo,hi=self.shot_zone()
        if not lo<=self.shot_marker<=hi:
            self.cooldowns['Shoot']=.45
            self.shot_miss_flash=.22
            self.last_action='MISSED SHOT'
            return False
        dx,dy=normalized(*(direction if direction is not None else self.facing))
        if not (dx or dy):dx,dy=self.facing
        ox,oy=self.x+dx*(PLAYER_RADIUS+10),self.y+dy*(PLAYER_RADIUS+10)
        self.projectiles.append(Projectile(ox,oy,dx*920,dy*920,radius=9))
        self.cooldowns['Shoot']=.18
        self.active['Shoot']=.16
        self.last_action='PERFECT SHOT'
        self.emit(self.x,self.y,YELLOW,7,hash_shape=True)
        # A fresh random target after every valid shot. No charging/holding.
        self.shot_zone_center=random.uniform(.18,.82)
        self.shot_cycle=0.0
        return True

    def _blink(self,distance):
        dx,dy=self.facing
        self.emit(self.x,self.y,YELLOW,8,hash_shape=True)
        nx,ny=self._position_outside_boss(self.x+dx*distance,self.y+dy*distance)
        if segment_circle(self.x,self.y,nx,ny,self.dummy_x,self.dummy_y,DUMMY_RADIUS+PLAYER_RADIUS):
            sx,sy=self.x-self.dummy_x,self.y-self.dummy_y
            m=math.hypot(sx,sy) or 1
            nx,ny=self._position_outside_boss(self.dummy_x+sx/m*(DUMMY_RADIUS+PLAYER_RADIUS+3),
                                               self.dummy_y+sy/m*(DUMMY_RADIUS+PLAYER_RADIUS+3))
        ox,oy=self.x,self.y
        self.x,self.y=nx,ny
        self.trail.append(TrailSquare(ox,oy))
        self.last_trail_position=(self.x,self.y)
        self.emit(self.x,self.y,YELLOW,10,hash_shape=True)
        self.dash_iframes=.62

    def _lance_attack(self):
        """Dash toward the nearest target and strike at the end of the lunge."""
        if not self.training or self.lance_build is None or self.cooldowns['Item 1']>0:
            return False
        if self.lance_dash_timer>0:
            return False
        living=[t for t in self.training_targets if t.respawn<=0]
        if not living:
            self.message='NO TARGET AVAILABLE';self.message_timer=.85
            return False
        target=min(living,key=lambda t:math.hypot(t.x-self.x,t.y-self.y))
        dx,dy=normalized(target.x-self.x,target.y-self.y)
        if (dx,dy)==(0,0):dx,dy=self.facing
        values=self.lance_build.lance_stats()
        distance=math.hypot(target.x-self.x,target.y-self.y)
        stop_distance=39+PLAYER_RADIUS+10
        max_lock_distance=values['reach']+values['dash_distance']+39+PLAYER_RADIUS
        if distance>max_lock_distance:
            self.message='LANCE DASH: GET CLOSER';self.message_timer=.85
            self.last_action='LANCE OUT OF RANGE'
            return False
        dash_distance=min(values['dash_distance'],max(0,distance-stop_distance))
        end_x=clamp(self.x+dx*dash_distance,-WORLD_W/2+PLAYER_RADIUS,WORLD_W/2-PLAYER_RADIUS)
        end_y=clamp(self.y+dy*dash_distance,-WORLD_H/2+PLAYER_RADIUS,WORLD_H/2-PLAYER_RADIUS)
        self.lance_direction=(dx,dy)
        self.lance_target=target
        self.lance_contact=(target.x,target.y)
        self.lance_dash_start=(self.x,self.y)
        self.lance_dash_end=(end_x,end_y)
        self.lance_dash_duration=values['dash_duration']
        self.lance_dash_timer=self.lance_dash_duration
        self.lance_pending_target=target
        self.lance_pending_values=values
        self.lance_animation=.34
        self.cooldowns['Item 1']=values['cooldown']
        self.active['Item 1']=.34
        self.facing=(dx,dy)
        self.last_action='LANCE DASH / '+self.lance_build.element.upper()
        self.emit(self.x,self.y,YELLOW,6,force=100,hash_shape=True)
        return True

    def _finish_lance_attack(self):
        target=self.lance_pending_target
        values=self.lance_pending_values
        self.lance_pending_target=None
        self.lance_pending_values=None
        if target is None or values is None or target.respawn>0:
            return
        dx,dy=normalized(target.x-self.x,target.y-self.y)
        if (dx,dy)==(0,0):dx,dy=self.lance_direction
        gap=math.hypot(target.x-self.x,target.y-self.y)-39-PLAYER_RADIUS
        if gap>values['reach']+8:
            self.message='LANCE DASH MISSED';self.message_timer=.7
            return
        self.lance_direction=(dx,dy)
        self.lance_contact=(target.x,target.y)
        self.training_hits+=1
        self._strike_training_target(target,values['damage'],dx,dy,values['knockback'])
        self._apply_lance_effect(target,dx,dy,values['effect_power'])
        self.emit(target.x,target.y,YELLOW,9,force=170,hash_shape=True)

    def _strike_training_target(self,target,damage,dx,dy,knockback):
        if target.respawn>0:return
        target.hp=max(0,target.hp-damage)
        target.flash=.22
        target.vx+=dx*knockback*2.4
        target.vy+=dy*knockback*2.4
        self.damage_dealt+=damage
        self.hits+=1
        if target.hp<=0:
            target.respawn=2.8
            target.poison=0
            self.training_kills+=1
            self.message='TARGET DOWN - RESPAWNING';self.message_timer=1.1

    def _apply_lance_effect(self,target,dx,dy,power):
        if target.respawn>0:return
        element=self.lance_build.element
        if element=='Fire':
            self._strike_training_target(target,12+8*power,dx,dy,0)
            self.emit(target.x,target.y,'#ff7039',9)
        elif element=='Thunder':
            target.stun=max(target.stun,.55+.17*power)
            self.emit(target.x,target.y,'#fff06c',8)
        elif element=='Ice':
            target.slow=max(target.slow,2.0+.35*power)
            self.emit(target.x,target.y,'#77d8ff',8)
        elif element=='Poison':
            target.poison=max(target.poison,3.5+.2*power)
            target.poison_dps=6+3.4*power
            self.emit(target.x,target.y,'#91cc71',8)
        elif element=='Air':
            target.vx+=dx*(150+55*power)
            target.vy+=dy*(150+55*power)
            self.emit(target.x,target.y,'#c6eeee',9)

    def update_training(self,dt):
        self.lance_animation=max(0.0,self.lance_animation-dt)
        if self.lance_dash_timer>0:
            self.lance_dash_timer=max(0.0,self.lance_dash_timer-dt)
            progress=1-self.lance_dash_timer/self.lance_dash_duration
            ox,oy=self.x,self.y
            sx,sy=self.lance_dash_start
            ex,ey=self.lance_dash_end
            self.x=sx+(ex-sx)*progress
            self.y=sy+(ey-sy)*progress
            if (self.x,self.y)!=(ox,oy):self._record_trail(ox,oy)
            if self.lance_dash_timer<=0:
                self.x,self.y=ex,ey
                self._finish_lance_attack()
        for index,target in enumerate(self.training_targets):
            if target.respawn>0:
                target.respawn=max(0,target.respawn-dt)
                if target.respawn==0:
                    target.hp=target.max_hp
                    target.x,target.y=target.home_x,target.home_y
                    target.stun=target.slow=target.poison=target.flash=0
                    target.vx=target.vy=0
                continue
            target.stun=max(0,target.stun-dt)
            target.slow=max(0,target.slow-dt)
            target.flash=max(0,target.flash-dt)
            if target.poison>0:
                target.poison=max(0,target.poison-dt)
                new_hp=max(0,target.hp-target.poison_dps*dt)
                self.damage_dealt+=target.hp-new_hp
                target.hp=new_hp
                if target.hp<=0:
                    target.respawn=2.8
                    self.training_kills+=1
            if target.stun<=0:
                # Gentle motion demonstrates Ice slow and Thunder stun.
                desired_x=target.home_x+62*math.sin(self.time_alive*.95+index*2)
                desired_y=target.home_y+42*math.sin(self.time_alive*.71+index*1.7)
                target.vx+=(desired_x-target.x)*dt*8
                target.vy+=(desired_y-target.y)*dt*8
                factor=.30 if target.slow>0 else 1
                target.x=clamp(target.x+target.vx*dt*factor,-WORLD_W/2+55,WORLD_W/2-55)
                target.y=clamp(target.y+target.vy*dt*factor,-WORLD_H/2+55,WORLD_H/2-55)
                target.vx*=max(0,1-dt*4.0)
                target.vy*=max(0,1-dt*4.0)

    def activate(self,action,direction=None):
        if action=='Shoot':
            return self.attempt_shot(direction,self.shot_aim_distance)
        if action=='Item 1' and self.training:
            return self._lance_attack()
        if action not in self.cooldowns or self.cooldowns[action]>0.00001 or self.lives<=0:
            return False
        dx,dy=normalized(*(direction if direction is not None else self.facing))
        if not (dx or dy):dx,dy=self.facing
        self.cooldowns[action]=ABILITY_COOLDOWN
        self.last_action=action.upper()
        if action=='Dash':
            self.facing=dx,dy;self._blink(DASH_LENGTH);self.active[action]=.22
        elif action=='Chestplate':
            self.guard_timer=.65;self.active[action]=.65
        else:
            self.active[action]=.32
            self.message=f'{action.upper()} - EMPTY SLOT';self.message_timer=.8
        return True

    def discover_boss_move(self,name):
        if name and name not in self.discovered_moves:self.discovered_moves.append(name)

    def take_debug_hit(self):
        self.lives=max(0,self.lives-1)
        self.emit(self.x,self.y,YELLOW,14,hash_shape=True)
        return self.lives==0

    def _hurt_player(self,px,py,radius):
        if self.lives<=0:return False
        qx=clamp(px,self.x-PLAYER_RADIUS,self.x+PLAYER_RADIUS)
        qy=clamp(py,self.y-PLAYER_RADIUS,self.y+PLAYER_RADIUS)
        if (px-qx)**2+(py-qy)**2>radius**2:return False
        if self.player_invulnerable>0 or self.dash_iframes>0:return False
        if self.guard_timer>0:return False
        self.lives-=1;self.player_invulnerable=1.1
        self.emit(self.x,self.y,YELLOW,16,hash_shape=True)
        return True

    def _spawn_health_pickup(self):
        """Spawn one collectible away from the player, boss and other hazards."""
        if self.health_pickup is not None or self.lives>=4 or self.lives<=0:
            return False
        for _ in range(160):
            x=random.uniform(-WORLD_W/2+85,WORLD_W/2-85)
            y=random.uniform(-WORLD_H/2+85,WORLD_H/2-85)
            if math.hypot(x-self.x,y-self.y)<230:continue
            if self.dummy_hp>0 and math.hypot(x-self.dummy_x,y-self.dummy_y)<DUMMY_RADIUS+90:continue
            if any(math.hypot(x-d.x,y-d.y)<95 for d in self.dots):continue
            if any(math.hypot(x-h.x,y-h.y)<95 for h in self.triangles):continue
            self.health_pickup=HashPickup(x,y)
            self.pickup_spawn_count+=1
            self.message='A HASH HAS APPEARED!';self.message_timer=2.2
            return True
        # Try again later if no safe spot was available.
        self.pickup_spawn_timer=3.0
        return False

    def _update_health_pickup(self,dt):
        """Tick only during live gameplay; tutorials freeze this timer."""
        if self.lives<=0 or self.dummy_hp<=0:return
        pickup=self.health_pickup
        if pickup is None:
            self.pickup_spawn_timer=max(0,self.pickup_spawn_timer-dt)
            if self.pickup_spawn_timer<=0 and self.lives<4:
                self._spawn_health_pickup()
            return
        pickup.age+=dt
        if self.lives<4 and math.hypot(self.x-pickup.x,self.y-pickup.y)<=PLAYER_RADIUS+26:
            self.lives=min(4,self.lives+1)
            self.health_pickup=None
            self.pickup_spawn_timer=random.uniform(11.0,16.0)
            self.message='+1 HASH LINE';self.message_timer=1.7
            self.last_action='HASH RESTORED'
            self.emit(pickup.x,pickup.y,YELLOW,16,force=180,hash_shape=True)
        elif pickup.age>=pickup.lifetime:
            self.health_pickup=None
            self.pickup_spawn_timer=random.uniform(11.0,16.0)

    def _begin(self,stage):
        self.stage=stage;self.stage_time=0.0
        self.stage_origin=(self.dummy_x,self.dummy_y)
        self.laser_paths=[];self.laser_active=False
        self.message_timer=max(self.message_timer,.5)
        if stage.startswith('dots'):
            self.dot_waves=0
            self._spawn_dots(shift=self.phase3)
        if stage in ('lasers_right','lasers_left'):
            self.discover_boss_move('EYE LASERS')
            self.laser_paths=self._laser_geometry('right' if stage=='lasers_right' else 'left')
        if stage=='tracking':
            self.discover_boss_move('TRACKING LASERS')
            self.eye_directions=[normalized(self.x-self.dummy_x-65,self.y-self.dummy_y),
                                 normalized(self.x-self.dummy_x+65,self.y-self.dummy_y)]
            self.laser_active=False
        if stage=='spikes':
            self.discover_boss_move('SPIKE RAIN')
            self.spike_spawn_timer=0.05
        if stage=='slam_prepare':self.discover_boss_move('SLAM')
        if stage=='pulses':
            self.discover_boss_move('PULSE')
            self.pulse_count=0;self.pulse_spawn_timer=.75
        if stage=='cycle_summon':
            self._summon_hunters(self.hunters_per_cycle)
            self._spawn_three_balls()
            self.cycle_count+=1
            self.dummy_phase='PHASE 3' if self.phase3 else 'PHASE 2'
            self.message='HUNTERS + BOUNCY BALLS';self.message_timer=1.4

    def _spawn_ball_pair(self):
        self.discover_boss_move('BOUNCY BALLS')
        heights=(DUMMY_RADIUS*.60,0,-DUMMY_RADIUS*.60)
        offset=heights[self.ball_pairs%3]
        for shift in (-23,23):
            oy=offset+shift
            rim=math.sqrt(max(0,DUMMY_RADIUS**2-oy**2))
            x=self.dummy_x-rim-25
            self.enemy_balls.append(EnemyBall(x,self.dummy_y+oy,
                          -random.uniform(230,310),random.choice((-1,1))*random.uniform(130,230)))
        self.ball_pairs+=1
        self.message='BOUNCY BALLS';self.message_timer=.65

    def _spawn_three_balls(self):
        self.discover_boss_move('BOUNCY BALLS')
        for offset in (-DUMMY_RADIUS*.58,0,DUMMY_RADIUS*.58):
            rim=math.sqrt(max(0,DUMMY_RADIUS**2-offset**2))
            x=self.dummy_x-rim-25
            self.enemy_balls.append(EnemyBall(x,self.dummy_y+offset,
                          -random.uniform(280,370),random.choice((-1,1))*random.uniform(150,270),
                          fuse=2.3 if self.phase3 else 2.8))

    def _spawn_dots(self,shift=False):
        self.discover_boss_move('RED DOTS')
        self.dots.clear()
        fuse=1.15 if self.phase3 else 1.6
        for i in range(30):
            for _ in range(90):
                x=random.uniform(-WORLD_W/2+75,WORLD_W/2-75)
                y=random.uniform(-WORLD_H/2+75,WORLD_H/2-75)
                if math.hypot(x-self.dummy_x,y-self.dummy_y)>DUMMY_RADIUS+65:break
            self.dots.append(BombDot(x,y,fuse=fuse,shift_time=fuse*.52 if shift else -1))
        self.message='RED DOTS / 30 AT ONCE';self.message_timer=.7

    @staticmethod
    def _wall_reflection_ray(x,y,dx,dy,bounces=3):
        """Real equal-angle wall ricochets, never reflecting from the boss.

        Returns world-coordinate points on rectangle walls. Vertical and
        horizontal walls reverse only the corresponding velocity component.
        """
        xmin,xmax=-WORLD_W/2+9,WORLD_W/2-9
        ymin,ymax=-WORLD_H/2+9,WORLD_H/2-9
        dx,dy=normalized(dx,dy)
        points=[(x,y)]
        for _ in range(bounces):
            tx=((xmax-x)/dx if dx>1e-9 else (xmin-x)/dx if dx<-1e-9 else float('inf'))
            ty=((ymax-y)/dy if dy>1e-9 else (ymin-y)/dy if dy<-1e-9 else float('inf'))
            travel=min(tx,ty)
            if not math.isfinite(travel) or travel<0:break
            x=clamp(x+dx*travel,xmin,xmax)
            y=clamp(y+dy*travel,ymin,ymax)
            points.append((x,y))
            if abs(tx-ty)<1e-6:
                dx=-dx;dy=-dy
            elif tx<ty:dx=-dx
            else:dy=-dy
        return points

    def _laser_geometry(self,side):
        # Five staggered rays per side, bouncing off ARENA WALLS alone.
        # The boss never changes a ray's direction or blocks its path.
        sign=1 if side=='right' else -1
        eye_y=self.dummy_y-DUMMY_RADIUS*.31
        paths=[]
        for n,slope in enumerate((-.85,-.43,.08,.52,.91)):
            ex=self.dummy_x+(-1 if n%2==0 else 1)*DUMMY_RADIUS*.26
            paths.append(self._wall_reflection_ray(ex,eye_y,sign,slope,4))
        return paths

    def _tracking_laser_geometry(self,dt):
        # Smoothly turn towards the player rather than snapping the aim to them.
        paths=[];updated=[]
        for n in range(2):
            ex=self.dummy_x+(-1 if n==0 else 1)*DUMMY_RADIUS*.27
            ey=self.dummy_y+(DUMMY_RADIUS*.20 if self.phase3 else -DUMMY_RADIUS*.20)
            desired=normalized(self.x-ex,self.y-ey)
            old=self.eye_directions[n]
            rate=min(1,dt*(.85 if self.phase3 else .65))
            aim=normalized(old[0]*(1-rate)+desired[0]*rate,old[1]*(1-rate)+desired[1]*rate)
            if aim==(0,0):aim=(0,1)
            updated.append(aim)
            # Move well beyond bounds; renderer clips lines to the arena.
            endpoint=(ex+aim[0]*2400,ey+aim[1]*2400)
            paths.append([(ex,ey),endpoint])
        self.eye_directions=updated
        return paths

    def _update_stage(self,dt):
        self.stage_time+=dt
        t=self.stage_time
        fast=.68 if self.phase3 else 1.0
        if self.stage=='bouncy':
            if self.ball_pairs<3 and t>=.4+self.ball_pairs*.72:self._spawn_ball_pair()
            if self.ball_pairs>=3 and not self.enemy_balls and not self.explosions and t>5:
                self._begin('leave_right')
        elif self.stage=='leave_right':
            a=min(1,t/1.5);e=a*a*(3-2*a)
            self.dummy_x=self.stage_origin[0]+(WORLD_W/2+DUMMY_RADIUS+55-self.stage_origin[0])*e
            if a>=1:
                self.dummy_x=0;self.dummy_y=WORLD_H/2+DUMMY_RADIUS+48
                self._begin('enter_top')
        elif self.stage=='enter_top':
            a=min(1,t/1.7);e=a*a*(3-2*a)
            self.dummy_y=self.stage_origin[1]+(WORLD_H/2-self.stage_origin[1])*e
            if a>=1:self._begin('dots')
        elif self.stage in ('dots','dots_repeat','phase3_dots'):
            if not self.dots and not self.explosions and t>1.2:
                if self.stage=='phase3_dots':self._begin('cycle_summon')
                else:self._begin('lasers_right')
        elif self.stage in ('lasers_right','lasers_left'):
            self.laser_active=(.85*fast<=t<2.25*fast)
            if t>=2.8*fast:
                if self.stage=='lasers_right':self._begin('lasers_left')
                elif self.cycle_count==0:self._begin('exit_for_spikes')
                else:
                    self.hunters_per_cycle+=1
                    if self.phase3:self._begin('tracking')
                    else:self._begin('cycle_summon')
        elif self.stage=='exit_for_spikes':
            a=min(1,t/1.2);e=a*a*(3-2*a)
            self.dummy_y=self.stage_origin[1]+(WORLD_H/2+DUMMY_RADIUS+65-self.stage_origin[1])*e
            if a>=1:self._begin('spikes')
        elif self.stage=='spikes':
            self.spike_spawn_timer-=dt
            if self.spike_spawn_timer<=0 and t<5.3:
                for _ in range(3):
                    x=random.uniform(-WORLD_W/2+45,WORLD_W/2-45)
                    self.spikes.append(Spike(x,WORLD_H/2+20,random.uniform(-35,35),
                                             -random.uniform(440,670)))
                self.spike_spawn_timer+=.20
            if t>=6 and not self.spikes:self._begin('slam_prepare')
        elif self.stage=='slam_prepare':
            # Telegraph: the center is dangerous; edges are safe.
            if t>=1.5:self._begin('slam')
        elif self.stage=='slam':
            a=min(1,t/.9);e=a*a*(3-2*a)
            self.dummy_x=self.stage_origin[0]*(1-e)
            self.dummy_y=self.stage_origin[1]+(0-self.stage_origin[1])*e
            if a>=1:
                # The impact radius spans the center but leaves narrow safe sides.
                if abs(self.x)<WORLD_W*.37:self._hurt_player(self.x,self.y,0)
                self._begin('pulses')
        elif self.stage=='pulses':
            self.pulse_spawn_timer-=dt
            if self.pulse_count<4 and self.pulse_spawn_timer<=0:
                self.pulses.append(Pulse(0,480+self.pulse_count*140,21))
                self.pulse_count+=1
                # 2.85 seconds between pulses, safely longer than 1s dash CD.
                self.pulse_spawn_timer+=2.85
                self.message=f'PULSE {self.pulse_count}/4';self.message_timer=.5
            if self.pulse_count==4 and not self.pulses and t>4:self._begin('cycle_summon')
        elif self.stage=='cycle_summon':
            if t>=.8:self._begin('dots_repeat')
        elif self.stage=='phase3_glide':
            a=min(1,t/1.7);e=a*a*(3-2*a)
            self.dummy_x=self.stage_origin[0]*(1-e)
            self.dummy_y=self.stage_origin[1]+(-WORLD_H/2-self.stage_origin[1])*e
            if a>=1:self._begin('tracking')
        elif self.stage=='tracking':
            # Follow the player during the red-dot warning, then lock the aim.
            if t < 1.2 or not self.laser_paths:
                self.laser_paths=self._tracking_laser_geometry(dt)
            self.laser_active=t>=1.2
            if t>=5.2*(.75 if self.phase3 and self.cycle_count>0 else 1):
                self._begin('phase3_dots')

    def _update_balls(self,dt):
        remaining=[]
        for ball in self.enemy_balls:
            ball.age+=dt
            if ball.age>=ball.fuse:
                self.explosions.append(Explosion(ball.x,ball.y,76))
                self.emit(ball.x,ball.y,NEON,5)
                continue
            ox,oy=ball.x,ball.y
            ball.x+=ball.vx*dt;ball.y+=ball.vy*dt
            l,r=-WORLD_W/2+ball.radius,WORLD_W/2-ball.radius
            b,t=-WORLD_H/2+ball.radius,WORLD_H/2-ball.radius
            if ball.x<l or ball.x>r:ball.vx*=-1;ball.x=clamp(ball.x,l,r)
            if ball.y<b or ball.y>t:ball.vy*=-1;ball.y=clamp(ball.y,b,t)
            dx,dy=ball.x-self.dummy_x,ball.y-self.dummy_y
            d=math.hypot(dx,dy)
            min_d=DUMMY_RADIUS+ball.radius
            if d<min_d and self.dummy_hp>0:
                if d<.001:dx,dy,d=1,0,1
                nx,ny=dx/d,dy/d
                ball.x=self.dummy_x+nx*min_d;ball.y=self.dummy_y+ny*min_d
                approach=ball.vx*nx+ball.vy*ny
                if approach<0:ball.vx-=2*approach*nx;ball.vy-=2*approach*ny
            self._hurt_player(ball.x,ball.y,ball.radius)
            remaining.append(ball)
        self.enemy_balls=remaining

    def _update_dots(self,dt):
        remaining=[]
        for dot in self.dots:
            dot.age+=dt
            if dot.shift_time>0 and dot.age>=dot.shift_time and not dot.shifted:
                for _ in range(40):
                    nx=clamp(dot.x+random.uniform(-260,260),-WORLD_W/2+60,WORLD_W/2-60)
                    ny=clamp(dot.y+random.uniform(-200,200),-WORLD_H/2+60,WORLD_H/2-60)
                    if math.hypot(nx-self.dummy_x,ny-self.dummy_y)>DUMMY_RADIUS+55:break
                dot.x,dot.y=nx,ny;dot.shifted=True
            if dot.age>=dot.fuse:self.explosions.append(Explosion(dot.x,dot.y,68))
            else:remaining.append(dot)
        self.dots=remaining

    def _update_explosions(self,dt):
        keep=[]
        for ex in self.explosions:
            ex.age+=dt
            self._hurt_player(ex.x,ex.y,ex.radius*min(1,ex.age/.11))
            if ex.age<ex.lifetime:keep.append(ex)
        self.explosions=keep

    def _update_lasers(self):
        if not self.laser_active:return
        for path in self.laser_paths:
            for (x1,y1),(x2,y2) in zip(path,path[1:]):
                if segment_circle(x1,y1,x2,y2,self.x,self.y,12+PLAYER_RADIUS):
                    self._hurt_player(self.x,self.y,0)
                    return

    def _update_hunters(self,dt):
        for h in self.triangles:
            h.fire_timer-=dt
            if h.fire_timer<=0:
                dx,dy=normalized(self.x-h.x,self.y-h.y)
                self.hunter_shots.append(HunterShot(h.x,h.y,dx*340,dy*340))
                h.fire_timer=3.2 if self.phase3 else 4.0
        remaining=[]
        for shot in self.hunter_shots:
            ox,oy=shot.x,shot.y
            shot.x+=shot.vx*dt;shot.y+=shot.vy*dt;shot.lifetime-=dt
            if segment_circle(ox,oy,shot.x,shot.y,self.x,self.y,shot.radius+PLAYER_RADIUS):
                self._hurt_player(self.x,self.y,0)
                continue
            if shot.lifetime>0 and abs(shot.x)<WORLD_W/2 and abs(shot.y)<WORLD_H/2:
                remaining.append(shot)
        self.hunter_shots=remaining

    def _update_spikes(self,dt):
        keep=[]
        for spike in self.spikes:
            ox,oy=spike.x,spike.y
            spike.x+=spike.vx*dt;spike.y+=spike.vy*dt
            if segment_circle(ox,oy,spike.x,spike.y,self.x,self.y,spike.radius+PLAYER_RADIUS):
                self._hurt_player(self.x,self.y,0)
            if spike.y>-WORLD_H/2-40:keep.append(spike)
        self.spikes=keep

    def _update_pulses(self,dt):
        keep=[]
        for pulse in self.pulses:
            pulse.radius+=pulse.speed*dt
            distance=math.hypot(self.x-self.dummy_x,self.y-self.dummy_y)
            if not pulse.hit and abs(distance-pulse.radius)<pulse.width+PLAYER_RADIUS:
                if self._hurt_player(self.x,self.y,0):pulse.hit=True
            # Drop the ring once it has reached every arena corner.
            farthest=max(math.hypot(x-self.dummy_x,y-self.dummy_y)
                         for x in (-WORLD_W/2,WORLD_W/2)
                         for y in (-WORLD_H/2,WORLD_H/2))
            if pulse.radius<farthest+80:keep.append(pulse)
        self.pulses=keep

    def update_boss(self,dt):
        if self.dummy_hp<=0 or self.lives<=0:return
        self.player_invulnerable=max(0,self.player_invulnerable-dt)
        self.dash_iframes=max(0,self.dash_iframes-dt)
        if not self.phase3 and self.dummy_hp<=self.dummy_max_hp*.5:
            self.phase3=True;self.dummy_phase='PHASE 3'
            self.enemy_balls.clear();self.dots.clear();self.explosions.clear()
            self.laser_paths.clear();self.spikes.clear();self.pulses.clear()
            self.triangles.clear();self.hunter_shots.clear()
            self._begin('phase3_glide')
            self.message='PHASE 3 - THE GREETER AWAKENS';self.message_timer=2.2
        self._update_stage(dt)
        self._update_balls(dt)
        self._update_dots(dt)
        self._update_explosions(dt)
        self._update_lasers()
        self._update_hunters(dt)
        self._update_spikes(dt)
        self._update_pulses(dt)
        self.x,self.y=self._position_outside_boss(self.x,self.y)
        # The giant moving body itself is dangerous when it slams.

    def update(self,dt):
        self.time_alive+=dt
        self.shot_cycle+=dt
        self.shot_miss_flash=max(0,self.shot_miss_flash-dt)
        self.message_timer=max(0,self.message_timer-dt)
        for t in self.trail:t.age+=dt
        self.trail=[t for t in self.trail if t.age<t.lifetime]
        for name in self.cooldowns:
            self.cooldowns[name]=max(0,self.cooldowns[name]-dt)
            self.active[name]=max(0,self.active[name]-dt)
        self.guard_timer=max(0,self.guard_timer-dt)
        keep=[]
        for shot in self.projectiles:
            ox,oy=shot.x,shot.y
            shot.x+=shot.vx*dt;shot.y+=shot.vy*dt;shot.lifetime-=dt
            hit=None
            if self.training:
                target_hit=next((t for t in self.training_targets if t.respawn<=0 and
                        segment_circle(ox,oy,shot.x,shot.y,t.x,t.y,39+shot.radius)),None)
                if target_hit is not None:
                    dx,dy=normalized(shot.vx,shot.vy)
                    self._strike_training_target(target_hit,22,dx,dy,10)
                    self.training_hits+=1
                    self.emit(shot.x,shot.y,YELLOW,5,hash_shape=True)
                    continue
            for h in self.triangles:
                if segment_circle(ox,oy,shot.x,shot.y,h.x,h.y,PLAYER_RADIUS*2+shot.radius):
                    hit=h;break
            if hit is not None:
                self._damage_hunter(hit);self.emit(shot.x,shot.y,YELLOW,5,hash_shape=True)
                continue
            if self.dummy_hp>0 and segment_circle(ox,oy,shot.x,shot.y,self.dummy_x,self.dummy_y,DUMMY_RADIUS+shot.radius):
                self._hit_dummy(22);self.emit(shot.x,shot.y,YELLOW,6,hash_shape=True)
                continue
            if shot.lifetime>0 and abs(shot.x)<WORLD_W/2 and abs(shot.y)<WORLD_H/2:
                keep.append(shot)
        self.projectiles=keep
        remaining=[]
        for p in self.particles:
            p.lifetime-=dt
            if p.lifetime>0:
                p.x+=p.vx*dt;p.y+=p.vy*dt
                p.vx*=max(0,1-2*dt);p.vy*=max(0,1-2*dt)
                remaining.append(p)
        self.particles=remaining
        if self.training:
            self.update_training(dt)
        else:
            self._update_health_pickup(dt)
