"""
Build Your Battle – PvE Arena Brawler
======================================
Run:  python main.py
"""

import sys
import random
import math
import pygame
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE,
    WHITE, BLACK, RED, GRAY, DARK_GRAY, GREEN, YELLOW, CYAN,
    GROUND_Y, GRAVITY, FRICTION,
    FIGHTER_WIDTH, FIGHTER_HEIGHT, JUMP_FORCE,
    CHARACTERS, ATTACK_COOLDOWN, KNOCKBACK_FORCE, KNOCKBACK_UP,
    PROJECTILE_SPEED, PROJECTILE_LIFETIME, PROJECTILE_WIDTH, PROJECTILE_HEIGHT,
    DASH_SPEED, DASH_DURATION, DASH_COOLDOWN,
    STUN_DURATION, FLASH_DURATION,
    SHAKE_INTENSITY, SHAKE_DURATION,
    PARTICLE_GRAVITY, HIT_PARTICLE_COUNT, LAND_PARTICLE_COUNT,
    COUNTDOWN_TIME,
    REGEN_DELAY, REGEN_RATE, SHARD_REWARD, FORGE_UPGRADES, FORGE_ABILITIES,
    NEON_GREEN, SOURZEST_DAMAGE, SOURZEST_SPEED, SOURZEST_WIDTH, SOURZEST_HEIGHT,
    SOURZEST_STUN_MS, CRYSTALLIZE_COLOR, CRYSTALLIZE_VULN,
    BLOCK_DAMAGE_MULT, BLOCK_COLOR, BLOCK_TINT,
    GROUND_SLAM_DAMAGE, GROUND_SLAM_RADIUS, GROUND_SLAM_SPEED,
    HEAL_PULSE_AMOUNT, HEAL_PULSE_COOLDOWN,
    BOSS_ABILITY_INTERVAL, BOSS_SPREAD_ANGLES, BOSS_SHIELD_DURATION,
    BOSS_CHARGE_SPEED,
    WAVE_HP_SCALE, WAVE_ATK_SCALE, WAVE_SPD_SCALE, WAVE_SHARD_BONUS,
    BOSS_WAVE_INTERVAL, BOSS_HP_MULT, BOSS_ATK_MULT,
    BOSS_COLOR, BOSS_PROJ_COLOR, BOSS_NAMES,
    PLATFORMS, PLATFORM_HEIGHT,
    PICKUP_SPAWN_CHANCE, PICKUP_LIFETIME, PICKUP_HP_AMOUNT,
    PICKUP_SHARD_AMOUNT, PICKUP_DAMAGE_BOOST,
    PICKUP_DAMAGE_BOOST_DURATION, PICKUP_SIZE,
    COMBO_RESET_TIME, COMBO_MIN_FOR_BONUS, COMBO_SHARD_BONUS,
    ARENAS,
    AI_IDEAL_RANGE_MIN, AI_IDEAL_RANGE_MAX, AI_SHOOT_CHANCE, AI_DODGE_CHANCE,
    AI_BOSS_SHOOT_CHANCE, AI_BOSS_DODGE_CHANCE,
    AI_DODGE_PROJECTILE_DIST, AI_DODGE_JUMP_CHANCE,
    AI_BLOCK_CHANCE, AI_BLOCK_DURATION, AI_LOW_HP_THRESHOLD, AI_RETREAT_RANGE,
)


# ---------------------------------------------------------------------------
# Particle
# ---------------------------------------------------------------------------
class Particle:
    def __init__(self, x, y, vx, vy, color, lifetime):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.color = color
        self.lifetime = lifetime
        self.age = 0

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += PARTICLE_GRAVITY
        self.age += 1

    def alive(self):
        return self.age < self.lifetime

    def draw(self, surface, ox=0, oy=0):
        size = max(2, int(4 * (1 - self.age / self.lifetime)))
        pygame.draw.rect(surface, self.color,
                         (int(self.x) + ox, int(self.y) + oy, size, size))


# ---------------------------------------------------------------------------
# Projectile
# ---------------------------------------------------------------------------
class Projectile:
    def __init__(self, x, y, direction, color, attack_power, owner,
                 width=PROJECTILE_WIDTH, height=PROJECTILE_HEIGHT,
                 speed=PROJECTILE_SPEED, crystallize_ms=0):
        self.rect = pygame.Rect(x, y, width, height)
        self.direction = direction
        self.speed = speed
        self.color = color
        self.attack_power = attack_power
        self.owner = owner
        self.crystallize_ms = crystallize_ms
        self.age = 0

    def update(self):
        self.rect.x += self.speed * self.direction
        self.age += 1

    def alive(self):
        return self.age < PROJECTILE_LIFETIME and 0 <= self.rect.x <= SCREEN_WIDTH

    def draw(self, surface, ox=0, oy=0):
        r = self.rect.move(ox, oy)
        pygame.draw.rect(surface, self.color, r)


# ---------------------------------------------------------------------------
# Pickup — floating collectible orbs that spawn during fights
# ---------------------------------------------------------------------------
class Pickup:
    """Collectible that floats on the ground or platforms.

    Types:
      'hp'     — restore health (green)
      'shard'  — +shards (yellow)
      'boost'  — temp damage multiplier (purple)
    """
    COLORS = {
        "hp":    (80, 230, 120),
        "shard": (255, 220, 80),
        "boost": (200, 120, 255),
    }

    def __init__(self, x, y, kind, spawn_time):
        self.rect = pygame.Rect(x, y, PICKUP_SIZE, PICKUP_SIZE)
        self.kind = kind
        self.spawn_time = spawn_time
        self.anim_frame = 0

    def update(self):
        self.anim_frame += 1

    def alive(self, now):
        return now - self.spawn_time < PICKUP_LIFETIME

    def draw(self, surface, ox=0, oy=0):
        # Gentle bob to draw the eye
        bob = int(math.sin(self.anim_frame * 0.12) * 3)
        pulse = int(math.sin(self.anim_frame * 0.2) * 2)
        cx = self.rect.centerx + ox
        cy = self.rect.centery + oy + bob
        color = Pickup.COLORS[self.kind]
        # Outer glow ring
        pygame.draw.circle(surface, color,
                           (cx, cy), PICKUP_SIZE // 2 + pulse, 2)
        # Inner filled orb
        pygame.draw.circle(surface, color,
                           (cx, cy), PICKUP_SIZE // 2 - 3)
        # Symbol inside
        if self.kind == "hp":
            # plus sign
            pygame.draw.line(surface, WHITE, (cx - 4, cy), (cx + 4, cy), 2)
            pygame.draw.line(surface, WHITE, (cx, cy - 4), (cx, cy + 4), 2)
        elif self.kind == "shard":
            # diamond
            pygame.draw.polygon(surface, WHITE,
                                [(cx, cy - 4), (cx + 4, cy),
                                 (cx, cy + 4), (cx - 4, cy)])
        else:  # boost
            # lightning zigzag (small)
            pygame.draw.line(surface, WHITE, (cx - 3, cy - 4), (cx + 1, cy), 2)
            pygame.draw.line(surface, WHITE, (cx + 1, cy), (cx - 1, cy + 4), 2)


def random_pickup_spawn(now):
    """Create a random pickup at a random walkable location."""
    kind = random.choices(
        ["hp", "shard", "boost"],
        weights=[0.45, 0.35, 0.20],  # HP most common, boost rarest
    )[0]
    # Choose spawn surface: ground or one of the platforms
    surfaces = [(40, GROUND_Y, SCREEN_WIDTH - 80)]
    for px, py, pw in PLATFORMS:
        surfaces.append((px + 10, py, pw - 20))
    sx, sy, sw = random.choice(surfaces)
    x = random.randint(sx, sx + sw - PICKUP_SIZE)
    y = sy - PICKUP_SIZE - 4
    return Pickup(x, y, kind, now)


# ---------------------------------------------------------------------------
# Fighter
# ---------------------------------------------------------------------------
class Fighter:
    def __init__(self, x, char_data, controls, facing=1, is_player=False):
        self.name = char_data["name"]
        self.color = char_data["color"]
        self.proj_color = char_data["proj_color"]
        self.max_health = char_data["health"]
        self.health = self.max_health
        self.attack_power = char_data["attack"]
        self.defense = char_data["defense"]
        self.speed = char_data["speed"]

        self.rect = pygame.Rect(x, GROUND_Y - FIGHTER_HEIGHT,
                                FIGHTER_WIDTH, FIGHTER_HEIGHT)
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.on_ground = True
        self.was_on_ground = True
        self.last_attack = 0
        self.facing = facing
        self.controls = controls
        self.walking = False
        self.is_player = is_player
        self.is_boss = False

        # dash
        self.dash_timer = 0
        self.last_dash = 0
        self.dash_dir = 0

        # hit feedback
        self.stun_timer = 0
        self.flash_timer = 0
        self.last_hit_time = 0
        self.crystallized_until = 0

        # blocking
        self.blocking = False

        # abilities (player only)
        self.abilities = set()
        self.has_double_jumped = False
        self.jump_released = True   # edge detection for double jump
        self.last_heal = -HEAL_PULSE_COOLDOWN
        self.slamming = False

        # stun immunity — prevents perma-stun from rapid hits
        self.stun_immune_until = 0

        # damage boost pickup
        self.damage_boost_until = 0

        # boss specials
        self.boss_ability_type = None
        self.last_boss_ability = 0
        self.boss_blocking_until = 0

        # animation
        self.anim_frame = 0

    def handle_input(self, keys, now, projectiles):
        if self.stun_timer > 0 or now < self.crystallized_until:
            return
        self.walking = False
        self.blocking = False

        # block (hold E)
        if keys[self.controls.get("block", pygame.K_F12)]:
            self.blocking = True
            return  # can't do anything else while blocking

        # ground slam (S while airborne)
        if (not self.on_ground and keys[self.controls.get("down", pygame.K_F12)]
                and "ground_slam" in self.abilities and not self.slamming):
            self.slamming = True
            self.vel_y = GROUND_SLAM_SPEED
            self.vel_x = 0
            return

        if self.dash_timer <= 0:
            if keys[self.controls["left"]]:
                self.vel_x = -self.speed
                self.facing = -1
                self.walking = True
            elif keys[self.controls["right"]]:
                self.vel_x = self.speed
                self.facing = 1
                self.walking = True

        # jump + double jump (edge detection)
        # We track whether the key was released since the last jump.
        # This prevents a held key from instantly consuming the
        # double jump — you must release W and press it again.
        jump_held = keys[self.controls["jump"]]
        if jump_held and self.jump_released:
            self.jump_released = False
            if self.on_ground and self.dash_timer <= 0:
                self.vel_y = JUMP_FORCE
                self.on_ground = False
                self.has_double_jumped = False
            elif (not self.on_ground and not self.has_double_jumped
                  and "double_jump" in self.abilities):
                self.vel_y = JUMP_FORCE * 0.85
                self.has_double_jumped = True
        elif not jump_held:
            self.jump_released = True

        if keys[self.controls["attack"]]:
            if now - self.last_attack >= ATTACK_COOLDOWN:
                self.fire(now, projectiles)

        if keys[self.controls["dash"]]:
            if self.dash_timer <= 0 and now - self.last_dash >= DASH_COOLDOWN:
                self.dash_timer = DASH_DURATION
                self.last_dash = now
                self.dash_dir = self.facing

        # heal pulse (Q)
        if (keys[self.controls.get("heal", pygame.K_F12)]
                and "heal_pulse" in self.abilities
                and now - self.last_heal >= HEAL_PULSE_COOLDOWN
                and self.health < self.max_health):
            self.last_heal = now
            self.health = min(self.max_health,
                              self.health + HEAL_PULSE_AMOUNT)

    def fire(self, now, projectiles):
        if now - self.last_attack >= ATTACK_COOLDOWN:
            self.last_attack = now
            boost = PICKUP_DAMAGE_BOOST if now < self.damage_boost_until else 1.0
            if self.is_player:
                w, h = SOURZEST_WIDTH, SOURZEST_HEIGHT
                spawn_x = (self.rect.right if self.facing == 1
                           else self.rect.left - w)
                spawn_y = self.rect.centery - h // 2
                projectiles.append(
                    Projectile(spawn_x, spawn_y, self.facing,
                               NEON_GREEN, int(SOURZEST_DAMAGE * boost), self,
                               width=w, height=h, speed=SOURZEST_SPEED,
                               crystallize_ms=SOURZEST_STUN_MS))
            else:
                spawn_x = (self.rect.right if self.facing == 1
                           else self.rect.left - PROJECTILE_WIDTH)
                spawn_y = self.rect.centery - PROJECTILE_HEIGHT // 2
                projectiles.append(
                    Projectile(spawn_x, spawn_y, self.facing,
                               self.proj_color, int(self.attack_power * boost), self))

    def update(self, particles, now=0):
        self.anim_frame += 1
        self.was_on_ground = self.on_ground

        if (self.health < self.max_health
                and now - self.last_hit_time >= REGEN_DELAY):
            self.health = min(self.max_health, self.health + REGEN_RATE)

        if self.stun_timer > 0:
            self.stun_timer -= 1
        if self.flash_timer > 0:
            self.flash_timer -= 1

        # boss block
        if now < self.boss_blocking_until:
            self.blocking = True
        elif self.is_boss:
            self.blocking = False

        if self.dash_timer > 0:
            self.vel_x = DASH_SPEED * self.dash_dir
            self.dash_timer -= 1

        self.vel_y += GRAVITY
        self.vel_x *= FRICTION

        self.rect.x += int(self.vel_x)
        self.rect.y += int(self.vel_y)

        # ── Platform collision (one-way: land on top only) ──
        # We only resolve if the fighter is falling (vel_y > 0).
        # This lets fighters jump up through platforms from below,
        # but land on them when falling down — a common platformer
        # pattern called "one-way platforms".
        if self.vel_y > 0:
            for px, py, pw in PLATFORMS:
                plat = pygame.Rect(px, py, pw, PLATFORM_HEIGHT)
                if (self.rect.colliderect(plat)
                        and self.rect.bottom - int(self.vel_y) <= py + 2):
                    self.rect.bottom = py
                    self.vel_y = 0
                    self.on_ground = True
                    if self.slamming:
                        self.slamming = False

        # floor
        if self.rect.bottom >= GROUND_Y:
            landed_hard = not self.was_on_ground and self.vel_y > 2
            if landed_hard:
                for _ in range(LAND_PARTICLE_COUNT):
                    vx = random.uniform(-2, 2)
                    vy = random.uniform(-1.5, -0.5)
                    particles.append(Particle(self.rect.centerx, GROUND_Y,
                                              vx, vy, GRAY, 15))
            self.rect.bottom = GROUND_Y
            self.vel_y = 0
            self.on_ground = True
            if self.slamming:
                self.slamming = False
        # walls
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH

    def take_hit(self, damage, direction, particles, now=0, crystallize_ms=0):
        actual = max(1, damage - self.defense)
        if now < self.crystallized_until:
            actual = int(actual * CRYSTALLIZE_VULN)
        if self.blocking:
            actual = max(1, int(actual * BLOCK_DAMAGE_MULT))
        self.health -= actual
        self.last_hit_time = now

        # crystallize: only apply if NOT already crystallized (no refresh)
        if crystallize_ms > 0 and not self.blocking and now >= self.crystallized_until:
            self.crystallized_until = now + crystallize_ms

        if not self.blocking:
            self.vel_x += KNOCKBACK_FORCE * direction
            self.vel_y += KNOCKBACK_UP
            self.on_ground = False
            # stun immunity: skip stun if recently stunned (prevents perma-lock)
            if now >= self.stun_immune_until:
                self.stun_timer = STUN_DURATION
                self.stun_immune_until = now + 600  # 600ms immunity window
        self.flash_timer = FLASH_DURATION
        for _ in range(HIT_PARTICLE_COUNT):
            vx = random.uniform(-3, 3)
            vy = random.uniform(-4, 1)
            c = BLOCK_COLOR if self.blocking else WHITE
            particles.append(Particle(self.rect.centerx, self.rect.centery,
                                      vx, vy, c, 20))

    def draw(self, surface, ox=0, oy=0):
        r = self.rect.move(ox, oy)

        if self.dash_timer > 0:
            draw_rect = pygame.Rect(r.x - 5, r.y + 10,
                                    r.width + 10, r.height - 10)
        elif not self.on_ground:
            if self.slamming:
                draw_rect = pygame.Rect(r.x - 4, r.y + 8,
                                        r.width + 8, r.height - 8)
            elif self.vel_y < 0:
                draw_rect = pygame.Rect(r.x + 4, r.y - 6,
                                        r.width - 8, r.height + 6)
            else:
                draw_rect = pygame.Rect(r.x - 3, r.y + 6,
                                        r.width + 6, r.height - 6)
        elif self.walking:
            lean = int(math.sin(self.anim_frame * 0.3) * 2)
            draw_rect = pygame.Rect(r.x + lean, r.y, r.width, r.height)
        else:
            bob = int(math.sin(self.anim_frame * 0.08) * 2)
            draw_rect = pygame.Rect(r.x, r.y + bob, r.width, r.height)

        now_ms = pygame.time.get_ticks()
        if now_ms < self.crystallized_until:
            color = CRYSTALLIZE_COLOR
        elif self.blocking:
            color = BLOCK_TINT    # tint whole body when blocking
        elif self.flash_timer > 0:
            color = WHITE
        else:
            color = self.color
        pygame.draw.rect(surface, color, draw_rect)

        # shield visual when blocking — big, obvious, pulsing
        if self.blocking:
            pulse = int(math.sin(self.anim_frame * 0.4) * 2)
            sx = draw_rect.right + 2 if self.facing == 1 else draw_rect.left - 14
            shield_rect = pygame.Rect(sx, draw_rect.y - 2 - pulse,
                                      12, draw_rect.height + 4 + pulse * 2)
            pygame.draw.rect(surface, BLOCK_COLOR, shield_rect, border_radius=3)
            pygame.draw.rect(surface, WHITE, shield_rect, 2, border_radius=3)
            if "reflect" in self.abilities:
                pygame.draw.rect(surface, CYAN, shield_rect, 3, border_radius=3)
            # outline the fighter too for extra feedback
            pygame.draw.rect(surface, BLOCK_COLOR, draw_rect, 2)

        # eyes
        if self.stun_timer > 0 or now_ms < self.crystallized_until:
            ey = draw_rect.y + 18
            cx1 = (draw_rect.x + draw_rect.width - 18 if self.facing == 1
                   else draw_rect.x + 8)
            for cx in (cx1, cx1 + 10):
                pygame.draw.line(surface, BLACK,
                                 (cx - 3, ey - 3), (cx + 3, ey + 3), 2)
                pygame.draw.line(surface, BLACK,
                                 (cx + 3, ey - 3), (cx - 3, ey + 3), 2)
        else:
            ey = draw_rect.y + 15
            if self.facing == 1:
                ex1 = draw_rect.x + draw_rect.width - 18
                ex2 = draw_rect.x + draw_rect.width - 10
            else:
                ex1 = draw_rect.x + 6
                ex2 = draw_rect.x + 14
            ec = BLACK if self.flash_timer <= 0 else GRAY
            pygame.draw.rect(surface, ec, (ex1, ey, 5, 6))
            pygame.draw.rect(surface, ec, (ex2, ey, 5, 6))

    def draw_health_bar(self, surface, x, y, width=200):
        ratio = max(self.health / self.max_health, 0)
        pygame.draw.rect(surface, DARK_GRAY, (x, y, width, 18))
        pygame.draw.rect(surface, GREEN, (x, y, int(width * ratio), 18))
        pygame.draw.rect(surface, WHITE, (x, y, width, 18), 2)

    def draw_cooldown_bar(self, surface, ox=0, oy=0):
        now = pygame.time.get_ticks()
        elapsed = now - self.last_attack
        ratio = min(elapsed / ATTACK_COOLDOWN, 1.0)
        bx = self.rect.x + ox
        by = self.rect.bottom + 4 + oy
        pygame.draw.rect(surface, DARK_GRAY, (bx, by, FIGHTER_WIDTH, 4))
        pygame.draw.rect(surface, YELLOW, (bx, by, int(FIGHTER_WIDTH * ratio), 4))


# ---------------------------------------------------------------------------
# AI controller
# ---------------------------------------------------------------------------
def ai_update(ai, player, now, projectiles):
    """
    Priority-based AI decision system.  Each frame the NPC evaluates
    threats and picks the highest-priority action:

      1. DODGE  — jump to avoid an incoming projectile
      2. BLOCK  — raise shield when recently hit and under pressure
      3. RETREAT — back away when health is low
      4. RANGE  — maintain ideal medium distance
      5. ATTACK — shoot when player is in line of sight
      6. IDLE   — occasional random hop

    This replaces the old "stand and shoot" logic that ignored danger.
    """
    if ai.stun_timer > 0 or now < ai.crystallized_until:
        return
    if now < ai.boss_blocking_until:
        return

    dx = player.rect.centerx - ai.rect.centerx
    distance = abs(dx)
    ai.facing = 1 if dx > 0 else -1
    ai.walking = False
    ai.blocking = False
    hp_ratio = ai.health / ai.max_health

    # ── PRIORITY 1: DODGE incoming projectiles ──
    # Scan every projectile — if one is owned by the player and
    # heading toward us within a danger radius, jump out of the way.
    # "heading toward us" means the projectile's direction points at
    # our position (dot-product sign check simplified to a < comparison).
    threat = False
    for proj in projectiles:
        if proj.owner is ai:
            continue
        # is it heading our way and close enough?
        proj_dx = ai.rect.centerx - proj.rect.centerx
        heading_toward = (proj.direction == 1 and proj_dx > 0) or \
                         (proj.direction == -1 and proj_dx < 0)
        if heading_toward and abs(proj_dx) < AI_DODGE_PROJECTILE_DIST:
            # vertical alignment check — only a threat if roughly same Y
            if abs(proj.rect.centery - ai.rect.centery) < FIGHTER_HEIGHT:
                threat = True
                break

    if threat and ai.on_ground and random.random() < AI_DODGE_JUMP_CHANCE:
        ai.vel_y = JUMP_FORCE
        ai.on_ground = False
        return  # dodge takes full priority this frame

    # ── PRIORITY 2: BLOCK when under pressure ──
    # "Under pressure" = hit within the last 800ms.  The AI raises
    # its shield with a probability check each frame — this prevents
    # perfect-blocking every hit while still making it reactive.
    recently_hit = now - ai.last_hit_time < AI_BLOCK_DURATION
    if recently_hit and random.random() < AI_BLOCK_CHANCE:
        ai.blocking = True
        return  # blocking prevents all other actions

    # ── PRIORITY 3: RETREAT when low health ──
    # Below a HP threshold the NPC prefers a wider range, creating
    # breathing room.  This is a simple behavioral "state change" —
    # the constants shift, not the logic.
    if hp_ratio < AI_LOW_HP_THRESHOLD:
        ideal_min = AI_RETREAT_RANGE
        ideal_max = AI_RETREAT_RANGE + 80
    else:
        ideal_min = AI_IDEAL_RANGE_MIN
        ideal_max = AI_IDEAL_RANGE_MAX

    # ── PRIORITY 4: RANGE — maintain ideal distance ──
    if distance < ideal_min:
        ai.vel_x = -ai.speed * ai.facing
        ai.walking = True
    elif distance > ideal_max:
        ai.vel_x = ai.speed * ai.facing
        ai.walking = True

    # ── PRIORITY 5: ATTACK ──
    shoot_chance = AI_BOSS_SHOOT_CHANCE if ai.is_boss else AI_SHOOT_CHANCE
    y_diff = abs(player.rect.centery - ai.rect.centery)
    if y_diff < FIGHTER_HEIGHT * 1.2:
        if now - ai.last_attack >= ATTACK_COOLDOWN:
            if random.random() < shoot_chance:
                ai.fire(now, projectiles)

    # ── PRIORITY 6: IDLE hop ──
    dodge_chance = AI_BOSS_DODGE_CHANCE if ai.is_boss else AI_DODGE_CHANCE
    if ai.on_ground and random.random() < dodge_chance:
        ai.vel_y = JUMP_FORCE
        ai.on_ground = False

    # ── BOSS specials (run alongside normal AI) ──
    if ai.is_boss and ai.boss_ability_type and now - ai.last_boss_ability >= BOSS_ABILITY_INTERVAL:
        _do_boss_ability(ai, player, now, projectiles)


def _do_boss_ability(ai, player, now, projectiles):
    ai.last_boss_ability = now
    ability = ai.boss_ability_type

    if ability == "spread":
        # fire 3 projectiles at different Y offsets
        ai.last_attack = now
        for y_off in BOSS_SPREAD_ANGLES:
            spawn_x = (ai.rect.right if ai.facing == 1
                       else ai.rect.left - PROJECTILE_WIDTH)
            spawn_y = ai.rect.centery + y_off
            projectiles.append(
                Projectile(spawn_x, spawn_y, ai.facing,
                           BOSS_PROJ_COLOR, ai.attack_power, ai))

    elif ability == "shield":
        ai.boss_blocking_until = now + BOSS_SHIELD_DURATION

    elif ability == "charge":
        ai.vel_x = BOSS_CHARGE_SPEED * ai.facing
        ai.dash_timer = DASH_DURATION

    elif ability == "slam":
        if ai.on_ground:
            ai.vel_y = JUMP_FORCE * 1.5
            ai.on_ground = False
            ai.slamming = True

    elif ability == "all":
        # pick one at random
        choice = random.choice(["spread", "shield", "charge", "slam"])
        ai.boss_ability_type = choice
        _do_boss_ability(ai, player, now, projectiles)
        ai.boss_ability_type = "all"


# ---------------------------------------------------------------------------
# Wave scaling
# ---------------------------------------------------------------------------
BOSS_ABILITY_MAP = {0: "spread", 1: "shield", 2: "charge", 3: "slam", 4: "all"}


def build_npc_data(base_char, wave):
    d = dict(base_char)
    d["health"] = int(d["health"] * (1 + WAVE_HP_SCALE * (wave - 1)))
    d["attack"] = int(d["attack"] * (1 + WAVE_ATK_SCALE * (wave - 1)))
    d["speed"] = min(12, d["speed"] * (1 + WAVE_SPD_SCALE * (wave - 1)))
    is_boss = wave % BOSS_WAVE_INTERVAL == 0
    if is_boss:
        d["health"] = int(d["health"] * BOSS_HP_MULT)
        d["attack"] = int(d["attack"] * BOSS_ATK_MULT)
        d["color"] = BOSS_COLOR
        d["proj_color"] = BOSS_PROJ_COLOR
        boss_idx = (wave // BOSS_WAVE_INTERVAL - 1) % len(BOSS_NAMES)
        d["name"] = BOSS_NAMES[boss_idx]
    else:
        d["name"] = d["name"] + f" Lv.{wave}"
    return d, is_boss


def boss_ability_for_wave(wave):
    idx = (wave // BOSS_WAVE_INTERVAL - 1) % len(BOSS_ABILITY_MAP)
    return BOSS_ABILITY_MAP[idx]


def wave_shard_reward(wave):
    return SHARD_REWARD + WAVE_SHARD_BONUS * (wave - 1)


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def draw_background(surface, ox=0, oy=0, arena=None):
    theme = arena or ARENAS[0]
    surface.fill(theme["bg"])
    pygame.draw.rect(surface, theme["bg2"],
                     (0, SCREEN_HEIGHT // 2, SCREEN_WIDTH, SCREEN_HEIGHT // 2))
    pygame.draw.rect(surface, theme["wall"],
                     (ox, 200 + oy, 20, GROUND_Y - 200))
    pygame.draw.rect(surface, theme["wall"],
                     (SCREEN_WIDTH - 20 + ox, 200 + oy, 20, GROUND_Y - 200))
    # platforms
    for px, py, pw in PLATFORMS:
        pygame.draw.rect(surface, theme["platform"],
                         (px + ox, py + oy, pw, PLATFORM_HEIGHT))
        pygame.draw.line(surface, WHITE,
                         (px + ox, py + oy), (px + pw + ox, py + oy), 2)
    # ground
    pygame.draw.rect(surface, theme["ground"],
                     (ox, GROUND_Y + oy, SCREEN_WIDTH, SCREEN_HEIGHT - GROUND_Y))
    pygame.draw.line(surface, WHITE,
                     (ox, GROUND_Y + oy), (SCREEN_WIDTH + ox, GROUND_Y + oy), 2)


def draw_stat_bars(surface, x, y, char_data, font):
    stats = [
        ("HP",  char_data["health"], 150, GREEN),
        ("ATK", char_data["attack"], 30, RED),
        ("DEF", char_data["defense"], 10, (100, 150, 255)),
        ("SPD", char_data["speed"], 10, YELLOW),
    ]
    for i, (label, value, max_val, color) in enumerate(stats):
        sy = y + i * 22
        txt = font.render(label, True, WHITE)
        surface.blit(txt, (x, sy))
        bx = x + 40
        bw = 120
        ratio = min(value / max_val, 1.0)
        pygame.draw.rect(surface, DARK_GRAY, (bx, sy + 2, bw, 12))
        pygame.draw.rect(surface, color, (bx, sy + 2, int(bw * ratio), 12))
        pygame.draw.rect(surface, WHITE, (bx, sy + 2, bw, 12), 1)


def draw_button(surface, font, text, center_x, center_y, color, bg_color):
    txt_surf = font.render(text, True, color)
    txt_rect = txt_surf.get_rect(center=(center_x, center_y))
    btn_rect = txt_rect.inflate(40, 16)
    pygame.draw.rect(surface, bg_color, btn_rect, border_radius=6)
    pygame.draw.rect(surface, color, btn_rect, 2, border_radius=6)
    surface.blit(txt_surf, txt_rect)
    return btn_rect


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    font_large = pygame.font.SysFont(None, 64)
    font_med = pygame.font.SysFont(None, 36)
    font_small = pygame.font.SysFont(None, 24)
    font_tiny = pygame.font.SysFont(None, 20)

    p1_controls = {
        "left": pygame.K_a, "right": pygame.K_d,
        "jump": pygame.K_w, "attack": pygame.K_SPACE,
        "dash": pygame.K_LSHIFT, "block": pygame.K_e,
        "heal": pygame.K_q, "down": pygame.K_s,
    }
    npc_controls = {
        "left": pygame.K_F1, "right": pygame.K_F2,
        "jump": pygame.K_F3, "attack": pygame.K_F4,
        "dash": pygame.K_F5,
    }

    state = "menu"
    menu_frame = 0
    p1_choice = 0
    npc_choice = 1

    player = npc = None
    projectiles = []
    particles = []
    shake_timer = 0
    state_timer = 0
    shards = 0
    wave = 1
    is_boss_wave = False
    last_shard_gain = 0

    # pickups + combo + arena theme
    pickups = []
    combo = 0
    max_combo = 0
    last_combo_hit = 0
    combo_bonus = 0         # extra shards awarded on victory from combo
    arena = ARENAS[0]

    upgrades = {"health": 0, "attack": 0, "defense": 0, "speed": 0}
    unlocked_abilities = set()

    # button rects
    btn_forge = btn_retry = btn_menu = None
    forge_buy_btns = [None] * len(FORGE_UPGRADES)
    forge_ability_btns = [None] * len(FORGE_ABILITIES)
    btn_forge_fight = btn_forge_menu = None

    def apply_upgrades():
        base = dict(CHARACTERS[p1_choice])
        for info in FORGE_UPGRADES:
            stat = info["stat"]
            base[stat] = base[stat] + info["amount"] * upgrades[stat]
        return base

    def start_fight():
        nonlocal player, npc, projectiles, particles, shake_timer, is_boss_wave
        nonlocal pickups, combo, max_combo, last_combo_hit, combo_bonus, arena
        char_data = apply_upgrades()
        player = Fighter(150, char_data, p1_controls, facing=1, is_player=True)
        player.abilities = set(unlocked_abilities)
        npc_data, is_boss_wave = build_npc_data(CHARACTERS[npc_choice], wave)
        npc = Fighter(550, npc_data, npc_controls, facing=-1)
        npc.is_boss = is_boss_wave
        if is_boss_wave:
            npc.boss_ability_type = boss_ability_for_wave(wave)
        projectiles.clear()
        particles.clear()
        pickups.clear()
        combo = 0
        max_combo = 0
        last_combo_hit = 0
        combo_bonus = 0
        arena = ARENAS[(wave - 1) % len(ARENAS)]
        shake_timer = 0

    def try_buy_ability(idx):
        nonlocal shards
        info = FORGE_ABILITIES[idx]
        if info["id"] not in unlocked_abilities and shards >= info["cost"]:
            shards -= info["cost"]
            unlocked_abilities.add(info["id"])

    running = True

    while running:
        now = pygame.time.get_ticks()
        menu_frame += 1
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if state == "menu":
                    if event.key == pygame.K_RETURN:
                        state = "select"
                        p1_choice = 0
                        npc_choice = random.randint(0, len(CHARACTERS) - 1)

                elif state == "select":
                    if event.key == pygame.K_a:
                        p1_choice = (p1_choice - 1) % len(CHARACTERS)
                    elif event.key == pygame.K_d:
                        p1_choice = (p1_choice + 1) % len(CHARACTERS)
                    elif event.key == pygame.K_SPACE:
                        wave = 1
                        start_fight()
                        state = "countdown"
                        state_timer = now
                    elif event.key == pygame.K_ESCAPE:
                        state = "menu"

                elif state == "fight":
                    if event.key == pygame.K_ESCAPE:
                        state = "pause"

                elif state == "pause":
                    if event.key == pygame.K_ESCAPE:
                        state = "fight"
                    elif event.key == pygame.K_q:
                        state = "menu"

                elif state == "victory":
                    if event.key == pygame.K_RETURN:
                        state = "forge"
                    elif event.key == pygame.K_ESCAPE:
                        state = "menu"

                elif state == "defeat":
                    if event.key == pygame.K_RETURN:
                        start_fight()
                        state = "countdown"
                        state_timer = now
                    elif event.key == pygame.K_ESCAPE:
                        state = "menu"

                elif state == "forge":
                    if event.key == pygame.K_ESCAPE:
                        state = "menu"
                    elif event.key == pygame.K_RETURN:
                        wave += 1
                        npc_choice = random.randint(0, len(CHARACTERS) - 1)
                        start_fight()
                        state = "countdown"
                        state_timer = now
                    elif event.key in (pygame.K_1, pygame.K_2,
                                       pygame.K_3, pygame.K_4):
                        idx = event.key - pygame.K_1
                        info = FORGE_UPGRADES[idx]
                        cost = info["base_cost"] + info["cost_inc"] * upgrades[info["stat"]]
                        if shards >= cost:
                            shards -= cost
                            upgrades[info["stat"]] += 1
                    elif event.key in (pygame.K_5, pygame.K_6,
                                       pygame.K_7, pygame.K_8):
                        try_buy_ability(event.key - pygame.K_5)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == "victory":
                    if btn_forge and btn_forge.collidepoint(mouse_pos):
                        state = "forge"
                    elif btn_menu and btn_menu.collidepoint(mouse_pos):
                        state = "menu"
                elif state == "defeat":
                    if btn_retry and btn_retry.collidepoint(mouse_pos):
                        start_fight()
                        state = "countdown"
                        state_timer = now
                    elif btn_menu and btn_menu.collidepoint(mouse_pos):
                        state = "menu"
                elif state == "forge":
                    for idx, btn in enumerate(forge_buy_btns):
                        if btn and btn.collidepoint(mouse_pos):
                            info = FORGE_UPGRADES[idx]
                            cost = info["base_cost"] + info["cost_inc"] * upgrades[info["stat"]]
                            if shards >= cost:
                                shards -= cost
                                upgrades[info["stat"]] += 1
                            break
                    for idx, btn in enumerate(forge_ability_btns):
                        if btn and btn.collidepoint(mouse_pos):
                            try_buy_ability(idx)
                            break
                    if btn_forge_fight and btn_forge_fight.collidepoint(mouse_pos):
                        wave += 1
                        npc_choice = random.randint(0, len(CHARACTERS) - 1)
                        start_fight()
                        state = "countdown"
                        state_timer = now
                    elif btn_forge_menu and btn_forge_menu.collidepoint(mouse_pos):
                        state = "menu"

        # -- update ---------------------------------------------------------
        if state == "countdown":
            if (now - state_timer) / 1000.0 >= COUNTDOWN_TIME + 0.5:
                state = "fight"

        elif state == "fight":
            keys = pygame.key.get_pressed()
            player.handle_input(keys, now, projectiles)
            ai_update(npc, player, now, projectiles)
            player.update(particles, now)
            npc.update(particles, now)

            # ground slam landing check
            for fighter in (player, npc):
                if fighter.was_on_ground is False and fighter.on_ground and fighter.slamming is False:
                    pass  # normal landing
                # slam damage handled below

            # player ground slam hit
            if player.was_on_ground is False and player.on_ground and "ground_slam" in player.abilities:
                # check if player just slammed (vel was high)
                pass
            # simpler: check slamming flag cleared this frame
            if not player.slamming and player.on_ground and player.was_on_ground is False:
                # this fires on any landing, only apply damage if abilities equipped
                # we need a better flag
                pass

            # fighter collision
            if player.rect.colliderect(npc.rect):
                overlap = player.rect.clip(npc.rect).width
                if player.rect.centerx < npc.rect.centerx:
                    player.rect.x -= overlap // 2 + 1
                    npc.rect.x += overlap // 2 + 1
                else:
                    player.rect.x += overlap // 2 + 1
                    npc.rect.x -= overlap // 2 + 1

            # projectiles
            alive_projs = []
            for proj in projectiles:
                proj.update()
                if not proj.alive():
                    continue
                hit = False
                for fighter in (player, npc):
                    if fighter is not proj.owner and proj.rect.colliderect(fighter.rect):
                        # reflect check
                        if (fighter.blocking and "reflect" in fighter.abilities):
                            proj.direction *= -1
                            proj.owner = fighter
                            proj.color = NEON_GREEN if fighter.is_player else fighter.proj_color
                            break
                        fighter.take_hit(proj.attack_power, proj.direction,
                                         particles, now, proj.crystallize_ms)
                        shake_timer = SHAKE_DURATION
                        # combo tracking
                        if fighter is npc:
                            combo += 1
                            max_combo = max(max_combo, combo)
                            last_combo_hit = now
                        else:
                            combo = 0
                        hit = True
                        break
                if not hit:
                    alive_projs.append(proj)
            projectiles[:] = alive_projs

            # boss slam shockwave damage
            if npc.is_boss and npc.on_ground and not npc.was_on_ground and npc.slamming:
                dist = abs(player.rect.centerx - npc.rect.centerx)
                if dist < GROUND_SLAM_RADIUS:
                    direction = 1 if player.rect.centerx > npc.rect.centerx else -1
                    player.take_hit(GROUND_SLAM_DAMAGE, direction, particles, now)
                    shake_timer = SHAKE_DURATION
                for _ in range(12):
                    vx = random.uniform(-5, 5)
                    vy = random.uniform(-3, -1)
                    particles.append(Particle(npc.rect.centerx, GROUND_Y,
                                              vx, vy, BOSS_COLOR, 20))

            # player ground slam shockwave
            if ("ground_slam" in player.abilities and player.on_ground
                    and not player.was_on_ground
                    and hasattr(player, '_was_slamming') and player._was_slamming):
                dist = abs(npc.rect.centerx - player.rect.centerx)
                if dist < GROUND_SLAM_RADIUS:
                    direction = 1 if npc.rect.centerx > player.rect.centerx else -1
                    npc.take_hit(GROUND_SLAM_DAMAGE, direction, particles, now)
                    shake_timer = SHAKE_DURATION
                for _ in range(10):
                    vx = random.uniform(-4, 4)
                    vy = random.uniform(-3, -1)
                    particles.append(Particle(player.rect.centerx, GROUND_Y,
                                              vx, vy, NEON_GREEN, 18))

            # track slamming state for next frame
            player._was_slamming = player.slamming or (not player.on_ground and player.vel_y > GROUND_SLAM_SPEED * 0.8)
            if npc.is_boss:
                npc._was_slamming = npc.slamming

            # particles
            for p in particles:
                p.update()
            particles[:] = [p for p in particles if p.alive()]

            # -- combo decay --
            if combo > 0 and now - last_combo_hit > COMBO_RESET_TIME:
                combo = 0

            # -- pickup spawning --
            if random.random() < PICKUP_SPAWN_CHANCE:
                pickups.append(random_pickup_spawn(now))

            # -- pickup update + collection --
            alive_pickups = []
            for pk in pickups:
                pk.update()
                if not pk.alive(now):
                    continue
                if pk.rect.colliderect(player.rect):
                    # player collects it
                    if pk.kind == "hp":
                        player.health = min(player.max_health,
                                            player.health + PICKUP_HP_AMOUNT)
                    elif pk.kind == "shard":
                        shards += PICKUP_SHARD_AMOUNT
                    elif pk.kind == "boost":
                        player.damage_boost_until = now + PICKUP_DAMAGE_BOOST_DURATION
                    # collection burst
                    for _ in range(10):
                        vx = random.uniform(-3, 3)
                        vy = random.uniform(-4, -1)
                        particles.append(Particle(
                            pk.rect.centerx, pk.rect.centery,
                            vx, vy, Pickup.COLORS[pk.kind], 22))
                    continue
                alive_pickups.append(pk)
            pickups[:] = alive_pickups

            # KO
            if npc.health <= 0:
                last_shard_gain = wave_shard_reward(wave)
                # combo bonus
                if max_combo >= COMBO_MIN_FOR_BONUS:
                    combo_bonus = (max_combo - COMBO_MIN_FOR_BONUS + 1) * COMBO_SHARD_BONUS
                    last_shard_gain += combo_bonus
                shards += last_shard_gain
                state = "victory"
                state_timer = now
            elif player.health <= 0:
                state = "defeat"
                state_timer = now

        elif state in ("victory", "defeat"):
            for p in particles:
                p.update()
            particles[:] = [p for p in particles if p.alive()]

        # -- shake --
        if shake_timer > 0:
            sx = random.randint(-SHAKE_INTENSITY, SHAKE_INTENSITY)
            sy = random.randint(-SHAKE_INTENSITY, SHAKE_INTENSITY)
            shake_timer -= 1
        else:
            sx = sy = 0

        # -- draw -----------------------------------------------------------
        btn_forge = btn_retry = btn_menu = None

        if state == "menu":
            screen.fill(DARK_GRAY)
            bob = int(math.sin(menu_frame * 0.05) * 5)
            t = font_large.render("BUILD YOUR BATTLE", True, WHITE)
            screen.blit(t, t.get_rect(center=(SCREEN_WIDTH // 2, 200 + bob)))
            s = font_med.render("PvE Arena Brawler", True, GRAY)
            screen.blit(s, s.get_rect(center=(SCREEN_WIDTH // 2, 260)))
            if menu_frame % 60 < 40:
                p = font_med.render("Press ENTER to start", True, YELLOW)
                screen.blit(p, p.get_rect(center=(SCREEN_WIDTH // 2, 400)))

        elif state == "select":
            screen.fill(DARK_GRAY)
            t = font_med.render("CHOOSE YOUR FIGHTER", True, WHITE)
            screen.blit(t, t.get_rect(center=(SCREEN_WIDTH // 2, 40)))
            # player panel
            char = CHARACTERS[p1_choice]
            px, py = 30, 80
            cx = px + 170
            pygame.draw.rect(screen, (50, 50, 60), (px, py, 340, 400), border_radius=8)
            screen.blit(font_med.render("Your Fighter", True, char["color"]), (px + 20, py + 10))
            screen.blit(font_med.render("<", True, WHITE), (px + 20, py + 85))
            screen.blit(font_med.render(">", True, WHITE), (px + 300, py + 85))
            pr = pygame.Rect(cx - FIGHTER_WIDTH // 2, py + 60, FIGHTER_WIDTH, FIGHTER_HEIGHT)
            pygame.draw.rect(screen, char["color"], pr)
            pygame.draw.rect(screen, BLACK, (pr.right - 18, pr.y + 15, 5, 6))
            pygame.draw.rect(screen, BLACK, (pr.right - 10, pr.y + 15, 5, 6))
            screen.blit(font_med.render(char["name"], True, WHITE),
                         font_med.render(char["name"], True, WHITE).get_rect(center=(cx, py + 160)))
            draw_stat_bars(screen, px + 40, py + 190, char, font_small)
            screen.blit(font_small.render("A/D select  |  SPACE confirm", True, GRAY),
                         font_small.render("A/D select  |  SPACE confirm", True, GRAY).get_rect(center=(cx, py + 370)))
            # NPC panel
            nchar = CHARACTERS[npc_choice]
            npx, ncx = 430, 600
            pygame.draw.rect(screen, (50, 50, 60), (npx, py, 340, 400), border_radius=8)
            screen.blit(font_med.render("Opponent", True, nchar["color"]), (npx + 20, py + 10))
            npr = pygame.Rect(ncx - FIGHTER_WIDTH // 2, py + 60, FIGHTER_WIDTH, FIGHTER_HEIGHT)
            pygame.draw.rect(screen, nchar["color"], npr)
            pygame.draw.rect(screen, BLACK, (npr.x + 6, npr.y + 15, 5, 6))
            pygame.draw.rect(screen, BLACK, (npr.x + 14, npr.y + 15, 5, 6))
            screen.blit(font_med.render(nchar["name"], True, WHITE),
                         font_med.render(nchar["name"], True, WHITE).get_rect(center=(ncx, py + 160)))
            draw_stat_bars(screen, npx + 40, py + 190, nchar, font_small)
            screen.blit(font_small.render("AI Controlled", True, GRAY),
                         font_small.render("AI Controlled", True, GRAY).get_rect(center=(ncx, py + 370)))

        elif state in ("countdown", "fight", "victory", "defeat", "pause"):
            draw_background(screen, sx, sy, arena)
            if player:
                player.draw(screen, sx, sy)
                npc.draw(screen, sx, sy)
                player.draw_cooldown_bar(screen, sx, sy)
                npc.draw_cooldown_bar(screen, sx, sy)
            for pk in pickups:
                pk.draw(screen, sx, sy)
            for proj in projectiles:
                proj.draw(screen, sx, sy)
            for p in particles:
                p.draw(screen, sx, sy)

            # HUD
            if player:
                player.draw_health_bar(screen, 20, 20)
                npc.draw_health_bar(screen, SCREEN_WIDTH - 220, 20)
                screen.blit(font_small.render(player.name, True, WHITE), (20, 42))
                screen.blit(font_small.render(npc.name + (" (BOSS)" if is_boss_wave else " (NPC)"),
                             True, WHITE), (SCREEN_WIDTH - 220, 42))
                # ability indicators
                if "heal_pulse" in player.abilities:
                    heal_cd = max(0, HEAL_PULSE_COOLDOWN - (now - player.last_heal))
                    if heal_cd > 0:
                        ht = font_tiny.render(f"Heal: {heal_cd // 1000 + 1}s", True, GRAY)
                    else:
                        ht = font_tiny.render("Heal: READY [Q]", True, GREEN)
                    screen.blit(ht, (20, 58))

            # wave + shards
            wc = BOSS_COLOR if is_boss_wave else GRAY
            wl = f"Wave {wave}" + ("  BOSS" if is_boss_wave else "")
            screen.blit(font_small.render(wl, True, wc),
                         font_small.render(wl, True, wc).get_rect(center=(SCREEN_WIDTH // 2, 15)))
            screen.blit(font_small.render(f"Shards: {shards}", True, YELLOW),
                         font_small.render(f"Shards: {shards}", True, YELLOW).get_rect(center=(SCREEN_WIDTH // 2, 35)))

            # arena label
            screen.blit(font_tiny.render(arena["name"], True, GRAY), (20, 78))

            # combo counter
            if combo >= 2:
                combo_col = YELLOW if combo >= COMBO_MIN_FOR_BONUS else WHITE
                ct = font_med.render(f"{combo}x COMBO", True, combo_col)
                screen.blit(ct, ct.get_rect(center=(SCREEN_WIDTH // 2, 90)))

            # damage boost timer
            if player and now < player.damage_boost_until:
                remain = (player.damage_boost_until - now) / 1000
                bt = font_tiny.render(
                    f"POWER BOOST  {remain:.1f}s", True, (200, 120, 255))
                screen.blit(bt, bt.get_rect(center=(SCREEN_WIDTH // 2, 115)))

            # block hint
            if state == "fight" and player and player.blocking:
                bt = font_tiny.render("BLOCKING", True, BLOCK_COLOR)
                screen.blit(bt, bt.get_rect(center=(player.rect.centerx, player.rect.top - 15)))

            if state == "countdown":
                elapsed = (now - state_timer) / 1000.0
                if is_boss_wave:
                    bw = font_med.render(f"BOSS: {npc.name}", True, BOSS_COLOR)
                    screen.blit(bw, bw.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60)))
                if elapsed < COUNTDOWN_TIME:
                    ct = font_large.render(str(COUNTDOWN_TIME - int(elapsed)), True, WHITE)
                else:
                    ct = font_large.render("FIGHT!", True, YELLOW)
                screen.blit(ct, ct.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))

            elif state == "victory":
                ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                ov.fill((0, 0, 0, 100))
                screen.blit(ov, (0, 0))
                screen.blit(font_large.render("VICTORY", True, YELLOW),
                             font_large.render("VICTORY", True, YELLOW).get_rect(
                                 center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80)))
                screen.blit(font_med.render(f"Wave {wave} cleared!   +{last_shard_gain} Shards", True, WHITE),
                             font_med.render(f"Wave {wave} cleared!   +{last_shard_gain} Shards", True, WHITE).get_rect(
                                 center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40)))
                if max_combo >= COMBO_MIN_FOR_BONUS:
                    cbt = font_small.render(
                        f"Best combo: {max_combo}x  (+{combo_bonus} bonus)",
                        True, YELLOW)
                    screen.blit(cbt, cbt.get_rect(
                        center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 14)))
                nl = "BOSS" if (wave + 1) % BOSS_WAVE_INTERVAL == 0 else f"Lv.{wave + 1}"
                screen.blit(font_small.render(f"Next: Wave {wave + 1} ({nl})", True, GRAY),
                             font_small.render(f"Next: Wave {wave + 1} ({nl})", True, GRAY).get_rect(
                                 center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 12)))
                btn_forge = draw_button(screen, font_med, "Enter the Forge  [ENTER]",
                                        SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30, YELLOW, (60, 50, 20))
                btn_menu = draw_button(screen, font_small, "Return to Menu  [ESC]",
                                       SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80, GRAY, (40, 40, 50))

            elif state == "defeat":
                ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                ov.fill((0, 0, 0, 100))
                screen.blit(ov, (0, 0))
                screen.blit(font_large.render("DEFEAT", True, RED),
                             font_large.render("DEFEAT", True, RED).get_rect(
                                 center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 70)))
                fl = f"Fell on Wave {wave}" + (" (Boss)" if is_boss_wave else "")
                screen.blit(font_med.render(fl, True, GRAY),
                             font_med.render(fl, True, GRAY).get_rect(
                                 center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30)))
                btn_retry = draw_button(screen, font_med, "Try Again  [ENTER]",
                                        SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 15, WHITE, (60, 40, 40))
                btn_menu = draw_button(screen, font_small, "Return to Menu  [ESC]",
                                       SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60, GRAY, (40, 40, 50))

            elif state == "pause":
                ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                ov.fill((0, 0, 0, 128))
                screen.blit(ov, (0, 0))
                screen.blit(font_large.render("PAUSED", True, WHITE),
                             font_large.render("PAUSED", True, WHITE).get_rect(
                                 center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30)))
                screen.blit(font_med.render("ESC resume  |  Q quit", True, GRAY),
                             font_med.render("ESC resume  |  Q quit", True, GRAY).get_rect(
                                 center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30)))

        elif state == "forge":
            screen.fill((30, 25, 20))
            forge_buy_btns = [None] * len(FORGE_UPGRADES)
            forge_ability_btns = [None] * len(FORGE_ABILITIES)

            screen.blit(font_large.render("THE FORGE", True, YELLOW),
                         font_large.render("THE FORGE", True, YELLOW).get_rect(center=(SCREEN_WIDTH // 2, 30)))
            screen.blit(font_med.render(f"Shards: {shards}", True, YELLOW),
                         font_med.render(f"Shards: {shards}", True, YELLOW).get_rect(center=(SCREEN_WIDTH // 2, 62)))

            # -- Stat upgrades (compact) --
            row_x, row_y0, row_h = 30, 95, 52
            screen.blit(font_small.render("STAT UPGRADES", True, GRAY), (row_x, 80))
            for i, info in enumerate(FORGE_UPGRADES):
                stat = info["stat"]
                level = upgrades[stat]
                cost = info["base_cost"] + info["cost_inc"] * level
                cur_val = CHARACTERS[p1_choice][stat] + info["amount"] * level
                next_val = cur_val + info["amount"]
                ry = row_y0 + i * row_h
                pygame.draw.rect(screen, (45, 40, 35), (row_x, ry, 370, row_h - 6), border_radius=4)
                screen.blit(font_small.render(f"[{i+1}]", True, GRAY), (row_x + 5, ry + 4))
                screen.blit(font_small.render(f"{info['label']} Lv.{level}", True, info["color"]),
                             (row_x + 30, ry + 4))
                # bar
                bar_x, bar_y, bar_w = row_x + 30, ry + 24, 150
                max_d = {"health": 400, "attack": 60, "defense": 15, "speed": 15}
                r1 = min(cur_val / max_d[stat], 1.0)
                r2 = min(next_val / max_d[stat], 1.0)
                pygame.draw.rect(screen, DARK_GRAY, (bar_x, bar_y, bar_w, 8))
                pygame.draw.rect(screen, (80, 80, 60), (bar_x, bar_y, int(bar_w * r2), 8))
                pygame.draw.rect(screen, info["color"], (bar_x, bar_y, int(bar_w * r1), 8))
                pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_w, 8), 1)
                screen.blit(font_tiny.render(f"{cur_val}→{next_val}", True, WHITE), (bar_x + bar_w + 5, bar_y - 2))
                can = shards >= cost
                forge_buy_btns[i] = draw_button(screen, font_tiny, f"+{info['amount']} ({cost})",
                                                row_x + 330, ry + 18,
                                                YELLOW if can else (100, 100, 100),
                                                (60, 50, 20) if can else (40, 40, 40))

            # -- Abilities --
            ab_x, ab_y0 = 420, 95
            screen.blit(font_small.render("ABILITIES", True, GRAY), (ab_x, 80))
            for i, info in enumerate(FORGE_ABILITIES):
                owned = info["id"] in unlocked_abilities
                ry = ab_y0 + i * row_h
                bg = (35, 55, 35) if owned else (45, 40, 35)
                pygame.draw.rect(screen, bg, (ab_x, ry, 360, row_h - 6), border_radius=4)
                screen.blit(font_small.render(f"[{i+5}]", True, GRAY), (ab_x + 5, ry + 4))
                nc = info["color"] if owned else WHITE
                screen.blit(font_small.render(info["name"], True, nc), (ab_x + 30, ry + 4))
                screen.blit(font_tiny.render(info["desc"], True, GRAY), (ab_x + 30, ry + 24))
                if owned:
                    screen.blit(font_tiny.render("OWNED", True, GREEN), (ab_x + 300, ry + 12))
                else:
                    can = shards >= info["cost"]
                    forge_ability_btns[i] = draw_button(
                        screen, font_tiny, f'{info["cost"]}',
                        ab_x + 320, ry + 18,
                        YELLOW if can else (100, 100, 100),
                        (60, 50, 20) if can else (40, 40, 40))

            # controls reference
            screen.blit(font_tiny.render("Controls: WASD move | SPACE shoot | E block | Q heal | S slam (air) | LSHIFT dash",
                         True, GRAY), (30, 310))

            # next wave preview
            next_w = wave + 1
            is_nb = next_w % BOSS_WAVE_INTERVAL == 0
            nwc = BOSS_COLOR if is_nb else WHITE
            nwl = f"Next: Wave {next_w}" + ("  BOSS!" if is_nb else "")
            screen.blit(font_med.render(nwl, True, nwc),
                         font_med.render(nwl, True, nwc).get_rect(center=(SCREEN_WIDTH // 2, 350)))

            btn_forge_fight = draw_button(screen, font_med, "Fight Again  [ENTER]",
                                          SCREEN_WIDTH // 2 - 130, 390, GREEN, (30, 60, 30))
            btn_forge_menu = draw_button(screen, font_small, "Menu  [ESC]",
                                         SCREEN_WIDTH // 2 + 130, 390, GRAY, (40, 40, 50))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
