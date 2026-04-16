"""
Build Your Battle – PvE Arena Brawler
======================================
Run:  python main.py
"""

import sys
import random
import math
import pygame

from services.ai_handler import AIHandler
from ui.components import TextInput, ParallaxManager
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
    BLOCK_CHARGES_BASE, BLOCK_CHARGES_UPGRADE, BLOCK_COLOR, BLOCK_TINT,
    GROUND_SLAM_DAMAGE, GROUND_SLAM_RADIUS, GROUND_SLAM_SPEED,
    HEAL_PULSE_AMOUNT, HEAL_PULSE_COOLDOWN,
    BOSS_ABILITY_INTERVAL, BOSS_SPREAD_ANGLES, BOSS_SHIELD_DURATION,
    BOSS_CHARGE_SPEED,
    WAVE_HP_SCALE, WAVE_ATK_SCALE, WAVE_SPD_SCALE, WAVE_SHARD_BONUS,
    BOSS_WAVE_INTERVAL, BOSS_HP_MULT, BOSS_ATK_MULT,
    BOSS_COLOR, BOSS_PROJ_COLOR, BOSS_NAMES,
    PLATFORM_HEIGHT,
    PICKUP_SPAWN_CHANCE, PICKUP_LIFETIME, PICKUP_HP_AMOUNT,
    PICKUP_SHARD_AMOUNT, PICKUP_DAMAGE_BOOST,
    PICKUP_DAMAGE_BOOST_DURATION, PICKUP_SIZE,
    COMBO_RESET_TIME, COMBO_MIN_FOR_BONUS, COMBO_SHARD_BONUS,
    TIER_NAMES, TIER_THEMES, TIER_LAYOUTS, TIER_HAZARDS,
    LAVA_RECTS, LAVA_DPS, LAVA_COLOR, LAVA_GLOW,
    WIND_FORCE, WIND_FLIP_INTERVAL, LOW_GRAVITY_MULT,
    AI_IDEAL_RANGE_MIN, AI_IDEAL_RANGE_MAX, AI_SHOOT_CHANCE, AI_DODGE_CHANCE,
    AI_BOSS_SHOOT_CHANCE, AI_BOSS_DODGE_CHANCE,
    AI_DODGE_PROJECTILE_DIST, AI_DODGE_JUMP_CHANCE,
    AI_BLOCK_CHANCE, AI_BLOCK_DURATION, AI_LOW_HP_THRESHOLD, AI_RETREAT_RANGE,
    UI_THEMES, STORY_PAGES, GAME_INTRO, TIER_LORE, BOSS_LORE,
)


# ---------------------------------------------------------------------------
# Runtime tier state
# ---------------------------------------------------------------------------
# `PLATFORMS` is a mutable module-level list that gets replaced in place
# when the tier changes.  Fighter.update, draw_background and
# random_pickup_spawn read from it, so in-place mutation means they all
# see the current tier's layout without needing to pass it around.
PLATFORMS = list(TIER_LAYOUTS[0])
CURRENT_HAZARDS = list(TIER_HAZARDS[0])
WIND_DIR = 1  # +1 pushes right, -1 pushes left — flips on a timer


def tier_for_wave(wave):
    """Tier 1 = waves 1-5, tier 2 = 6-10, ... tier 5 = 21+."""
    return min(len(TIER_LAYOUTS), max(1, (wave - 1) // 5 + 1))


def apply_tier(tier):
    """Swap to a new tier's platforms + hazards.  Called from start_fight."""
    PLATFORMS[:] = TIER_LAYOUTS[tier - 1]
    CURRENT_HAZARDS[:] = TIER_HAZARDS[tier - 1]


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
        self.accent = char_data.get("accent", char_data["color"])
        self.eye_col = char_data.get("eye_col", BLACK)
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

        # blocking (charge-based: each charge fully negates one hit)
        self.blocking = False
        self.block_charges = BLOCK_CHARGES_BASE

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

        # block (hold E) — only works if charges remain
        if (keys[self.controls.get("block", pygame.K_F12)]
                and self.block_charges > 0):
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

        # gravity (scaled down in "low_gravity" hazard tiers)
        grav_mult = LOW_GRAVITY_MULT if "low_gravity" in CURRENT_HAZARDS else 1.0
        self.vel_y += GRAVITY * grav_mult
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
        # -- BLOCKED: fully negate the hit, consume one charge --
        if self.blocking and self.block_charges > 0:
            self.block_charges -= 1
            # Big blue burst to show the block worked
            for _ in range(14):
                vx = random.uniform(-4, 4)
                vy = random.uniform(-5, 1)
                particles.append(Particle(self.rect.centerx, self.rect.centery,
                                          vx, vy, BLOCK_COLOR, 25))
            self.flash_timer = FLASH_DURATION
            return  # zero damage, no knockback, no stun, no crystallize

        # -- UNBLOCKED: normal damage path --
        actual = max(1, damage - self.defense)
        if now < self.crystallized_until:
            actual = int(actual * CRYSTALLIZE_VULN)
        self.health -= actual
        self.last_hit_time = now

        if crystallize_ms > 0 and now >= self.crystallized_until:
            self.crystallized_until = now + crystallize_ms

        self.vel_x += KNOCKBACK_FORCE * direction
        self.vel_y += KNOCKBACK_UP
        self.on_ground = False
        if now >= self.stun_immune_until:
            self.stun_timer = STUN_DURATION
            self.stun_immune_until = now + 600
        self.flash_timer = FLASH_DURATION
        for _ in range(HIT_PARTICLE_COUNT):
            vx = random.uniform(-3, 3)
            vy = random.uniform(-4, 1)
            particles.append(Particle(self.rect.centerx, self.rect.centery,
                                      vx, vy, WHITE, 20))

    def draw(self, surface, ox=0, oy=0):
        """Cartoon character rendering.

        Players are round/friendly (Mario-style).
        NPCs are angular/menacing with boss-specific effects.
        """
        r = self.rect.move(ox, oy)
        cx = r.centerx
        now_ms = pygame.time.get_ticks()
        is_npc = not self.is_player

        # -- animation offsets --
        bob_y = lean_x = squash_w = squash_h = 0
        if self.dash_timer > 0:
            squash_w, squash_h = 6, -8
        elif not self.on_ground:
            if self.slamming:
                squash_w, squash_h = 4, -6
            elif self.vel_y < 0:
                squash_w, squash_h = -4, 6
            else:
                squash_w, squash_h = 3, -4
        elif self.walking:
            lean_x = int(math.sin(self.anim_frame * 0.3) * 3)
        else:
            bob_y = int(math.sin(self.anim_frame * 0.08) * 2)

        # -- colour overrides --
        if now_ms < self.crystallized_until:
            body_col = CRYSTALLIZE_COLOR
            accent = CRYSTALLIZE_COLOR
        elif self.blocking:
            body_col = BLOCK_TINT
            accent = BLOCK_COLOR
        elif self.flash_timer > 0:
            body_col = WHITE
            accent = WHITE
        else:
            body_col = self.color
            accent = self.accent

        head_cx = cx + lean_x
        head_cy = r.y + 18 + bob_y
        stunned = self.stun_timer > 0 or now_ms < self.crystallized_until

        if is_npc:
            # ── NPC: angular, menacing silhouette ──────────────────
            head_w, head_h = 30 + squash_w, 24
            body_w = 38 + squash_w
            body_h = 34 + squash_h
            body_top = head_cy + head_h // 2 - 2
            body_rect = pygame.Rect(head_cx - body_w // 2, body_top,
                                    body_w, body_h)
            foot_y = body_rect.bottom

            # feet (sharp, claw-like)
            step = int(math.sin(self.anim_frame * 0.35) * 3) if self.walking else 0
            for fx, sy in [(head_cx - 12, foot_y + step),
                           (head_cx + 4, foot_y - step)]:
                pygame.draw.polygon(surface, accent, [
                    (fx, sy), (fx + 10, sy), (fx + 5, sy + 10)])

            # body (sharp corners)
            pygame.draw.rect(surface, body_col, body_rect, border_radius=3)
            # V-stripe (aggressive)
            vy = body_rect.y + 6
            pygame.draw.polygon(surface, accent, [
                (body_rect.centerx, vy + 14),
                (body_rect.x + 6, vy), (body_rect.right - 6, vy)])

            # head (angular — pentagon shape)
            hx, hy = head_cx, head_cy
            hw2, hh2 = head_w // 2, head_h // 2
            head_pts = [
                (hx - hw2, hy + 2),          # bottom-left
                (hx - hw2 + 4, hy - hh2),    # top-left
                (hx, hy - hh2 - 5),           # crown point
                (hx + hw2 - 4, hy - hh2),    # top-right
                (hx + hw2, hy + 2),           # bottom-right
            ]
            pygame.draw.polygon(surface, body_col, head_pts)
            pygame.draw.polygon(surface, accent, head_pts, 2)

            # spike horns on top
            pygame.draw.polygon(surface, accent, [
                (hx - 10, hy - hh2), (hx - 14, hy - hh2 - 10),
                (hx - 6, hy - hh2)])
            pygame.draw.polygon(surface, accent, [
                (hx + 10, hy - hh2), (hx + 14, hy - hh2 - 10),
                (hx + 6, hy - hh2)])

            # angry eyes (slanted, narrow)
            pupil_shift = 3 if self.facing == 1 else -3
            for eye_off in (-8, 8):
                ex = hx + eye_off + pupil_shift // 2
                ey = hy - 1
                # angular eye shape
                slant = -2 if eye_off < 0 else 2
                pygame.draw.ellipse(surface, (200, 0, 0),
                                    (ex - 5, ey - 3 + slant, 10, 7))
                if stunned:
                    pygame.draw.line(surface, BLACK,
                                     (ex - 3, ey - 2), (ex + 3, ey + 2), 2)
                    pygame.draw.line(surface, BLACK,
                                     (ex + 3, ey - 2), (ex - 3, ey + 2), 2)
                else:
                    pygame.draw.circle(surface, YELLOW,
                                       (ex + pupil_shift, ey), 3)
                    pygame.draw.circle(surface, BLACK,
                                       (ex + pupil_shift, ey), 1)

            # angry mouth (fangs)
            pygame.draw.line(surface, BLACK,
                             (hx - 6, hy + 7), (hx + 6, hy + 7), 2)
            pygame.draw.polygon(surface, WHITE, [
                (hx - 4, hy + 7), (hx - 2, hy + 11), (hx, hy + 7)])
            pygame.draw.polygon(surface, WHITE, [
                (hx + 4, hy + 7), (hx + 2, hy + 11), (hx, hy + 7)])

            # ── Boss-specific aura effects ──
            if self.is_boss and self.boss_ability_type:
                t = now_ms * 0.003
                atype = self.boss_ability_type
                if atype == "spread" or atype == "all":
                    # Inferno/Cataclysm: flame particles around body
                    for i in range(5):
                        fx = hx + int(math.sin(t * 3 + i * 1.3) * (hw2 + 8))
                        fy = hy - hh2 - 5 - int(abs(math.cos(t * 2 + i)) * 12)
                        size = 3 + int(abs(math.sin(t + i)) * 3)
                        pygame.draw.circle(surface, (255, 160, 40),
                                           (fx, fy), size)
                        pygame.draw.circle(surface, (255, 80, 20),
                                           (fx, fy), max(1, size - 1))
                if atype == "shield":
                    # Glacier: ice shards floating around
                    for i in range(4):
                        ix = hx + int(math.cos(t * 1.5 + i * 1.6) * (hw2 + 12))
                        iy = hy + int(math.sin(t * 1.5 + i * 1.6) * (hh2 + 10))
                        pygame.draw.polygon(surface, (180, 230, 255), [
                            (ix, iy - 5), (ix + 3, iy), (ix, iy + 5), (ix - 3, iy)])
                if atype == "charge":
                    # Tempest: wind streaks
                    for i in range(3):
                        wy = body_rect.y + i * 12
                        wx = body_rect.x - 8 + int(math.sin(t * 4 + i) * 6)
                        pygame.draw.line(surface, (180, 220, 255),
                                         (wx, wy), (wx + 14, wy), 2)
                if atype == "slam":
                    # Oblivion: void orbs orbiting
                    for i in range(3):
                        ox2 = hx + int(math.cos(t * 2 + i * 2.1) * 24)
                        oy2 = hy + int(math.sin(t * 2 + i * 2.1) * 18)
                        pygame.draw.circle(surface, (120, 60, 180),
                                           (ox2, oy2), 4)
                        pygame.draw.circle(surface, (200, 160, 255),
                                           (ox2, oy2), 2)
        else:
            # ── PLAYER: round, friendly Mario-style ───────────────
            head_r = 16
            body_w = 36 + squash_w
            body_h = 32 + squash_h
            foot_w, foot_h = 14, 8
            body_top = head_cy + head_r - 6
            body_rect = pygame.Rect(head_cx - body_w // 2, body_top,
                                    body_w, body_h)
            foot_y = body_rect.bottom

            # feet (rounded)
            step = int(math.sin(self.anim_frame * 0.35) * 3) if self.walking else 0
            pygame.draw.ellipse(surface, accent,
                                (head_cx - body_w // 2 + 2, foot_y + step,
                                 foot_w, foot_h))
            pygame.draw.ellipse(surface, accent,
                                (head_cx + body_w // 2 - foot_w - 2, foot_y - step,
                                 foot_w, foot_h))

            # body (rounded)
            pygame.draw.rect(surface, body_col, body_rect, border_radius=10)
            belt_y = body_rect.y + body_rect.height // 2 - 2
            pygame.draw.rect(surface, accent,
                             (body_rect.x + 5, belt_y, body_rect.width - 10, 4),
                             border_radius=2)

            # head (circle)
            pygame.draw.circle(surface, body_col, (head_cx, head_cy), head_r)
            pygame.draw.circle(surface, accent, (head_cx, head_cy), head_r, 2)

            # friendly eyes (big, round)
            pupil_shift = 3 if self.facing == 1 else -3
            for eye_off in (-7, 7):
                ex = head_cx + eye_off + pupil_shift // 2
                ey = head_cy - 2
                pygame.draw.circle(surface, WHITE, (ex, ey), 6)
                pygame.draw.circle(surface, (220, 220, 230), (ex, ey), 6, 1)
                if stunned:
                    pygame.draw.line(surface, BLACK,
                                     (ex - 3, ey - 3), (ex + 3, ey + 3), 2)
                    pygame.draw.line(surface, BLACK,
                                     (ex + 3, ey - 3), (ex - 3, ey + 3), 2)
                else:
                    ix = ex + pupil_shift
                    ec = self.eye_col if self.flash_timer <= 0 else GRAY
                    pygame.draw.circle(surface, ec, (ix, ey), 4)
                    pygame.draw.circle(surface, BLACK, (ix, ey), 2)
                    pygame.draw.circle(surface, WHITE, (ix - 1, ey - 1), 1)

            # mouth
            if stunned:
                pygame.draw.arc(surface, BLACK,
                                (head_cx - 5, head_cy + 5, 10, 8),
                                0.3, 2.8, 2)
            else:
                pygame.draw.arc(surface, BLACK,
                                (head_cx - 4, head_cy + 4, 8, 6),
                                3.4, 6.0, 2)

        # -- shield visual when blocking (both player and NPC) --
        if self.blocking:
            pulse = int(math.sin(self.anim_frame * 0.4) * 2)
            sx = (body_rect.right + 4 if self.facing == 1
                  else body_rect.left - 16)
            shield_rect = pygame.Rect(sx, r.y - pulse,
                                      12, body_rect.bottom - r.y + pulse * 2)
            pygame.draw.rect(surface, BLOCK_COLOR, shield_rect, border_radius=4)
            pygame.draw.rect(surface, WHITE, shield_rect, 2, border_radius=4)
            if "reflect" in self.abilities:
                pygame.draw.rect(surface, CYAN, shield_rect, 3, border_radius=4)

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
    # Early-wave ramp: waves 1-3 are weaker so new players aren't overwhelmed.
    # Wave 1 = 55%, wave 2 = 70%, wave 3 = 85%, wave 4+ = 100% of base.
    if wave <= 3:
        early_mult = 0.55 + 0.15 * (wave - 1)
    else:
        early_mult = 1.0
    # Growth starts from wave 4 onward (so early waves don't compound).
    growth_wave = max(0, wave - 3)
    d["health"] = int(d["health"] * early_mult * (1 + WAVE_HP_SCALE * growth_wave))
    d["attack"] = int(d["attack"] * early_mult * (1 + WAVE_ATK_SCALE * growth_wave))
    d["speed"] = min(12, d["speed"] * (1 + WAVE_SPD_SCALE * growth_wave))
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
def draw_background(surface, ox=0, oy=0, arena=None, hazards=None,
                    skip_sky=False):
    """Paint the arena walls, platforms, ground, and hazard overlays.

    `skip_sky=True` preserves whatever the caller already drew (like
    the parallax background) instead of filling the screen with the
    arena's flat backdrop colour.
    """
    theme = arena or TIER_THEMES[0]
    hazards = hazards or []
    if not skip_sky:
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

    # lava hazards
    if "lava" in hazards:
        flicker = (pygame.time.get_ticks() // 120) % 2
        for lx, ly, lw, lh in LAVA_RECTS:
            col = LAVA_GLOW if flicker else LAVA_COLOR
            pygame.draw.rect(surface, col, (lx + ox, ly + oy, lw, lh))
            pygame.draw.line(surface, (255, 240, 180),
                             (lx + ox, ly + oy),
                             (lx + lw + ox, ly + oy), 2)

    # wind indicator (animated streaks at arena edges)
    if "wind" in hazards:
        t = pygame.time.get_ticks()
        for i in range(5):
            sy = 80 + i * 70 + ((t // 10) % 40)
            sx_offset = (t // 6) % 40
            if WIND_DIR == 1:
                pygame.draw.line(surface, (200, 220, 255),
                                 (20 + sx_offset + ox, sy + oy),
                                 (50 + sx_offset + ox, sy + oy), 2)
            else:
                pygame.draw.line(surface, (200, 220, 255),
                                 (SCREEN_WIDTH - 50 - sx_offset + ox, sy + oy),
                                 (SCREEN_WIDTH - 20 - sx_offset + ox, sy + oy), 2)


def draw_char_preview(surface, cx, cy, char_data, scale=1.0):
    """Draw a mini cartoon character preview for UI cards.

    Uses the same round-head/body proportions as the in-game player sprite.
    `scale` shrinks or grows relative to the default (1.0 = full FIGHTER_HEIGHT).
    """
    color = char_data.get("color", (150, 150, 150))
    accent = char_data.get("accent", color)
    eye_col = char_data.get("eye_col", BLACK)
    s = scale
    hr = int(14 * s)     # head radius
    bw = int(32 * s)     # body width
    bh = int(28 * s)     # body height
    fw, fh = int(12 * s), int(7 * s)  # foot

    head_cy = cy - int(18 * s)
    body_top = head_cy + hr - int(4 * s)
    body_rect = pygame.Rect(cx - bw // 2, body_top, bw, bh)
    foot_y = body_rect.bottom

    # feet
    pygame.draw.ellipse(surface, accent,
                        (cx - bw // 2 + 2, foot_y, fw, fh))
    pygame.draw.ellipse(surface, accent,
                        (cx + bw // 2 - fw - 2, foot_y, fw, fh))
    # body
    pygame.draw.rect(surface, color, body_rect, border_radius=int(8 * s))
    belt_y = body_rect.y + body_rect.height // 2 - 2
    pygame.draw.rect(surface, accent,
                     (body_rect.x + 4, belt_y, body_rect.width - 8, 3),
                     border_radius=2)
    # head
    pygame.draw.circle(surface, color, (cx, head_cy), hr)
    pygame.draw.circle(surface, accent, (cx, head_cy), hr, 2)
    # eyes
    for eoff in (int(-6 * s), int(6 * s)):
        ex = cx + eoff + 2
        ey = head_cy - int(2 * s)
        pygame.draw.circle(surface, WHITE, (ex, ey), int(5 * s))
        pygame.draw.circle(surface, eye_col, (ex + 2, ey), int(3 * s))
        pygame.draw.circle(surface, BLACK, (ex + 2, ey), int(1.5 * s))
        pygame.draw.circle(surface, WHITE, (ex + 1, ey - 1), max(1, int(s)))
    # smile
    pygame.draw.arc(surface, BLACK,
                    (cx - int(4 * s), head_cy + int(3 * s),
                     int(8 * s), int(5 * s)),
                    3.4, 6.0, 2)


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

    state = "intro"          # start with story intro on first launch
    menu_frame = 0
    story_page = 0
    has_seen_intro = False
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
    arena = TIER_THEMES[0]
    tier = 1
    tier_up_banner_until = 0  # ms timestamp for "TIER UP!" overlay
    prev_tier = 1
    demo_mode = False

    # UI theme + customize screen state
    ui_theme_idx = 0
    btn_theme_prev = btn_theme_next = btn_start = None
    char_card_rects = [None] * len(CHARACTERS)

    # -------- Character Forge (AI-driven character creator) --------
    ai = AIHandler()
    parallax = ParallaxManager(SCREEN_WIDTH, SCREEN_HEIGHT, GROUND_Y)
    forge_text_input = TextInput(
        (120, 200, 560, 52),
        pygame.font.SysFont(None, 28),
        max_chars=60,
        placeholder="Describe your champion  e.g. 'a fire-breathing golem'")
    ai_character = None        # validated dict from AIHandler.poll()
    ai_requested_at = 0        # ms timestamp when a request kicked off
    btn_forge_submit = btn_forge_use = btn_forge_back = None
    wind_timer = 0

    # Per-character upgrade tracking.  Keys = character name.
    # Each character gets their own upgrade levels.
    _empty_upgrades = {"health": 0, "attack": 0, "defense": 0, "speed": 0}
    roster_upgrades = {}   # name → upgrade dict
    unlocked_abilities = set()

    # The "active" roster: base 3 characters + any AI-forged ones
    player_roster = [dict(c) for c in CHARACTERS]

    def _get_upgrades(name):
        if name not in roster_upgrades:
            roster_upgrades[name] = dict(_empty_upgrades)
        return roster_upgrades[name]

    # Convenience alias — points to active character's upgrade dict
    upgrades = _get_upgrades(CHARACTERS[0]["name"])

    # button rects
    btn_forge = btn_retry = btn_menu = None
    forge_buy_btns = [None] * len(FORGE_UPGRADES)
    forge_ability_btns = [None] * len(FORGE_ABILITIES)
    btn_forge_fight = btn_forge_menu = None

    def apply_upgrades():
        """Return the active character's data with their specific upgrades."""
        base = dict(player_roster[p1_choice])
        char_ups = _get_upgrades(base["name"])
        for info in FORGE_UPGRADES:
            stat = info["stat"]
            base[stat] = base[stat] + info["amount"] * char_ups[stat]
        return base

    def start_fight():
        nonlocal player, npc, projectiles, particles, shake_timer, is_boss_wave
        nonlocal pickups, combo, max_combo, last_combo_hit, combo_bonus
        nonlocal arena, tier, prev_tier, tier_up_banner_until, wind_timer
        # Always use the selected roster character + their per-character upgrades.
        char_data = apply_upgrades()
        player = Fighter(150, char_data, p1_controls, facing=1, is_player=True)
        player.abilities = set(unlocked_abilities)
        if "extra_shields" in unlocked_abilities:
            player.block_charges = BLOCK_CHARGES_BASE + BLOCK_CHARGES_UPGRADE
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
        # tier selection
        new_tier = tier_for_wave(wave)
        if new_tier != prev_tier:
            tier_up_banner_until = pygame.time.get_ticks() + 3000
            prev_tier = new_tier
        tier = new_tier
        apply_tier(tier)
        arena = TIER_THEMES[tier - 1]
        wind_timer = 0
        shake_timer = 0

    def start_demo_fight():
        """Lightweight training match — weak dummy NPC, all abilities,
        no shards awarded, no defeat state.  Purely for learning."""
        nonlocal player, npc, projectiles, particles, shake_timer, is_boss_wave
        nonlocal pickups, combo, max_combo, last_combo_hit, combo_bonus
        nonlocal arena, tier, prev_tier, tier_up_banner_until, wind_timer
        # Player gets every ability so they can try them all in demo
        char_data = dict(CHARACTERS[p1_choice])
        player = Fighter(150, char_data, p1_controls, facing=1, is_player=True)
        player.abilities = {a["id"] for a in FORGE_ABILITIES}
        player.block_charges = BLOCK_CHARGES_BASE + BLOCK_CHARGES_UPGRADE
        # NPC: 40% stats, slow to shoot, no boss
        dummy_char = dict(CHARACTERS[npc_choice])
        dummy_char["health"] = int(dummy_char["health"] * 0.4)
        dummy_char["attack"] = int(dummy_char["attack"] * 0.4)
        dummy_char["speed"] = dummy_char["speed"] * 0.7
        dummy_char["name"] = "Training Dummy"
        npc = Fighter(550, dummy_char, npc_controls, facing=-1)
        npc.is_boss = False
        is_boss_wave = False
        projectiles.clear()
        particles.clear()
        pickups.clear()
        combo = 0
        max_combo = 0
        last_combo_hit = 0
        combo_bonus = 0
        # Always Tier 1 layout in demo
        tier = 1
        prev_tier = 1
        tier_up_banner_until = 0
        apply_tier(1)
        arena = TIER_THEMES[0]
        wind_timer = 0
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
                if state == "intro":
                    # Any key or click advances the story page
                    story_page += 1
                    if story_page >= len(STORY_PAGES):
                        has_seen_intro = True
                        state = "menu"

                elif state == "menu":
                    if event.key == pygame.K_RETURN:
                        state = "select"
                        p1_choice = 0
                        npc_choice = random.randint(0, len(CHARACTERS) - 1)
                    elif event.key == pygame.K_f:
                        # Open the AI Character Forge
                        state = "char_forge"
                        ai_character = None
                        forge_text_input.clear()
                        forge_text_input.focused = True
                    elif event.key == pygame.K_t:
                        # Demo / trial mode — no stakes, safe to learn
                        demo_mode = True
                        p1_choice = 0
                        npc_choice = 1
                        wave = 1
                        start_demo_fight()
                        state = "demo"

                elif state == "select":
                    if event.key == pygame.K_a:
                        p1_choice = (p1_choice - 1) % len(player_roster)
                        upgrades = _get_upgrades(player_roster[p1_choice]["name"])
                    elif event.key == pygame.K_d:
                        p1_choice = (p1_choice + 1) % len(player_roster)
                        upgrades = _get_upgrades(player_roster[p1_choice]["name"])
                    elif event.key == pygame.K_TAB:
                        ui_theme_idx = (ui_theme_idx + 1) % len(UI_THEMES)
                    elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                        idx = event.key - pygame.K_1
                        if idx < len(player_roster):
                            p1_choice = idx
                            upgrades = _get_upgrades(player_roster[p1_choice]["name"])
                    elif event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                        wave = 1
                        upgrades = _get_upgrades(player_roster[p1_choice]["name"])
                        start_fight()
                        state = "countdown"
                        state_timer = now
                    elif event.key == pygame.K_ESCAPE:
                        state = "menu"

                elif state == "fight":
                    if event.key == pygame.K_ESCAPE:
                        state = "pause"

                elif state == "demo":
                    if event.key == pygame.K_ESCAPE:
                        demo_mode = False
                        state = "menu"
                    elif event.key == pygame.K_r:
                        # reset dummy + player health
                        start_demo_fight()

                elif state == "char_forge":
                    # Forward keystrokes into the TextInput first
                    consumed = forge_text_input.handle_event(event)
                    if consumed:
                        # ENTER fires submit — TextInput invokes callback,
                        # but we handle submission imperatively here too.
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            if not ai.is_busy() and forge_text_input.text.strip():
                                ai.request_character(forge_text_input.text)
                                ai_requested_at = now
                                ai_character = None
                    elif event.key == pygame.K_ESCAPE:
                        state = "menu"

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
                    elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        p1_choice = (p1_choice - 1) % len(player_roster)
                        upgrades = _get_upgrades(player_roster[p1_choice]["name"])
                    elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        p1_choice = (p1_choice + 1) % len(player_roster)
                        upgrades = _get_upgrades(player_roster[p1_choice]["name"])
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
                                       pygame.K_7, pygame.K_8, pygame.K_9):
                        idx = event.key - pygame.K_5
                        if idx < len(FORGE_ABILITIES):
                            try_buy_ability(idx)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == "intro":
                    story_page += 1
                    if story_page >= len(STORY_PAGES):
                        has_seen_intro = True
                        state = "menu"
                elif state == "char_forge":
                    forge_text_input.handle_event(event)
                    if btn_forge_submit and btn_forge_submit.collidepoint(mouse_pos):
                        if not ai.is_busy() and forge_text_input.text.strip():
                            ai.request_character(forge_text_input.text)
                            ai_requested_at = now
                            ai_character = None
                    elif btn_forge_use and btn_forge_use.collidepoint(mouse_pos):
                        if ai_character is not None:
                            # Add AI character to roster (avoid duplicates by name)
                            existing = [c["name"] for c in player_roster]
                            if ai_character["name"] not in existing:
                                player_roster.append(dict(ai_character))
                            p1_choice = next(i for i, c in enumerate(player_roster)
                                             if c["name"] == ai_character["name"])
                            upgrades = _get_upgrades(ai_character["name"])
                            wave = 1
                            npc_choice = random.randint(0, len(CHARACTERS) - 1)
                            parallax.set_theme(ai_character.get("theme", "arcane"))
                            start_fight()
                            state = "countdown"
                            state_timer = now
                    elif btn_forge_back and btn_forge_back.collidepoint(mouse_pos):
                        state = "menu"
                elif state == "select":
                    # Theme prev/next
                    if btn_theme_prev and btn_theme_prev.collidepoint(mouse_pos):
                        ui_theme_idx = (ui_theme_idx - 1) % len(UI_THEMES)
                    elif btn_theme_next and btn_theme_next.collidepoint(mouse_pos):
                        ui_theme_idx = (ui_theme_idx + 1) % len(UI_THEMES)
                    # Character card click
                    for i, cr in enumerate(char_card_rects):
                        if cr and cr.collidepoint(mouse_pos):
                            p1_choice = i
                            upgrades = _get_upgrades(player_roster[p1_choice]["name"])
                            break
                    # Start button
                    if btn_start and btn_start.collidepoint(mouse_pos):
                        wave = 1
                        start_fight()
                        state = "countdown"
                        state_timer = now
                elif state == "victory":
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
        # Poll the AI handler every frame — cheap queue check, never blocks
        if state == "char_forge":
            result = ai.poll()
            if result is not None:
                ai_character = result
                # Rebuild parallax with the returned theme for instant preview
                parallax.set_theme(ai_character.get("theme", "arcane"))

        if state == "countdown":
            if (now - state_timer) / 1000.0 >= COUNTDOWN_TIME + 0.5:
                state = "fight"

        elif state in ("fight", "demo"):
            keys = pygame.key.get_pressed()
            player.handle_input(keys, now, projectiles)
            ai_update(npc, player, now, projectiles)
            player.update(particles, now)
            npc.update(particles, now)

            # -- Hazard: Wind (horizontal force, flips periodically) --
            if "wind" in CURRENT_HAZARDS:
                global WIND_DIR
                wind_timer += 1
                if wind_timer * (1000 // FPS) >= WIND_FLIP_INTERVAL:
                    WIND_DIR *= -1
                    wind_timer = 0
                player.vel_x += WIND_FORCE * WIND_DIR
                npc.vel_x += WIND_FORCE * WIND_DIR

            # -- Hazard: Lava (damage while standing on lava patches) --
            if "lava" in CURRENT_HAZARDS:
                for lx, ly, lw, lh in LAVA_RECTS:
                    lava = pygame.Rect(lx, ly, lw, lh)
                    for fighter in (player, npc):
                        if fighter.on_ground and fighter.rect.colliderect(lava):
                            # damage scales with dt (~per-frame)
                            dmg = LAVA_DPS / FPS
                            fighter.health = max(0, fighter.health - dmg)
                            fighter.last_hit_time = now
                            # lava sizzle particle
                            if random.random() < 0.3:
                                particles.append(Particle(
                                    fighter.rect.centerx, fighter.rect.bottom,
                                    random.uniform(-1, 1), random.uniform(-3, -1),
                                    LAVA_GLOW, 12))

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
                if demo_mode:
                    # endless training — just respawn the dummy
                    npc.health = npc.max_health
                    npc.rect.x = 550
                    npc.rect.bottom = GROUND_Y
                    npc.crystallized_until = 0
                    npc.stun_timer = 0
                else:
                    last_shard_gain = wave_shard_reward(wave)
                    if max_combo >= COMBO_MIN_FOR_BONUS:
                        combo_bonus = (max_combo - COMBO_MIN_FOR_BONUS + 1) * COMBO_SHARD_BONUS
                        last_shard_gain += combo_bonus
                    shards += last_shard_gain
                    state = "victory"
                    state_timer = now
            elif player.health <= 0:
                if demo_mode:
                    player.health = player.max_health
                    player.rect.x = 150
                    player.rect.bottom = GROUND_Y
                    player.crystallized_until = 0
                    player.stun_timer = 0
                else:
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

        if state == "intro":
            # ── Story intro — full-screen pages with procedural visuals ──
            theme = UI_THEMES[ui_theme_idx]
            page = STORY_PAGES[min(story_page, len(STORY_PAGES) - 1)]
            vis = page["visual"]

            # Background — dark with parallax preview
            parallax.draw(screen, menu_frame * 0.3)
            scrim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            scrim.fill((0, 0, 0, 180))
            screen.blit(scrim, (0, 0))

            # Visual element per page (drawn above scrim)
            cx, cy = SCREEN_WIDTH // 2, 180
            t = now * 0.002  # slow animation driver

            if vis == "crucible":
                # Pulsing diamond shape
                pulse = int(math.sin(t) * 15) + 60
                pts = [(cx, cy - pulse), (cx + pulse, cy),
                       (cx, cy + pulse), (cx - pulse, cy)]
                pygame.draw.polygon(screen, theme["accent"], pts, 3)
                inner = int(pulse * 0.5)
                pts2 = [(cx, cy - inner), (cx + inner, cy),
                        (cx, cy + inner), (cx - inner, cy)]
                pygame.draw.polygon(screen, theme["accent2"], pts2)

            elif vis == "bosses":
                # Five boss silhouettes in a row
                boss_colors = [(200, 50, 30), (60, 140, 200), (100, 180, 255),
                               (80, 40, 120), (200, 30, 30)]
                for i, bc in enumerate(boss_colors):
                    bx = cx - 160 + i * 80
                    h = 50 + int(math.sin(t + i * 0.7) * 8)
                    r = pygame.Rect(bx - 15, cy - h // 2, 30, h)
                    pygame.draw.rect(screen, bc, r)
                    # eyes
                    pygame.draw.rect(screen, (255, 255, 200),
                                     (r.x + 8, r.y + 12, 4, 5))
                    pygame.draw.rect(screen, (255, 255, 200),
                                     (r.x + 18, r.y + 12, 4, 5))

            elif vis == "forge":
                # Anvil shape with sparks
                anvil_top = pygame.Rect(cx - 50, cy - 10, 100, 20)
                anvil_body = pygame.Rect(cx - 30, cy + 10, 60, 40)
                pygame.draw.rect(screen, (120, 110, 100), anvil_top,
                                 border_radius=4)
                pygame.draw.rect(screen, (90, 80, 70), anvil_body,
                                 border_radius=3)
                # sparks
                for i in range(8):
                    sx = cx + int(math.sin(t * 3 + i * 0.8) * 40)
                    sy = cy - 20 - int(abs(math.cos(t * 2 + i)) * 30)
                    pygame.draw.circle(screen, theme["accent"], (sx, sy), 2)

            elif vis == "call_to_arms":
                # Glowing champion silhouette
                glow = int(abs(math.sin(t * 0.8)) * 60) + 40
                # outer glow
                glow_surf = pygame.Surface((100, 130), pygame.SRCALPHA)
                glow_surf.fill((theme["accent"][0], theme["accent"][1],
                                theme["accent"][2], glow))
                screen.blit(glow_surf,
                            glow_surf.get_rect(center=(cx, cy)))
                # body
                body = pygame.Rect(cx - 25, cy - 40, 50, 80)
                pygame.draw.rect(screen, theme["accent"], body)
                pygame.draw.rect(screen, WHITE, body, 2)

            # Story text panel
            text_y = 320
            for i, line in enumerate(page["text"]):
                if line:
                    col = theme["accent"] if i == 0 else theme["text"]
                    lt = font_med.render(line, True, col)
                else:
                    lt = font_small.render("", True, theme["text"])
                screen.blit(lt, lt.get_rect(
                    center=(SCREEN_WIDTH // 2, text_y + i * 36)))

            # Page indicator + prompt
            dots = ""
            for i in range(len(STORY_PAGES)):
                dots += "●  " if i == story_page else "○  "
            dt = font_small.render(dots.strip(), True, theme["text_dim"])
            screen.blit(dt, dt.get_rect(
                center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60)))

            prompt_txt = "Click or press any key to continue"
            if story_page == len(STORY_PAGES) - 1:
                prompt_txt = "Click or press any key to begin"
            if menu_frame % 60 < 45:
                pt = font_small.render(prompt_txt, True, theme["accent"])
                screen.blit(pt, pt.get_rect(
                    center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30)))

        elif state == "menu":
            theme = UI_THEMES[ui_theme_idx]
            screen.fill(theme["bg"])
            pygame.draw.rect(screen, theme["bg2"],
                             (0, SCREEN_HEIGHT // 2, SCREEN_WIDTH, SCREEN_HEIGHT // 2))

            bob = int(math.sin(menu_frame * 0.05) * 5)
            t = font_large.render("BUILD YOUR BATTLE", True, theme["accent"])
            screen.blit(t, t.get_rect(center=(SCREEN_WIDTH // 2, 130 + bob)))
            s = font_med.render("Climb the Crucible.  Forge your power.",
                                True, theme["text_dim"])
            screen.blit(s, s.get_rect(center=(SCREEN_WIDTH // 2, 180)))

            # Lore panel
            lore_panel = pygame.Rect(90, 220, SCREEN_WIDTH - 180, 140)
            pygame.draw.rect(screen, theme["panel"], lore_panel, border_radius=10)
            pygame.draw.rect(screen, theme["border"], lore_panel, 2, border_radius=10)
            for i, line in enumerate(GAME_INTRO.split("\n")):
                ll = font_small.render(line, True, theme["text"])
                screen.blit(ll, ll.get_rect(
                    center=(SCREEN_WIDTH // 2, lore_panel.y + 30 + i * 28)))

            if menu_frame % 60 < 40:
                p = font_med.render("Press ENTER to begin",
                                    True, theme["accent"])
                screen.blit(p, p.get_rect(center=(SCREEN_WIDTH // 2, 420)))
            demo_prompt = font_small.render(
                "Press T for Demo / Training Mode", True, theme["accent2"])
            screen.blit(demo_prompt, demo_prompt.get_rect(
                center=(SCREEN_WIDTH // 2, 470)))
            forge_prompt = font_small.render(
                "Press F for AI Character Forge", True, theme["accent"])
            screen.blit(forge_prompt, forge_prompt.get_rect(
                center=(SCREEN_WIDTH // 2, 500)))
            tip = font_tiny.render(
                f"Theme: {theme['name']}  (change on customize screen)",
                True, theme["text_dim"])
            screen.blit(tip, tip.get_rect(
                center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 20)))

        elif state == "select":
            # ── CUSTOMIZATION SCREEN ─────────────────────────────────────
            # Layout: [Title bar] [Theme toggle] [Character grid (3 cards)]
            #         [Preview panel with selected theme + character]
            #         [START button]
            theme = UI_THEMES[ui_theme_idx]
            char_card_rects = [None] * len(CHARACTERS)

            # Background with subtle diagonal gradient feel (two bands)
            screen.fill(theme["bg"])
            pygame.draw.rect(screen, theme["bg2"],
                             (0, SCREEN_HEIGHT // 2, SCREEN_WIDTH, SCREEN_HEIGHT // 2))

            # Title bar
            title_panel = pygame.Rect(20, 20, SCREEN_WIDTH - 40, 60)
            pygame.draw.rect(screen, theme["panel"], title_panel, border_radius=8)
            pygame.draw.rect(screen, theme["border"], title_panel, 2, border_radius=8)
            ttxt = font_large.render("CUSTOMIZE", True, theme["accent"])
            screen.blit(ttxt, ttxt.get_rect(midleft=(title_panel.x + 20,
                                                    title_panel.centery)))
            subtxt = font_small.render(theme["tagline"], True, theme["text_dim"])
            screen.blit(subtxt, subtxt.get_rect(
                midright=(title_panel.right - 20, title_panel.centery)))

            # Theme toggle row (below title)
            theme_y = 100
            tl = font_small.render("THEME", True, theme["text_dim"])
            screen.blit(tl, (40, theme_y))
            # current theme name centered with prev/next
            tn = font_med.render(theme["name"], True, theme["accent"])
            tn_rect = tn.get_rect(center=(SCREEN_WIDTH // 2, theme_y + 18))
            screen.blit(tn, tn_rect)
            btn_theme_prev = draw_button(
                screen, font_med, "<",
                tn_rect.left - 40, tn_rect.centery,
                theme["button_fg"], theme["button_bg"])
            btn_theme_next = draw_button(
                screen, font_med, ">",
                tn_rect.right + 40, tn_rect.centery,
                theme["button_fg"], theme["button_bg"])
            hint = font_tiny.render("click arrows  |  TAB", True, theme["text_dim"])
            screen.blit(hint, hint.get_rect(
                center=(SCREEN_WIDTH // 2, theme_y + 50)))

            # Character grid — shows the full roster (base 3 + any AI-forged)
            # Scrollable: if more than 3 characters, show 3 at a time with arrows
            grid_y = 180
            card_w, card_h, card_gap = 235, 250, 12
            visible_chars = player_roster  # show all for now
            num_show = min(3, len(visible_chars))
            total_w = card_w * num_show + card_gap * max(0, num_show - 1)
            grid_start_x = (SCREEN_WIDTH - total_w) // 2

            char_card_rects = [None] * len(visible_chars)
            count_label = f"CHAMPION  ({len(player_roster)} available)"
            glabel = font_small.render(count_label, True, theme["text_dim"])
            screen.blit(glabel, (grid_start_x, grid_y - 20))

            # Only show up to 3 centered around p1_choice
            scroll_start = max(0, min(p1_choice - 1,
                                      len(visible_chars) - num_show))
            for vi, i in enumerate(range(scroll_start,
                                         scroll_start + num_show)):
                if i >= len(visible_chars):
                    break
                ch = visible_chars[i]
                cx_left = grid_start_x + vi * (card_w + card_gap)
                card = pygame.Rect(cx_left, grid_y, card_w, card_h)
                char_card_rects[i] = card
                selected = (i == p1_choice)
                hovering = card.collidepoint(mouse_pos)

                # card background
                bg = theme["panel_hl"] if (selected or hovering) else theme["panel"]
                pygame.draw.rect(screen, bg, card, border_radius=10)
                # border — thicker and accent colored if selected
                bw = 3 if selected else 1
                bc = theme["accent"] if selected else theme["border"]
                pygame.draw.rect(screen, bc, card, bw, border_radius=10)

                # number badge
                num = font_tiny.render(f"[{i+1}]", True, theme["text_dim"])
                screen.blit(num, (card.x + 10, card.y + 8))

                # cartoon character preview
                draw_char_preview(screen, card.centerx, card.y + 100, ch,
                                  scale=1.1)

                # name
                nm = font_med.render(ch["name"], True, theme["text"])
                screen.blit(nm, nm.get_rect(
                    center=(card.centerx, card.y + 145)))

                # role description — split at " — " to fit card width
                role = ch.get("role", "")
                if role:
                    parts = role.split(" — ", 1)
                    rl1 = font_tiny.render(parts[0], True, theme["accent"])
                    screen.blit(rl1, rl1.get_rect(
                        center=(card.centerx, card.y + 168)))
                    if len(parts) > 1:
                        rl2 = font_tiny.render(parts[1], True, theme["text_dim"])
                        screen.blit(rl2, rl2.get_rect(
                            center=(card.centerx, card.y + 184)))

                # mini stat line (compact)
                statline = f"HP {ch['health']}  ATK {ch['attack']}  DEF {ch['defense']}  SPD {ch['speed']}"
                sl = font_tiny.render(statline, True, theme["text_dim"])
                screen.blit(sl, sl.get_rect(
                    center=(card.centerx, card.y + 202)))

                if selected:
                    sel = font_tiny.render("SELECTED", True, theme["accent"])
                    screen.blit(sel, sel.get_rect(
                        center=(card.centerx, card.y + 228)))

            # Preview / summary panel
            prev_y = 445
            prev_panel = pygame.Rect(40, prev_y, SCREEN_WIDTH - 80, 80)
            pygame.draw.rect(screen, theme["panel"], prev_panel, border_radius=8)
            pygame.draw.rect(screen, theme["border"], prev_panel, 2, border_radius=8)

            chosen = player_roster[p1_choice]
            draw_char_preview(screen, prev_panel.x + 38,
                              prev_panel.centery + 10, chosen, scale=0.7)

            ready = font_med.render(
                f"{chosen['name']}  —  {theme['name']}", True, theme["accent"])
            screen.blit(ready, (prev_panel.x + 65, prev_panel.y + 12))
            rdy2 = font_small.render(
                "Ready to enter the Crucible.", True, theme["text_dim"])
            screen.blit(rdy2, (prev_panel.x + 65, prev_panel.y + 44))

            # Start button
            btn_start = draw_button(
                screen, font_med, "START  [SPACE]",
                SCREEN_WIDTH // 2, 560,
                theme["button_fg"], theme["button_bg"])

            # bottom hint
            tip = font_tiny.render(
                "1/2/3 pick fighter  |  A/D cycle  |  TAB theme  |  ESC back",
                True, theme["text_dim"])
            screen.blit(tip, tip.get_rect(
                center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 12)))

        elif state in ("countdown", "fight", "demo",
                        "victory", "defeat", "pause"):
            # Parallax backdrop (camera tracks the player so the world
            # shifts opposite to movement — 2.5D depth effect).
            camera_x = (player.rect.centerx - SCREEN_WIDTH // 2) if player else 0
            parallax.draw(screen, camera_x)
            draw_background(screen, sx, sy, arena, CURRENT_HAZARDS,
                            skip_sky=True)
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
                # block charges indicator
                bc_col = BLOCK_COLOR if player.block_charges > 0 else (100, 100, 100)
                bc_txt = "E Block: " + "■ " * player.block_charges + "□ " * (BLOCK_CHARGES_BASE + (BLOCK_CHARGES_UPGRADE if "extra_shields" in player.abilities else 0) - player.block_charges)
                screen.blit(font_tiny.render(bc_txt.strip(), True, bc_col),
                            (20, 58))

                if "heal_pulse" in player.abilities:
                    heal_cd = max(0, HEAL_PULSE_COOLDOWN - (now - player.last_heal))
                    if heal_cd > 0:
                        ht = font_tiny.render(f"Heal: {heal_cd // 1000 + 1}s", True, GRAY)
                    else:
                        ht = font_tiny.render("Heal: READY [Q]", True, GREEN)
                    screen.blit(ht, (20, 74))

            # wave + shards
            wc = BOSS_COLOR if is_boss_wave else GRAY
            wl = f"Wave {wave}" + ("  BOSS" if is_boss_wave else "")
            screen.blit(font_small.render(wl, True, wc),
                         font_small.render(wl, True, wc).get_rect(center=(SCREEN_WIDTH // 2, 15)))
            screen.blit(font_small.render(f"Shards: {shards}", True, YELLOW),
                         font_small.render(f"Shards: {shards}", True, YELLOW).get_rect(center=(SCREEN_WIDTH // 2, 35)))

            # arena label
            # Tier label (uses the tier's HUD accent color)
            tier_label = f"Tier {tier}: {TIER_NAMES[tier - 1]}"
            screen.blit(font_tiny.render(tier_label, True, arena["hud"]),
                        (20, 78))
            # Active hazard badges
            hz_x = 20
            for hz in CURRENT_HAZARDS:
                col = {"lava": LAVA_COLOR,
                       "wind": (150, 200, 255),
                       "low_gravity": (200, 140, 255)}.get(hz, GRAY)
                label = {"lava": "LAVA",
                         "wind": "WIND",
                         "low_gravity": "LOW-G"}.get(hz, hz.upper())
                badge = font_tiny.render(label, True, col)
                screen.blit(badge, (hz_x, 96))
                hz_x += badge.get_width() + 8

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

            # Demo / training mode overlay with control tips
            if state == "demo":
                panel = pygame.Surface((SCREEN_WIDTH, 70), pygame.SRCALPHA)
                panel.fill((0, 0, 0, 150))
                screen.blit(panel, (0, 120))
                title = font_small.render(
                    "DEMO MODE — Training Dummy  (ESC menu, R reset)",
                    True, (180, 220, 255))
                screen.blit(title, title.get_rect(
                    center=(SCREEN_WIDTH // 2, 135)))
                tips = ("A/D move  |  W jump (W again for double jump)  |  "
                        "SPACE shoot  |  E block  |  Q heal  |  "
                        "S slam in air  |  LSHIFT dash")
                tt = font_tiny.render(tips, True, GRAY)
                screen.blit(tt, tt.get_rect(
                    center=(SCREEN_WIDTH // 2, 165)))

            # TIER UP! celebration banner with lore
            if now < tier_up_banner_until:
                banner_y = 160 + int(math.sin(now * 0.005) * 6)
                tier_up_surf = pygame.Surface(
                    (SCREEN_WIDTH, 180), pygame.SRCALPHA)
                tier_up_surf.fill((0, 0, 0, 170))
                screen.blit(tier_up_surf, (0, banner_y - 30))
                tu = font_large.render("TIER UP!", True, arena["hud"])
                screen.blit(tu, tu.get_rect(
                    center=(SCREEN_WIDTH // 2, banner_y)))
                tn = font_med.render(
                    f"Tier {tier}: {TIER_NAMES[tier - 1]}",
                    True, WHITE)
                screen.blit(tn, tn.get_rect(
                    center=(SCREEN_WIDTH // 2, banner_y + 40)))
                # lore blurb
                if tier <= len(TIER_LORE):
                    for i, line in enumerate(TIER_LORE[tier - 1].split("\n")):
                        ll = font_small.render(line, True, arena["hud"])
                        screen.blit(ll, ll.get_rect(
                            center=(SCREEN_WIDTH // 2, banner_y + 72 + i * 22)))
                # hazard list
                if CURRENT_HAZARDS:
                    haz_txt = "Hazards: " + ", ".join(
                        h.replace("_", " ").upper() for h in CURRENT_HAZARDS)
                    hz = font_tiny.render(haz_txt, True, arena["hud"])
                    screen.blit(hz, hz.get_rect(
                        center=(SCREEN_WIDTH // 2, banner_y + 128)))

            if state == "countdown":
                elapsed = (now - state_timer) / 1000.0
                if is_boss_wave:
                    bw = font_med.render(f"BOSS: {npc.name}", True, BOSS_COLOR)
                    screen.blit(bw, bw.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80)))
                    # boss flavour line
                    lore = BOSS_LORE.get(npc.name)
                    if lore:
                        bl = font_small.render(lore, True, WHITE)
                        screen.blit(bl, bl.get_rect(
                            center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50)))
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

        elif state == "char_forge":
            # ── AI Character Forge screen ────────────────────────────────
            theme = UI_THEMES[ui_theme_idx]
            # Parallax preview in the background (tinted by current theme)
            parallax.draw(screen, camera_x=menu_frame * 0.4)
            # Dark scrim so UI is readable over parallax
            scrim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT),
                                   pygame.SRCALPHA)
            scrim.fill((0, 0, 0, 120))
            screen.blit(scrim, (0, 0))

            # Title
            tt = font_large.render("CHARACTER FORGE", True, theme["accent"])
            screen.blit(tt, tt.get_rect(center=(SCREEN_WIDTH // 2, 60)))
            sub = font_small.render(
                "Describe a fighter — the AI will conjure their stats.",
                True, theme["text_dim"])
            screen.blit(sub, sub.get_rect(
                center=(SCREEN_WIDTH // 2, 100)))

            # Endpoint status line
            if ai.is_busy():
                status = "Contacting LM Studio..."
                stat_col = theme["accent2"]
            elif ai_character is None:
                status = f"Endpoint: {getattr(ai, 'url', 'local')}"
                stat_col = theme["text_dim"]
            else:
                status = (f"Response source: {ai_character.get('source', '?')}"
                          + (" (offline fallback)"
                             if ai_character.get("source") == "fallback"
                             else " (AI)"))
                stat_col = (theme["text_dim"]
                            if ai_character.get("source") == "fallback"
                            else theme["accent"])
            ss = font_tiny.render(status, True, stat_col)
            screen.blit(ss, ss.get_rect(center=(SCREEN_WIDTH // 2, 125)))

            # Label above input
            lab = font_small.render("DESCRIPTION", True, theme["text_dim"])
            screen.blit(lab, (120, 180))
            forge_text_input.draw(screen)

            # Submit button
            submit_label = ("FORGING..." if ai.is_busy()
                            else "FORGE CHAMPION  [ENTER]")
            btn_forge_submit = draw_button(
                screen, font_med, submit_label,
                SCREEN_WIDTH // 2, 290,
                theme["button_fg"] if not ai.is_busy() else (120, 120, 120),
                theme["button_bg"])

            # Result / loading panel
            panel = pygame.Rect(80, 330, SCREEN_WIDTH - 160, 200)
            pygame.draw.rect(screen, theme["panel"], panel, border_radius=10)
            pygame.draw.rect(screen, theme["border"], panel, 2, border_radius=10)

            if ai.is_busy():
                # Pulsing silhouette while thinking
                pulse = abs(math.sin((now - ai_requested_at) * 0.005))
                alpha = int(80 + pulse * 140)
                sil = pygame.Surface((60, 90), pygame.SRCALPHA)
                sil.fill((theme["accent"][0], theme["accent"][1],
                          theme["accent"][2], alpha))
                screen.blit(sil, sil.get_rect(
                    center=(panel.x + 80, panel.centery)))
                msg = font_med.render("Conjuring champion...",
                                      True, theme["accent"])
                screen.blit(msg, msg.get_rect(
                    midleft=(panel.x + 140, panel.y + 50)))
                dots = "." * (((now // 300) % 3) + 1)
                dt = font_small.render(
                    f"querying the ether{dots}",
                    True, theme["text_dim"])
                screen.blit(dt, dt.get_rect(
                    midleft=(panel.x + 140, panel.y + 100)))
            elif ai_character is not None:
                # Result card: procedural sprite + stats + lore
                draw_char_preview(screen, panel.x + 65,
                                  panel.y + 80, ai_character, scale=1.0)

                nm = font_med.render(ai_character["name"], True,
                                     theme["accent"])
                screen.blit(nm, (panel.x + 120, panel.y + 20))
                theme_tag = font_small.render(
                    f"Theme: {ai_character['theme'].upper()}",
                    True, theme["text_dim"])
                screen.blit(theme_tag, (panel.x + 120, panel.y + 55))
                draw_stat_bars(screen, panel.x + 120, panel.y + 85,
                               ai_character, font_tiny)
                lr = font_tiny.render('"' + ai_character["lore"] + '"',
                                      True, theme["text_dim"])
                screen.blit(lr, (panel.x + 20, panel.y + 172))
            else:
                hint = font_small.render(
                    "Type a description above, then press ENTER.",
                    True, theme["text_dim"])
                screen.blit(hint, hint.get_rect(center=panel.center))

            # Bottom buttons
            if ai_character is not None and not ai.is_busy():
                btn_forge_use = draw_button(
                    screen, font_med, "ENTER ARENA",
                    SCREEN_WIDTH // 2 - 120, 560,
                    theme["button_fg"], theme["button_bg"])
            else:
                btn_forge_use = None
            btn_forge_back = draw_button(
                screen, font_small, "Back  [ESC]",
                SCREEN_WIDTH // 2 + 120, 560,
                theme["text_dim"], theme["bg2"])

        elif state == "forge":
            theme = UI_THEMES[ui_theme_idx]
            screen.fill(theme["bg"])
            pygame.draw.rect(screen, theme["bg2"],
                             (0, SCREEN_HEIGHT // 2, SCREEN_WIDTH, SCREEN_HEIGHT // 2))
            forge_buy_btns = [None] * len(FORGE_UPGRADES)
            forge_ability_btns = [None] * len(FORGE_ABILITIES)

            cur_char = player_roster[p1_choice]
            upgrades = _get_upgrades(cur_char["name"])

            screen.blit(font_large.render("THE FORGE", True, theme["accent"]),
                         font_large.render("THE FORGE", True, theme["accent"]).get_rect(center=(SCREEN_WIDTH // 2, 22)))
            # Character name + switcher
            cname = cur_char["name"]
            cn = font_med.render(f"< {cname} >", True, theme["text"])
            screen.blit(cn, cn.get_rect(center=(SCREEN_WIDTH // 2, 50)))
            shards_txt = font_small.render(f"Shards: {shards}", True, theme["accent2"])
            screen.blit(shards_txt, shards_txt.get_rect(center=(SCREEN_WIDTH // 2, 72)))

            # -- Stat upgrades (left column, compact rows) --
            row_x, row_y0, row_h = 20, 100, 46
            screen.blit(font_small.render("STAT UPGRADES", True, GRAY), (row_x, 86))
            for i, info in enumerate(FORGE_UPGRADES):
                stat = info["stat"]
                level = upgrades[stat]
                cost = info["base_cost"] + info["cost_inc"] * level
                cur_val = cur_char[stat] + info["amount"] * level
                next_val = cur_val + info["amount"]
                ry = row_y0 + i * row_h
                pygame.draw.rect(screen, (45, 40, 35),
                                 (row_x, ry, 380, row_h - 4), border_radius=4)
                screen.blit(font_tiny.render(f"[{i+1}]", True, GRAY),
                            (row_x + 5, ry + 3))
                screen.blit(font_tiny.render(
                    f"{info['label']} Lv.{level}", True, info["color"]),
                    (row_x + 26, ry + 3))
                bar_x, bar_y, bar_w = row_x + 26, ry + 20, 140
                max_d = {"health": 400, "attack": 60, "defense": 15, "speed": 15}
                r1 = min(cur_val / max_d[stat], 1.0)
                r2 = min(next_val / max_d[stat], 1.0)
                pygame.draw.rect(screen, DARK_GRAY, (bar_x, bar_y, bar_w, 7))
                pygame.draw.rect(screen, (80, 80, 60),
                                 (bar_x, bar_y, int(bar_w * r2), 7))
                pygame.draw.rect(screen, info["color"],
                                 (bar_x, bar_y, int(bar_w * r1), 7))
                pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_w, 7), 1)
                screen.blit(font_tiny.render(
                    f"{cur_val} > {next_val}", True, WHITE),
                    (bar_x + bar_w + 6, bar_y - 2))
                can = shards >= cost
                forge_buy_btns[i] = draw_button(
                    screen, font_tiny, f"+{info['amount']} ({cost})",
                    row_x + 340, ry + 16,
                    YELLOW if can else (100, 100, 100),
                    (60, 50, 20) if can else (40, 40, 40))

            # -- Abilities (right column) --
            ab_x, ab_y0, ab_h = 420, 90, 46
            screen.blit(font_small.render("ABILITIES", True, GRAY), (ab_x, 76))
            for i, info in enumerate(FORGE_ABILITIES):
                owned = info["id"] in unlocked_abilities
                ry = ab_y0 + i * ab_h
                bg = (35, 55, 35) if owned else (45, 40, 35)
                pygame.draw.rect(screen, bg,
                                 (ab_x, ry, 360, ab_h - 4), border_radius=4)
                screen.blit(font_tiny.render(f"[{i+5}]", True, GRAY),
                            (ab_x + 5, ry + 3))
                nc = info["color"] if owned else WHITE
                screen.blit(font_tiny.render(info["name"], True, nc),
                            (ab_x + 26, ry + 3))
                screen.blit(font_tiny.render(info["desc"], True, GRAY),
                            (ab_x + 26, ry + 20))
                if owned:
                    screen.blit(font_tiny.render("OWNED", True, GREEN),
                                (ab_x + 300, ry + 10))
                else:
                    can = shards >= info["cost"]
                    forge_ability_btns[i] = draw_button(
                        screen, font_tiny, f'{info["cost"]}',
                        ab_x + 326, ry + 16,
                        YELLOW if can else (100, 100, 100),
                        (60, 50, 20) if can else (40, 40, 40))

            # Controls + wave info (below both columns)
            ctrl_y = row_y0 + max(len(FORGE_UPGRADES), len(FORGE_ABILITIES)) * ab_h + 6
            screen.blit(font_tiny.render(
                "WASD move | SPACE shoot | E block | Q heal | S slam | LSHIFT dash",
                True, GRAY), (20, ctrl_y))

            # Next wave preview
            next_w = wave + 1
            is_nb = next_w % BOSS_WAVE_INTERVAL == 0
            nwc = BOSS_COLOR if is_nb else WHITE
            nwl = f"Next: Wave {next_w}" + ("  BOSS!" if is_nb else "")
            nwt = font_med.render(nwl, True, nwc)
            screen.blit(nwt, nwt.get_rect(center=(SCREEN_WIDTH // 2, ctrl_y + 36)))

            btn_forge_fight = draw_button(
                screen, font_med, "Fight Again  [ENTER]",
                SCREEN_WIDTH // 2 - 130, ctrl_y + 76, GREEN, (30, 60, 30))
            btn_forge_menu = draw_button(
                screen, font_small, "Menu  [ESC]",
                SCREEN_WIDTH // 2 + 130, ctrl_y + 76, GRAY, (40, 40, 50))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
