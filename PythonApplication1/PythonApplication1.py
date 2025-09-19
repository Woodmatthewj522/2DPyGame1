# -*- coding: utf-8 -*-
import os
import random
import sys
import pygame, json, sys


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
RESPAWN_TIME = 1500

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
CRAFTING_Y = (HEIGHT - CRAFTING_PANEL_HEIGHT) // 2

# Equipment GUI constants
EQUIPMENT_SLOT_SIZE = 40
EQUIPMENT_GAP = 25
EQUIPMENT_ROWS = 4
EQUIPMENT_COLS = 2
EQUIPMENT_PANEL_WIDTH = 2 * EQUIPMENT_SLOT_SIZE + 3 * EQUIPMENT_GAP + 20
EQUIPMENT_PANEL_HEIGHT = EQUIPMENT_ROWS * EQUIPMENT_SLOT_SIZE + (EQUIPMENT_ROWS + 1) * EQUIPMENT_GAP + 50
EQUIPMENT_X = (WIDTH - EQUIPMENT_PANEL_WIDTH) // 2
EQUIPMENT_Y = (HEIGHT - EQUIPMENT_PANEL_HEIGHT) // 2

# Mining constants
MINING_DURATION = 2000  # ms

# --- ITEM CLASS ---
class Item:
    def __init__(self, name, image, count=1, category=None):
        self.name = name
        self.image = image
        self.count = count
        self.category = category

# --- GAME STATE GLOBALS ---
# Player is kept at a fixed screen position (center). World moves (map_offset).
player_pos = pygame.Rect(WIDTH // 2, HEIGHT // 2, PLAYER_SIZE, PLAYER_SIZE)  # screen coordinates
map_offset_x = 0  # how much world is shifted (subtracted when drawing): screen_x = world_x - map_offset_x
map_offset_y = 0
current_level = "world"
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

# Game objects
inventory = [[None for _ in range(4)] for _ in range(4)]
equipment_slots = {"weapon": None}
tree_rects = []
house_list = []
stone_rects = []
chopped_trees = {}
chopped_stones = {}
indoor_colliders = []
flower_tiles = []
leaf_tiles = []

# Crafting button rects
axe_button_rect = None
pickaxe_button_rect = None

# --- HELPERS FOR COORDINATES ---
def get_player_world_rect():
    """Return the player's rectangle in world coordinates."""
    return player_pos.move(map_offset_x, map_offset_y)

def world_to_screen_rect(world_rect):
    """Convert a world rect to screen coordinates (pygame.Rect)."""
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
    sheet = pygame.image.load("Player.PNG").convert_alpha()
    frames = {}
    right_frames = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col * 32, 32, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(COLS)]
    frames["right"] = right_frames
    frames["left"] = [pygame.transform.flip(frame, True, False) for frame in right_frames]
    frames["up"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col * 32, 64, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(COLS)]
    frames["down"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col * 32, 96, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(COLS)]
    frames["idle"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(0, 0, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE))]
    return frames

def load_chopping_frames():
    """Loads and scales the chopping animation frames."""
    sheet = pygame.image.load("Player.PNG").convert_alpha()
    chopping_frames = {}
    chopping_frames["right"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col * 32, 224, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(4)]
    chopping_frames["left"] = [pygame.transform.flip(frame, True, False) for frame in chopping_frames["right"]]
    chopping_frames["up"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col * 32, 255, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(4)]
    chopping_frames["down"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col * 32, 190, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(4)]
    return chopping_frames

def load_assets():
    """Loads all game assets and defines Item objects."""
    tile_folder = "Tiles"
    sheet = pygame.image.load("OutdoorStuff.PNG").convert_alpha()

    # Load and scale static images
    grass_image = pygame.transform.scale(pygame.image.load(os.path.join(tile_folder, "grass_middle.png")).convert_alpha(), (TILE_SIZE, TILE_SIZE))
    tree_image = pygame.transform.scale(pygame.image.load(os.path.join(tile_folder, "tree.png")).convert_alpha(), (TILE_SIZE + 5, TILE_SIZE + 5))
    house_image = pygame.transform.scale(pygame.image.load(os.path.join(tile_folder, "house.png")).convert_alpha(), (TILE_SIZE * 2, TILE_SIZE * 2))
    house1_image = pygame.transform.scale(pygame.image.load(os.path.join(tile_folder, "house1.png")).convert_alpha(), (TILE_SIZE * 2, TILE_SIZE * 2))
    flower_positions = [(0, 144), (16, 144)]
    flower_images = [pygame.transform.scale(sheet.subsurface(pygame.Rect(x, y, 16, 16)), (30, 30)) for (x, y) in flower_positions]
    leaf_image = pygame.transform.scale(sheet.subsurface(pygame.Rect(0, 0, 16, 16)), (25, 25))
    log_image_rect = pygame.Rect(4, 110, 24, 24)
    log_image = pygame.transform.scale(sheet.subsurface(log_image_rect), (TILE_SIZE, TILE_SIZE))

    # Load UI icons
    backpack_icon = pygame.transform.scale(pygame.image.load("bag.png").convert_alpha(), (ICON_SIZE, ICON_SIZE))
    crafting_icon = pygame.transform.scale(pygame.image.load("craft.png").convert_alpha(), (ICON_SIZE, ICON_SIZE))
    equipment_icon = pygame.transform.scale(pygame.image.load("equipped.png").convert_alpha(), (ICON_SIZE, ICON_SIZE))

    # Load item images (with fallback surfaces)
    try:
        axe_image = pygame.transform.scale(pygame.image.load("axe.png").convert_alpha(), (TILE_SIZE, TILE_SIZE))
    except pygame.error:
        axe_image = pygame.Surface((TILE_SIZE, TILE_SIZE)); axe_image.fill((255, 0, 0))

    try:
        pickaxe_image = pygame.transform.scale(pygame.image.load("pickaxe.png").convert_alpha(), (TILE_SIZE, TILE_SIZE))
    except pygame.error:
        pickaxe_image = pygame.Surface((TILE_SIZE, TILE_SIZE)); pickaxe_image.fill((100, 100, 100))

    try:
        stone_image = pygame.transform.scale(pygame.image.load("stone.png").convert_alpha(), (TILE_SIZE // 2, TILE_SIZE // 2))
    except pygame.error:
        stone_image = pygame.Surface((TILE_SIZE, TILE_SIZE)); stone_image.fill((150, 150, 150))

    # Define Item objects
    log_item = Item("Log", log_image)
    axe_item = Item("Axe", axe_image, category="Weapon")
    pickaxe_item = Item("Pickaxe", pickaxe_image, category="Weapon")
    stone_item = Item("Stone", stone_image)

    assets = {
        "grass": grass_image,
        "tree": tree_image,
        "house": house_image,
        "house1": house1_image,
        "interiors": [
            pygame.transform.scale(pygame.image.load("indoor2.png").convert_alpha(), (WIDTH, HEIGHT)),
            pygame.transform.scale(pygame.image.load("indoor3.png").convert_alpha(), (WIDTH, HEIGHT))
        ],
        "flowers": flower_images,
        "leaf": leaf_image,
        "font": pygame.font.SysFont(None, 36),
        "small_font": pygame.font.SysFont(None, 24),
        "backpack_icon": backpack_icon,
        "crafting_icon": crafting_icon,
        "equipment_icon": equipment_icon,
        "log_item": log_item,
        "axe_item": axe_item,
        "pickaxe_item": pickaxe_item,
        "stone_item": stone_item,
        "stone_img": stone_image
    }
    return assets

#MAP SWITCHING
def enter_house():
    global current_map, colliders
    current_map = "house1"
    colliders = load_colliders(current_map)
    # safe indoor spawn
    player.x, player.y = 80, 240

def exit_house():
    global current_map, colliders
    current_map = "outdoors"
    colliders = load_colliders(current_map)
    # safe outdoor spawn
    player.x, player.y = 120, 120

# --- Indoor Colliders (adjustable!) ---
# Define each wall or obstacle as (x, y, width, height)
INDOOR_WALLS = [
    (0, 0, WIDTH, 10),              # Top wall
    (0, HEIGHT - 10, WIDTH, 10),  # Bottom wall
    (0, 0, 10, HEIGHT),             # Left wall
    (WIDTH - 10, 0, 10, HEIGHT),  # Right wall
    # Add more walls or furniture here
    (200, 150, 100, 20),           # Example table
    (400, 300, 150, 30)             # Example counter
]

def setup_indoor_colliders():
    global indoor_colliders
    indoor_colliders[:] = [
        pygame.Rect(0, 0, WIDTH, 10),           # top
        pygame.Rect(0, HEIGHT-10, WIDTH, 10),   # bottom
        pygame.Rect(0, 0, 10, HEIGHT),          # left
        pygame.Rect(WIDTH-10, 0, 10, HEIGHT)    # right
    ]


# --- SETUP COLLIDERS AND WORLD ---
def setup_colliders():
    """Generates the world colliders for the current level."""
    global tree_rects, house_list, indoor_colliders, flower_tiles, leaf_tiles, stone_rects
    tree_rects.clear()
    flower_tiles.clear()
    leaf_tiles.clear()
    house_list.clear()
    stone_rects.clear()

    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    pygame.display.set_caption("Indoor/Outdoor Colliders")
    clock = pygame.time.Clock()


    player_world_rect = get_player_world_rect()
    map_cols, map_rows = 50, 50

    for row in range(map_rows):
        for col in range(map_cols):
            x = col * TILE_SIZE
            y = row * TILE_SIZE
            # Borders
            if row < BORDER_THICKNESS or row >= map_rows - BORDER_THICKNESS or col < BORDER_THICKNESS or col >= map_cols - BORDER_THICKNESS:
                tree_rects.append(pygame.Rect(x + 5, y + 5, TILE_SIZE - 10, TILE_SIZE - 10))
            else:
                rnd = random.random()
                if rnd < 0.02:
                    tree_rects.append(pygame.Rect(x + 5, y + 5, TILE_SIZE - 10, TILE_SIZE - 10))
                elif rnd < 0.035:
                    offset = (TILE_SIZE - (TILE_SIZE // 2)) // 2
                    stone_rect = pygame.Rect(x + offset, y + offset, TILE_SIZE // 2, TILE_SIZE // 2)
                    stone_rects.append(stone_rect)
                elif rnd < 0.065:
                    flower_tiles.append((x + 10, y + 10, random.randint(0, 1)))
                elif rnd < 0.185:
                    leaf_tiles.append((x + random.randint(8, 14), y + random.randint(8, 14)))

    # Place two houses near the player's current world position
    house_rect_1 = pygame.Rect(player_world_rect.x + 100, player_world_rect.y, TILE_SIZE * 2, TILE_SIZE * 2)
    house_rect_2 = pygame.Rect(house_rect_1.x + 200, house_rect_1.y, TILE_SIZE * 2, TILE_SIZE * 2)
    tree_rects.extend([house_rect_1, house_rect_2])
    house_list.extend([house_rect_1, house_rect_2])

    indoor_colliders[:] = [
        pygame.Rect(0, 0, WIDTH, 10),        # top wall
        pygame.Rect(0, HEIGHT-10, WIDTH, 10),  # bottom wall
        pygame.Rect(0, 0, 10, HEIGHT),       # left wall
        pygame.Rect(WIDTH-10, 0, 10, HEIGHT)  # right wall
    ]

def give_starting_items(assets):
    """Adds initial items to the inventory."""
    for _ in range(10):
        add_item_to_inventory(assets["log_item"])
    add_item_to_inventory(assets["axe_item"])

# --- INVENTORY/CRAFTING/EQUIPMENT LOGIC ---
def add_item_to_inventory(item_to_add):
    """Adds an item to the first available slot in the inventory (stack up to 20)."""
    for row in range(4):
        for col in range(4):
            slot = inventory[row][col]
            if slot and slot.name == item_to_add.name and slot.count < 20:
                slot.count += 1
                return True

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
    """Unequips the currently held weapon (places back into inventory if possible)."""
    item_to_unequip = equipment_slots.get("weapon")
    if item_to_unequip:
        if add_item_to_inventory(item_to_unequip):
            equipment_slots["weapon"] = None
            print(f"{item_to_unequip.name} unequipped!")
            return True
        else:
            print("Inventory is full, cannot unequip.")
    return False

# --- DRAW FUNCTIONS ---
def draw_world(screen, assets):
    """Draws the outdoor world and its objects."""
    start_col = map_offset_x // TILE_SIZE
    start_row = map_offset_y // TILE_SIZE
    cols_to_draw = (WIDTH // TILE_SIZE) + 3
    rows_to_draw = (HEIGHT // TILE_SIZE) + 3
    tree_size_diff = 5

    for row in range(start_row, start_row + rows_to_draw):
        for col in range(start_col, start_col + cols_to_draw):
            x, y = col * TILE_SIZE, row * TILE_SIZE
            screen.blit(assets["grass"], (x - map_offset_x, y - map_offset_y))

    for tree in tree_rects:
        screen.blit(assets["tree"], (tree.x - map_offset_x - tree_size_diff // 6, tree.y - map_offset_y - tree_size_diff // 6))

    for stone in stone_rects:
        screen.blit(assets["stone_img"], (stone.x - map_offset_x, stone.y - map_offset_y))

    for fx, fy, idx in flower_tiles:
        screen.blit(assets["flowers"][idx], (fx - map_offset_x, fy - map_offset_y))

    for lx, ly in leaf_tiles:
        screen.blit(assets["leaf"], (lx - map_offset_x, ly - map_offset_y))

    if house_list:
        screen.blit(assets["house"], (house_list[0].x - map_offset_x, house_list[0].y - map_offset_y))
        screen.blit(assets["house1"], (house_list[1].x - map_offset_x, house_list[1].y - map_offset_y))

def draw_prompt(screen, font):
    """Draws the 'Press E' prompt when a player is near an interactive object."""
    show_e = False
    player_world_rect = get_player_world_rect()
    # Check houses
    if current_level == "world":
        if check_house_entry(player_world_rect.inflate(20, 20)) is not None:
            show_e = True
        else:
            # Check trees
            for tree in tree_rects:
                if player_world_rect.colliderect(tree.inflate(20, 20)):
                    show_e = True
                    break
            # Check stones
            if not show_e:
                for stone in stone_rects:
                    if player_world_rect.colliderect(stone.inflate(20, 20)):
                        show_e = True
                        break
    else:
        door_zone = pygame.Rect(WIDTH // 2 - 40, HEIGHT - 100, 80, 80)
        # player_pos is screen rect
        if door_zone.colliderect(player_pos.inflate(PLAYER_SIZE * 2, PLAYER_SIZE * 2)):
            show_e = True

    if show_e and not is_chopping and not is_mining:
        # show prompt above player (screen coords)
        text = font.render("Press E", True, (255, 255, 255))
        text_rect = text.get_rect(centerx=player_pos.centerx, centery=player_pos.y - 30)
        screen.blit(text, text_rect)

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
    """Draws the crafting GUI with buttons for different items."""
    global axe_button_rect, pickaxe_button_rect

    panel_rect = pygame.Rect(CRAFTING_X, CRAFTING_Y, CRAFTING_PANEL_WIDTH, CRAFTING_PANEL_HEIGHT)
    pygame.draw.rect(screen, (101, 67, 33), panel_rect)
    header_rect = pygame.Rect(CRAFTING_X, CRAFTING_Y, CRAFTING_PANEL_WIDTH, 40)
    pygame.draw.rect(screen, (50, 33, 16), header_rect)
    header_text = assets["small_font"].render("Crafting", True, (255, 255, 255))
    screen.blit(header_text, header_text.get_rect(centerx=header_rect.centerx, top=CRAFTING_Y + 10))

    button_width, button_height, gap = 180, 50, 20
    log_count = get_item_count("Log")

    # Axe Button
    axe_button_rect = pygame.Rect(CRAFTING_X + gap, CRAFTING_Y + header_rect.height + gap, button_width, button_height)
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
    """Handles player movement input and updates direction (returns dx, dy for world movement)."""
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
    """Checks for collision with world objects; new_world_rect must be in world coords."""
    if current_level == "world":
        # collide with trees/houses
        if any(new_world_rect.colliderect(r) for r in tree_rects):
            return True
        # collide with stones
        if any(new_world_rect.colliderect(r) for r in stone_rects):
            return True
        return False
    else:
        return any(new_world_rect.colliderect(r) for r in indoor_colliders)

def check_house_entry(world_rect):
    """Checks if the player's world rect is near a house door (use world rect)."""
    for i, h in enumerate(house_list):
        if world_rect.colliderect(h.inflate(20, 20)):
            return i
    return None

# --- HELPERS FOR COORDINATES ---
def get_player_world_rect():
    """Return the player's rectangle in world coordinates."""
    # This function should be fixed to handle both indoor/outdoor states.
    # The existing logic is correct for the 'world' level.
    # We will use it for collision checks with world objects.
    return player_pos.move(map_offset_x, map_offset_y)

def world_to_screen_rect(world_rect):
    """Convert a world rect to screen coordinates (pygame.Rect)."""
    return pygame.Rect(world_rect.x - map_offset_x, world_rect.y - map_offset_y, world_rect.width, world_rect.height)

# --- SETUP COLLIDERS AND WORLD ---
def setup_colliders():
    """Generates the world colliders for the current level."""
    global tree_rects, house_list, indoor_colliders, flower_tiles, leaf_tiles, stone_rects
    tree_rects.clear()
    flower_tiles.clear()
    leaf_tiles.clear()
    house_list.clear()
    stone_rects.clear()

    # DO NOT put pygame.init() inside here, it's already done in the main init() function
    # The redundant screen and clock initialization has been removed.

    player_world_rect = get_player_world_rect()
    map_cols, map_rows = 50, 50

    for row in range(map_rows):
        for col in range(map_cols):
            x = col * TILE_SIZE
            y = row * TILE_SIZE
            # Borders
            if row < BORDER_THICKNESS or row >= map_rows - BORDER_THICKNESS or col < BORDER_THICKNESS or col >= map_cols - BORDER_THICKNESS:
                tree_rects.append(pygame.Rect(x + 5, y + 5, TILE_SIZE - 10, TILE_SIZE - 10))
            else:
                rnd = random.random()
                if rnd < 0.02:
                    tree_rects.append(pygame.Rect(x + 5, y + 5, TILE_SIZE - 10, TILE_SIZE - 10))
                elif rnd < 0.035:
                    offset = (TILE_SIZE - (TILE_SIZE // 2)) // 2
                    stone_rect = pygame.Rect(x + offset, y + offset, TILE_SIZE // 2, TILE_SIZE // 2)
                    stone_rects.append(stone_rect)
                elif rnd < 0.065:
                    flower_tiles.append((x + 10, y + 10, random.randint(0, 1)))
                elif rnd < 0.185:
                    leaf_tiles.append((x + random.randint(8, 14), y + random.randint(8, 14)))

    # Place two houses near the player's current world position
    house_rect_1 = pygame.Rect(player_world_rect.x + 100, player_world_rect.y, TILE_SIZE * 2, TILE_SIZE * 2)
    house_rect_2 = pygame.Rect(house_rect_1.x + 200, house_rect_1.y, TILE_SIZE * 2, TILE_SIZE * 2)
    tree_rects.extend([house_rect_1, house_rect_2])
    house_list.extend([house_rect_1, house_rect_2])

    indoor_colliders[:] = [
        pygame.Rect(0, 0, WIDTH, 10),     # top wall
        pygame.Rect(0, HEIGHT-10, WIDTH, 10), # bottom wall
        pygame.Rect(0, 0, 10, HEIGHT),       # left wall
        pygame.Rect(WIDTH-10, 0, 10, HEIGHT)  # right wall
    ]

# The rest of the functions are unchanged from the previous version,
# so they are not included in this code block for brevity.

# --- MAIN GAME LOGIC ---
def main():
    """Main game loop."""
    global map_offset_x, map_offset_y, current_level, current_house_index
    global player_frame_index, player_frame_timer, current_direction, last_direction
    global show_inventory, show_crafting, show_equipment
    global is_chopping, chopping_timer, chopping_target_tree, is_swinging
    global is_crafting, crafting_timer, item_to_craft
    global is_mining, mining_timer, mining_target_stone
    global player_pos, indoor_colliders, PLAYER_SIZE

    # --- Initialize ---
    screen, clock = init()
    assets = load_assets()
    player_frames = load_player_frames()
    chopping_frames = load_chopping_frames()
    setup_colliders()
    give_starting_items(assets)
    HOUSE_SPAWN_OFFSET_X = -73
    HOUSE_SPAWN_OFFSET_Y = -52  

    # Store a larger player size for indoors
    PLAYER_SIZE_INDOOR = 80
    
    while True:
        dt = clock.tick(60)
        current_time = pygame.time.get_ticks()

        # --- UI Hover State ---
        is_hovering = None
        mouse_pos = pygame.mouse.get_pos()
        if show_crafting:
            if axe_button_rect and axe_button_rect.collidepoint(mouse_pos):
                is_hovering = "axe"
            elif pickaxe_button_rect and pickaxe_button_rect.collidepoint(mouse_pos):
                is_hovering = "pickaxe"

        # --- Event Handling ---
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
    
                # --- Interact with World ---
                player_world_rect = get_player_world_rect()
                if event.key == pygame.K_e:
                    if current_level == "world":
                        # --- PRIORITY 1: Enter House ---
                        house_index = check_house_entry(player_world_rect)
                        if house_index is not None:
                            current_level = "house"
                            current_house_index = house_index
                            # Resize player_pos rect and place it in the center of the screen
                            player_pos.size = (PLAYER_SIZE_INDOOR, PLAYER_SIZE_INDOOR)
                            player_pos.center = (WIDTH // 2, HEIGHT // 2)
                            setup_indoor_colliders()
                        else:
                            # --- PRIORITY 2: Chop Trees ---
                            if equipment_slots["weapon"] and equipment_slots["weapon"].name == "Axe":
                                for tree in list(tree_rects):
                                    if player_world_rect.colliderect(tree.inflate(20, 20)):
                                        is_chopping = True
                                        chopping_target_tree = tree
                                        chopping_timer = 0
                                        current_direction = "idle"
                                        break
                            # --- PRIORITY 3: Mine Stones ---
                            elif equipment_slots["weapon"] and equipment_slots["weapon"].name == "Pickaxe":
                                for stone in list(stone_rects):
                                    if player_world_rect.colliderect(stone.inflate(20, 20)):
                                        is_mining = True
                                        mining_target_stone = stone
                                        mining_timer = 0
                                        current_direction = "idle"
                                        break
                            else:
                                print("You need an Axe to chop trees or a Pickaxe to mine stone!")
                    else:
                        # Inside house -> Exit
                        door_zone = pygame.Rect(WIDTH // 2 - 40, HEIGHT - 100, 80, 80)
                        if door_zone.colliderect(player_pos.inflate(PLAYER_SIZE_INDOOR * 2, PLAYER_SIZE_INDOOR * 2)):
                            # Switch back to world
                            current_level = "world"
                            player_pos.size = (PLAYER_SIZE, PLAYER_SIZE)

                            # Offsets to spawn slightly left and higher in front of the house
                            HOUSE_SPAWN_OFFSET_X = -20
                            HOUSE_SPAWN_OFFSET_Y = 20

                            # Get the house rect in world coordinates
                            exit_rect = house_list[current_house_index]

                            # Compute the desired player world position
                            player_world_x = exit_rect.centerx + HOUSE_SPAWN_OFFSET_X
                            player_world_y = exit_rect.bottom + HOUSE_SPAWN_OFFSET_Y

                            # Update map offsets so player appears centered on screen
                            map_offset_x = player_world_x - WIDTH // 2
                            map_offset_y = player_world_y - HEIGHT // 2

                            # Keep the player rect centered on the screen
                            player_pos.center = (WIDTH // 2, HEIGHT // 2)

                            # Clear current house index
                            current_house_index = None


    
            # --- Mouse Button Handling (Crafting / Equipment / Inventory) ---
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Crafting
                if show_crafting and not is_crafting:
                    if axe_button_rect and axe_button_rect.collidepoint(event.pos):
                        if get_item_count("Log") >= 5:
                            is_crafting = True
                            crafting_timer = 0
                            item_to_craft = assets["axe_item"]
                            remove_item_from_inventory("Log", 5)
                            print(f"Crafting an {item_to_craft.name}...")
                        else:
                            print("Not enough logs!")
                    elif pickaxe_button_rect and pickaxe_button_rect.collidepoint(event.pos):
                        if get_item_count("Log") >= 10:
                            is_crafting = True
                            crafting_timer = 0
                            item_to_craft = assets["pickaxe_item"]
                            remove_item_from_inventory("Log", 10)
                            print(f"Crafting a {item_to_craft.name}...")
                        else:
                            print("Not enough logs!")
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

        # --- Game State Updates ---
        # Crafting
        if is_crafting:
            crafting_timer += dt
            if crafting_timer >= CRAFTING_TIME_MS:
                if add_item_to_inventory(item_to_craft):
                    print(f"Crafting complete! {item_to_craft.name} added to inventory.")
                else:
                    print(f"Crafting failed: Inventory is full. {item_to_craft.name} materials refunded.")
                    add_item_to_inventory(assets["log_item"], item_to_craft.craft_cost)  # Assuming a craft_cost attribute
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
                    # Fix: Use a tuple of the Rect's values as the dictionary key
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
                    # Fix: Use a tuple of the Rect's values as the dictionary key
                    chopped_stones[(mining_target_stone.x, mining_target_stone.y, mining_target_stone.width, mining_target_stone.height)] = current_time
                    add_item_to_inventory(assets["stone_item"])
                    print("Mined a stone!")
                is_mining = False
                is_swinging = False
                mining_timer = 0
                mining_target_stone = None
                current_direction = "idle"
       
        #RESPAWN LOGIC
        # Fix: Convert keys back to Rects for collision checking
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

        # --- Player Movement ---
        if not (show_inventory or show_crafting or show_equipment or is_chopping or is_mining):
            keys = pygame.key.get_pressed()
            dx, dy = handle_movement(keys)
            
            if current_level == "world":
                new_player_world_rect = get_player_world_rect().move(dx, dy)
                if not handle_collision(new_player_world_rect):
                    map_offset_x += dx
                    map_offset_y += dy
            else: # current_level == "house"
                new_player_pos = player_pos.move(dx, dy)
                if not handle_collision(new_player_pos): # check collision using screen coordinates
                    player_pos = new_player_pos

        # Animation state update
        if not is_chopping and not is_mining:
            player_frame_timer += dt
            if current_direction == "idle":
                player_frame_index = 0
            elif player_frame_timer > player_frame_delay:
                player_frame_index = (player_frame_index + 1) % len(player_frames[current_direction])
                player_frame_timer = 0
                
        # --- Drawing ---
        screen.fill((0, 0, 0))
        if current_level == "world":
            draw_world(screen, assets)
        else:
            screen.blit(assets["interiors"][current_house_index], (0, 0))

        # Determine the current size of the player for drawing and scaling
        player_size_current = player_pos.width # Use the Rect's current size

        # Draw player
        if is_chopping or is_mining:
            # Scale chopping frames based on current player size
            scaled_frame = pygame.transform.scale(chopping_frames[last_direction][player_frame_index], (player_size_current, player_size_current))
            screen.blit(scaled_frame, player_pos)
        else:
            # Scale regular frames based on current player size
            frame_set = player_frames.get(current_direction, player_frames["idle"])
            scaled_frame = pygame.transform.scale(frame_set[player_frame_index], (player_size_current, player_size_current))
            screen.blit(scaled_frame, player_pos)

        draw_hud(screen, assets)
        draw_prompt(screen, assets["small_font"])

        # Draw UI panels
        if show_inventory:
            draw_inventory(screen, assets)
        if show_crafting:
            draw_crafting_panel(screen, assets, is_hovering)
        if show_equipment:
            draw_equipment_panel(screen, assets)

        pygame.display.flip()

if __name__ == '__main__':
    main()