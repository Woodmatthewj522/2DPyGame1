import pygame
import sys
import os

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("2D Game with Player + Tree Border + Two Houses")
clock = pygame.time.Clock()

# Player setup
player_size = 40
player_pos = pygame.Rect(WIDTH // 2, HEIGHT // 2, player_size, player_size)
player_speed = 5

# Load player sprite sheet
frame_width, frame_height = 32, 32
cols = 4
player_sheet = pygame.image.load("Player.PNG").convert_alpha()

player_frames = {}

# Right (row 1)
right_frames = []
for col in range(cols):
    frame = player_sheet.subsurface(
        pygame.Rect(col * frame_width, 1 * frame_height, frame_width, frame_height)
    )
    frame = pygame.transform.scale(frame, (player_size, player_size))
    right_frames.append(frame)
player_frames["right"] = right_frames

# Left is flipped right
player_frames["left"] = [pygame.transform.flip(frame, True, False) for frame in right_frames]

# Up (row 2)
up_frames = []
for col in range(cols):
    frame = player_sheet.subsurface(
        pygame.Rect(col * frame_width, 2 * frame_height, frame_width, frame_height)
    )
    frame = pygame.transform.scale(frame, (player_size, player_size))
    up_frames.append(frame)
player_frames["up"] = up_frames

# Down (row 3)
down_frames = []
for col in range(cols):
    frame = player_sheet.subsurface(
        pygame.Rect(col * frame_width, 3 * frame_height, frame_width, frame_height)
    )
    frame = pygame.transform.scale(frame, (player_size, player_size))
    down_frames.append(frame)
player_frames["down"] = down_frames

# Idle (row 0, first frame only)
idle_frame = player_sheet.subsurface(pygame.Rect(0, 0, frame_width, frame_height))
idle_frame = pygame.transform.scale(idle_frame, (player_size, player_size))
player_frames["idle"] = [idle_frame]

# Animation setup
player_frame_index = 0
player_frame_timer = 0
player_frame_delay = 120
current_direction = "idle"

# --- TILE MAP SETUP ---
tile_size = 50
tile_folder = "tiles"

# Load tiles
grass_tile = pygame.image.load(os.path.join(tile_folder, "grass_middle.png")).convert_alpha()
grass_tile = pygame.transform.scale(grass_tile, (tile_size, tile_size))

tree_tile = pygame.image.load(os.path.join(tile_folder, "tree.png")).convert_alpha()
tree_tile = pygame.transform.scale(tree_tile, (tile_size, tile_size))

# Load house sprites
house_tile = pygame.image.load(os.path.join(tile_folder, "house.png")).convert_alpha()
house_tile = pygame.transform.scale(house_tile, (tile_size * 2, tile_size * 2))

house1_tile = pygame.image.load(os.path.join(tile_folder, "house1.png")).convert_alpha()
house1_tile = pygame.transform.scale(house1_tile, (tile_size * 2, tile_size * 2))

# Map dimensions
map_cols = 50
map_rows = 50

# Border thickness
border_thickness = 6

# --- COLLISION SETUP ---
tree_rects = []
for row in range(map_rows):
    for col in range(map_cols):
        if row < border_thickness or row >= map_rows - border_thickness or \
           col < border_thickness or col >= map_cols - border_thickness:
            tree_rects.append(pygame.Rect(col * tile_size, row * tile_size, tile_size, tile_size))

# --- Houses and their colliders ---
house_x = player_pos.x + 100
house_y = player_pos.y
house_rect = pygame.Rect(house_x, house_y, tile_size * 2, tile_size * 2)
tree_rects.append(house_rect)

house1_x = house_rect.x + 200
house1_y = house_rect.y
house1_rect = pygame.Rect(house1_x, house1_y, tile_size * 2, tile_size * 2)
tree_rects.append(house1_rect)

# Map offset
map_offset_x = 0
map_offset_y = 0

# --- GAME LOOP ---
running = True
while running:
    dt = clock.tick(60)
    screen.fill((0, 0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    # Player movement
    keys = pygame.key.get_pressed()
    dx = dy = 0

    if keys[pygame.K_a]:
        dx = -player_speed
        current_direction = "left"
    if keys[pygame.K_d]:
        dx = player_speed
        current_direction = "right"
    if keys[pygame.K_w]:
        dy = -player_speed
        current_direction = "up"
    if keys[pygame.K_s]:
        dy = player_speed
        current_direction = "down"
    if dx == 0 and dy == 0:
        current_direction = "idle"
        player_frame_index = 0

    # Collision check
    new_player_rect = player_pos.move(dx, dy)
    collision = False
    for rect in tree_rects:
        if new_player_rect.colliderect(rect):
            collision = True
            break
    if not collision:
        player_pos = new_player_rect

    # Camera follows player
    map_offset_x = player_pos.x - WIDTH // 2 + player_size // 2
    map_offset_y = player_pos.y - HEIGHT // 2 + player_size // 2

    # Clamp camera offset
    max_offset_x = map_cols * tile_size - WIDTH
    max_offset_y = map_rows * tile_size - HEIGHT
    map_offset_x = max(0, min(map_offset_x, max_offset_x))
    map_offset_y = max(0, min(map_offset_y, max_offset_y))

    # Player screen position
    player_screen_x = player_pos.x - map_offset_x
    player_screen_y = player_pos.y - map_offset_y

    # Animate player
    moving = dx != 0 or dy != 0
    if moving:
        player_frame_timer += dt
        if player_frame_timer >= player_frame_delay:
            player_frame_timer = 0
            player_frame_index = (player_frame_index + 1) % cols
        frame = player_frames[current_direction][player_frame_index]
    else:
        frame = player_frames["idle"][0]

    # Draw visible tiles
    start_col = map_offset_x // tile_size
    start_row = map_offset_y // tile_size
    cols_to_draw = (WIDTH // tile_size) + 3
    rows_to_draw = (HEIGHT // tile_size) + 3

    for row in range(start_row, start_row + rows_to_draw):
        for col in range(start_col, start_col + cols_to_draw):
            screen_x = (col * tile_size) - map_offset_x
            screen_y = (row * tile_size) - map_offset_y

            screen.blit(grass_tile, (screen_x, screen_y))

            tile_rect = pygame.Rect(col * tile_size, row * tile_size, tile_size, tile_size)
            if any(tile_rect.colliderect(tr) for tr in tree_rects):
                screen.blit(tree_tile, (screen_x, screen_y))

    # Draw houses
    house_screen_x = house_rect.x - map_offset_x
    house_screen_y = house_rect.y - map_offset_y
    screen.blit(house_tile, (house_screen_x, house_screen_y))

    house1_screen_x = house1_rect.x - map_offset_x
    house1_screen_y = house1_rect.y - map_offset_y
    screen.blit(house1_tile, (house1_screen_x, house1_screen_y))

    # Draw player
    screen.blit(frame, (player_screen_x, player_screen_y))

    pygame.display.flip()