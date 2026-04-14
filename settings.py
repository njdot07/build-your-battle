# ---------------------------------------------------------------------------
# settings.py  –  game-wide constants & fighter stats
# ---------------------------------------------------------------------------

# Display
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
TITLE = "Build Your Battle – 1v1 Arena Brawler"

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 50, 50)
BLUE = (50, 100, 220)
GRAY = (180, 180, 180)
DARK_GRAY = (40, 40, 40)
GREEN = (50, 200, 80)
YELLOW = (240, 220, 50)
ORANGE = (255, 150, 50)
CYAN = (100, 220, 255)
PURPLE = (160, 80, 220)

# Arena
GROUND_Y = 500
GRAVITY = 0.5
FRICTION = 0.92

# Fighter defaults
FIGHTER_WIDTH = 50
FIGHTER_HEIGHT = 80
MOVE_SPEED = 5
JUMP_FORCE = -11

# Characters  (Blaze stats from Gemma)
CHARACTERS = [
    {
        "name": "Blaze",
        "health": 240,
        "attack": 25,
        "defense": 3,
        "speed": 6,
        "color": RED,
        "proj_color": ORANGE,
    },
    {
        "name": "Frost",
        "health": 200,
        "attack": 15,
        "defense": 5,
        "speed": 5,
        "color": BLUE,
        "proj_color": CYAN,
    },
    {
        "name": "Volt",
        "health": 160,
        "attack": 20,
        "defense": 2,
        "speed": 8,
        "color": PURPLE,
        "proj_color": YELLOW,
    },
]

# Projectile
PROJECTILE_SPEED = 7
PROJECTILE_LIFETIME = 45
PROJECTILE_WIDTH = 12
PROJECTILE_HEIGHT = 6
ATTACK_COOLDOWN = 400         # milliseconds
KNOCKBACK_FORCE = 10
KNOCKBACK_UP = -4

# Dash
DASH_SPEED = 15
DASH_DURATION = 8             # frames
DASH_COOLDOWN = 800           # milliseconds

# Hit feedback
STUN_DURATION = 12            # frames – can't act
FLASH_DURATION = 8            # frames – white flash

# Screen shake
SHAKE_INTENSITY = 6
SHAKE_DURATION = 8            # frames

# Particles
PARTICLE_GRAVITY = 0.3
HIT_PARTICLE_COUNT = 8
LAND_PARTICLE_COUNT = 4

# Rounds
COUNTDOWN_TIME = 3            # seconds

# Health regen
REGEN_DELAY = 3000            # ms without being hit before regen starts
REGEN_RATE = 0.05             # HP per frame (~3 HP/sec at 60 FPS)

# Shards
SHARD_REWARD = 50             # shards earned per NPC defeat

# Forge upgrades  (amount per level, base cost, cost increase per level)
FORGE_UPGRADES = [
    {"stat": "health",  "label": "HP",  "amount": 20, "base_cost": 30, "cost_inc": 15, "color": GREEN},
    {"stat": "attack",  "label": "ATK", "amount": 5,  "base_cost": 40, "cost_inc": 20, "color": RED},
    {"stat": "defense", "label": "DEF", "amount": 1,  "base_cost": 35, "cost_inc": 15, "color": (100, 150, 255)},
    {"stat": "speed",   "label": "SPD", "amount": 1,  "base_cost": 45, "cost_inc": 20, "color": YELLOW},
]

# Sour-Zest Shockwave  (player hybrid ability)
NEON_GREEN = (57, 255, 20)
SOURZEST_DAMAGE = 45
SOURZEST_SPEED = int(PROJECTILE_SPEED * 1.5)   # 50% faster
SOURZEST_WIDTH = 30
SOURZEST_HEIGHT = 4
SOURZEST_STUN_MS = 1500       # 1.5s crystallize on hit
CRYSTALLIZE_COLOR = (150, 255, 230)   # bright yellow-cyan tint
CRYSTALLIZE_VULN = 1.2        # damage multiplier while crystallized

# Wave progression
WAVE_HP_SCALE = 0.12          # +12% NPC health per wave
WAVE_ATK_SCALE = 0.08         # +8% NPC attack per wave
WAVE_SPD_SCALE = 0.04         # +4% NPC speed per wave
WAVE_SHARD_BONUS = 10         # extra shards per wave
BOSS_WAVE_INTERVAL = 5        # boss every N waves
BOSS_HP_MULT = 1.8            # boss gets 1.8x health on top of wave scaling
BOSS_ATK_MULT = 1.3           # boss gets 1.3x attack
BOSS_COLOR = (200, 30, 30)    # dark red boss tint
BOSS_PROJ_COLOR = (255, 80, 80)
BOSS_NAMES = ["Inferno", "Glacier", "Tempest", "Oblivion", "Cataclysm"]

# Shield / Block
BLOCK_DAMAGE_MULT = 0.15      # take 15% damage while blocking (strong)
BLOCK_COLOR = (100, 200, 255)
BLOCK_TINT = (140, 210, 255)  # tint applied to fighter body while blocking

# Forge abilities (one-time purchases)
FORGE_ABILITIES = [
    {"id": "double_jump", "name": "Double Jump", "cost": 75,
     "desc": "Jump again mid-air [W]", "color": CYAN},
    {"id": "reflect", "name": "Reflect Shield", "cost": 120,
     "desc": "Block reflects projectiles [E]", "color": (100, 150, 255)},
    {"id": "ground_slam", "name": "Ground Slam", "cost": 100,
     "desc": "Slam down while airborne [S]", "color": ORANGE},
    {"id": "heal_pulse", "name": "Heal Pulse", "cost": 90,
     "desc": "Heal 30 HP, 8s cooldown [Q]", "color": GREEN},
]

# Ability stats
GROUND_SLAM_DAMAGE = 35
GROUND_SLAM_RADIUS = 120      # px from landing point
GROUND_SLAM_SPEED = 18        # downward velocity
HEAL_PULSE_AMOUNT = 30
HEAL_PULSE_COOLDOWN = 8000    # ms

# Boss special abilities
BOSS_ABILITY_INTERVAL = 4000  # ms between specials
BOSS_SPREAD_ANGLES = [-12, 0, 12]  # Y offsets for spread shot
BOSS_SHIELD_DURATION = 2000   # ms
BOSS_CHARGE_SPEED = 18

# Pickups (spawn randomly during fights)
PICKUP_SPAWN_CHANCE = 0.0017  # per-frame chance (~1 every 10 sec at 60 FPS)
PICKUP_LIFETIME = 8000        # ms before pickup despawns
PICKUP_HP_AMOUNT = 30
PICKUP_SHARD_AMOUNT = 15
PICKUP_DAMAGE_BOOST = 1.5     # multiplier
PICKUP_DAMAGE_BOOST_DURATION = 5000  # ms
PICKUP_SIZE = 22

# Combo system
COMBO_RESET_TIME = 2500       # ms without landing a hit resets combo
COMBO_MIN_FOR_BONUS = 3       # need this many hits before bonus kicks in
COMBO_SHARD_BONUS = 2         # bonus shards per combo level above threshold

# Arena themes (cycle by wave)
ARENAS = [
    {"name": "Skyforge", "bg": (25, 25, 50), "bg2": (35, 30, 55),
     "wall": (60, 60, 70), "ground": (180, 180, 180),
     "platform": (80, 80, 100)},
    {"name": "Crystal Cavern", "bg": (30, 15, 45), "bg2": (45, 22, 58),
     "wall": (80, 55, 95), "ground": (150, 120, 170),
     "platform": (160, 110, 200)},
    {"name": "Emberforge", "bg": (40, 20, 15), "bg2": (55, 25, 20),
     "wall": (90, 55, 45), "ground": (170, 120, 95),
     "platform": (190, 90, 65)},
]

# Platforms  (x, y, width)
# These are solid ledges fighters can land on from above.
PLATFORMS = [
    (200, 390, 130),   # left mid-height
    (470, 390, 130),   # right mid-height
    (310, 290, 180),   # center high
]
PLATFORM_HEIGHT = 10
PLATFORM_COLOR = (80, 80, 100)

# AI
AI_IDEAL_RANGE_MIN = 180      # px – back away if closer
AI_IDEAL_RANGE_MAX = 280      # px – approach if farther
AI_SHOOT_CHANCE = 0.65        # probability per eligible frame
AI_DODGE_CHANCE = 0.02        # chance to jump per frame when idle
AI_BOSS_SHOOT_CHANCE = 0.80   # bosses shoot more aggressively
AI_BOSS_DODGE_CHANCE = 0.04   # bosses dodge more

# AI reactive behaviours
AI_DODGE_PROJECTILE_DIST = 200  # px — react to projectiles within this range
AI_DODGE_JUMP_CHANCE = 0.6      # chance to jump when a projectile is incoming
AI_BLOCK_CHANCE = 0.3           # chance to block after being hit recently
AI_BLOCK_DURATION = 500         # ms — how long the NPC holds a block
AI_LOW_HP_THRESHOLD = 0.35      # retreat more below 35% health
AI_RETREAT_RANGE = 320          # px — preferred distance when low HP
