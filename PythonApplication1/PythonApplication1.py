import pygame
import sys
import os
import random

# --- CONSTANTS ---
WIDTH, HEIGHT = 800, 600
TILE_SIZE = 50
PLAYER_SIZE = 40
PLAYER_SPEED = 5
FRAME_WIDTH, FRAME_HEIGHT = 32, 32
COLS = 4
BORDER_THICKNESS = 6

# --- GLOBALS ---
player_pos = pygame.Rect(WIDTH // 2, HEIGHT // 2, PLAYER_SIZE, PLAYER_SIZE)
player_frame_index = 0
player_frame_timer = 0
player_frame_delay = 120
current_direction = "idle"
map_offset_x = map_offset_y = 0
current_level = "world"
current_house_index = None

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
    pygame.display.set_caption("2D Game with Flowers and Grass Leaves")
    return screen, pygame.time.Clock()

# --- LOAD ASSETS ---
def load_assets():
    tile_folder = "Tiles"
    sheet = pygame.image.load("OutdoorStuff.png").convert_alpha()  # Replace with actual filename

    # Slice flowers (red, yellow only)
    flower_positions = [(0, 144), (16, 144)]  # Red, Yellow
    flowers = [
        pygame.transform.scale(sheet.subsurface(pygame.Rect(x, y, 16, 16)), (30, 30))
        for (x, y) in flower_positions
    ]

    # Slice grass leaf from top-left corner
    leaf = pygame.transform.scale(sheet.subsurface(pygame.Rect(0, 0, 16, 16)), (25, 25))

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
        "font": pygame.font.SysFont(None, 36)
    }
    return assets

# --- LOAD PLAYER FRAMES ---
def load_player_frames():
    sheet = pygame.image.load("Player.PNG").convert_alpha()
    frames = {}
    right = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col*FRAME_WIDTH, FRAME_HEIGHT, FRAME_WIDTH, FRAME_HEIGHT)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(COLS)]
    frames["right"] = right
    frames["left"] = [pygame.transform.flip(frame, True, False) for frame in right]
    frames["up"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col*FRAME_WIDTH, 2*FRAME_HEIGHT, FRAME_WIDTH, FRAME_HEIGHT)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(COLS)]
    frames["down"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(col*FRAME_WIDTH, 3*FRAME_HEIGHT, FRAME_WIDTH, FRAME_HEIGHT)), (PLAYER_SIZE, PLAYER_SIZE)) for col in range(COLS)]
    frames["idle"] = [pygame.transform.scale(sheet.subsurface(pygame.Rect(0, 0, FRAME_WIDTH, FRAME_HEIGHT)), (PLAYER_SIZE, PLAYER_SIZE))]
    return frames

# --- SETUP COLLIDERS ---
def setup_colliders():
    global tree_rects, house_list, indoor_rects, flower_tiles, leaf_tiles
    map_cols, map_rows = 50, 50
    for row in range(map_rows):
        for col in range(map_cols):
            x = col * TILE_SIZE
            y = row * TILE_SIZE
            if row < BORDER_THICKNESS or row >= map_rows - BORDER_THICKNESS or col < BORDER_THICKNESS or col >= map_cols - BORDER_THICKNESS:
                tree_rects.append(pygame.Rect(x + 5, y + 5, TILE_SIZE - 10, TILE_SIZE - 10))
            elif random.random() < 0.02:
                tree_rects.append(pygame.Rect(x + 5, y + 5, TILE_SIZE - 10, TILE_SIZE - 10))
            elif random.random() < 0.03:
                flower_tiles.append((x + 10, y + 10, random.randint(0, 1)))  # Red or Yellow
            elif random.random() < 0.12:
                leaf_tiles.append((x + 12, y + 12))

    house_rect = pygame.Rect(player_pos.x + 100, player_pos.y, TILE_SIZE*2, TILE_SIZE*2)
    house1_rect = pygame.Rect(house_rect.x + 200, house_rect.y, TILE_SIZE*2, TILE_SIZE*2)
    tree_rects.extend([house_rect, house1_rect])
    house_list.extend([house_rect, house1_rect])

    indoor_rects = [
        pygame.Rect(0, 80, WIDTH, 2),
        pygame.Rect(0, HEIGHT - 70, WIDTH, 2),
        pygame.Rect(-40, 0, 1, HEIGHT),
        pygame.Rect(WIDTH - 60, 0, 2, HEIGHT)
    ]

# --- CHECK HOUSE ENTRY ---
def check_house_entry(rect):
    for i, h in enumerate(house_list):
        if rect.colliderect(h.inflate(20, 20)):
            return i
    return None

# --- HANDLE MOVEMENT ---
def handle_movement(keys):
    global current_direction
    dx = dy = 0
    if keys[pygame.K_a]: dx = -PLAYER_SPEED; current_direction = "left"
    if keys[pygame.K_d]: dx = PLAYER_SPEED; current_direction = "right"
    if keys[pygame.K_w]: dy = -PLAYER_SPEED; current_direction = "up"
    if keys[pygame.K_s]: dy = PLAYER_SPEED; current_direction = "down"
    if dx == 0 and dy == 0: current_direction = "idle"
    return dx, dy

# --- HANDLE COLLISION ---
def handle_collision(new_rect):
    if current_level == "world":
        return any(new_rect.colliderect(r) for r in tree_rects)
    else:
        scaled = new_rect.inflate(PLAYER_SIZE * 2, PLAYER_SIZE * 2)
        return any(scaled.colliderect(r) for r in indoor_rects)

# --- DRAW EVERYTHING ---
def draw(screen, assets, frames, frame):
    screen.fill((0, 0, 0))
    if current_level == "world":
        draw_world(screen, assets)
    else:
        screen.blit(assets["interiors"][current_house_index], (0, 0))
    screen.blit(frame, (player_pos.x - map_offset_x, player_pos.y - map_offset_y))
    draw_prompt(screen, assets["font"])

def draw_world(screen, assets):
    start_col = map_offset_x // TILE_SIZE
    start_row = map_offset_y // TILE_SIZE
    cols_to_draw = (WIDTH // TILE_SIZE) + 3
    rows_to_draw = (HEIGHT // TILE_SIZE) + 3
    for row in range(start_row, start_row + rows_to_draw):
        for col in range(start_col, start_col + cols_to_draw):
            x = col * TILE_SIZE
            y = row * TILE_SIZE
            sx = x - map_offset_x
            sy = y - map_offset_y
            screen.blit(assets["grass"], (sx, sy))
            tile_rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
            if any(tile_rect.colliderect(tree) for tree in tree_rects):
                screen.blit(assets["tree"], (sx, sy))

    for fx, fy, flower_index in flower_tiles:
        sx = fx - map_offset_x
        sy = fy - map_offset_y
        screen.blit(assets["flowers"][flower_index], (sx, sy))

    for lx, ly in leaf_tiles:
        sx = lx - map_offset_x
        sy = ly - map_offset_y
        screen.blit(assets["leaf"], (sx, sy))

    screen.blit(assets["house"], (house_list[0].x - map_offset_x, house_list[0].y - map_offset_y))
    screen.blit(assets["house1"], (house_list[1].x - map_offset_x, house_list[1].y - map_offset_y))

def draw_prompt(screen, font):
    show_e = False
    if current_level == "world":
        if check_house_entry(player_pos) is not None:
            show_e = True
    else:
        if door_zone.colliderect(player_pos.inflate(PLAYER_SIZE * 2, PLAYER_SIZE * 2)):
            show_e = True
    if show_e:
        text = font.render("Press E", True, (255, 255, 255))
        screen.blit(text, (player_pos.x - map_offset_x + 10, player_pos.y - map_offset_y - 40))
# --- MAIN LOOP ---
def main():
    global player_pos, player_frame_index, player_frame_timer, current_level, current_house_index, map_offset_x, map_offset_y
    screen, clock = init()
    assets = load_assets()
    frames = load_player_frames()
    setup_colliders()

    running = True
    while running:
        dt = clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()
        dx, dy = handle_movement(keys)
        new_rect = player_pos.move(dx, dy)
        if not handle_collision(new_rect):
            player_pos = new_rect

        if current_level == "world":
            map_offset_x = player_pos.x - WIDTH // 2 + PLAYER_SIZE // 2
            map_offset_y = player_pos.y - HEIGHT // 2 + PLAYER_SIZE // 2
            map_offset_x = max(0, min(map_offset_x, 50 * TILE_SIZE - WIDTH))
            map_offset_y = max(0, min(map_offset_y, 50 * TILE_SIZE - HEIGHT))
        else:
            map_offset_x = map_offset_y = 0

        moving = dx != 0 or dy != 0
        if moving:
            player_frame_timer += dt
            if player_frame_timer >= player_frame_delay:
                player_frame_timer = 0
                player_frame_index = (player_frame_index + 1) % COLS

        # --- FRAME SELECTION ---
        if current_level != "world":
            indoor_player_size = PLAYER_SIZE * 3
            frame = pygame.transform.scale(frames[current_direction][player_frame_index if moving else 0], (indoor_player_size, indoor_player_size))
        else:
            frame = frames[current_direction][player_frame_index if moving else 0]

        # --- HOUSE ENTRY ---
        if current_level == "world" and keys[pygame.K_e]:
            house_index = check_house_entry(player_pos)
            if house_index is not None:
                current_level = f"house{house_index + 1}"
                current_house_index = house_index
                player_pos.x = WIDTH // 2
                player_pos.y = HEIGHT // 2

        # --- HOUSE EXIT ---
        if current_level != "world" and keys[pygame.K_e]:
            if door_zone.colliderect(player_pos.inflate(PLAYER_SIZE * 2, PLAYER_SIZE * 2)):
                current_level = "world"
                exit_rect = house_list[current_house_index]
                player_pos.x = exit_rect.x + exit_rect.width + 10
                player_pos.y = exit_rect.y
                current_house_index = None

        # --- DRAW EVERYTHING ---
        draw(screen, assets, frames, frame)

        # --- DISPLAY UPDATE ---
        pygame.display.flip()

# --- RUN GAME ---
if __name__ == "__main__":
    main()