## -*- coding: utf-8 -*-
import os
import random
import sys
import math
import pygame
import json

# --- CONSTANTS ---
WIDTH, HEIGHT = 800, 600
TILE_SIZE = 50
PLAYER_SIZE = 40
PLAYER_SPEED = 5
COLS = 4
BORDER_THICKNESS = 6
CRAFTING_TIME_MS = 3000
ICON_SIZE = 30
CHOPPING_DURATION = 3000
RESPAWN_TIME = 120000  # 2 mins
MINING_DURATION = 2000  # ms

# Player constants
PLAYER_SIZE_INDOOR = 80

# Inventory GUI constants
INVENTORY_SLOT_SIZE = 40
INVENTORY_GAP = 5
INVENTORY_WIDTH = 4 * INVENTORY_SLOT_SIZE + 5 * INVENTORY_GAP
INVENTORY_HEIGHT = 4 * INVENTORY_SLOT_SIZE + 5 * INVENTORY_GAP
INVENTORY_X = (WIDTH - INVENTORY_WIDTH) // 2
INVENTORY_Y = (HEIGHT - INVENTORY_HEIGHT) // 2

# Crafting GUI constants
CRAFTING_PANEL_WIDTH = 420
CRAFTING_PANEL_HEIGHT = 220
CRAFTING_X = (WIDTH - CRAFTING_PANEL_WIDTH) // 2
CRAFTING_Y = (WIDTH - CRAFTING_PANEL_HEIGHT) // 2

# Equipment GUI constants
EQUIPMENT_SLOT_SIZE = 40
EQUIPMENT_GAP = 25
EQUIPMENT_ROWS = 4
EQUIPMENT_COLS = 2
EQUIPMENT_PANEL_WIDTH = 2 * EQUIPMENT_SLOT_SIZE + 3 * EQUIPMENT_GAP + 20
EQUIPMENT_PANEL_HEIGHT = EQUIPMENT_ROWS * EQUIPMENT_SLOT_SIZE + (EQUIPMENT_ROWS + 1) * EQUIPMENT_GAP + 50
EQUIPMENT_X = (WIDTH - EQUIPMENT_PANEL_WIDTH) // 2
EQUIPMENT_Y = (HEIGHT - EQUIPMENT_PANEL_HEIGHT) // 2

# Dungeon constants
DUNGEON_SIZE = 30
DUNGEON_SPAWN_X = 5 * TILE_SIZE
DUNGEON_SPAWN_Y = 5 * TILE_SIZE

# --- ITEM CLASS ---
class Item:
    def __init__(self, name, image, count=1, category=None):
        self.name = name
        self.image = image
        self.count = count
        self.category = category

# --- GAME STATE GLOBALS ---
player_pos = pygame.Rect(WIDTH // 2, HEIGHT // 2, PLAYER_SIZE, PLAYER_SIZE)
map_offset_x = 0
map_offset_y = 0
current_level = "world"  # "world", "house", or "dungeon"
current_house_index = None

# Player animation state
last_direction = "down"
current_direction = "idle"
player_frame_index = 0
player_frame_timer = 0
player_frame_delay = 120

# Player action state
is_chopping = False
chopping_timer = 0
chopping_target_tree = None
is_swinging = False
swing_delay = 150
idle_chop_delay = 500

# Stone specific state
is_mining = False
mining_timer = 0
mining_target_stone = None

# UI state
show_inventory = False
show_crafting = False
show_equipment = False
is_crafting = False
crafting_timer = 0
item_to_craft = None
crafting_tab = "smithing"

# NPC and Quest state
show_npc_dialog = False
npc_quest_active = False
npc_quest_completed = False
potions_needed = 3
potions_delivered = 0
npc_idle_timer = 0
npc_idle_offset_y = 0
npc_idle_direction = 1

# Miner NPC state
show_miner_dialog = False
miner_quest_active = False
miner_quest_completed = False
ore_needed = 10
miner_idle_timer = 0
miner_idle_offset_y = 0
miner_idle_direction = 1

# Game objects
inventory = [[None for _ in range(4)] for _ in range(4)]
equipment_slots = {"weapon": None}
tree_rects = []
house_list = []
stone_rects = []
chopped_trees = {}
chopped_stones = {}
picked_flowers = {}
indoor_colliders = []
flower_tiles = []
leaf_tiles = []
npc_rect = None
miner_npc_rect = None
gold_coins = []

# Dungeon objects
dungeon_portal = None
dungeon_walls = []
dungeon_enemies = []
dungeon_exit = None

# Crafting button rects
axe_button_rect = None
pickaxe_button_rect = None
potion_button_rect = None
smithing_tab_rect = None
alchemy_tab_rect = None

# --- HELPERS FOR COORDINATES ---
def get_player_world_rect():
    """Return the player's rectangle in world coordinates."""
    return player_pos.move(map_offset_x, map_offset_y)

def world_to_screen_rect(world_rect):
    """Convert a world rect to screen coordinates."""
    return pygame.Rect(world_rect.x - map_offset_x, world_rect.y - map_offset_y, world_rect.width, world_rect.height)

# --- INIT ---
def init():
    """Initializes Pygame and sets up the screen."""
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Not Pokemon")
    return screen, pygame.time.Clock()

# --- LOAD ASSETS ---
def load_player_frames():
    """Loads and scales the player character frames."""
    try:
        sheet = pygame.image.load("Player.PNG").convert_alpha()
    except pygame.error:
        # Create fallback player frames
        sheet = pygame.Surface((128, 128))
        sheet.fill((0, 100, 200))
    
    frames = {}
    try:
        right_frames = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col * 32, 32, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(COLS)]
        frames["right"] = right_frames
        frames["left"] = [pygame.transform.flip(frame, True, False) for frame in right_frames]
        frames["up"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col * 32, 64, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(COLS)]
        frames["down"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col * 32, 96, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(COLS)]
        frames["idle"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(0, 0, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE))]
    except:
        # Fallback frames
        fallback_frame = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE))
        fallback_frame.fill((0, 100, 200))
        frames = {
            "right": [fallback_frame],
            "left": [fallback_frame],
            "up": [fallback_frame],
            "down": [fallback_frame],
            "idle": [fallback_frame]
        }
    return frames

def load_chopping_frames():
    """Loads and scales the chopping animation frames."""
    try:
        sheet = pygame.image.load("Player.PNG").convert_alpha()
        chopping_frames = {}
        chopping_frames["right"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col * 32, 224, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(4)]
        chopping_frames["left"] = [pygame.transform.flip(frame, True, False) for frame in chopping_frames["right"]]
        chopping_frames["up"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col * 32, 255, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(4)]
        chopping_frames["down"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col * 32, 190, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(4)]
    except:
        # Fallback chopping frames
        fallback_frame = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE))
        fallback_frame.fill((200, 100, 0))
        chopping_frames = {
            "right": [fallback_frame],
            "left": [fallback_frame],
            "up": [fallback_frame],
            "down": [fallback_frame]
        }
    return chopping_frames

def load_assets():
    """Loads all game assets and defines Item objects."""
    # Create fallback surfaces for missing assets
    def create_fallback_surface(size, color):
        surf = pygame.Surface(size)
        surf.fill(color)
        return surf

    # Load basic tiles
    try:
        tile_folder = "Tiles"
        grass_image = pygame.transform.scale(pygame.image.load(os.path.join(tile_folder, "grass_middle.png")).convert_alpha(), (TILE_SIZE, TILE_SIZE))
    except:
        grass_image = create_fallback_surface((TILE_SIZE, TILE_SIZE), (34, 139, 34))

    try:
        tree_image = pygame.transform.scale(pygame.image.load(os.path.join(tile_folder, "tree.png")).convert_alpha(), (TILE_SIZE + 5, TILE_SIZE + 5))
    except:
        tree_image = create_fallback_surface((TILE_SIZE + 5, TILE_SIZE + 5), (101, 67, 33))

    try:
        house_image = pygame.transform.scale(pygame.image.load(os.path.join(tile_folder, "house.png")).convert_alpha(), (TILE_SIZE * 2, TILE_SIZE * 2))
    except:
        house_image = create_fallback_surface((TILE_SIZE * 2, TILE_SIZE * 2), (139, 69, 19))

    try:
        house1_image = pygame.transform.scale(pygame.image.load(os.path.join(tile_folder, "house1.png")).convert_alpha(), (TILE_SIZE * 2, TILE_SIZE * 2))
    except:
        house1_image = create_fallback_surface((TILE_SIZE * 2, TILE_SIZE * 2), (160, 82, 45))

    # Load OutdoorStuff sheet or create fallbacks
    try:
        sheet = pygame.image.load("OutdoorStuff.PNG").convert_alpha()
        flower_positions = [(0, 144), (16, 144)]
        flower_images = [pygame.transform.scale(sheet.subsurface(pygame.Rect(x, y, 16, 16)), (30, 30)) for (x, y) in flower_positions]
        leaf_image = pygame.transform.scale(sheet.subsurface(pygame.Rect(0, 0, 16, 16)), (25, 25))
        log_image_rect = pygame.Rect(4, 110, 24, 24)
        log_image = pygame.transform.scale(sheet.subsurface(log_image_rect), (TILE_SIZE, TILE_SIZE))
    except:
        flower_images = [create_fallback_surface((30, 30), (255, 192, 203)), create_fallback_surface((30, 30), (255, 20, 147))]
        leaf_image = create_fallback_surface((25, 25), (34, 139, 34))
        log_image = create_fallback_surface((TILE_SIZE, TILE_SIZE), (139, 69, 19))

    # Load individual item images
    try:
        potion_image = pygame.transform.scale(pygame.image.load("PotionR.png").convert_alpha(), (TILE_SIZE, TILE_SIZE))
    except:
        potion_image = create_fallback_surface((TILE_SIZE, TILE_SIZE), (150, 0, 150))

    try:
        coin_image = pygame.transform.scale(pygame.image.load("Coin.png").convert_alpha(), (TILE_SIZE, TILE_SIZE))
    except:
        coin_image = create_fallback_surface((TILE_SIZE, TILE_SIZE), (255, 215, 0))

    try:
        axe_image = pygame.transform.scale(pygame.image.load("axe.png").convert_alpha(), (TILE_SIZE, TILE_SIZE))
    except:
        axe_image = create_fallback_surface((TILE_SIZE, TILE_SIZE), (139, 69, 19))

    try:
        pickaxe_image = pygame.transform.scale(pygame.image.load("pickaxe.png").convert_alpha(), (TILE_SIZE, TILE_SIZE))
    except:
        pickaxe_image = create_fallback_surface((TILE_SIZE, TILE_SIZE), (105, 105, 105))

    try:
        stone_image = pygame.transform.scale(pygame.image.load("stone.png").convert_alpha(), (TILE_SIZE // 2, TILE_SIZE // 2))
    except:
        stone_image = create_fallback_surface((TILE_SIZE // 2, TILE_SIZE // 2), (150, 150, 150))

    try:
        ore_image = pygame.transform.scale(pygame.image.load("ore.png").convert_alpha(), (TILE_SIZE // 2, TILE_SIZE // 2))
    except:
        ore_image = create_fallback_surface((TILE_SIZE // 2, TILE_SIZE // 2), (139, 69, 19))

    # Load UI icons
    try:
        backpack_icon = pygame.transform.scale(pygame.image.load("bag.png").convert_alpha(), (ICON_SIZE, ICON_SIZE))
    except:
        backpack_icon = create_fallback_surface((ICON_SIZE, ICON_SIZE), (101, 67, 33))

    try:
        crafting_icon = pygame.transform.scale(pygame.image.load("craft.png").convert_alpha(), (ICON_SIZE, ICON_SIZE))
    except:
        crafting_icon = create_fallback_surface((ICON_SIZE, ICON_SIZE), (160, 82, 45))

    try:
        equipment_icon = pygame.transform.scale(pygame.image.load("equipped.png").convert_alpha(), (ICON_SIZE, ICON_SIZE))
    except:
        equipment_icon = create_fallback_surface((ICON_SIZE, ICON_SIZE), (105, 105, 105))

    # Load NPC images
    try:
        soldier_sheet = pygame.image.load("soldier.png").convert_alpha()
        npc_image = pygame.transform.scale(soldier_sheet.subsurface(pygame.Rect(0, 0, 100, 100)), (PLAYER_SIZE * 4, PLAYER_SIZE * 4))
    except:
        npc_image = create_fallback_surface((PLAYER_SIZE * 4, PLAYER_SIZE * 4), (255, 255, 0))

    try:
        miner_sheet = pygame.image.load("npc1.png").convert_alpha()
        frame_width = miner_sheet.get_width() // 8
        frame_height = miner_sheet.get_height()
        frame_rect = pygame.Rect(0, 0, frame_width, frame_height)
        miner_image = pygame.transform.scale(miner_sheet.subsurface(frame_rect), (PLAYER_SIZE, PLAYER_SIZE))
    except:
        miner_image = create_fallback_surface((PLAYER_SIZE, PLAYER_SIZE), (160, 82, 45))

    # Portal and dungeon assets
    try:
        portal_image = pygame.image.load("cave.png").convert_alpha()
        original_width, original_height = portal_image.get_size()
        scale_factor = 0.1
        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)
        portal_image = pygame.transform.smoothscale(portal_image, (new_width, new_height))
    except:
        portal_image = create_fallback_surface((50, 50), (64, 0, 128))


    # Load images instead of creating fallback surfaces
    dungeon_wall_image = pygame.image.load("wall.png").convert_alpha()
    dungeon_floor_image = pygame.image.load("caveFloor.png").convert_alpha()

    # Scale them to your tile size (important if your images aren’t already TILE_SIZE x TILE_SIZE)
    dungeon_wall_image = pygame.transform.scale(dungeon_wall_image, (TILE_SIZE, TILE_SIZE))
    dungeon_floor_image = pygame.transform.scale(dungeon_floor_image, (TILE_SIZE, TILE_SIZE))


    # Interior images
    try:
        interiors = [
            pygame.transform.scale(pygame.image.load("indoor2.png").convert_alpha(), (WIDTH, HEIGHT)),
            pygame.transform.scale(pygame.image.load("indoor3.png").convert_alpha(), (WIDTH, HEIGHT))
        ]
    except:
        interior1 = create_fallback_surface((WIDTH, HEIGHT), (101, 67, 33))
        interior2 = create_fallback_surface((WIDTH, HEIGHT), (139, 69, 19))
        interiors = [interior1, interior2]

    # Define Item objects
    log_item = Item("Log", log_image)
    axe_item = Item("Axe", axe_image, category="Weapon")
    pickaxe_item = Item("Pickaxe", pickaxe_image, category="Weapon")
    stone_item = Item("Stone", stone_image)
    ore_item = Item("Ore", ore_image)
    flower_item = Item("Flower", flower_images[0])
    potion_item = Item("Potion", potion_image)
    coin_item = Item("Coin", coin_image)

    assets = {
        "grass": grass_image,
        "tree": tree_image,
        "house": house_image,
        "house1": house1_image,
        "interiors": interiors,
        "flowers": flower_images,
        "leaf": leaf_image,
        "portal": portal_image,
        "dungeon_wall": dungeon_wall_image,
        "dungeon_floor": dungeon_floor_image,
        "font": pygame.font.SysFont(None, 36),
        "small_font": pygame.font.SysFont(None, 24),
        "backpack_icon": backpack_icon,
        "crafting_icon": crafting_icon,
        "equipment_icon": equipment_icon,
        "log_item": log_item,
        "axe_item": axe_item,
        "pickaxe_item": pickaxe_item,
        "stone_item": stone_item,
        "ore_item": ore_item,
        "stone_img": stone_image,
        "ore_img": ore_image,
        "flower_item": flower_item,
        "potion_item": potion_item,
        "npc_image": npc_image,
        "miner_image": miner_image,
        "coin_item": coin_item,
    }
    return assets

def setup_indoor_colliders():
    """Set up collision boundaries for indoor areas."""
    global indoor_colliders
    indoor_colliders[:] = [
        pygame.Rect(0, 0, WIDTH, 100),           # top
        pygame.Rect(0, HEIGHT-10, WIDTH, 10),   # bottom
        pygame.Rect(0, 0, 10, HEIGHT),          # left
        pygame.Rect(WIDTH-10, 0, 10, HEIGHT)    # right
    ]

def setup_dungeon():
    """Creates the dungeon layout with walls, ore deposits, and exit."""
    global dungeon_walls, dungeon_exit
    dungeon_walls.clear()
    
    # Create dungeon walls around the perimeter
    for row in range(DUNGEON_SIZE):
        for col in range(DUNGEON_SIZE):
            x = col * TILE_SIZE
            y = row * TILE_SIZE
            
            # Border walls
            if row == 0 or row == DUNGEON_SIZE-1 or col == 0 or col == DUNGEON_SIZE-1:
                dungeon_walls.append(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))
            # Add some interior walls for complexity
            elif (row == 10 and col > 5 and col < 20) or (col == 15 and row > 8 and row < 15):
                dungeon_walls.append(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))
    
    # Add ore deposits scattered on the dungeon floor
    for row in range(2, DUNGEON_SIZE - 2):
        for col in range(2, DUNGEON_SIZE - 2):
            x = col * TILE_SIZE
            y = row * TILE_SIZE
        
            # Check if this tile is a wall
            wall_here = any(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE).colliderect(wall) for wall in dungeon_walls)

            # Only place ore on *floor tiles* (not walls)
            if not wall_here and random.random() < 0.08:  # 8% chance
                offset = (TILE_SIZE - (TILE_SIZE // 2)) // 2
                ore_rect = pygame.Rect(x + offset, y + offset, TILE_SIZE // 2, TILE_SIZE // 2)
                stone_rects.append(ore_rect)
    # Create exit portal in the bottom-right area
    dungeon_exit = pygame.Rect((DUNGEON_SIZE-5) * TILE_SIZE, (DUNGEON_SIZE-5) * TILE_SIZE, TILE_SIZE * 2, TILE_SIZE * 2)

def setup_colliders():
    """Generates the world colliders for the current level."""
    global tree_rects, house_list, indoor_colliders, flower_tiles, leaf_tiles, stone_rects
    global npc_rect, dungeon_portal, miner_npc_rect

    # Clear existing colliders
    tree_rects.clear()
    flower_tiles.clear()
    leaf_tiles.clear()
    house_list.clear()
    stone_rects.clear()

    player_world_rect = get_player_world_rect()
    map_cols, map_rows = 50, 50
    occupied_positions = set()  # Track occupied grid positions

    # --- BORDER TREES ---
    for row in range(map_rows):
        for col in range(map_cols):
            x = col * TILE_SIZE
            y = row * TILE_SIZE
            if row < BORDER_THICKNESS or row >= map_rows - BORDER_THICKNESS or col < BORDER_THICKNESS or col >= map_cols - BORDER_THICKNESS:
                tree_rects.append(pygame.Rect(x + 5, y + 5, TILE_SIZE - 10, TILE_SIZE - 10))
                occupied_positions.add((col, row))

    # --- HOUSES ---
    house_rect_1 = pygame.Rect(player_world_rect.x + 100, player_world_rect.y, TILE_SIZE * 2, TILE_SIZE * 2)
    house_rect_2 = pygame.Rect(house_rect_1.x + 200, house_rect_1.y, TILE_SIZE * 2, TILE_SIZE * 2)
    tree_rects.extend([house_rect_1, house_rect_2])
    house_list.extend([house_rect_1, house_rect_2])
    
    # Mark house positions as occupied
    for house in house_list:
        for dx in range(-1, 3):  # Extra buffer around houses
            for dy in range(-1, 3):
                grid_x = (house.x // TILE_SIZE) + dx
                grid_y = (house.y // TILE_SIZE) + dy
                if 0 <= grid_x < map_cols and 0 <= grid_y < map_rows:
                    occupied_positions.add((grid_x, grid_y))

    # NPCs
    npc_rect = pygame.Rect(house_rect_1.x - 60, house_rect_1.y + 30, PLAYER_SIZE * 4, PLAYER_SIZE * 4)
    
    # --- DUNGEON PORTAL ---
    dungeon_portal = pygame.Rect(1270, 1915, 50, 50)
    tree_rects.append(dungeon_portal)
    
    # Mark portal area as occupied
    portal_grid_x = dungeon_portal.x // TILE_SIZE
    portal_grid_y = dungeon_portal.y // TILE_SIZE
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            grid_x = portal_grid_x + dx
            grid_y = portal_grid_y + dy
            if 0 <= grid_x < map_cols and 0 <= grid_y < map_rows:
                occupied_positions.add((grid_x, grid_y))

    # Miner NPC near portal
    miner_npc_rect = pygame.Rect(dungeon_portal.x - 40, dungeon_portal.y, PLAYER_SIZE, PLAYER_SIZE)

    # --- RANDOM WORLD OBJECTS (avoiding occupied positions) ---
    for row in range(map_rows):
        for col in range(map_cols):
            # Skip borders and occupied positions
            if row < BORDER_THICKNESS or row >= map_rows - BORDER_THICKNESS or col < BORDER_THICKNESS or col >= map_cols - BORDER_THICKNESS:
                continue
            if (col, row) in occupied_positions:
                continue

            x = col * TILE_SIZE
            y = row * TILE_SIZE
            rnd = random.random()
            
            if rnd < 0.02:  # Trees
                tree_rects.append(pygame.Rect(x + 5, y + 5, TILE_SIZE - 10, TILE_SIZE - 10))
                occupied_positions.add((col, row))
            elif rnd < 0.035:  # Stones (only if no tree here)
                offset = (TILE_SIZE - (TILE_SIZE // 2)) // 2
                stone_rects.append(pygame.Rect(x + offset, y + offset, TILE_SIZE // 2, TILE_SIZE // 2))
            elif rnd < 0.065:  # Flowers
                flower_tiles.append((x + 10, y + 10, random.randint(0, 1)))
            elif rnd < 0.185:  # Leaves
                leaf_tiles.append((x + random.randint(8, 14), y + random.randint(8, 14)))

    # --- Indoor colliders ---
    setup_indoor_colliders()

    # --- Setup dungeon if needed ---
    if not dungeon_walls:
        setup_dungeon()

def give_starting_items(assets):
    """Adds initial items to the inventory."""
    add_item_to_inventory(assets["potion_item"])
    add_item_to_inventory(assets["axe_item"])

# --- INVENTORY/CRAFTING/EQUIPMENT LOGIC ---
def add_item_to_inventory(item_to_add):
    """Adds an item to the first available slot in the inventory (stack up to 20)."""
    # First, try to stack with existing items
    for row in range(4):
        for col in range(4):
            slot = inventory[row][col]
            if slot and slot.name == item_to_add.name and slot.count < 20:
                slot.count += 1
                return True

    # Then, try to find an empty slot
    for row in range(4):
        for col in range(4):
            if inventory[row][col] is None:
                new_item = Item(item_to_add.name, item_to_add.image, category=item_to_add.category)
                inventory[row][col] = new_item
                return True
    return False

def get_item_count(item_name):
    """Returns the total count of an item in the inventory."""
    count = 0
    for row in range(4):
        for col in range(4):
            slot = inventory[row][col]
            if slot and slot.name == item_name:
                count += slot.count
    return count

def remove_item_from_inventory(item_name, quantity):
    """Removes a specified quantity of an item from the inventory."""
    removed_count = 0
    for row in range(4):
        for col in range(4):
            slot = inventory[row][col]
            if slot and slot.name == item_name:
                to_remove = min(slot.count, quantity - removed_count)
                slot.count -= to_remove
                removed_count += to_remove
                if slot.count <= 0:
                    inventory[row][col] = None
                if removed_count >= quantity:
                    return True
    return False

def equip_item(item_to_equip):
    """Equips a weapon from the inventory to the weapon slot."""
    if item_to_equip and item_to_equip.category == "Weapon":
        if equipment_slots["weapon"] is None:
            equipment_slots["weapon"] = item_to_equip
            print(f"{item_to_equip.name} equipped!")
            return True
        else:
            print("Weapon slot is already taken.")
    return False

def unequip_item():
    """Unequips the currently held weapon."""
    item_to_unequip = equipment_slots.get("weapon")
    if item_to_unequip:
        if add_item_to_inventory(item_to_unequip):
            equipment_slots["weapon"] = None
            print(f"{item_to_unequip.name} unequipped!")
            return True
        else:
            print("Inventory is full, cannot unequip.")
    return False

# --- DRAWING FUNCTIONS ---
def draw_player_coordinates(screen, font):
    """Draws the player's current world coordinates in the top-left corner."""
    player_rect = get_player_world_rect()
    coord_text = f"Player: ({player_rect.x}, {player_rect.y}) - Level: {current_level}"
    text_surf = font.render(coord_text, True, (255, 255, 255))
    screen.blit(text_surf, (10, 10))

def draw_world(screen, assets):
    """Draws the outdoor world and its objects."""
    start_col = map_offset_x // TILE_SIZE
    start_row = map_offset_y // TILE_SIZE
    cols_to_draw = (WIDTH // TILE_SIZE) + 3
    rows_to_draw = (HEIGHT // TILE_SIZE) + 3
    tree_size_diff = 5

    # Draw grass
    for row in range(start_row, start_row + rows_to_draw):
        for col in range(start_col, start_col + cols_to_draw):
            x, y = col * TILE_SIZE, row * TILE_SIZE
            screen.blit(assets["grass"], (x - map_offset_x, y - map_offset_y))

    # Draw trees
    for tree in tree_rects:
        screen.blit(assets["tree"], (tree.x - map_offset_x - tree_size_diff // 6, tree.y - map_offset_y - tree_size_diff // 6))

    # Draw stones
    for stone in stone_rects:
        screen.blit(assets["stone_img"], (stone.x - map_offset_x, stone.y - map_offset_y))

    # Draw flowers
    for fx, fy, idx in flower_tiles:
        screen.blit(assets["flowers"][idx], (fx - map_offset_x, fy - map_offset_y))

    # Draw leaves
    for lx, ly in leaf_tiles:
        screen.blit(assets["leaf"], (lx - map_offset_x, ly - map_offset_y))

    # Draw the dungeon portal
    if dungeon_portal:
        screen.blit(assets["portal"], (dungeon_portal.x - map_offset_x, dungeon_portal.y - map_offset_y))

    # Draw the houses
    if house_list:
        screen.blit(assets["house"], (house_list[0].x - map_offset_x, house_list[0].y - map_offset_y))
        screen.blit(assets["house1"], (house_list[1].x - map_offset_x, house_list[1].y - map_offset_y))

    # Draw NPC with idle animation
    if npc_rect:
        animated_y = npc_rect.y + npc_idle_offset_y
        screen.blit(assets["npc_image"], (npc_rect.x - map_offset_x, animated_y - map_offset_y))
    
    # Draw Miner NPC with idle animation
    if miner_npc_rect:
        miner_animated_y = miner_npc_rect.y + miner_idle_offset_y
        screen.blit(assets["miner_image"], (miner_npc_rect.x - map_offset_x, miner_animated_y - map_offset_y))

def draw_dungeon(screen, assets):
    dungeon_width = 30   # number of tiles across
    dungeon_height = 30   # number of tiles down

    # Load floor tile only once
    if "dungeon_floor" not in assets:
        assets["dungeon_floor"] = pygame.image.load("caveFloor.png").convert_alpha()
        assets["dungeon_floor"] = pygame.transform.scale(
            assets["dungeon_floor"], (TILE_SIZE, TILE_SIZE)
        )

    floor_tile = assets["dungeon_floor"]

    # Draw floor tiles
    for x in range(dungeon_width):
        for y in range(dungeon_height):
            screen.blit(floor_tile, (x * TILE_SIZE - map_offset_x, y * TILE_SIZE - map_offset_y))

    # Draw dungeon walls
    for wall in dungeon_walls:
        screen.blit(assets["dungeon_wall"], (wall.x - map_offset_x, wall.y - map_offset_y))
    
    # Draw ore deposits
    for ore in stone_rects:
        screen.blit(assets["ore_img"], (ore.x - map_offset_x, ore.y - map_offset_y))
    
    # Draw exit portal
    if dungeon_exit:
        screen.blit(assets["portal"], (dungeon_exit.x - map_offset_x, dungeon_exit.y - map_offset_y))


def draw_tooltip(screen, font, text, pos):
    """Draw a tooltip at the specified position."""
    padding = 6
    text_surface = font.render(text, True, (255, 255, 255))
    rect = text_surface.get_rect()
    rect.midbottom = (pos[0] + 15, pos[1] - 5)

    bg_surf = pygame.Surface((rect.width + 2*padding, rect.height + 2*padding), pygame.SRCALPHA)
    bg_surf.fill((0, 0, 0, 180))
    pygame.draw.rect(bg_surf, (255, 255, 255), bg_surf.get_rect(), 1)

    screen.blit(bg_surf, (rect.x - padding, rect.y - padding))
    screen.blit(text_surface, rect)

def draw_npc_dialog(screen, assets):
    """Draws the NPC dialog box for Soldier Marcus."""
    if not show_npc_dialog:
        return

    dialog_width = 500
    dialog_height = 150
    dialog_x = (WIDTH - dialog_width) // 2
    dialog_y = HEIGHT - dialog_height - 20
    dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
    
    pygame.draw.rect(screen, (40, 40, 40), dialog_rect)
    pygame.draw.rect(screen, (255, 255, 255), dialog_rect, 3)

    name_text = assets["small_font"].render("Soldier Marcus", True, (255, 215, 0))
    screen.blit(name_text, (dialog_x + 10, dialog_y + 5))

    if not npc_quest_active and not npc_quest_completed:
        dialog_lines = [
            f"Greetings, Traveler! I'm in need of healing potions. Could",
            f"you brew {potions_needed} potions for us? I'd be grateful!",
            "Press [SPACE] to accept the quest, or [ESC] to decline."
        ]
    elif npc_quest_active:
        potions_current = get_item_count("Potion")
        if potions_current >= potions_needed:
            dialog_lines = [
                f"Excellent! You have the 3 potions I needed!",
                f"Press [SPACE] to deliver {potions_needed} potions and complete the quest."
            ]
        else:
            dialog_lines = [
                f"You currently have {potions_current}/{potions_needed} potions.",
                "Return when you have brewed enough for my unit!",
                "Press [ESC] to close."
            ]
    elif npc_quest_completed:
        dialog_lines = [
            "Thank you for the potions! My unit is ready for battle!",
            "I gave you your reward, 10 coins.",
            "I have a friend down south that could use your help too.",
            "Press [ESC] to close."
        ]

    y_offset = 35
    for line in dialog_lines:
        line_text = assets["small_font"].render(line, True, (255, 255, 255))
        screen.blit(line_text, (dialog_x + 10, dialog_y + y_offset))
        y_offset += 25

def draw_miner_dialog(screen, assets):
    """Draws the Miner NPC dialog box."""
    if not show_miner_dialog:
        return

    dialog_width = 500
    dialog_height = 150
    dialog_x = (WIDTH - dialog_width) // 2
    dialog_y = HEIGHT - dialog_height - 20
    dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
    
    pygame.draw.rect(screen, (40, 40, 40), dialog_rect)
    pygame.draw.rect(screen, (255, 255, 255), dialog_rect, 3)

    name_text = assets["small_font"].render("Miner Gareth", True, (139, 69, 19))
    screen.blit(name_text, (dialog_x + 10, dialog_y + 5))

    if not miner_quest_active and not miner_quest_completed:
        dialog_lines = [
            f"Ho there, adventurer! The mines below have been overrun by",
            f"creatures! I need someone to gather {ore_needed} ore chunks for our village.",
            "Press [SPACE] to accept the quest, or [ESC] to decline."
        ]
    elif miner_quest_active:
        ore_current = get_item_count("Ore")
        if ore_current >= ore_needed:
            dialog_lines = [
                f"Amazing! You found the {ore_needed} ore chunks we needed!",
                f"Press [SPACE] to deliver {ore_needed} ore and complete the quest."
            ]
        else:
            dialog_lines = [
                f"You currently have {ore_current}/{ore_needed} ore chunks.",
                "The dungeon below should have plenty. Be careful down there!",
                "Press [ESC] to close."
            ]
    elif miner_quest_completed:
        dialog_lines = [
            "Thank you for the ore! Our smiths can work again thanks to you!",
            "I've rewarded you with 15 coins for your bravery.",
            "May fortune smile upon your future adventures!",
            "Press [ESC] to close."
        ]

    y_offset = 35
    for line in dialog_lines:
        line_text = assets["small_font"].render(line, True, (255, 255, 255))
        screen.blit(line_text, (dialog_x + 10, dialog_y + y_offset))
        y_offset += 25

def draw_tooltip_for_nearby_objects(screen, font):
    """Draw a tooltip for interactive objects."""
    tooltip_text = None
    tooltip_pos = None
    mouse_pos = pygame.mouse.get_pos()
    player_world_rect = get_player_world_rect()

    if current_level == "world":
        # Portal Entry: check if near dungeon portal
        if dungeon_portal and player_world_rect.colliderect(dungeon_portal.inflate(20, 20)):
            tooltip_text = "Enter Dungeon [e]"
            portal_screen = world_to_screen_rect(dungeon_portal)
            tooltip_pos = (portal_screen.x, portal_screen.y)
        
        # Houses: show tooltip if near the player
        elif tooltip_text is None:
            house_index = check_house_entry(player_world_rect)
            if house_index is not None:
                house_screen = world_to_screen_rect(house_list[house_index])
                tooltip_text = "Enter [e]"
                tooltip_pos = (house_screen.x, house_screen.y)

        # Mouse hover tooltips
        if tooltip_text is None:
            # Flowers: show only on mouse hover
            for fx, fy, idx in flower_tiles:
                flower_rect = pygame.Rect(fx - map_offset_x, fy - map_offset_y, 30, 30)
                if flower_rect.collidepoint(mouse_pos):
                    tooltip_text = "Flower [e]"
                    tooltip_pos = (fx - map_offset_x, fy - map_offset_y)
                    break

        if tooltip_text is None:
            # Trees: show only on mouse hover
            for tree in tree_rects:
                tree_screen = world_to_screen_rect(tree)
                if tree_screen.collidepoint(mouse_pos) and tree not in house_list and tree != dungeon_portal:
                    tooltip_text = "Tree [e]"
                    tooltip_pos = (tree_screen.x, tree_screen.y)
                    break

        if tooltip_text is None:
            # Stones: show only on mouse hover
            for stone in stone_rects:
                stone_screen = world_to_screen_rect(stone)
                if stone_screen.collidepoint(mouse_pos):
                    tooltip_text = "Stone [e]"
                    tooltip_pos = (stone_screen.x, stone_screen.y)
                    break

        if tooltip_text is None:
            # Marcus: show only on mouse hover
            if npc_rect:
                marcus_screen = pygame.Rect(
                    npc_rect.x - map_offset_x,
                    npc_rect.y - map_offset_y + npc_idle_offset_y,
                    npc_rect.width,
                    npc_rect.height
                )
                if marcus_screen.collidepoint(mouse_pos):
                    tooltip_text = "Marcus [e]"
                    tooltip_pos = (marcus_screen.x, marcus_screen.y)

        if tooltip_text is None:
            # Miner: show only on mouse hover
            if miner_npc_rect:
                miner_screen = pygame.Rect(
                    miner_npc_rect.x - map_offset_x,
                    miner_npc_rect.y - map_offset_y + miner_idle_offset_y,
                    miner_npc_rect.width,
                    miner_npc_rect.height
                )
                if miner_screen.collidepoint(mouse_pos):
                    tooltip_text = "Miner Gareth [e]"
                    tooltip_pos = (miner_screen.x, miner_screen.y)

    elif current_level == "house":
        # Inside house: Exit door tooltip if near
        door_zone = pygame.Rect(WIDTH // 2 - 40, HEIGHT - 100, 80, 80)
        if player_pos.colliderect(door_zone):
            tooltip_text = "Exit [e]"
            tooltip_pos = door_zone.topleft
    
    elif current_level == "dungeon":
        # Inside dungeon: Exit portal tooltip if near
        player_world_rect = get_player_world_rect()
        if dungeon_exit and player_world_rect.colliderect(dungeon_exit.inflate(20, 20)):
            exit_screen = world_to_screen_rect(dungeon_exit)
            tooltip_text = "Exit Dungeon [e]"
            tooltip_pos = (exit_screen.x, exit_screen.y)
        
        # Dungeon ore: show only on mouse hover
        elif tooltip_text is None:
            for stone in stone_rects:
                stone_screen = world_to_screen_rect(stone)
                if stone_screen.collidepoint(mouse_pos):
                    tooltip_text = "Ore Deposit [e]"
                    tooltip_pos = (stone_screen.x, stone_screen.y)
                    break

    # Draw the tooltip if we have text and position
    if tooltip_text and tooltip_pos:
        draw_tooltip(screen, font, tooltip_text, tooltip_pos)

def draw_inventory(screen, assets):
    """Draws the inventory GUI."""
    pygame.draw.rect(screen, (101, 67, 33), (INVENTORY_X, INVENTORY_Y, INVENTORY_WIDTH, INVENTORY_HEIGHT + 50))
    header_rect = pygame.Rect(INVENTORY_X, INVENTORY_Y, INVENTORY_WIDTH, 40)
    pygame.draw.rect(screen, (50, 33, 16), header_rect)
    header_text = assets["small_font"].render("Backpack", True, (255, 255, 255))
    screen.blit(header_text, header_text.get_rect(centerx=header_rect.centerx, top=INVENTORY_Y + 10))

    for row in range(4):
        for col in range(4):
            slot_x = INVENTORY_X + INVENTORY_GAP + col * (INVENTORY_SLOT_SIZE + INVENTORY_GAP)
            slot_y = INVENTORY_Y + 40 + INVENTORY_GAP + row * (INVENTORY_SLOT_SIZE + INVENTORY_GAP)
            slot_rect = pygame.Rect(slot_x, slot_y, INVENTORY_SLOT_SIZE, INVENTORY_SLOT_SIZE)
            pygame.draw.rect(screen, (70, 70, 70), slot_rect)
            pygame.draw.rect(screen, (150, 150, 150), slot_rect, 2)

            item = inventory[row][col]
            if item:
                screen.blit(pygame.transform.scale(item.image, (INVENTORY_SLOT_SIZE, INVENTORY_SLOT_SIZE)), slot_rect)
                if item.count > 1:
                    count_text = assets["small_font"].render(str(item.count), True, (255, 255, 255))
                    screen.blit(count_text, count_text.get_rect(bottomright=slot_rect.bottomright))

def draw_crafting_panel(screen, assets, is_hovering):
    """Draws the crafting GUI with tabs for smithing and alchemy."""
    global axe_button_rect, pickaxe_button_rect, potion_button_rect, alchemy_tab_rect, smithing_tab_rect

    panel_rect = pygame.Rect(CRAFTING_X, CRAFTING_Y, CRAFTING_PANEL_WIDTH, CRAFTING_PANEL_HEIGHT)
    pygame.draw.rect(screen, (101, 67, 33), panel_rect)

    # Header
    header_rect = pygame.Rect(CRAFTING_X, CRAFTING_Y, CRAFTING_PANEL_WIDTH, 35)
    pygame.draw.rect(screen, (50, 33, 16), header_rect)
    header_text = assets["small_font"].render("Crafting", True, (255, 255, 255))
    screen.blit(header_text, header_text.get_rect(centerx=header_rect.centerx, centery=header_rect.centery))

    # Tab buttons
    tab_width = 90
    tab_height = 25
    tab_y = CRAFTING_Y + 40
    tab_spacing = 10
    
    smithing_tab_rect = pygame.Rect(CRAFTING_X + tab_spacing, tab_y, tab_width, tab_height)
    alchemy_tab_rect = pygame.Rect(CRAFTING_X + tab_spacing + tab_width + 5, tab_y, tab_width, tab_height)

    # Draw smithing tab
    smithing_color = (80, 150, 80) if crafting_tab == "smithing" else (60, 60, 60)
    pygame.draw.rect(screen, smithing_color, smithing_tab_rect)
    pygame.draw.rect(screen, (255, 255, 255), smithing_tab_rect, 2)
    smithing_text = assets["small_font"].render("Smithing", True, (255, 255, 255))
    screen.blit(smithing_text, smithing_text.get_rect(center=smithing_tab_rect.center))

    # Draw alchemy tab
    alchemy_color = (80, 80, 150) if crafting_tab == "alchemy" else (60, 60, 60)
    pygame.draw.rect(screen, alchemy_color, alchemy_tab_rect)
    pygame.draw.rect(screen, (255, 255, 255), alchemy_tab_rect, 2)
    alchemy_text = assets["small_font"].render("Alchemy", True, (255, 255, 255))
    screen.blit(alchemy_text, alchemy_text.get_rect(center=alchemy_tab_rect.center))

    # Content area
    content_y = tab_y + tab_height + 10
    content_height = CRAFTING_PANEL_HEIGHT - (content_y - CRAFTING_Y)

    if crafting_tab == "smithing":
        draw_smithing_content(screen, assets, is_hovering, content_y)
    elif crafting_tab == "alchemy":
        draw_alchemy_content(screen, assets, is_hovering, content_y)

def draw_smithing_content(screen, assets, is_hovering, content_y):
    """Draws the smithing crafting options."""
    global axe_button_rect, pickaxe_button_rect
    
    button_width, button_height, gap = 180, 50, 20
    log_count = get_item_count("Log")

    # Axe Button
    axe_button_rect = pygame.Rect(CRAFTING_X + gap, content_y + gap, button_width, button_height)
    req_logs_axe = 5

    # Pickaxe Button
    pickaxe_button_rect = pygame.Rect(CRAFTING_X + gap, axe_button_rect.bottom + gap, button_width, button_height)
    req_logs_pickaxe = 10

    buttons = [
        (axe_button_rect, "axe", req_logs_axe, assets["axe_item"]),
        (pickaxe_button_rect, "pickaxe", req_logs_pickaxe, assets["pickaxe_item"])
    ]

    for rect, item_name, req_logs, item_obj in buttons:
        can_craft = log_count >= req_logs
        
        if is_crafting and item_to_craft and item_to_craft.name.lower() == item_name:
            progress = (crafting_timer / CRAFTING_TIME_MS) * 100
            text_to_display = f"Crafting... {int(progress)}%"
            color = (120, 120, 120)
        elif is_hovering == item_name:
            text_to_display = f"{item_obj.name}: {log_count}/{req_logs} Logs"
            color = (0, 100, 0) if can_craft else (50, 50, 50)
        else:
            text_to_display = f"Craft {item_obj.name}"
            color = (0, 150, 0) if can_craft else (70, 70, 70)

        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, (150, 150, 150), rect, 2)
        text_surface = assets["small_font"].render(text_to_display, True, (255, 255, 255))
        screen.blit(text_surface, text_surface.get_rect(center=rect.center))

def draw_alchemy_content(screen, assets, is_hovering, content_y):
    """Draws the alchemy crafting options."""
    global potion_button_rect
    
    button_width, button_height, gap = 180, 50, 20
    flower_count = get_item_count("Flower")

    # Potion Button
    potion_button_rect = pygame.Rect(CRAFTING_X + gap, content_y + gap, button_width, button_height)
    req_flowers = 3

    can_craft = flower_count >= req_flowers
    
    if is_crafting and item_to_craft and item_to_craft.name == "Potion":
        progress = (crafting_timer / CRAFTING_TIME_MS) * 100
        text_to_display = f"Brewing... {int(progress)}%"
        color = (120, 120, 120)
    elif is_hovering == "potion":
        text_to_display = f"Potion: {flower_count}/{req_flowers} Flowers"
        color = (100, 0, 100) if can_craft else (50, 50, 50)
    else:
        text_to_display = f"Brew Potion"
        color = (150, 0, 150) if can_craft else (70, 70, 70)

    pygame.draw.rect(screen, color, potion_button_rect)
    pygame.draw.rect(screen, (150, 150, 150), potion_button_rect, 2)
    text_surface = assets["small_font"].render(text_to_display, True, (255, 255, 255))
    screen.blit(text_surface, text_surface.get_rect(center=potion_button_rect.center))

def draw_equipment_panel(screen, assets):
    """Draws the equipment GUI."""
    panel_rect = pygame.Rect(EQUIPMENT_X, EQUIPMENT_Y, EQUIPMENT_PANEL_WIDTH, EQUIPMENT_PANEL_HEIGHT)
    pygame.draw.rect(screen, (101, 67, 33), panel_rect)
    header_rect = pygame.Rect(EQUIPMENT_X, EQUIPMENT_Y, EQUIPMENT_PANEL_WIDTH, 40)
    pygame.draw.rect(screen, (50, 33, 16), header_rect)
    header_text = assets["small_font"].render("Equipment", True, (255, 255, 255))
    screen.blit(header_text, header_text.get_rect(centerx=header_rect.centerx, top=EQUIPMENT_Y + 10))

    # Draw weapon slot
    weapon_slot_rect = pygame.Rect(EQUIPMENT_X + EQUIPMENT_GAP, EQUIPMENT_Y + 40 + EQUIPMENT_GAP,
                                     EQUIPMENT_SLOT_SIZE, EQUIPMENT_SLOT_SIZE)
    pygame.draw.rect(screen, (70, 70, 70), weapon_slot_rect)
    pygame.draw.rect(screen, (150, 150, 150), weapon_slot_rect, 2)

    equipped_weapon = equipment_slots.get("weapon")
    if equipped_weapon:
        screen.blit(pygame.transform.scale(equipped_weapon.image, (EQUIPMENT_SLOT_SIZE, EQUIPMENT_SLOT_SIZE)), weapon_slot_rect)

def draw_hud(screen, assets):
    """Draws the main HUD elements (icons)."""
    icons = [
        (assets["backpack_icon"], "[ i ]", WIDTH - 40),
        (assets["crafting_icon"], "[ c ]", WIDTH - 80),
        (assets["equipment_icon"], "[ r ]", WIDTH - 120)
    ]
    for icon, label, x_pos in icons:
        icon_rect = icon.get_rect(centerx=x_pos, top=10)
        label_text = assets["small_font"].render(label, True, (255, 255, 255))
        label_rect = label_text.get_rect(centerx=icon_rect.centerx, top=icon_rect.bottom + 5)
        screen.blit(icon, icon_rect)
        screen.blit(label_text, label_rect)

# --- MAIN GAME LOGIC ---
def handle_movement(keys):
    """Handles player movement input and updates direction."""
    global current_direction, last_direction
    dx = dy = 0
    if keys[pygame.K_a]:
        dx -= PLAYER_SPEED
        current_direction = "left"
    if keys[pygame.K_d]:
        dx += PLAYER_SPEED
        current_direction = "right"
    if keys[pygame.K_w]:
        dy -= PLAYER_SPEED
        current_direction = "up"
    if keys[pygame.K_s]:
        dy += PLAYER_SPEED
        current_direction = "down"
    if dx == 0 and dy == 0:
        current_direction = "idle"
    else:
        last_direction = current_direction
    return dx, dy

def handle_collision(new_world_rect):
    """Checks for collision with world objects."""
    if current_level == "world":
        # Collide with trees/houses
        if any(new_world_rect.colliderect(r) for r in tree_rects):
            return True
        # Collide with stones
        if any(new_world_rect.colliderect(r) for r in stone_rects):
            return True
        return False
    elif current_level == "dungeon":
        # Collide with dungeon walls
        if any(new_world_rect.colliderect(r) for r in dungeon_walls):
            return True
        # Collide with ore deposits
        if any(new_world_rect.colliderect(r) for r in stone_rects):
            return True
        return False
    else:
        # Indoor collisions
        return any(new_world_rect.colliderect(r) for r in indoor_colliders)

def check_house_entry(world_rect):
    """Checks if the player's world rect is near a house door."""
    for i, h in enumerate(house_list):
        if world_rect.colliderect(h.inflate(20, 20)):
            return i
    return None

def main():
    """Main game loop."""
    global map_offset_x, map_offset_y, current_level, current_house_index
    global player_frame_index, player_frame_timer, current_direction, last_direction
    global show_inventory, show_crafting, show_equipment, crafting_tab
    global is_chopping, chopping_timer, chopping_target_tree, is_swinging
    global is_crafting, crafting_timer, item_to_craft
    global is_mining, mining_timer, mining_target_stone
    global player_pos
    global show_npc_dialog, npc_quest_active, npc_quest_completed
    global show_miner_dialog, miner_quest_active, miner_quest_completed
    global npc_idle_timer, npc_idle_offset_y, npc_idle_direction
    global miner_idle_timer, miner_idle_offset_y, miner_idle_direction

    # Initialize
    screen, clock = init()
    assets = load_assets()
    player_frames = load_player_frames()
    chopping_frames = load_chopping_frames()
    setup_colliders()
    give_starting_items(assets)

    while True:
        dt = clock.tick(60)
        current_time = pygame.time.get_ticks()

        # UI Hover State
        is_hovering = None
        mouse_pos = pygame.mouse.get_pos()
        if show_crafting:
            if crafting_tab == "smithing":
                if axe_button_rect and axe_button_rect.collidepoint(mouse_pos):
                    is_hovering = "axe"
                elif pickaxe_button_rect and pickaxe_button_rect.collidepoint(mouse_pos):
                    is_hovering = "pickaxe"
            elif crafting_tab == "alchemy":
                if potion_button_rect and potion_button_rect.collidepoint(mouse_pos):
                    is_hovering = "potion"

        # Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN:
                # Toggle UI panels
                if event.key == pygame.K_i:
                    show_inventory = not show_inventory
                    show_crafting = show_equipment = False
                elif event.key == pygame.K_c and not (is_chopping or is_crafting):
                    show_crafting = not show_crafting
                    show_inventory = show_equipment = False
                elif event.key == pygame.K_r and not (is_chopping or is_crafting):
                    show_equipment = not show_equipment
                    show_inventory = show_crafting = False

                # Interact with World
                player_world_rect = get_player_world_rect()
                if event.key == pygame.K_e:
                    if current_level == "world":
                        # Priority 1: Enter Dungeon Portal
                        if dungeon_portal and player_world_rect.colliderect(dungeon_portal.inflate(20, 20)):
                            current_level = "dungeon"
                            map_offset_x = DUNGEON_SPAWN_X - WIDTH // 2
                            map_offset_y = DUNGEON_SPAWN_Y - HEIGHT // 2
                            player_pos.center = (WIDTH // 2, HEIGHT // 2)
                            
                        # Priority 2: Enter House
                        elif check_house_entry(player_world_rect) is not None:
                            house_index = check_house_entry(player_world_rect)
                            current_level = "house"
                            current_house_index = house_index
                            player_pos.size = (PLAYER_SIZE_INDOOR, PLAYER_SIZE_INDOOR)
                            player_pos.center = (WIDTH // 2, HEIGHT // 2)
                            setup_indoor_colliders()
                            
                        # Priority 3: Talk to NPCs
                        elif npc_rect and player_world_rect.colliderect(npc_rect.inflate(20, 20)):
                            show_npc_dialog = True
                        elif miner_npc_rect and player_world_rect.colliderect(miner_npc_rect.inflate(20, 20)):
                            show_miner_dialog = True
                            
                        # Priority 4: Chop Trees
                        elif equipment_slots["weapon"] and equipment_slots["weapon"].name == "Axe":
                            for tree in list(tree_rects):
                                if (player_world_rect.colliderect(tree.inflate(20, 20)) and 
                                    tree not in house_list and tree != dungeon_portal):
                                    is_chopping = True
                                    chopping_target_tree = tree
                                    chopping_timer = 0
                                    current_direction = "idle"
                                    break
                            else:
                                # Priority 5: Mine Stones
                                if equipment_slots["weapon"] and equipment_slots["weapon"].name == "Pickaxe":
                                    for stone in list(stone_rects):
                                        if player_world_rect.colliderect(stone.inflate(20, 20)):
                                            is_mining = True
                                            mining_target_stone = stone
                                            mining_timer = 0
                                            current_direction = "idle"
                                            break
                                else:
                                    # Priority 6: Pick Flowers
                                    for fx, fy, idx in list(flower_tiles):
                                        flower_rect = pygame.Rect(fx, fy, 30, 30)
                                        if player_world_rect.colliderect(flower_rect.inflate(10, 10)):
                                            add_item_to_inventory(assets["flower_item"])
                                            flower_tiles.remove((fx, fy, idx))
                                            print("Picked a flower!")
                                            break
                                    else:
                                        print("You need an Axe to chop trees or a Pickaxe to mine stone!")
                        elif equipment_slots["weapon"] and equipment_slots["weapon"].name == "Pickaxe":
                            for stone in list(stone_rects):
                                if player_world_rect.colliderect(stone.inflate(20, 20)):
                                    is_mining = True
                                    mining_target_stone = stone
                                    mining_timer = 0
                                    current_direction = "idle"
                                    break
                            else:
                                # Pick Flowers
                                for fx, fy, idx in list(flower_tiles):
                                    flower_rect = pygame.Rect(fx, fy, 30, 30)
                                    if player_world_rect.colliderect(flower_rect.inflate(10, 10)):
                                        add_item_to_inventory(assets["flower_item"])
                                        flower_tiles.remove((fx, fy, idx))
                                        print("Picked a flower!")
                                        break
                        else:
                            # Pick Flowers without tools
                            for fx, fy, idx in list(flower_tiles):
                                flower_rect = pygame.Rect(fx, fy, 30, 30)
                                if player_world_rect.colliderect(flower_rect.inflate(10, 10)):
                                    add_item_to_inventory(assets["flower_item"])
                                    flower_tiles.remove((fx, fy, idx))
                                    print("Picked a flower!")
                                    break
                    
                    elif current_level == "dungeon":
                        # Inside dungeon: Mine ore or exit
                        if dungeon_exit and player_world_rect.colliderect(dungeon_exit.inflate(20, 20)):
                            # Exit dungeon back to world
                            current_level = "world"
                            portal_x = 25 * TILE_SIZE
                            portal_y = 38 * TILE_SIZE
                            map_offset_x = portal_x - WIDTH // 2
                            map_offset_y = portal_y - HEIGHT // 2 + 100
                            player_pos.center = (WIDTH // 2, HEIGHT // 2)
                        elif equipment_slots["weapon"] and equipment_slots["weapon"].name == "Pickaxe":
                            for stone in list(stone_rects):
                                if player_world_rect.colliderect(stone.inflate(20, 20)):
                                    is_mining = True
                                    mining_target_stone = stone
                                    mining_timer = 0
                                    current_direction = "idle"
                                    break
                        else:
                            print("You need a Pickaxe to mine ore!")
                            
                    else:  # current_level == "house"
                        # Inside house -> Exit
                        door_zone = pygame.Rect(WIDTH // 2 - 40, HEIGHT - 100, 80, 80)
                        if door_zone.colliderect(player_pos.inflate(50, 50)):
                            current_level = "world"
                            player_pos.size = (PLAYER_SIZE, PLAYER_SIZE)
                            exit_rect = house_list[current_house_index]
                            player_world_x = exit_rect.centerx - 20
                            player_world_y = exit_rect.bottom + 20
                            map_offset_x = player_world_x - WIDTH // 2
                            map_offset_y = player_world_y - HEIGHT // 2
                            player_pos.center = (WIDTH // 2, HEIGHT // 2)
                            current_house_index = None

                # NPC Dialog controls
                if event.key == pygame.K_SPACE and show_npc_dialog:
                    if not npc_quest_active and not npc_quest_completed:
                        # Accept quest
                        npc_quest_active = True
                        show_npc_dialog = False
                        print("Quest accepted! Bring 3 potions to Soldier Marcus.")
                    elif npc_quest_active and get_item_count("Potion") >= potions_needed:
                        # Complete quest
                        remove_item_from_inventory("Potion", potions_needed)
                        for _ in range(10):
                            add_item_to_inventory(assets["coin_item"])
                        npc_quest_completed = True
                        npc_quest_active = False
                        show_npc_dialog = False
                        print("Quest completed! You received 10 coins as a reward!")
                
                # Miner Dialog controls
                if event.key == pygame.K_SPACE and show_miner_dialog:
                    if not miner_quest_active and not miner_quest_completed:
                        # Accept miner quest
                        miner_quest_active = True
                        show_miner_dialog = False
                        print("Quest accepted! Gather 10 ore from the dungeon for Miner Gareth.")
                    elif miner_quest_active and get_item_count("Ore") >= ore_needed:
                        # Complete miner quest
                        remove_item_from_inventory("Ore", ore_needed)
                        for _ in range(15):
                            add_item_to_inventory(assets["coin_item"])
                        miner_quest_completed = True
                        miner_quest_active = False
                        show_miner_dialog = False
                        print("Quest completed! You received 15 coins as a reward!")
                
                elif event.key == pygame.K_ESCAPE and (show_npc_dialog or show_miner_dialog):
                    show_npc_dialog = False
                    show_miner_dialog = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if show_crafting and not is_crafting:
                    # Check tab clicks first
                    if smithing_tab_rect and smithing_tab_rect.collidepoint(event.pos):
                        crafting_tab = "smithing"
                    elif alchemy_tab_rect and alchemy_tab_rect.collidepoint(event.pos):
                        crafting_tab = "alchemy"
                    
                    # Then check crafting buttons based on active tab
                    elif crafting_tab == "smithing":
                        if axe_button_rect and axe_button_rect.collidepoint(event.pos):
                            if get_item_count("Log") >= 5:
                                is_crafting = True
                                crafting_timer = 0
                                item_to_craft = assets["axe_item"]
                                remove_item_from_inventory("Log", 5)
                                print("Crafting an Axe...")
                            else:
                                print("Not enough logs!")
                        elif pickaxe_button_rect and pickaxe_button_rect.collidepoint(event.pos):
                            if get_item_count("Log") >= 10:
                                is_crafting = True
                                crafting_timer = 0
                                item_to_craft = assets["pickaxe_item"]
                                remove_item_from_inventory("Log", 10)
                                print("Crafting a Pickaxe...")
                            else:
                                print("Not enough logs!")
                    
                    elif crafting_tab == "alchemy":
                        if potion_button_rect and potion_button_rect.collidepoint(event.pos):
                            if get_item_count("Flower") >= 3:
                                is_crafting = True
                                crafting_timer = 0
                                item_to_craft = assets["potion_item"]
                                remove_item_from_inventory("Flower", 3)
                                print("Brewing a Potion...")
                            else:
                                print("Not enough flowers!")

                # Equipment
                if show_equipment:
                    weapon_slot_rect = pygame.Rect(EQUIPMENT_X + EQUIPMENT_GAP, EQUIPMENT_Y + 40 + EQUIPMENT_GAP,
                                                    EQUIPMENT_SLOT_SIZE, EQUIPMENT_SLOT_SIZE)
                    if weapon_slot_rect.collidepoint(event.pos):
                        unequip_item()
                        
                # Inventory
                if show_inventory:
                    for row in range(4):
                        for col in range(4):
                            slot_x = INVENTORY_X + INVENTORY_GAP + col * (INVENTORY_SLOT_SIZE + INVENTORY_GAP)
                            slot_y = INVENTORY_Y + 40 + INVENTORY_GAP + row * (INVENTORY_SLOT_SIZE + INVENTORY_GAP)
                            slot_rect = pygame.Rect(slot_x, slot_y, INVENTORY_SLOT_SIZE, INVENTORY_SLOT_SIZE)
                            if slot_rect.collidepoint(event.pos):
                                item_to_equip = inventory[row][col]
                                if item_to_equip and item_to_equip.category == "Weapon":
                                    if equip_item(item_to_equip):
                                        inventory[row][col] = None
                                        break

        # Game State Updates
        # NPC idle animations
        npc_idle_timer += dt
        if npc_idle_timer >= 2000:
            npc_idle_direction *= -1
            npc_idle_timer = 0
        
        idle_progress = npc_idle_timer / 2000.0
        npc_idle_offset_y = int(3 * math.sin(idle_progress * 3.14159) * npc_idle_direction)
        
        # Miner NPC idle animation
        miner_idle_timer += dt
        if miner_idle_timer >= 2200:
            miner_idle_direction *= -1
            miner_idle_timer = 0
        
        miner_idle_progress = miner_idle_timer / 2200.0
        miner_idle_offset_y = int(4 * math.sin(miner_idle_progress * 3.14159) * miner_idle_direction)
        
        # Crafting
        if is_crafting:
            crafting_timer += dt
            if crafting_timer >= CRAFTING_TIME_MS:
                if add_item_to_inventory(item_to_craft):
                    print(f"Crafting complete! {item_to_craft.name} added to inventory.")
                else:
                    print(f"Crafting failed: Inventory is full.")
                is_crafting = False
                item_to_craft = None

        # Chopping animation
        if is_chopping:
            chopping_timer += dt
            player_frame_timer += dt
            if player_frame_timer > idle_chop_delay:
                is_swinging = True
                if player_frame_timer >= swing_delay:
                    player_frame_index = (player_frame_index + 1) % len(chopping_frames[last_direction])
                    player_frame_timer = 0

            if chopping_timer >= CHOPPING_DURATION:
                if chopping_target_tree in tree_rects:
                    tree_rects.remove(chopping_target_tree)
                    chopped_trees[(chopping_target_tree.x, chopping_target_tree.y, chopping_target_tree.width, chopping_target_tree.height)] = current_time
                    add_item_to_inventory(assets["log_item"])
                    print("Chopped a tree! Gained a log.")
                is_chopping = False
                is_swinging = False
                chopping_timer = 0
                chopping_target_tree = None
                current_direction = "idle"

        # Mining animation
        if is_mining:
            mining_timer += dt
            player_frame_timer += dt
            if player_frame_timer > idle_chop_delay:
                is_swinging = True
                if player_frame_timer >= swing_delay:
                    player_frame_index = (player_frame_index + 1) % len(chopping_frames[last_direction])
                    player_frame_timer = 0

            if mining_timer >= MINING_DURATION:
                if mining_target_stone in stone_rects:
                    stone_rects.remove(mining_target_stone)
                    chopped_stones[(mining_target_stone.x, mining_target_stone.y, mining_target_stone.width, mining_target_stone.height)] = current_time
                    # Give ore if in dungeon, stone if in world
                    if current_level == "dungeon":
                        add_item_to_inventory(assets["ore_item"])
                        print("Mined ore!")
                    else:
                        add_item_to_inventory(assets["stone_item"])
                        print("Mined a stone!")
                is_mining = False
                is_swinging = False
                mining_timer = 0
                mining_target_stone = None
                current_direction = "idle"
       
        # Respawn Logic
        for tree_rect_tuple, time_chopped in list(chopped_trees.items()):
            tree_rect = pygame.Rect(tree_rect_tuple)
            if current_time - time_chopped > RESPAWN_TIME:
                tree_rects.append(tree_rect)
                del chopped_trees[tree_rect_tuple]

        for stone_rect_tuple, time_mined in list(chopped_stones.items()):
            stone_rect = pygame.Rect(stone_rect_tuple)
            if current_time - time_mined > RESPAWN_TIME:
                stone_rects.append(stone_rect)
                del chopped_stones[stone_rect_tuple]

        # Player Movement
        if not (show_inventory or show_crafting or show_equipment or is_chopping or is_mining or show_npc_dialog or show_miner_dialog):
            keys = pygame.key.get_pressed()
            dx, dy = handle_movement(keys)
            
            if current_level == "world" or current_level == "dungeon":
                new_player_world_rect = get_player_world_rect().move(dx, dy)
                if not handle_collision(new_player_world_rect):
                    map_offset_x += dx
                    map_offset_y += dy
            else:  # current_level == "house"
                new_player_pos = player_pos.move(dx, dy)
                if not handle_collision(new_player_pos):
                    player_pos = new_player_pos

        # Animation state update
        if not is_chopping and not is_mining:
            player_frame_timer += dt
            if current_direction == "idle":
                player_frame_index = 0
            elif player_frame_timer > player_frame_delay:
                player_frame_index = (player_frame_index + 1) % len(player_frames[current_direction])
                player_frame_timer = 0
                
        # Drawing
        screen.fill((0, 0, 0))
        if current_level == "world":
            draw_world(screen, assets)
        elif current_level == "dungeon":
            draw_dungeon(screen, assets)
        else:
            screen.blit(assets["interiors"][current_house_index], (0, 0))

        # Determine the current size of the player for drawing
        player_size_current = player_pos.width

        # Draw player
        if is_chopping or is_mining:
            scaled_frame = pygame.transform.scale(chopping_frames[last_direction][player_frame_index], (player_size_current, player_size_current))
            screen.blit(scaled_frame, player_pos)
        else:
            frame_set = player_frames.get(current_direction, player_frames["idle"])
            scaled_frame = pygame.transform.scale(frame_set[player_frame_index], (player_size_current, player_size_current))
            screen.blit(scaled_frame, player_pos)

        draw_hud(screen, assets)
        draw_tooltip_for_nearby_objects(screen, assets["small_font"])

        # Draw dialogs
        draw_npc_dialog(screen, assets)
        draw_miner_dialog(screen, assets)

        # Draw UI panels
        if show_inventory:
            draw_inventory(screen, assets)
        if show_crafting:
            draw_crafting_panel(screen, assets, is_hovering)
        if show_equipment:
            draw_equipment_panel(screen, assets)
        
        draw_player_coordinates(screen, assets["small_font"])
        pygame.display.flip()

if __name__ == '__main__':
    main()