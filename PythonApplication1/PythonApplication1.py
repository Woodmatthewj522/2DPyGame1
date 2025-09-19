# -*- coding: utf-8 -*-

import pygame
import sys
import os
import random

# --- CONSTANTS ---
WIDTH, HEIGHT = 800, 600
TILE_SIZE = 50
PLAYER_SIZE = 40
PLAYER_SPEED = 5
COLS = 4
BORDER_THICKNESS = 6
CRAFTING_TIME_MS = 3000  # 3 seconds to craft an axe
ICON_SIZE = 30 # New constant for consistent icon size

# --- ITEM CLASS ---
class Item:
    def __init__(self, name, image, count=1, category=None): # Add category to init
        self.name = name
        self.image = image
        self.count = count
        self.category = category # Store the category

# --- GLOBALS ---
player_pos = pygame.Rect(WIDTH // 2, HEIGHT // 2, PLAYER_SIZE, PLAYER_SIZE)
player_frame_index = 0
player_frame_timer = 0
player_frame_delay = 120
current_direction = "idle"
map_offset_x = map_offset_y = 0
current_level = "world"
current_house_index = None
last_direction = "down"
is_swinging = False
swing_delay = 150
idle_chop_delay = 500
TREE_RESPAWN_TIME = 120000

# Inventory GUI constants
INVENTORY_SLOT_SIZE = 40
INVENTORY_GAP = 5
INVENTORY_WIDTH = 4 * INVENTORY_SLOT_SIZE + 5 * INVENTORY_GAP
INVENTORY_HEIGHT = 4 * INVENTORY_SLOT_SIZE + 5 * INVENTORY_GAP
INVENTORY_X = (WIDTH - INVENTORY_WIDTH) // 2
INVENTORY_Y = (HEIGHT - INVENTORY_HEIGHT) // 2

# Crafting GUI constants
CRAFTING_PANEL_WIDTH = 420
CRAFTING_PANEL_HEIGHT = 150
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

# New globals for chopping animation and timer
is_chopping = False
chopping_timer = 0
chopping_duration = 3000
chopping_frame_index = 0
chopping_frames = []
chopped_tree_timers = []
TreeRespawnTime = 1500

# Game state lists
inventory = [[None for _ in range(4)] for _ in range(4)]
equipment_slots = {
    "left_slots": [None] * EQUIPMENT_ROWS,
    "right_slots": [None] * EQUIPMENT_ROWS,
    "weapon": None,
}
tree_rects = []
house_list = []
indoor_rects = []
door_zone = pygame.Rect(WIDTH//2 - 40, HEIGHT - 100, 80, 80)
flower_tiles = []
leaf_tiles = []

# --- INIT ---
def init():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Not Pokemon")
    return screen, pygame.time.Clock()

# --- LOAD ASSETS ---
def load_player_frames():
    sheet = pygame.image.load("Player.PNG").convert_alpha()
    frames = {}
    right = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col * 32, 32, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(COLS)]
    frames["right"] = right
    frames["left"] = [pygame.transform.flip(frame, True, False) for frame in right]
    frames["up"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col * 32, 64, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(COLS)]
    frames["down"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col * 32, 96, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(COLS)]
    frames["idle"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(0, 0, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE))]
    return frames

def load_chopping_frames():
    sheet = pygame.image.load("Player.PNG").convert_alpha()
    chopping_frames = {}
    chopping_frames["right"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col * 32, 224, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(4)]
    chopping_frames["left"] = [pygame.transform.flip(frame, True, False) for frame in chopping_frames["right"]]
    chopping_frames["up"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col * 32, 255, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(4)]
    chopping_frames["down"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col * 32, 190, 32, 32)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(4)]
    return chopping_frames

def load_assets():
    tile_folder = "Tiles"
    sheet = pygame.image.load("OutdoorStuff.PNG").convert_alpha()
    flower_positions = [(0, 144), (16, 144)]
    flowers = [pygame.transform.scale(sheet.subsurface(pygame.Rect(x, y, 16, 16)), (30, 30)) for (x, y) in flower_positions]
    leaf = pygame.transform.scale(sheet.subsurface(pygame.Rect(0, 0, 16, 16)), (25, 25))
    log_rect = pygame.Rect(4, 110, 24, 24)
    log_image = pygame.transform.scale(sheet.subsurface(log_rect), (TILE_SIZE, TILE_SIZE))
    
    # Scale icons using the new ICON_SIZE constant
    backpack_icon = pygame.transform.scale(pygame.image.load("bag.png").convert_alpha(), (ICON_SIZE, ICON_SIZE))
    crafting_icon = pygame.transform.scale(pygame.image.load("craft.png").convert_alpha(), (ICON_SIZE, ICON_SIZE))
    equipment_icon = pygame.transform.scale(pygame.image.load("equipped.png").convert_alpha(), (ICON_SIZE, ICON_SIZE))
    
    try:
        axe_image = pygame.transform.scale(pygame.image.load("axe.png").convert_alpha(), (TILE_SIZE, TILE_SIZE))
    except pygame.error:
        print("Could not find 'axe.png'. Using a placeholder rect.")
        axe_image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        axe_image.fill((255, 0, 0))

    assets = {
        "grass": pygame.transform.scale(pygame.image.load(os.path.join(tile_folder, "grass_middle.png")).convert_alpha(), (TILE_SIZE, TILE_SIZE)),
        "tree": pygame.transform.scale(pygame.image.load(os.path.join(tile_folder, "tree.png")).convert_alpha(), (TILE_SIZE, TILE_SIZE)),
        "house": pygame.transform.scale(pygame.image.load(os.path.join(tile_folder, "house.png")).convert_alpha(), (TILE_SIZE*2, TILE_SIZE*2)),
        "house1": pygame.transform.scale(pygame.image.load(os.path.join(tile_folder, "house1.png")).convert_alpha(), (TILE_SIZE*2, TILE_SIZE*2)),
        "interiors": [
            pygame.transform.scale(pygame.image.load("indoor2.png").convert_alpha(), (WIDTH, HEIGHT)),
            pygame.transform.scale(pygame.image.load("indoor3.png").convert_alpha(), (WIDTH, HEIGHT))
        ],
        "flowers": flowers,
        "leaf": leaf,
        "font": pygame.font.SysFont(None, 36),
        "small_font": pygame.font.SysFont(None, 24),
        "backpack_icon": backpack_icon,
        "crafting_icon": crafting_icon,
        "equipment_icon": equipment_icon, 
        "log": Item("Log", log_image),
        "axe": Item("Axe", axe_image, category="Weapon")
    }
    return assets

# --- COLLIDERS ---
def setup_colliders():
    global tree_rects, house_list, indoor_rects, flower_tiles, leaf_tiles
    tree_rects.clear()
    flower_tiles.clear()
    leaf_tiles.clear()
    house_list.clear()

    map_cols, map_rows = 50, 50
    for row in range(map_rows):
        for col in range(map_cols):
            x = col * TILE_SIZE
            y = row * TILE_SIZE
            if row < BORDER_THICKNESS or row >= map_rows - BORDER_THICKNESS or col < BORDER_THICKNESS or col >= map_cols - BORDER_THICKNESS:
                tree_rects.append(pygame.Rect(x+5, y+5, TILE_SIZE-10, TILE_SIZE-10))
            elif random.random() < 0.02:
                tree_rects.append(pygame.Rect(x+5, y+5, TILE_SIZE-10, TILE_SIZE-10))
            elif random.random() < 0.03:
                flower_tiles.append((x+10, y+10, random.randint(0, 1)))
            elif random.random() < 0.12:
                leaf_tiles.append((x+random.randint(8,14), y+random.randint(8,14)))

    house_rect = pygame.Rect(player_pos.x + 100, player_pos.y, TILE_SIZE*2, TILE_SIZE*2)
    house1_rect = pygame.Rect(house_rect.x + 200, house_rect.y, TILE_SIZE*2, TILE_SIZE*2)
    tree_rects.extend([house_rect, house1_rect])
    house_list.extend([house_rect, house1_rect])

    indoor_rects[:] = [
        pygame.Rect(0, 80, WIDTH, 2),
        pygame.Rect(0, HEIGHT-70, WIDTH, 2),
        pygame.Rect(-40, 0, 1, HEIGHT),
        pygame.Rect(WIDTH-60, 0, 2, HEIGHT)
    ]

def give_starting_items(assets):
    for _ in range(5):
        add_item_to_inventory(assets["log"])
    add_item_to_inventory(assets["axe"])


# --- MOVEMENT / COLLISION ---
def handle_movement(keys):
    global current_direction
    dx = dy = 0
    if keys[pygame.K_a]: dx=-PLAYER_SPEED; current_direction="left"
    if keys[pygame.K_d]: dx=PLAYER_SPEED; current_direction="right"
    if keys[pygame.K_w]: dy=-PLAYER_SPEED; current_direction="up"
    if keys[pygame.K_s]: dy=PLAYER_SPEED; current_direction="down"
    if dx==0 and dy==0: current_direction="idle"
    return dx, dy

def handle_collision(new_rect):
    if current_level == "world":
        return any(new_rect.colliderect(r) for r in tree_rects)
    else:
        scaled = new_rect.inflate(PLAYER_SIZE*2, PLAYER_SIZE*2)
        return any(scaled.colliderect(r) for r in indoor_rects)

def check_house_entry(rect):
    for i, h in enumerate(house_list):
        if rect.colliderect(h.inflate(20,20)):
            return i
    return None

# --- INVENTORY FUNCTIONS ---
def add_item_to_inventory(item_to_add):
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
    count = 0
    for row in range(4):
        for col in range(4):
            slot = inventory[row][col]
            if slot and slot.name == item_name:
                count += slot.count
    return count

def remove_item_from_inventory(item_name, quantity):
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
    if item_to_equip.category == "Weapon":
        if equipment_slots["weapon"] is None:
            equipment_slots["weapon"] = item_to_equip
            print(f"{item_to_equip.name} equipped as a weapon!")
            return True
        else:
            print("Weapon slot is already taken.")
    return False

def unequip_item(slot_name):
    if slot_name == "weapon":
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
    start_col = map_offset_x // TILE_SIZE
    start_row = map_offset_y // TILE_SIZE
    cols_to_draw = (WIDTH // TILE_SIZE) + 3
    rows_to_draw = (HEIGHT // TILE_SIZE) + 3
    for row in range(start_row, start_row+rows_to_draw):
        for col in range(start_col, start_col+cols_to_draw):
            x = col*TILE_SIZE
            y = row*TILE_SIZE
            sx = x - map_offset_x
            sy = y - map_offset_y
            screen.blit(assets["grass"], (sx, sy))
    for tree in tree_rects:
        sx = tree.x - map_offset_x
        sy = tree.y - map_offset_y
        screen.blit(assets["tree"], (sx, sy))
    for fx, fy, idx in flower_tiles:
        screen.blit(assets["flowers"][idx], (fx-map_offset_x, fy-map_offset_y))
    for lx, ly in leaf_tiles:
        screen.blit(assets["leaf"], (lx-map_offset_x, ly-map_offset_y))
    screen.blit(assets["house"], (house_list[0].x-map_offset_x, house_list[0].y-map_offset_y))
    screen.blit(assets["house1"], (house_list[1].x-map_offset_x, house_list[1].y-map_offset_y))

def draw_prompt(screen, font):
    show_e = False
    if current_level == "world":
        if check_house_entry(player_pos) is not None:
            show_e = True
        else:
            for tree in tree_rects:
                if player_pos.colliderect(tree.inflate(20, 20)):
                    show_e = True
                    break
    elif current_level != "world" and door_zone.colliderect(player_pos.inflate(PLAYER_SIZE*2, PLAYER_SIZE*2)):
        show_e = True
        
    if show_e and not is_chopping:
        text = font.render("Press E", True, (255,255,255))
        screen.blit(text, (player_pos.x - map_offset_x + 10, player_pos.y - map_offset_y - 40))

def draw_inventory(screen, assets):
    pygame.draw.rect(screen, (101, 67, 33), (INVENTORY_X, INVENTORY_Y, INVENTORY_WIDTH, INVENTORY_HEIGHT + 50))
    label_bar_rect = pygame.Rect(INVENTORY_X, INVENTORY_Y, INVENTORY_WIDTH, 40)
    pygame.draw.rect(screen, (50, 33, 16), label_bar_rect)
    label_text = assets["small_font"].render("Backpack", True, (255, 255, 255))
    label_rect = label_text.get_rect(centerx=INVENTORY_X + INVENTORY_WIDTH // 2, top=INVENTORY_Y + 10)
    screen.blit(label_text, label_rect)

    for row in range(4):
        for col in range(4):
            slot_x = INVENTORY_X + INVENTORY_GAP + col * (INVENTORY_SLOT_SIZE + INVENTORY_GAP)
            slot_y = INVENTORY_Y + INVENTORY_GAP + row * (INVENTORY_SLOT_SIZE + INVENTORY_GAP) + 40
            slot_rect = pygame.Rect(slot_x, slot_y, INVENTORY_SLOT_SIZE, INVENTORY_SLOT_SIZE)
            pygame.draw.rect(screen, (70, 70, 70), slot_rect)
            pygame.draw.rect(screen, (150, 150, 150), slot_rect, 2)
            item = inventory[row][col]
            if item:
                item_image = pygame.transform.scale(item.image, (INVENTORY_SLOT_SIZE, INVENTORY_SLOT_SIZE))
                screen.blit(item_image, slot_rect)
                if item.count > 1:
                    count_text = assets["small_font"].render(str(item.count), True, (255, 255, 255))
                    screen.blit(count_text, count_text.get_rect(bottomright=slot_rect.bottomright))

def draw_crafting_panel(screen, assets, is_hovering):
    """Draws the crafting GUI with buttons for different items."""
    global axe_button_rect, pickaxe_button_rect, other_button_rect

    panel_rect = pygame.Rect(CRAFTING_X, CRAFTING_Y, CRAFTING_PANEL_WIDTH, CRAFTING_PANEL_HEIGHT)
    pygame.draw.rect(screen, (101, 67, 33), panel_rect)
    
    header_rect = pygame.Rect(CRAFTING_X, CRAFTING_Y, CRAFTING_PANEL_WIDTH, 40)
    pygame.draw.rect(screen, (50, 33, 16), header_rect)
    label_text = assets["small_font"].render("Crafting", True, (255, 255, 255))
    label_rect = label_text.get_rect(centerx=CRAFTING_X + CRAFTING_PANEL_WIDTH // 2, top=CRAFTING_Y + 10)
    screen.blit(label_text, label_rect)

    button_width = 180
    button_height = 50
    gap = 20
    
    global axe_button_rect, other_button_rect
    
    # Axe Button
    axe_button_x = CRAFTING_X + gap
    axe_button_y = CRAFTING_Y + header_rect.height + gap
    axe_button_rect = pygame.Rect(axe_button_x, axe_button_y, button_width, button_height)
    
    log_count = get_item_count("Log")
    
    # Determine the button color
    if is_crafting:
        button_color = (120, 120, 120)
    elif is_crafting_clicked and is_hovering == "axe":
        button_color = (40, 40, 40)  # Darken on click
    elif log_count >= 5:
        if is_hovering == "axe":
            button_color = (0, 100, 0) # Dark green on hover
        else:
            button_color = (0, 150, 0) # Normal green
    else:
        if is_hovering == "axe":
            button_color = (50, 50, 50) # Dark gray on hover
        else:
            button_color = (70, 70, 70) # Normal gray
        
    pygame.draw.rect(screen, button_color, axe_button_rect)
    pygame.draw.rect(screen, (150, 150, 150), axe_button_rect, 2)
    
    # Display the logs you have vs. what's required ONLY ON HOVER or while crafting
    if is_crafting:
        progress = (crafting_timer / CRAFTING_TIME_MS) * 100
        axe_text = assets["small_font"].render(f"Crafting... {int(progress)}%", True, (255, 255, 255))
    elif is_hovering == "axe":
        axe_text = assets["small_font"].render(f"Axe: {log_count}/5 Logs", True, (255, 255, 255))
    else:
        axe_text = assets["small_font"].render("Craft Axe", True, (255, 255, 255))
        
    axe_text_rect = axe_text.get_rect(center=axe_button_rect.center)
    screen.blit(axe_text, axe_text_rect)
    
    # Other Button
    other_button_x = axe_button_x + button_width + gap
    other_button_y = CRAFTING_Y + header_rect.height + gap
    other_button_rect = pygame.Rect(other_button_x, other_button_y, button_width, button_height)

    if is_hovering == "other":
        button_color = (50, 50, 50) # Dark gray on hover
    else:
        button_color = (70, 70, 70) # Normal gray

    pygame.draw.rect(screen, button_color, other_button_rect)
    pygame.draw.rect(screen, (150, 150, 150), other_button_rect, 2)
    
    if is_hovering == "other":
        other_text = assets["small_font"].render("Other Item", True, (255, 255, 255))
    else:
        other_text = assets["small_font"].render("Craft Other", True, (255, 255, 255))
        
    other_text_rect = other_text.get_rect(center=other_button_rect.center)
    screen.blit(other_text, other_text_rect)

def draw_equipment_panel(screen, assets):
    panel_rect = pygame.Rect(EQUIPMENT_X, EQUIPMENT_Y, EQUIPMENT_PANEL_WIDTH, EQUIPMENT_PANEL_HEIGHT)
    pygame.draw.rect(screen, (101, 67, 33), panel_rect)
    header_rect = pygame.Rect(EQUIPMENT_X, EQUIPMENT_Y, EQUIPMENT_PANEL_WIDTH, 40)
    pygame.draw.rect(screen, (50, 33, 16), header_rect)
    label_text = assets["small_font"].render("Equipment", True, (255, 255, 255))
    label_rect = label_text.get_rect(centerx=EQUIPMENT_X + EQUIPMENT_PANEL_WIDTH // 2, top=EQUIPMENT_Y + 10)
    screen.blit(label_text, label_rect)
    
    # Draw weapon slot on the bottom-left
    weapon_slot_x = EQUIPMENT_X + EQUIPMENT_GAP
    weapon_slot_y = EQUIPMENT_Y + 40 + EQUIPMENT_GAP + (EQUIPMENT_ROWS-1) * (EQUIPMENT_SLOT_SIZE + EQUIPMENT_GAP)
    weapon_slot_rect = pygame.Rect(weapon_slot_x, weapon_slot_y, EQUIPMENT_SLOT_SIZE, EQUIPMENT_SLOT_SIZE)
    pygame.draw.rect(screen, (70, 70, 70), weapon_slot_rect)
    pygame.draw.rect(screen, (150, 150, 150), weapon_slot_rect, 2)
    
    # Draw equipped weapon if it exists
    equipped_weapon = equipment_slots.get("weapon")
    if equipped_weapon:
        item_image = pygame.transform.scale(equipped_weapon.image, (EQUIPMENT_SLOT_SIZE, EQUIPMENT_SLOT_SIZE))
        screen.blit(item_image, weapon_slot_rect)

    # Draw placeholder slots on the left and right (excluding the weapon slot)
    for row in range(EQUIPMENT_ROWS):
        # Left side slots
        if row != EQUIPMENT_ROWS - 1: # Skip the bottom-left slot
            slot_x_left = EQUIPMENT_X + EQUIPMENT_GAP
            slot_y_left = EQUIPMENT_Y + 40 + EQUIPMENT_GAP + row * (EQUIPMENT_SLOT_SIZE + EQUIPMENT_GAP)
            slot_rect_left = pygame.Rect(slot_x_left, slot_y_left, EQUIPMENT_SLOT_SIZE, EQUIPMENT_SLOT_SIZE)
            pygame.draw.rect(screen, (70, 70, 70), slot_rect_left)
            pygame.draw.rect(screen, (150, 150, 150), slot_rect_left, 2)
        
        # Right side slots
        slot_x_right = EQUIPMENT_X + EQUIPMENT_PANEL_WIDTH - EQUIPMENT_GAP - EQUIPMENT_SLOT_SIZE
        slot_y_right = EQUIPMENT_Y + 40 + EQUIPMENT_GAP + row * (EQUIPMENT_SLOT_SIZE + EQUIPMENT_GAP)
        slot_rect_right = pygame.Rect(slot_x_right, slot_y_right, EQUIPMENT_SLOT_SIZE, EQUIPMENT_SLOT_SIZE)
        pygame.draw.rect(screen, (70, 70, 70), slot_rect_right)
        pygame.draw.rect(screen, (150, 150, 150), slot_rect_right, 2)
    
def draw(screen, assets, frames, current_frame, is_hovering):
    screen.fill((0,0,0))
    if current_level == "world":
        draw_world(screen, assets)
    else:
        screen.blit(assets["interiors"][current_house_index], (0,0))

    screen.blit(current_frame, (player_pos.x - map_offset_x, player_pos.y - map_offset_y))
    
    if is_chopping:
        progress = (chopping_timer / chopping_duration) * 100
        progress_text = assets["small_font"].render(f"Chopping: {int(progress)}%", True, (255, 255, 255))
        screen.blit(progress_text, (player_pos.x - map_offset_x - 10, player_pos.y - map_offset_y - 60))
        
    draw_prompt(screen, assets["font"])
    
    draw_inventory_icon(screen, assets)
    draw_crafting_icon(screen, assets)
    draw_equipment_icon(screen, assets)

    if show_inventory:
        draw_inventory(screen, assets)
    
    if show_crafting:
        draw_crafting_panel(screen, assets, is_hovering)

    if show_equipment:
        draw_equipment_panel(screen, assets)


# --- MAIN LOOP ---
def main():
    global player_pos, player_frame_index, player_frame_timer, map_offset_x, map_offset_y
    global current_level, current_house_index, show_inventory, show_crafting, show_equipment
    global is_chopping, chopping_timer, chopping_frame_index, player_frame_delay
    global current_direction, chopped_tree_timers, last_direction
    global is_swinging, swing_delay, idle_chop_delay
    global axe_button_rect, other_button_rect
    global is_crafting_clicked, click_timer
    global is_crafting, crafting_timer

    screen, clock = init()
    assets = load_assets()
    frames = load_player_frames()
    chopping_frames = load_chopping_frames()
    setup_colliders()
    
    give_starting_items(assets)

    chopping_target_tree = None

    while True:
        dt = clock.tick(60)
        current_time = pygame.time.get_ticks()

        is_hovering = None
        if show_crafting:
            mouse_pos = pygame.mouse.get_pos()
            if axe_button_rect.collidepoint(mouse_pos):
                is_hovering = "axe"
            elif other_button_rect.collidepoint(mouse_pos):
                is_hovering = "other"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_i:
                    show_inventory = not show_inventory
                    show_crafting = False
                    show_equipment = False
                elif event.key == pygame.K_c:
                    show_crafting = not show_crafting
                    show_inventory = False
                    show_equipment = False
                elif event.key == pygame.K_r:
                    if not is_chopping and not is_crafting:
                        show_equipment = not show_equipment
                        show_inventory = False
                        show_crafting = False
            
                if event.key == pygame.K_e:
                    if not show_inventory and not show_crafting and not show_equipment:
                        if current_level == "world":
                            house_index = check_house_entry(player_pos)
                            if house_index is not None:
                                current_level = "house"
                                current_house_index = house_index
                                player_pos.x = WIDTH // 2
                                player_pos.y = HEIGHT // 2
                            else:
                                for tree in tree_rects:
                                    if player_pos.colliderect(tree.inflate(20, 20)):
                                        chopping_target_tree = tree
                                        is_chopping = True
                                        chopping_timer = 0
                                        chopping_frame_index = 0
                                        if current_direction != "idle":
                                            last_direction = current_direction
                                        current_direction = "idle"
                                        is_swinging = False
                                        player_frame_timer = 0
                                        break
                        
                        elif current_level == "house" and door_zone.colliderect(player_pos.inflate(PLAYER_SIZE*2, PLAYER_SIZE*2)):
                            current_level = "world"
                            exit_rect = house_list[current_house_index]
                            player_pos.x = exit_rect.x + exit_rect.width + 10
                            player_pos.y = exit_rect.y
                            current_house_index = None

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if show_crafting and not is_crafting:
                    if axe_button_rect.collidepoint(event.pos):
                        log_count = get_item_count("Log")
                        if log_count >= 5:
                            print("Starting to craft an Axe...")
                            is_crafting = True
                            crafting_timer = 0
                            is_crafting_clicked = True
                            click_timer = pygame.time.get_ticks()
                            remove_item_from_inventory("Log", 5)
                        else:
                            print("Not enough logs!")
                    
                    if other_button_rect.collidepoint(event.pos):
                        print("Other button clicked!")
                
                if show_inventory:
                    mouse_x, mouse_y = event.pos
                    for row in range(4):
                        for col in range(4):
                            slot_x = INVENTORY_X + INVENTORY_GAP + col * (INVENTORY_SLOT_SIZE + INVENTORY_GAP)
                            slot_y = INVENTORY_Y + INVENTORY_GAP + row * (INVENTORY_SLOT_SIZE + INVENTORY_GAP) + 40
                            slot_rect = pygame.Rect(slot_x, slot_y, INVENTORY_SLOT_SIZE, INVENTORY_SLOT_SIZE)
                            if slot_rect.collidepoint(mouse_x, mouse_y):
                                item_to_equip = inventory[row][col]
                                if item_to_equip and item_to_equip.category == "Weapon":
                                    if equip_item(item_to_equip):
                                        inventory[row][col] = None
                                    break
                
                if show_equipment:
                    mouse_x, mouse_y = event.pos
                    weapon_slot_rect = pygame.Rect(EQUIPMENT_X + EQUIPMENT_GAP, EQUIPMENT_Y + 40 + EQUIPMENT_GAP + (EQUIPMENT_ROWS-1) * (EQUIPMENT_SLOT_SIZE + EQUIPMENT_GAP), EQUIPMENT_SLOT_SIZE, EQUIPMENT_SLOT_SIZE)
                    if weapon_slot_rect.collidepoint(mouse_x, mouse_y):
                        unequip_item("weapon")

        if is_crafting_clicked:
            if pygame.time.get_ticks() - click_timer > click_duration:
                is_crafting_clicked = False

        if is_crafting:
            crafting_timer += dt
            if crafting_timer >= CRAFTING_TIME_MS:
                is_crafting = False
                crafting_timer = 0
                add_item_to_inventory(assets["axe"])
                print("Axe crafted!")

        if is_chopping and equipment_slots["weapon"] is None:
            is_chopping = False
            print("Can't chop without a weapon! Equip one first.")

        if is_chopping:
            chopping_timer += dt
            player_frame_timer += dt
            
            if is_swinging:
                if player_frame_timer >= swing_delay:
                    player_frame_timer = 0
                    chopping_frame_index += 1
                    if chopping_frame_index >= len(chopping_frames[last_direction]):
                        is_swinging = False
                        chopping_frame_index = 0
            else:
                if player_frame_timer >= idle_chop_delay:
                    player_frame_timer = 0
                    is_swinging = True
                    chopping_frame_index = 0

            if chopping_timer >= chopping_duration:
                is_chopping = False
                chopping_timer = 0
                is_swinging = False
                
                if chopping_target_tree:
                    is_border_tree = False
                    map_cols, map_rows = 50, 50
                    if (chopping_target_tree.x // TILE_SIZE < BORDER_THICKNESS) or \
                       (chopping_target_tree.x // TILE_SIZE >= map_cols - BORDER_THICKNESS) or \
                       (chopping_target_tree.y // TILE_SIZE < BORDER_THICKNESS) or \
                       (chopping_target_tree.y // TILE_SIZE >= map_rows - BORDER_THICKNESS):
                        is_border_tree = True
                    
                    if not is_border_tree:
                        if add_item_to_inventory(assets["log"]):
                            chopped_tree_timers.append({
                                'rect': chopping_target_tree,
                                'respawn_time': current_time + TREE_RESPAWN_TIME
                            })
                            tree_rects.remove(chopping_target_tree)
                chopping_target_tree = None
        
        respawn_list = []
        for chopped_tree in chopped_tree_timers:
            if current_time >= chopped_tree['respawn_time']:
                respawn_list.append(chopped_tree)

        for tree_to_respawn in respawn_list:
            tree_rects.append(tree_to_respawn['rect'])
            chopped_tree_timers.remove(tree_to_respawn)

        if not is_chopping and not is_crafting and not show_inventory and not show_crafting and not show_equipment:
            keys = pygame.key.get_pressed()
            dx, dy = handle_movement(keys)
            
            if dx != 0 or dy != 0:
                last_direction = current_direction
            
            new_rect = player_pos.move(dx, dy)
            if not handle_collision(new_rect):
                player_pos = new_rect

            moving = dx != 0 or dy != 0
            if moving:
                player_frame_timer += dt
                if player_frame_timer >= player_frame_delay:
                    player_frame_timer = 0
                    player_frame_index = (player_frame_index + 1) % COLS
            else:
                player_frame_index = 0
        
        if current_level == "world":
            map_offset_x = player_pos.x - WIDTH // 2 + PLAYER_SIZE // 2
            map_offset_y = player_pos.y - HEIGHT // 2 + PLAYER_SIZE // 2
            map_offset_x = max(0, min(map_offset_x, 50*TILE_SIZE - WIDTH))
            map_offset_y = max(0, min(map_offset_y, 50*TILE_SIZE - HEIGHT))
        else:
            map_offset_x = map_offset_y = 0

        if is_chopping:
            if is_swinging:
                frame = chopping_frames[last_direction][chopping_frame_index]
            else:
                frame = chopping_frames[f"idle_{last_direction}"]
        elif current_level != "world":
            indoor_size = PLAYER_SIZE * 4
            frame = pygame.transform.scale(frames[current_direction][player_frame_index if (dx!=0 or dy!=0) else 0], (indoor_size, indoor_size))
        else:
            if current_direction == "idle":
                frame = frames[last_direction][0]
            else:
                frame = frames[current_direction][player_frame_index]
        
        draw(screen, assets, frames, frame, is_hovering)
        pygame.display.flip()

if __name__ == "__main__":
    main()