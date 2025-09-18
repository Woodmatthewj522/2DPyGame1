import pygame
import random
import sys

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simple 2D Game with NPCs")
clock = pygame.time.Clock()

# Colors
WHITE = (255, 255, 255)
RED = (200, 0, 0)

# Player setup
player_size = 40
player_pos = pygame.Rect(WIDTH // 2, HEIGHT // 2, player_size, player_size)
player_speed = 5

# Load Player sprite sheet
frame_width, frame_height = 32, 32  # size of each frame in Player.png
cols = 4  # number of animation frames per direction
rows = 4  # number of directions

player_sheet = pygame.image.load("Player.PNG").convert_alpha()

# Directions assumed: row0=down, row1=left, row2=right, row3=up
directions = ["left", "right", "up", "down"]
player_frames = {}

for row, direction in enumerate(directions):
    frames = []
    for col in range(cols):
        frame = player_sheet.subsurface(
            pygame.Rect(col * frame_width, row * frame_height, frame_width, frame_height)
        )
        frame = pygame.transform.scale(frame, (player_size, player_size))
        frames.append(frame)
    player_frames[direction] = frames

player_frame_index = 0
player_frame_timer = 0
player_frame_delay = 120  # ms per frame
current_direction = "down"

# Enemy setup (simple red squares)
enemy_size = 40
enemy_speed = 2
num_enemies = 5
enemies = [
    pygame.Rect(
        random.randint(0, WIDTH - enemy_size),
        random.randint(0, HEIGHT - enemy_size),
        enemy_size,
        enemy_size,
    )
    for _ in range(num_enemies)
]

enemy_dirs = [
    random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)]) for _ in range(num_enemies)
]


def move_enemies():
    for i, enemy in enumerate(enemies):
        dx, dy = enemy_dirs[i]
        enemy.x += dx * enemy_speed
        enemy.y += dy * enemy_speed

        # Bounce off walls
        if enemy.left < 0 or enemy.right > WIDTH:
            enemy_dirs[i] = (-dx, dy)
        if enemy.top < 0 or enemy.bottom > HEIGHT:
            enemy_dirs[i] = (dx, -dy)


def check_collision():
    for enemy in enemies:
        if player_pos.colliderect(enemy):
            return True
    return False


# Game loop
running = True
while running:
    screen.fill(WHITE)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    # Player movement
    keys = pygame.key.get_pressed()
    moving = False

    if keys[pygame.K_a]:
        player_pos.x -= player_speed
        current_direction = "left"
        moving = True
    elif keys[pygame.K_d]:
        player_pos.x += player_speed
        current_direction = "right"
        moving = True
    elif keys[pygame.K_w]:
        player_pos.y -= player_speed
        current_direction = "up"
        moving = True
    elif keys[pygame.K_s]:
        player_pos.y += player_speed
        current_direction = "down"
        moving = True

    move_enemies()

    if check_collision():
        print("Game Over!")
        running = False

    # Animate player
    if moving:
        player_frame_timer += clock.get_time()
        if player_frame_timer >= player_frame_delay:
            player_frame_timer = 0
            player_frame_index = (player_frame_index + 1) % cols
    else:
        player_frame_index = 0  # idle frame

    # Draw player
    screen.blit(player_frames[current_direction][player_frame_index], player_pos.topleft)

    # Draw enemies
    for enemy in enemies:
        pygame.draw.rect(screen, RED, enemy)

    pygame.display.flip()
    clock.tick(60)
