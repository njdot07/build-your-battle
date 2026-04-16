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
FRICTION = 0.88     # tighter control — was 0.92

# Fighter defaults
FIGHTER_WIDTH = 50
FIGHTER_HEIGHT = 80
MOVE_SPEED = 5
JUMP_FORCE = -11

# Characters  (Blaze stats from Gemma)
# Each character has a distinct silhouette, role, and colour identity.
#   accent  = secondary colour drawn on the sprite (flame tips, ice shards, etc)
#   eye_col = custom eye colour to reinforce personality
#   role    = short descriptor for the select screen
CHARACTERS = [
    {
        "name": "Blaze",
        "health": 260,
        "attack": 28,
        "defense": 3,
        "speed": 5,
        "color": (200, 55, 30),        # deep ember red
        "accent": (255, 180, 50),       # flame tips
        "eye_col": (255, 220, 80),
        "proj_color": ORANGE,
        "role": "Juggernaut — slow but devastating hits",
    },
    {
        "name": "Frost",
        "health": 220,
        "attack": 16,
        "defense": 7,
        "speed": 5,
        "color": (90, 160, 220),        # glacier blue
        "accent": (200, 240, 255),      # ice sheen
        "eye_col": (220, 245, 255),
        "proj_color": CYAN,
        "role": "Guardian — high defense, outlasts opponents",
    },
    {
        "name": "Volt",
        "health": 160,
        "attack": 22,
        "defense": 2,
        "speed": 9,
        "color": (130, 80, 220),        # electric purple
        "accent": (255, 240, 100),      # spark yellow
        "eye_col": (255, 255, 150),
        "proj_color": YELLOW,
        "role": "Assassin — glass cannon, fastest in the arena",
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

# Shield / Block (charge-based — each block fully negates one hit)
BLOCK_CHARGES_BASE = 3        # charges per round
BLOCK_CHARGES_UPGRADE = 2     # extra charges from forge ability
BLOCK_COLOR = (100, 200, 255)
BLOCK_TINT = (140, 210, 255)

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
    {"id": "extra_shields", "name": "Extra Shields", "cost": 60,
     "desc": f"+{2} block charges per fight [E]", "color": CYAN},
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

# ---------------------------------------------------------------------------
# TIER SYSTEM — the game "levels up" after every boss wave.
# Each tier has its own arena theme, platform layout, and hazards.
# ---------------------------------------------------------------------------

TIER_NAMES = [
    "Skyforge",          # Tier 1
    "The Foundry",       # Tier 2
    "Storm Realm",       # Tier 3
    "Void Arena",        # Tier 4
    "Infinity Crucible", # Tier 5
]

# Each tier's arena theme
TIER_THEMES = [
    {"bg": (25, 25, 50),  "bg2": (35, 30, 55),
     "wall": (60, 60, 70),  "ground": (180, 180, 180),
     "platform": (80, 80, 100),  "hud": (200, 200, 220)},
    {"bg": (40, 20, 15),  "bg2": (55, 25, 20),
     "wall": (90, 55, 45),  "ground": (170, 120, 95),
     "platform": (190, 90, 65),  "hud": (255, 170, 90)},
    {"bg": (15, 30, 55),  "bg2": (25, 45, 75),
     "wall": (50, 80, 120), "ground": (140, 180, 220),
     "platform": (100, 160, 220), "hud": (120, 200, 255)},
    {"bg": (15, 10, 30),  "bg2": (25, 15, 45),
     "wall": (60, 40, 90),  "ground": (90, 70, 130),
     "platform": (130, 90, 180), "hud": (200, 140, 255)},
    {"bg": (45, 15, 30),  "bg2": (70, 25, 50),
     "wall": (120, 60, 90), "ground": (180, 140, 100),
     "platform": (220, 120, 90), "hud": (255, 200, 120)},
]

# Platforms per tier  (list of (x, y, width) tuples)
TIER_LAYOUTS = [
    # Tier 1 — standard three-platform layout
    [(200, 390, 130), (470, 390, 130), (310, 290, 180)],
    # Tier 2 — narrower platforms with side gaps (edges become lava)
    [(110, 400, 100), (590, 400, 100),
     (260, 320, 90), (450, 320, 90),
     (340, 230, 120)],
    # Tier 3 — vertical pyramid, more air play
    [(80, 430, 100), (620, 430, 100),
     (200, 340, 100), (500, 340, 100),
     (350, 230, 100)],
    # Tier 4 — small floating platforms, tricky landings
    [(140, 410, 70), (590, 410, 70),
     (260, 340, 60), (480, 340, 60),
     (370, 260, 60)],
    # Tier 5 — chaotic mix of all layouts
    [(90, 420, 80), (630, 420, 80),
     (240, 350, 70), (490, 350, 70),
     (360, 260, 80), (180, 200, 60), (560, 200, 60)],
]

# Hazards active per tier (strings: "lava", "wind", "low_gravity")
TIER_HAZARDS = [
    [],
    ["lava"],
    ["wind"],
    ["low_gravity"],
    ["lava", "wind", "low_gravity"],
]

PLATFORM_HEIGHT = 10

# Hazard constants
LAVA_RECTS = [  # ground-edge lava pits active from Tier 2+
    (0, 498, 80, 12),
    (720, 498, 80, 12),
]
LAVA_DPS = 12              # damage per second while standing on lava
LAVA_COLOR = (255, 80, 40)
LAVA_GLOW = (255, 180, 60)

WIND_FORCE = 0.25          # horizontal force per frame
WIND_FLIP_INTERVAL = 3500  # ms between direction flips

LOW_GRAVITY_MULT = 0.55    # gravity is multiplied by this in tier 4+

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

# ---------------------------------------------------------------------------
# UI THEMES — global colour palettes for menus, HUD, forge.
# Arena colours are tier-specific (see TIER_THEMES); these control the
# frame/UI around the gameplay and give the app a consistent aesthetic.
# ---------------------------------------------------------------------------
UI_THEMES = [
    {
        "id": "cyberpunk",
        "name": "CYBERPUNK",
        "tagline": "Neon-wired duelists in a chrome arena",
        "bg": (12, 14, 30),
        "bg2": (22, 24, 48),
        "panel": (28, 32, 58),
        "panel_hl": (50, 60, 100),
        "accent": (0, 240, 220),     # cyan
        "accent2": (255, 60, 170),   # magenta
        "text": (230, 240, 255),
        "text_dim": (150, 170, 200),
        "border": (0, 200, 180),
        "button_bg": (40, 80, 100),
        "button_fg": (0, 240, 220),
    },
    {
        "id": "dark_fantasy",
        "name": "DARK FANTASY",
        "tagline": "Ancient champions clash in a dread crucible",
        "bg": (22, 16, 12),
        "bg2": (38, 28, 20),
        "panel": (48, 36, 26),
        "panel_hl": (80, 55, 35),
        "accent": (230, 180, 90),    # gold
        "accent2": (180, 50, 50),    # blood red
        "text": (245, 225, 195),
        "text_dim": (170, 145, 110),
        "border": (160, 110, 55),
        "button_bg": (70, 45, 25),
        "button_fg": (230, 180, 90),
    },
]

# ---------------------------------------------------------------------------
# STORYLINE / LORE
# The game frames progression as climbing the Crucible — an arena that
# shifts realms after each champion is defeated.  Each tier has a
# short flavour blurb shown on the TIER UP banner and victory screen.
# ---------------------------------------------------------------------------
# Story intro pages — each entry is a dict with:
#   "text"    list of lines (rendered centered)
#   "visual"  keyword that tells the renderer what to draw
#             ("crucible", "bosses", "forge", "call_to_arms")
STORY_PAGES = [
    {
        "text": [
            "In a world between worlds, there exists a place",
            "where warriors are forged and legends are tested.",
            "",
            "It is called the CRUCIBLE.",
        ],
        "visual": "crucible",
    },
    {
        "text": [
            "The Crucible is a shifting arena — five realms",
            "stacked atop one another, each more dangerous than the last.",
            "",
            "Only by defeating each realm's guardian can",
            "a champion ascend to the next.",
        ],
        "visual": "bosses",
    },
    {
        "text": [
            "Between battles, the FORGE awaits.",
            "Spend the shards you earn to upgrade your stats,",
            "unlock new abilities, and forge your perfect build.",
            "",
            "But the guardians grow stronger too...",
        ],
        "visual": "forge",
    },
    {
        "text": [
            "Five bosses guard the path to the Infinity Vault.",
            "Inferno.  Glacier.  Tempest.  Oblivion.  Cataclysm.",
            "",
            "Are you ready to enter the Crucible?",
        ],
        "visual": "call_to_arms",
    },
]

GAME_INTRO = (
    "You enter the CRUCIBLE — a shifting arena where only champions climb.\n"
    "Defeat the guardians of each realm.  Forge your power between battles.\n"
    "Five bosses stand between you and the Infinity Vault."
)

TIER_LORE = [
    # Tier 1
    "The Skyforge  —  a clockwork sanctum where new champions are tested.\n"
    "The air hums with stored lightning.  Prove your worth.",
    # Tier 2
    "The Foundry  —  molten veins bleed beneath the arena floor.\n"
    "One false step and the furnace claims you.",
    # Tier 3
    "The Storm Realm  —  winds carry the whispers of fallen warriors.\n"
    "Fight the gale as much as the guardian.",
    # Tier 4
    "The Void Arena  —  a realm between realms, gravity grown soft.\n"
    "Here your leaps carry you further than you expect.",
    # Tier 5
    "The Infinity Crucible  —  end of the climb, where every realm collides.\n"
    "Only the Undying stand this far.  Become one.",
]

# Lore intro per boss — shown briefly at boss countdown
BOSS_LORE = {
    "Inferno":   "Inferno — the forge's first warden, burns with ancient fuel.",
    "Glacier":   "Glacier — storm-scholar, reads your moves in the wind.",
    "Tempest":   "Tempest — the gale-dancer, its blade is the wind itself.",
    "Oblivion":  "Oblivion — void-king, gravity is merely its suggestion.",
    "Cataclysm": "Cataclysm — the End.  All hazards bend to its will.",
}
