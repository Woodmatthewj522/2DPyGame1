## -*- coding: utf-8 -*-
import os
import random
import sys
import math
import pygame
import json
import pygame.mixer
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

# Combat constants
COMBAT_RANGE = 80
COMBAT_COOLDOWN = 2000  # ms between attacks (slower)
ENEMY_SPAWN_RATE = 0.02  # chance per frame in dungeon
MAX_ENEMIES = 8
ENEMY_SPEED = 2
ENEMY_AGGRO_RANGE = 150
ENEMY_ATTACK_RANGE = 60
ENEMY_ATTACK_COOLDOWN = 1500
# Attack animation state
is_attacking = False
attack_timer = 0
# Player constants
PLAYER_SIZE_INDOOR = 80
PLAYER_MAX_HEALTH = 100
PLAYER_BASE_DAMAGE = 15
PLAYER_BASE_DEFENSE = 0
# Inventory GUI constants
INVENTORY_SLOT_SIZE = 40
INVENTORY_GAP = 5
INVENTORY_WIDTH = 4 * INVENTORY_SLOT_SIZE + 5 * INVENTORY_GAP
INVENTORY_HEIGHT = 4 * INVENTORY_SLOT_SIZE + 5 * INVENTORY_GAP
INVENTORY_X = (WIDTH - INVENTORY_WIDTH) // 2
INVENTORY_Y = (HEIGHT - INVENTORY_HEIGHT) // 2

# Crafting GUI constants
CRAFTING_PANEL_WIDTH = 420
CRAFTING_PANEL_HEIGHT = 300
CRAFTING_X = (WIDTH - CRAFTING_PANEL_WIDTH) // 2
CRAFTING_Y = (HEIGHT - CRAFTING_PANEL_HEIGHT) // 2

# Equipment GUI constants
EQUIPMENT_SLOT_SIZE = 40
EQUIPMENT_GAP = 20
EQUIPMENT_ROWS = 2
EQUIPMENT_COLS = 4
EQUIPMENT_PANEL_WIDTH = 4 * EQUIPMENT_SLOT_SIZE + 4 * EQUIPMENT_GAP + 20
EQUIPMENT_PANEL_HEIGHT = 2 * EQUIPMENT_SLOT_SIZE + 4 * EQUIPMENT_GAP + 100  # Extra space for stats
EQUIPMENT_X = (WIDTH - EQUIPMENT_PANEL_WIDTH) // 2
EQUIPMENT_Y = (HEIGHT - EQUIPMENT_PANEL_HEIGHT) // 2

# Dungeon constants
DUNGEON_SIZE = 30
DUNGEON_SPAWN_X = 5 * TILE_SIZE
DUNGEON_SPAWN_Y = 5 * TILE_SIZE
player_movement_history = []
is_dashing = False
dash_cooldown = 0
# Music constants
MUSIC_FILES = {
    "main_menu": "main.mp3",       # points to main.mp3
    "forest": "forest.mp3",        # points to forest.mp3
    "dungeon": "dungeon_theme.mp3", 
    "boss_room": "music/boss_battle.mp3"
}

# --- CLASSES ---
class Item:
    def __init__(self, name, image=None, count=1, category=None, damage=0, defense=0):
        if image is None:
            # fallback magenta box if image is missing
            image = pygame.Surface((32, 32))
            image.fill((255, 0, 255))
        self.name = name
        self.image = image
        self.count = count
        self.category = category
        self.damage = damage
        self.defense = defense

class FloatingText:
    def __init__(self, text, pos, color=(255, 0, 0), lifetime=1000):
        """
        text: string to display
        pos: (x, y) world coordinates where the text starts
        color: RGB color of the text
        lifetime: how long (ms) the text stays visible
        """
        self.text = text
        self.x, self.y = pos
        self.color = color
        self.lifetime = lifetime
        self.start_time = pygame.time.get_ticks()
        self.alpha = 255  # start fully opaque

    def update(self):
        elapsed = pygame.time.get_ticks() - self.start_time
        if elapsed < self.lifetime:
            # Move upward
            self.y -= 0.5  
            # Fade out
            self.alpha = max(0, 255 - int((elapsed / self.lifetime) * 255))
        else:
            self.alpha = 0  # invisible

    def is_alive(self):
        return self.alpha > 0

    def draw(self, surface, font, camera_x=0, camera_y=0):
        if self.alpha <= 0:
            return
        text_surf = font.render(self.text, True, self.color)
        text_surf.set_alpha(self.alpha)
        surface.blit(text_surf, (self.x - camera_x, self.y - camera_y))

import pygame

class Player:
    def __init__(self):
        # Core stats
        self.level = 1
        self.experience = 0
        self.experience_to_next = 100

        # Base stats
        self.base_max_health = PLAYER_MAX_HEALTH
        self.base_damage = PLAYER_BASE_DAMAGE
        self.base_defense = PLAYER_BASE_DEFENSE
        # Dynamic stats
        self.max_health = self.base_max_health
        self.health = self.max_health
        self.damage = self.base_damage
        self.defense = self.base_defense
        # Combat & state
        self.last_attack_time = 0
        self.is_invulnerable = False
        self.invulnerability_timer = 0
        self.invulnerability_duration = 1000  # ms

        # Position & hitbox
        self.rect = pygame.Rect(WIDTH // 2, HEIGHT // 2, PLAYER_SIZE, PLAYER_SIZE)
        self.hitbox = self.rect.inflate(-PLAYER_SIZE // 4, -PLAYER_SIZE // 4)

        # Status effects (buffs/debuffs)
        self.status_effects = {}  # {"poison": {"duration": 3000, "timer": 0, "tick_damage": 2}}

    # ------------------------
    # Combat
    # ------------------------
    def take_damage(self, damage_amount, current_time):
        """Apply damage, respecting invulnerability, defense, and effects."""
        if self.is_invulnerable:
            return False

        # FIXED: Calculate damage reduction from defense
        total_defense = self.get_total_defense()
    
        # Defense reduces damage by a percentage (diminishing returns formula)
        damage_reduction = total_defense / (total_defense + 100)
    
        # Apply damage reduction
        reduced_damage = damage_amount * (1 - damage_reduction)
        final_damage = max(1, int(reduced_damage))  # Always take at least 1 damage
    
        self.health -= final_damage
        self.is_invulnerable = True
        self.invulnerability_timer = current_time

        # Show damage feedback with defense info
        if total_defense > 0:
            floating_texts.append(FloatingText(
                f"-{final_damage} ({int(damage_reduction*100)}% blocked)",
                (self.rect.x, self.rect.y - 15),
                color=(255, 150, 0)  # Orange for reduced damage
            ))
        else:
            floating_texts.append(FloatingText(
                f"-{final_damage}",
                (self.rect.x, self.rect.y - 15),
                color=(255, 0, 0)
            ))

        if self.health <= 0:
            self.die()
            return True
        return False

    def heal(self, heal_amount):
        """Heal with feedback, no overheal beyond max_health."""
        old_health = self.health
        self.health = min(self.max_health, self.health + heal_amount)
        actual_heal = self.health - old_health

        if actual_heal > 0:
            floating_texts.append(FloatingText(
                f"+{actual_heal}",
                (self.rect.x, self.rect.y - 15),
                color=(0, 255, 0)
            ))

    def die(self):
        """Handle player death (game over, respawn, etc.)."""
        print("💀 Player has died!")
        # TODO: trigger game over screen or respawn

    # ------------------------
    # Leveling
    # ------------------------
    def gain_experience(self, exp_amount):
        self.experience += exp_amount
        while self.experience >= self.experience_to_next:
            self.experience -= self.experience_to_next
            self.level_up()

    def level_up(self):
        self.level += 1
        self.experience_to_next = int(self.experience_to_next * 1.25)

        # Growth formulas
        health_bonus = 10 + self.level * 5
        damage_bonus = 2 + self.level // 2
        defense_bonus = 1 + self.level // 3  # Add defense growth per level

        self.max_health += health_bonus
        self.health = self.max_health
        self.damage += damage_bonus
        self.base_defense += defense_bonus  # Increase base defense

        # Popup feedback
        global show_level_up, level_up_timer, level_up_text
        show_level_up = True
        level_up_timer = 0
        level_up_text = f"LEVEL UP! Level {self.level}"

        print(f"⬆️ Level {self.level} | HP: {self.max_health} | Defense: {self.get_total_defense()}")


    # ------------------------
    # Combat Actions
    # ------------------------

    def can_attack(self, current_time):
        """Check if player can attack (cooldown check)."""
        return current_time - self.last_attack_time >= COMBAT_COOLDOWN  # Use COMBAT_COOLDOWN, not ENEMY_ATTACK_COOLDOWN

    def attack(self, current_time):
        if self.can_attack(current_time):
            self.last_attack_time = current_time
            return True
        return False

    def get_total_damage(self, equipped_weapon=None):
        """Return base + weapon + buffs damage."""
        weapon_damage = equipped_weapon.damage if equipped_weapon else 0
        buff_bonus = sum(buff.get("damage", 0) for buff in self.status_effects.values())
        return self.damage + weapon_damage + buff_bonus

    # ------------------------
    # Status Effects
    # ------------------------
    def add_status_effect(self, name, duration, **kwargs):
        """Apply a buff/debuff (ex: poison, regen)."""
        self.status_effects[name] = {"duration": duration, "timer": 0, **kwargs}
    def get_total_defense(self):
        total_defense = self.base_defense
    
        # Add defense from all equipped armor pieces
        for slot_name, equipped_item in equipment_slots.items():
            if equipped_item and hasattr(equipped_item, 'defense'):
                total_defense += equipped_item.defense
    
        # Add any temporary buffs
        buff_bonus = sum(buff.get("defense", 0) for buff in self.status_effects.values())
        total_defense += buff_bonus
    
        return total_defense
    def update_status_effects(self, dt):
        expired = []
        for effect, data in self.status_effects.items():
            data["timer"] += dt
            if effect == "poison" and data["timer"] >= 1000:
                self.take_damage(data.get("tick_damage", 1), pygame.time.get_ticks())
                data["timer"] = 0
            if data["duration"] <= 0:
                expired.append(effect)
            else:
                data["duration"] -= dt
        for effect in expired:
            del self.status_effects[effect]

    # ------------------------
    # Update Loop
    # ------------------------
    def update(self, dt, current_time):
        if self.is_invulnerable and current_time - self.invulnerability_timer >= self.invulnerability_duration:
            self.is_invulnerable = False
        self.update_status_effects(dt)
        self.hitbox.center = self.rect.center
        
class Enemy:
    def __init__(self, x, y, enemy_type="orc", frames=None, enemy_frames=None):
        # Animation frames for this enemy type (list of Surfaces)
        # Prefer passed frames, then global enemy_frames, then fallback.
        if frames is None and 'enemy_frames' in globals():
            frames = enemy_frames
        self.frames = (frames.get(enemy_type, []) if frames else [])

        # Choose a visible image: first animation frame or fallback colored surface
        if self.frames:
            # use first frame as initial image
            self.image = self.frames[0].copy()
            # ensure rect matches the image size
            self.rect = self.image.get_rect(topleft=(x, y))
        else:
            # fallback square so enemy is visible
            self.image = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE), pygame.SRCALPHA)
            self.image.fill((180, 60, 60))
            self.rect = self.image.get_rect(topleft=(x, y))

        # Smaller hitbox for fair collisions
        self.hitbox = self.rect.inflate(-PLAYER_SIZE // 3, -PLAYER_SIZE // 3)

        # Enemy type stats (unchanged)
        self.type = enemy_type
        if enemy_type == "orc":
            self.health = 50
            self.damage = 15
            base_xp = 30
        else:
            self.health = 30
            self.damage = 10
            base_xp = 20

        self.max_health = self.health
        self.speed = ENEMY_SPEED
        self.last_attack_time = 0
        self.state = "idle"  # idle, chasing, attacking
        self.target = None

        # XP reward scales with player level
        self.experience_reward = base_xp + (player.level * 5)

        # Animation control
        self.frame_index = 0
        self.frame_timer = 0
        self.frame_delay = 200

        # Idle movement
        self.path_timer = 0
        self.random_direction = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1), (0, 0)])


    # ------------------------
    # Core Combat
    # ------------------------
    def take_damage(self, damage_amount):
        self.health -= damage_amount
        floating_texts.append(FloatingText(
            f"-{damage_amount}",
            (self.rect.x, self.rect.y - 15),
            color=(255, 50, 50)
        ))
        return self.health <= 0

    # ------------------------
    # AI + Movement
    # ------------------------
    def update(self, dt, current_time, player_world_rect, obstacles):
        # Animate
        self.frame_timer += dt
        if self.frame_timer >= self.frame_delay:
            self.frame_index = (self.frame_index + 1) % 4
            self.frame_timer = 0

        # Distance to player
        dx = player_world_rect.centerx - self.hitbox.centerx
        dy = player_world_rect.centery - self.hitbox.centery
        distance_to_player = math.hypot(dx, dy)

        # State logic
        if distance_to_player <= ENEMY_AGGRO_RANGE:
            self.state = "chasing"
            self.target = player_world_rect
        elif distance_to_player > ENEMY_AGGRO_RANGE * 1.5:
            self.state = "idle"
            self.target = None

        # Movement
        old_rect = self.rect.copy()

        if self.state == "chasing" and self.target:
            if distance_to_player > ENEMY_ATTACK_RANGE * 0.8:  # stop if close enough
                dx /= distance_to_player
                dy /= distance_to_player
                self.rect.x += dx * self.speed
                self._resolve_collisions(obstacles, axis="x", old_rect=old_rect)
                self.rect.y += dy * self.speed
                self._resolve_collisions(obstacles, axis="y", old_rect=old_rect)

        elif self.state == "idle":
            self.path_timer += dt
            if self.path_timer >= 2000:  # change direction every 2s
                self.random_direction = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1), (0, 0)])
                self.path_timer = 0

            dx, dy = self.random_direction
            self.rect.x += dx * self.speed * 0.5
            self._resolve_collisions(obstacles, axis="x", old_rect=old_rect)
            self.rect.y += dy * self.speed * 0.5
            self._resolve_collisions(obstacles, axis="y", old_rect=old_rect)

        # Sync hitbox with sprite
        self.hitbox.center = self.rect.center

    # ------------------------
    # Collision helper
    # ------------------------
    def _resolve_collisions(self, obstacles, axis, old_rect):
        for obstacle in obstacles:
            if self.rect.colliderect(obstacle):
                if axis == "x":
                    self.rect.x = old_rect.x
                elif axis == "y":
                    self.rect.y = old_rect.y
                break
class EnemySpawnPoint:
    def __init__(self, x, y, enemy_type="orc", respawn_time=30000):
        self.x = x
        self.y = y
        self.enemy_type = enemy_type
        self.respawn_time = respawn_time  # milliseconds
        self.last_spawn_time = 0
        self.current_enemy = None  # Reference to spawned enemy
        self.is_active = True
        print(f"Created {enemy_type} spawn point at ({x}, {y}) with {respawn_time}ms respawn")
        
    def can_spawn(self, current_time):
        """Check if this spawn point can create a new enemy."""
        # Don't spawn if enemy still alive and in the enemies list
        if self.current_enemy and self.current_enemy in enemies:
            return False
            
        # Check respawn timer
        time_since_spawn = current_time - self.last_spawn_time
        can_spawn_now = time_since_spawn >= self.respawn_time
        
        if not can_spawn_now:
            remaining_time = (self.respawn_time - time_since_spawn) / 1000.0
            # Only print occasionally to avoid spam
            if int(remaining_time) % 5 == 0 and remaining_time > 0:
                print(f"{self.enemy_type} spawn at ({self.x}, {self.y}) cooldown: {remaining_time:.1f}s remaining")
        
        return can_spawn_now
    
    def spawn_enemy(self, current_time):
        """Create and spawn an enemy at this point."""
        if not self.can_spawn(current_time):
            return None
        
        # Check if position is safe (not inside walls)
        test_rect = pygame.Rect(self.x, self.y, PLAYER_SIZE, PLAYER_SIZE)
        
        # Check collision with walls
        for wall in dungeon_walls:
            if test_rect.colliderect(wall):
                print(f"Cannot spawn {self.enemy_type} at ({self.x}, {self.y}) - inside wall!")
                # Try nearby positions
                for offset_x in [-TILE_SIZE, TILE_SIZE, 0]:
                    for offset_y in [-TILE_SIZE, TILE_SIZE, 0]:
                        if offset_x == 0 and offset_y == 0:
                            continue
                        new_test_rect = pygame.Rect(self.x + offset_x, self.y + offset_y, PLAYER_SIZE, PLAYER_SIZE)
                        collision = False
                        for wall in dungeon_walls:
                            if new_test_rect.colliderect(wall):
                                collision = True
                                break
                        if not collision:
                            self.x += offset_x
                            self.y += offset_y
                            print(f"Moved spawn point to ({self.x}, {self.y})")
                            break
                    if not collision:
                        break
                else:
                    print(f"Could not find safe spawn position near ({self.x}, {self.y})")
                    return None
        

        # Create the enemy with frames
        enemy = Enemy(
            self.x, 
            self.y, 
            self.enemy_type,
            frames=(enemy_frames if 'enemy_frames' in globals() else None)
        )
        print(f"Spawned {self.enemy_type} with {len(enemy.frames) if enemy.frames else 0} frames")

        self.current_enemy = enemy
        self.last_spawn_time = current_time
        enemies.append(enemy)
        print(f"✓ Spawned {self.enemy_type} at ({self.x}, {self.y}) - Total enemies: {len(enemies)}")
        return enemy
class Boss(Enemy):
    def __init__(self, x, y, boss_data=None):
        # Call Enemy constructor with type "boss"
        super().__init__(x, y, enemy_type="boss")
        
        # Load boss sprite
        try:
            self.image = pygame.image.load("boss1.png").convert_alpha()
            self.image = pygame.transform.scale(self.image, (PLAYER_SIZE * 4, PLAYER_SIZE * 4))
        except Exception as e:
            print("Error loading boss1.png:", e)
            self.image = pygame.Surface((PLAYER_SIZE * 4, PLAYER_SIZE * 4))
            self.image.fill((200, 0, 0))  # Red boss

        # Update rect size to match the larger sprite
        self.rect = self.image.get_rect(topleft=(x, y))
        self.hitbox = self.rect.inflate(-PLAYER_SIZE // 2, -PLAYER_SIZE // 2)

        # Boss stats: can be set from boss_data or use defaults
        if boss_data:
            self.health = int(boss_data.get("health", 300))
            self.max_health = self.health
            self.damage = int(boss_data.get("damage", 40))
            self.name = boss_data.get("name", "Boss")
        else:
            self.health = 300
            self.max_health = 300
            self.damage = 40
            self.name = "Ancient Guardian"

        # Boss-specific stats
        self.experience_reward = 500  # More XP than regular enemies
        self.speed = ENEMY_SPEED * 0.8  # Slightly slower than regular enemies
        
        # Special abilities
        self.special_ability_cooldown = 5000  # ms
        self.last_special_ability = 0
        self.charge_cooldown = 8000  # ms
        self.last_charge_attack = 0
        self.is_charging = False
        self.charge_timer = 0
        self.charge_duration = 2000  # ms
        self.charge_target = None
        
        # Boss phases based on health
        self.phase = 1  # 1, 2, or 3
        self.last_phase_change = 0
        
        # Enhanced aggro range for boss
        self.aggro_range = ENEMY_AGGRO_RANGE * 2
        self.attack_range = ENEMY_ATTACK_RANGE * 1.5
        
        # Boss movement patterns
        self.movement_pattern = "chase"  # "chase", "circle", "charge", "retreat"
        self.pattern_timer = 0
        self.circle_angle = 0
        self.retreat_timer = 0

    def get_current_phase(self):
        """Determine boss phase based on health percentage."""
        health_percent = self.health / self.max_health
        if health_percent > 0.66:
            return 1
        elif health_percent > 0.33:
            return 2
        else:
            return 3

    def change_phase(self, new_phase, current_time):
        """Handle phase transitions with special effects."""
        if new_phase != self.phase:
            old_phase = self.phase
            self.phase = new_phase
            self.last_phase_change = current_time
            
            # Visual feedback for phase change
            floating_texts.append(FloatingText(
                f"Phase {self.phase}!",
                (self.rect.centerx, self.rect.y - 50),
                color=(255, 215, 0),  # Gold
                lifetime=2000
            ))
            
            # Phase-specific changes
            if self.phase == 2:
                self.speed = ENEMY_SPEED * 1.0  # Normal speed
                self.special_ability_cooldown = 4000  # Faster specials
                print(f"{self.name} enters Phase 2 - Enhanced Aggression!")
                
            elif self.phase == 3:
                self.speed = ENEMY_SPEED * 1.2  # Faster
                self.special_ability_cooldown = 3000  # Even faster specials
                self.charge_cooldown = 6000  # More frequent charges
                print(f"{self.name} enters Phase 3 - Enraged!")

    

    def _slam_attack(self, player, current_time):
        """Basic slam attack - high damage, single target."""
        damage = int(self.damage * 1.5)
        if player.take_damage(damage, current_time):
            return
            
        floating_texts.append(FloatingText(
            "Mighty Slam!",
            (self.rect.centerx, self.rect.y - 30),
            color=(255, 100, 0),
            lifetime=1500
        ))

    def _shockwave_attack(self, player, current_time):
        """AOE attack that hits if player is nearby."""
        shockwave_range = self.attack_range * 1.5
        distance = math.hypot(
            player.rect.centerx - self.rect.centerx,
            player.rect.centery - self.rect.centery
        )
        
        if distance <= shockwave_range:
            damage = int(self.damage * 1.2)
            player.take_damage(damage, current_time)
            
        floating_texts.append(FloatingText(
            "Shockwave!",
            (self.rect.centerx, self.rect.y - 30),
            color=(255, 150, 0),
            lifetime=1500
        ))

    def _combo_attack(self, player, current_time):
        """Phase 3 combo attack - multiple hits."""
        base_damage = int(self.damage * 0.8)
        
        # First hit
        if player.take_damage(base_damage, current_time):
            return
            
        # Schedule second hit (simplified - in a full implementation you'd use a proper system)
        player.take_damage(base_damage, current_time + 500)
        
        floating_texts.append(FloatingText(
            "Fury Combo!",
            (self.rect.centerx, self.rect.y - 30),
            color=(255, 50, 50),
            lifetime=2000
        ))

    def initiate_charge_attack(self, player_pos, current_time):
        """Start a charge attack toward the player."""
        if current_time - self.last_charge_attack < self.charge_cooldown:
            return False
            
        if self.is_charging:
            return False
            
        self.is_charging = True
        self.charge_timer = 0
        self.charge_target = (player_pos.centerx, player_pos.centery)
        self.last_charge_attack = current_time
        self.movement_pattern = "charge"
        
        floating_texts.append(FloatingText(
            "Charging!",
            (self.rect.centerx, self.rect.y - 40),
            color=(255, 200, 0),
            lifetime=1000
        ))
        
        return True

    def update_movement_pattern(self, dt, current_time, player_world_rect):
        """Advanced movement patterns for the boss."""
        self.pattern_timer += dt
        
        # Change patterns periodically or based on conditions
        if self.pattern_timer > 5000:  # Change pattern every 5 seconds
            patterns = ["chase", "circle"]
            if self.phase >= 2:
                patterns.append("retreat")
            
            self.movement_pattern = random.choice(patterns)
            self.pattern_timer = 0
            
        # Handle charge attack opportunity
        if (self.phase >= 2 and 
            not self.is_charging and 
            current_time - self.last_charge_attack > self.charge_cooldown and
            random.random() < 0.002):  # Small chance each frame
            
            distance = math.hypot(
                player_world_rect.centerx - self.rect.centerx,
                player_world_rect.centery - self.rect.centery
            )
            
            if 100 < distance < 300:  # Good charge distance
                self.initiate_charge_attack(player_world_rect, current_time)

    def update(self, dt, current_time, player_world_rect, obstacles):
        """Enhanced boss update with phases and special behaviors."""
        # Update phase based on health
        current_phase = self.get_current_phase()
        if current_phase != self.phase:
            self.change_phase(current_phase, current_time)
        
        # Update movement patterns
        self.update_movement_pattern(dt, current_time, player_world_rect)
        
        # Handle charge attack
        if self.is_charging:
            self.charge_timer += dt
            if self.charge_timer >= self.charge_duration:
                self.is_charging = False
                self.movement_pattern = "chase"
                
        # Animate
        self.frame_timer += dt
        if self.frame_timer >= self.frame_delay:
            self.frame_index = (self.frame_index + 1) % 4
            self.frame_timer = 0

        # Distance and direction to player
        dx = player_world_rect.centerx - self.hitbox.centerx
        dy = player_world_rect.centery - self.hitbox.centery
        distance_to_player = math.hypot(dx, dy)

        # Enhanced AI state logic
        if distance_to_player <= self.aggro_range:
            self.state = "chasing"
            self.target = player_world_rect
        elif distance_to_player > self.aggro_range * 1.5:
            self.state = "idle"
            self.target = None

        # Movement based on pattern and state
        old_rect = self.rect.copy()
        
        if self.state == "chasing" and self.target:
            if self.is_charging:
                # Charge movement - fast and direct
                if self.charge_target:
                    charge_dx = self.charge_target[0] - self.rect.centerx
                    charge_dy = self.charge_target[1] - self.rect.centery
                    charge_distance = math.hypot(charge_dx, charge_dy)
                    
                    if charge_distance > 10:  # Still moving toward target
                        charge_dx /= charge_distance
                        charge_dy /= charge_distance
                        charge_speed = self.speed * 3  # Much faster during charge
                        self.rect.x += charge_dx * charge_speed
                        self._resolve_collisions(obstacles, axis="x", old_rect=old_rect)
                        self.rect.y += charge_dy * charge_speed  
                        self._resolve_collisions(obstacles, axis="y", old_rect=old_rect)
                        
            elif self.movement_pattern == "circle" and distance_to_player < 200:
                # Circle around player
                self.circle_angle += 0.05
                circle_radius = 120
                target_x = player_world_rect.centerx + math.cos(self.circle_angle) * circle_radius
                target_y = player_world_rect.centery + math.sin(self.circle_angle) * circle_radius
                
                circle_dx = target_x - self.rect.centerx
                circle_dy = target_y - self.rect.centery
                circle_distance = math.hypot(circle_dx, circle_dy)
                
                if circle_distance > 10:
                    circle_dx /= circle_distance
                    circle_dy /= circle_distance
                    self.rect.x += circle_dx * self.speed * 0.7
                    self._resolve_collisions(obstacles, axis="x", old_rect=old_rect)
                    self.rect.y += circle_dy * self.speed * 0.7
                    self._resolve_collisions(obstacles, axis="y", old_rect=old_rect)
                    
            elif self.movement_pattern == "retreat" and distance_to_player < 100:
                # Retreat to a better position
                self.retreat_timer += dt
                if self.retreat_timer < 2000:  # Retreat for 2 seconds
                    retreat_dx = -dx / distance_to_player  # Move away from player
                    retreat_dy = -dy / distance_to_player
                    self.rect.x += retreat_dx * self.speed * 1.5
                    self._resolve_collisions(obstacles, axis="x", old_rect=old_rect)
                    self.rect.y += retreat_dy * self.speed * 1.5
                    self._resolve_collisions(obstacles, axis="y", old_rect=old_rect)
                else:
                    self.retreat_timer = 0
                    self.movement_pattern = "chase"
                    
            else:
                # Standard chase behavior
                if distance_to_player > self.attack_range * 0.8:
                    dx /= distance_to_player
                    dy /= distance_to_player
                    self.rect.x += dx * self.speed
                    self._resolve_collisions(obstacles, axis="x", old_rect=old_rect)
                    self.rect.y += dy * self.speed
                    self._resolve_collisions(obstacles, axis="y", old_rect=old_rect)

        elif self.state == "idle":
            # Idle movement - slower and more random
            self.path_timer += dt
            if self.path_timer >= 3000:  # Change direction every 3s (slower than regular enemies)
                self.random_direction = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1), (0, 0)])
                self.path_timer = 0

            dx, dy = self.random_direction
            self.rect.x += dx * self.speed * 0.3  # Slower idle movement
            self._resolve_collisions(obstacles, axis="x", old_rect=old_rect)
            self.rect.y += dy * self.speed * 0.3
            self._resolve_collisions(obstacles, axis="y", old_rect=old_rect)

        # Sync hitbox with sprite
        self.hitbox.center = self.rect.center
        
        # Try special abilities
        if self.state == "chasing" and distance_to_player <= self.attack_range * 1.5:
            self.use_special_ability(current_time, player)

    def attack_player(self, player_world_rect, current_time):
        """Check if enemy can attack player and return True if attacking."""
        if current_time - self.last_attack_time < ENEMY_ATTACK_COOLDOWN:
            return False
    
        attack_range_rect = self.hitbox.inflate(ENEMY_ATTACK_RANGE, ENEMY_ATTACK_RANGE)
        if attack_range_rect.colliderect(player_world_rect):
            self.last_attack_time = current_time
            return True
        return False

    # In your Boss class, move this method to the proper level
    def take_damage(self, damage_amount):
        """Override to add boss-specific damage feedback."""
        old_health = self.health
        self.health -= damage_amount

        floating_texts.append(FloatingText(
            f"-{damage_amount}",
            (self.rect.x, self.rect.y - 15),
            color=(255, 50, 50)
        ))

        # Boss-specific damage feedback
        if self.health > 0:
            # Show percentage of health remaining
            health_percent = int((self.health / self.max_health) * 100)
            floating_texts.append(FloatingText(
                f"{health_percent}%",
                (self.rect.centerx + 30, self.rect.y - 10),
                color=(255, 255, 100),
                lifetime=800
            ))

            # Special reactions to taking damage
            if self.health < self.max_health * 0.5 and old_health >= self.max_health * 0.5:
                floating_texts.append(FloatingText(
                    "You will pay for that!",
                    (self.rect.centerx, self.rect.y - 60),
                    color=(255, 100, 100),
                    lifetime=2000
                ))
        else:
            # Boss death message
            floating_texts.append(FloatingText(
                "The Ancient Guardian falls!",
                (self.rect.centerx, self.rect.y - 50),
                color=(255, 215, 0),
                lifetime=3000
            ))

        return self.health <= 0

# --- GAME STATE GLOBALS ---
player_pos = pygame.Rect(WIDTH // 2, HEIGHT // 2, PLAYER_SIZE, PLAYER_SIZE)
player = Player()
map_offset_x = 0
map_offset_y = 0
current_level = "world"  # "world", "house", or "dungeon"
current_house_index = None
current_music = None
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
enemy_frames = None
# Stone specific state
is_mining = False
mining_timer = 0
mining_target_stone = None

# Pause menu state
show_pause_menu = False
pause_menu_selected_option = 0
pause_button_rects = {}

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

# Vendor system
show_vendor_gui = False
vendor_tab = "buy"  # "buy" or "sell"
buy_button_rects = {}
sell_button_rects = {}

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
equipment_slots = {
    "weapon": None,
    "helmet": None,
    "armor": None,
    "boots": None,
    "ring1": None,
    "ring2": None,
    "amulet": None,
    "shield": None,
}
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
last_enemy_spawn = 0

# Level up visual feedback
level_up_timer = 0
level_up_text = ""
show_level_up = False

# Dungeon objects
boss1_portal = None
dungeon_portal = None
dungeon_walls = []
dungeon_enemies = []
dungeon_exit = None
boss_room_walls = []
enemies = []
enemy_spawn_points = []
floating_texts = []
boss_door_rect = None
# Crafting button rects
axe_button_rect = None
pickaxe_button_rect = None
potion_button_rect = None
smithing_tab_rect = None
alchemy_tab_rect = None
chest_button_rect = None
helmet_button_rect = None
boots_button_rect = None
# Game state management
game_state = "main_menu"  # "main_menu", "playing", "save_select"
selected_save_slot = 1
save_slots = [None, None, None, None]  # 4 save slots
menu_selected_option = 0
boss_enemy = None
music_volume = 0.5
# --- HELPERS FOR COORDINATES ---
def get_player_world_rect():
    """Return the player's rectangle in world coordinates."""
    return player_pos.move(map_offset_x, map_offset_y)

def world_to_screen_rect(world_rect):
    """Convert a world rect to screen coordinates."""
    return pygame.Rect(world_rect.x - map_offset_x, world_rect.y - map_offset_y, world_rect.width, world_rect.height)

def find_safe_spawn_position(avoid_rects, spawn_area_rect, entity_size=(PLAYER_SIZE, PLAYER_SIZE)):
    """Find a safe position to spawn an entity avoiding obstacles."""
    for attempt in range(100):  # Try 100 times to find a safe spot
        x = random.randint(spawn_area_rect.x, spawn_area_rect.x + spawn_area_rect.width - entity_size[0])
        y = random.randint(spawn_area_rect.y, spawn_area_rect.y + spawn_area_rect.height - entity_size[1])
        
        test_rect = pygame.Rect(x, y, entity_size[0], entity_size[1])
        
        # Check if this position collides with any obstacles
        collision = False
        for obstacle in avoid_rects:
            if test_rect.colliderect(obstacle):
                collision = True
                break
        
        if not collision:
            return (x, y)
    
    # If no safe position found, return center of spawn area
    return (spawn_area_rect.centerx - entity_size[0]//2, spawn_area_rect.centery - entity_size[1]//2)

def init_music():
    """Initialize pygame mixer for music playback."""
    try:
        pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
        pygame.mixer.init()
        music_volume = 0.5
        pygame.mixer.music.set_volume(music_volume)
        print("Music system initialized successfully")
        return True
    except pygame.error as e:
        print(f"Could not initialize music system: {e}")
        return False

# Add this function to play background music
def play_music(music_key, loop=True):
    """Play background music for a specific game area."""
    global current_music
    
    # Don't restart the same music
    if current_music == music_key and pygame.mixer.music.get_busy():
        return
    
    try:
        # Stop current music
        pygame.mixer.music.stop()
        
        # Load and play new music
        if music_key in MUSIC_FILES:
            pygame.mixer.music.load(MUSIC_FILES[music_key])
            loops = -1 if loop else 0  # -1 means infinite loop
            pygame.mixer.music.play(loops)
            current_music = music_key
            print(f"Playing music: {music_key}")
        else:
            print(f"Music key '{music_key}' not found")
            current_music = None
            
    except pygame.error as e:
        print(f"Could not play music '{music_key}': {e}")
        current_music = None

# Add this function to stop music
def stop_music():
    """Stop all background music."""
    global current_music
    pygame.mixer.music.stop()
    current_music = None

# Add this function to fade out music smoothly
def fade_out_music(fade_time_ms=1000):
    """Fade out current music over specified time."""
    global current_music
    pygame.mixer.music.fadeout(fade_time_ms)
    current_music = None

# Add this function to change volume
def set_music_volume(volume):
    """Set music volume (0.0 to 1.0)."""
    global music_volume
    music_volume = max(0.0, min(1.0, volume))
    pygame.mixer.music.set_volume(music_volume)

def draw_pause_menu(screen, assets):
    """Draw the in-game pause/options menu."""
    if not show_pause_menu:
        return
    
    global pause_button_rects
    pause_button_rects = {}
    
    # Semi-transparent overlay
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(128)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))
    
    # Main panel
    panel_width = 400
    panel_height = 300
    panel_x = (WIDTH - panel_width) // 2
    panel_y = (HEIGHT - panel_height) // 2
    panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
    
    pygame.draw.rect(screen, (40, 40, 60), panel_rect)
    pygame.draw.rect(screen, (255, 255, 255), panel_rect, 3)
    
    # Title
    title_text = assets["large_font"].render("Game Paused", True, (255, 255, 255))
    title_rect = title_text.get_rect(center=(WIDTH // 2, panel_y + 40))
    screen.blit(title_text, title_rect)
    
    # Menu options
    menu_options = ["Resume", "Save Game", "Main Menu", "Exit Game"]
    button_height = 50
    button_width = 300
    start_y = panel_y + 80
    
    mouse_pos = pygame.mouse.get_pos()
    
    for i, option in enumerate(menu_options):
        button_y = start_y + i * (button_height + 10)
        button_rect = pygame.Rect((WIDTH - button_width) // 2, button_y, button_width, button_height)
        
        # Check for hover
        is_hovered = button_rect.collidepoint(mouse_pos)
        is_selected = i == pause_menu_selected_option
        
        # Button colors
        if is_selected or is_hovered:
            button_color = (70, 70, 100)
            text_color = (255, 255, 0)
        else:
            button_color = (50, 50, 70)
            text_color = (255, 255, 255)
        
        # Draw button
        pygame.draw.rect(screen, button_color, button_rect)
        pygame.draw.rect(screen, (200, 200, 200), button_rect, 2)
        
        # Button text
        text_surf = assets["font"].render(option, True, text_color)
        text_rect = text_surf.get_rect(center=button_rect.center)
        screen.blit(text_surf, text_rect)
        
        # Store rect for clicking
        pause_button_rects[option.lower().replace(" ", "_")] = button_rect
    
    # Instructions
    instruction_text = assets["small_font"].render("Use arrow keys or mouse to navigate, ENTER or click to select", True, (200, 200, 200))
    instruction_rect = instruction_text.get_rect(center=(WIDTH // 2, panel_y + panel_height - 30))
    screen.blit(instruction_text, instruction_rect)

def handle_pause_menu_input(event, assets, dt):
    """Handle input for the pause menu."""
    global show_pause_menu, pause_menu_selected_option, game_state
    
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            show_pause_menu = False
        elif event.key == pygame.K_UP:
            pause_menu_selected_option = (pause_menu_selected_option - 1) % 4
        elif event.key == pygame.K_DOWN:
            pause_menu_selected_option = (pause_menu_selected_option + 1) % 4
        elif event.key == pygame.K_RETURN:
            execute_pause_menu_option(assets)
    
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        # Handle mouse clicks
        for option, rect in pause_button_rects.items():
            if rect.collidepoint(event.pos):
                # Set selection and execute
                if option == "resume":
                    pause_menu_selected_option = 0
                elif option == "save_game":
                    pause_menu_selected_option = 1
                elif option == "main_menu":
                    pause_menu_selected_option = 2
                elif option == "exit_game":
                    pause_menu_selected_option = 3
                execute_pause_menu_option(assets)
                break
    
    elif event.type == pygame.MOUSEMOTION:
        # Handle mouse hover
        for i, (option, rect) in enumerate(pause_button_rects.items()):
            if rect.collidepoint(event.pos):
                if option == "resume":
                    pause_menu_selected_option = 0
                elif option == "save_game":
                    pause_menu_selected_option = 1
                elif option == "main_menu":
                    pause_menu_selected_option = 2
                elif option == "exit_game":
                    pause_menu_selected_option = 3
                break

def execute_pause_menu_option(assets):
    """Execute the selected pause menu option."""
    global show_pause_menu, game_state
    
    if pause_menu_selected_option == 0:  # Resume
        show_pause_menu = False
    elif pause_menu_selected_option == 1:  # Save Game
        # You can implement save slot selection here or quick save
        if save_game_data(1):  # Quick save to slot 1
            print("Game saved!")
        show_pause_menu = False
    elif pause_menu_selected_option == 2:  # Main Menu
        show_pause_menu = False
        game_state = "main_menu"
    elif pause_menu_selected_option == 3:  # Exit Game
        pygame.quit()
        sys.exit()
def find_nearest_enemy(player_world_rect):
    """Find enemies in the direction the player was moving."""
    attack_range = COMBAT_RANGE * 1.5  # Longer range
    nearest_enemy = None
    min_distance = float('inf')
    
    # Get attack direction from recent movement
    attack_direction = "down"  # default
    if player_movement_history:
        attack_direction = player_movement_history[-1][0]
    
    # Direction vectors
    direction_map = {
        "up": (0, -1),
        "down": (0, 1),
        "left": (-1, 0),
        "right": (1, 0)
    }
    
    if attack_direction not in direction_map:
        attack_direction = "down"
    
    dx, dy = direction_map[attack_direction]
    
    for enemy in enemies:
        # Get distance and direction to enemy
        to_enemy_x = enemy.rect.centerx - player_world_rect.centerx
        to_enemy_y = enemy.rect.centery - player_world_rect.centery
        distance = math.sqrt(to_enemy_x**2 + to_enemy_y**2)
        
        if distance > attack_range:
            continue
            
        # Check if enemy is in the attack direction
        if distance > 0:
            to_enemy_x /= distance
            to_enemy_y /= distance
            
            # Check if enemy is in attack direction (dot product)
            direction_match = (dx * to_enemy_x) + (dy * to_enemy_y)
            
            # Enemy must be somewhat in attack direction
            if direction_match > 0.3 and distance < min_distance:
                nearest_enemy = enemy
                min_distance = distance
    
    return nearest_enemy

def load_text_map(filename):
    """Load a map from a text file."""
    map_data = {
        'tiles': [],
        'entities': [],
        'spawn_point': (WIDTH // 2, HEIGHT // 2),
        'borders': []
    }
    
    tile_mapping = {
        'G': 'grass',
        'T': 'tree', 
        'S': 'stone',
        'H': 'house',
        'P': 'portal',
        'N': 'npc',
        'M': 'miner',
        'F': 'flower',
        'L': 'leaf',
        '@': 'player_spawn',
        '.': 'grass',  # empty space = grass
        'B': 'boss1_portal',
    }
    
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
            for row, line in enumerate(lines):
                for col, char in enumerate(line.strip()):
                    x, y = col * TILE_SIZE, row * TILE_SIZE
                    if char in tile_mapping:
                        if char == '@':
                            map_data['spawn_point'] = (x, y)
                        elif char in ['N', 'M', 'P', 'H']:
                            map_data['entities'].append({
                                'type': tile_mapping[char],
                                'pos': (x, y)
                            })
                        elif char == 'T':
                            map_data['borders'].append(pygame.Rect(x + 5, y + 5, TILE_SIZE - 10, TILE_SIZE - 10))
                        elif char == 'S':
                            offset = (TILE_SIZE - (TILE_SIZE // 2)) // 2
                            map_data['tiles'].append({
                                'type': 'stone',
                                'rect': pygame.Rect(x + offset, y + offset, TILE_SIZE // 2, TILE_SIZE // 2)
                            })
                        elif char == 'F':
                            map_data['tiles'].append({
                                'type': 'flower',
                                'pos': (x + 10, y + 10, random.randint(0, 1))
                            })

                        elif char == 'L':
                            map_data['tiles'].append({
                                'type': 'leaf',
                                'pos': (x + random.randint(8, 14), y + random.randint(8, 14))
                            })
    except FileNotFoundError:
        print(f"Could not load map: {filename}")

    
    return map_data

# Add this debug function and call it in your boss room drawing
def debug_boss_rendering():
    print("=== BOSS RENDERING DEBUG ===")
    print(f"Current level: {current_level}")
    print(f"Enemies count: {len(enemies)}")
    print(f"Player pos: {player_pos}")
    print(f"Camera offset: ({map_offset_x}, {map_offset_y})")
    
    for i, enemy in enumerate(enemies):
        print(f"\nEnemy {i}:")
        print(f"  Type: {type(enemy).__name__}")
        print(f"  World rect: {enemy.rect}")
        print(f"  Image size: {enemy.image.get_size()}")
        print(f"  Image type: {type(enemy.image)}")
        
        # Calculate screen position
        screen_x = enemy.rect.x - map_offset_x
        screen_y = enemy.rect.y - map_offset_y
        print(f"  Screen pos: ({screen_x}, {screen_y})")
        print(f"  On screen: {-200 <= screen_x <= WIDTH + 200 and -200 <= screen_y <= HEIGHT + 200}")

def draw_boss_room(screen, assets):
    """Draw the boss room including floor, walls, ore, portals, and enemies."""
    # Draw black floor for boss room
    screen.fill((20, 20, 20))  # Dark floor
    
    # Draw boss room walls
    for wall in boss_room_walls:
        screen.blit(assets["dungeon_wall"], (wall.x - map_offset_x, wall.y - map_offset_y))
    
    # Draw ore deposits in boss room
    for ore in stone_rects:
        screen.blit(assets["ore_img"], (ore.x - map_offset_x, ore.y - map_offset_y))
    
    # Draw boss portal if it exists
    if boss1_portal:
        screen.blit(assets["boss1_portal"], (boss1_portal.x - map_offset_x, boss1_portal.y - map_offset_y))
    
    # Draw exit portal
    if dungeon_exit:
        screen.blit(assets["portal"], (dungeon_exit.x - map_offset_x, dungeon_exit.y - map_offset_y))
    
    # Draw enemies (including boss)
    for enemy in enemies:
        enemy_screen_rect = world_to_screen_rect(enemy.rect)
        if -100 <= enemy_screen_rect.x <= WIDTH + 100 and -100 <= enemy_screen_rect.y <= HEIGHT + 100:
            screen.blit(enemy.image, enemy_screen_rect)
            
            # Draw boss health bar at top of screen
            if isinstance(enemy, Boss):
                draw_boss_health_bar(screen, assets, enemy)
            
            # Draw regular enemy health bar if damaged
            elif enemy.health < enemy.max_health:
                bar_y = enemy_screen_rect.y - 15
                draw_health_bar(screen, enemy_screen_rect.x, bar_y, enemy.health, enemy.max_health, enemy.rect.width, 8)

    # Update and draw floating texts
    for text in floating_texts[:]:
        text.update()
        if not text.is_alive():
            floating_texts.remove(text)
        else:
            text.draw(screen, assets["small_font"], map_offset_x, map_offset_y)

    # ... rest of existing code ...
def load_boss_room_map(boss_room):
    data = {
        "walls": [],
        "ore_deposits": [],
        "boss_portal": None,
        "exit_point": None,
        "spawn_point": (5 * TILE_SIZE, 5 * TILE_SIZE),
        "boss_spawn": None  # Add this line
    }
    with open(boss_room, "r") as f:
        lines = [line.rstrip("\n") for line in f]
    for y, line in enumerate(lines):
        for x, char in enumerate(line):
            world_x = x * TILE_SIZE
            world_y = y * TILE_SIZE
            if char == "#":
                data["walls"].append(pygame.Rect(world_x, world_y, TILE_SIZE, TILE_SIZE))
            elif char == "O":
                data["ore_deposits"].append(pygame.Rect(world_x, world_y, TILE_SIZE, TILE_SIZE))
            elif char == "B":
                data["boss_portal"] = pygame.Rect(world_x, world_y, TILE_SIZE * 2, TILE_SIZE * 2)
            elif char == "P":
                data["exit_point"] = pygame.Rect(world_x, world_y, TILE_SIZE, TILE_SIZE)
            elif char == "S":
                data["spawn_point"] = (world_x, world_y)
            elif char == "b":  # Boss spawn marker
                data["boss_spawn"] = (world_x, world_y)
    return data
def setup_boss_room(filename="boss_room.txt"):
    global boss_room_walls, stone_rects, boss1_portal, dungeon_exit, enemies, boss_enemy

    boss_room_walls.clear()
    stone_rects.clear()
    enemies.clear()
    boss1_portal = None
    dungeon_exit = None
    boss_enemy = None

    map_data = load_boss_room_map(filename)

    boss_room_walls.extend(map_data["walls"])
    stone_rects.extend(map_data["ore_deposits"])
    boss1_portal = map_data["boss_portal"]
    dungeon_exit = map_data["exit_point"]

    # Spawn boss if marker exists
    if map_data["boss_spawn"]:
        spawn_x, spawn_y = map_data["boss_spawn"]
        boss_enemy = Boss(spawn_x, spawn_y)
        enemies.append(boss_enemy)
        print("Boss created at:", spawn_x, spawn_y)
        print("Enemies list:", enemies)

    # Return player spawn point
    spawn_x, spawn_y = map_data["spawn_point"]
    return (spawn_x, spawn_y)

def update_enemy_spawns():
    """Update enemy spawn points and create new enemies when needed."""
    if current_level != "dungeon":
        return
        
    current_time = pygame.time.get_ticks()
    total_enemies_before = len(enemies)
    
    for spawn_point in enemy_spawn_points:
        # Clean up dead enemy references
        if spawn_point.current_enemy and spawn_point.current_enemy not in enemies:
            print(f"Cleaning up dead {spawn_point.enemy_type} reference at spawn ({spawn_point.x}, {spawn_point.y})")
            spawn_point.current_enemy = None
        
        # Try to spawn new enemy
        if spawn_point.can_spawn(current_time):
            new_enemy = spawn_point.spawn_enemy(current_time)
            if new_enemy:
                print(f"Successfully spawned {new_enemy.type}")
    
    total_enemies_after = len(enemies)
    if total_enemies_after > total_enemies_before:
        print(f"Enemy count increased from {total_enemies_before} to {total_enemies_after}")
def load_dungeon_map_with_enemies(dungeon1):
    """Enhanced map loading that includes walls, ores, portals, and enemy spawn points."""
    global enemy_spawn_points  # keep synced with map loading

    map_data = {
        'walls': [],
        'ore_deposits': [],
        'spawn_point': (5 * TILE_SIZE, 5 * TILE_SIZE),
        'exit_point': None,
        'boss_portal': None,
        'enemy_spawns': []
    }

    
    # ADD THIS DEBUG:
    print(f"\n=== DUNGEON MAP LOADED ===")
    print(f"File: {dungeon1}")
    print(f"Enemy spawns found: {len(map_data['enemy_spawns'])}")
    for i, spawn in enumerate(map_data['enemy_spawns']):
        print(f"  Spawn {i+1}: {spawn.enemy_type} at ({spawn.x}, {spawn.y})")
    print(f"Walls: {len(map_data['walls'])}")
    print(f"Ore deposits: {len(map_data['ore_deposits'])}")
    print("========================\n")
    tile_mapping = {
        '#': 'wall',
        'O': 'ore',
        '@': 'player_spawn',
        'B': 'boss_portal',
        'E': 'exit',
        '.': 'floor',
        'e': 'enemy_orc',       # Orc
        'g': 'enemy_goblin',    # Goblin
        's': 'enemy_strong',    # Stronger enemy (e.g., elite orc)
    }

    print(f"Loading dungeon map: {dungeon1}")

    try:
        with open(dungeon1, 'r') as f:
            lines = f.readlines()

        print(f"Map file loaded, {len(lines)} lines found")

        for row, line in enumerate(lines):
            line = line.strip()
            for col, char in enumerate(line):
                x, y = col * TILE_SIZE, row * TILE_SIZE

                if char not in tile_mapping:
                    continue

                if char == '@':  # Player spawn
                    map_data['spawn_point'] = (x, y)
                    print(f"Player spawn at ({x}, {y})")

                elif char == 'E':  # Exit
                    map_data['exit_point'] = pygame.Rect(x, y, TILE_SIZE * 2, TILE_SIZE * 2)
                    print(f"Exit portal at ({x}, {y})")

                elif char == '#':  # Wall
                    map_data['walls'].append(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))

                elif char == 'O':  # Ore
                    offset = (TILE_SIZE - (TILE_SIZE // 2)) // 2
                    map_data['ore_deposits'].append(
                        pygame.Rect(x + offset, y + offset, TILE_SIZE // 2, TILE_SIZE // 2)
                    )

                elif char == 'B':  # Boss portal
                    map_data['boss_portal'] = pygame.Rect(x, y, TILE_SIZE * 2, TILE_SIZE * 2)
                    print(f"Boss portal at ({x}, {y})")

                # === Enemy spawn points ===
                elif char == 'e':  # Orc
                    sp = EnemySpawnPoint(x + TILE_SIZE // 2, y + TILE_SIZE // 2, "orc", respawn_time=30000)
                    map_data['enemy_spawns'].append(sp)

                elif char == 's':  # Strong enemy (elite orc)
                    sp = EnemySpawnPoint(x + TILE_SIZE // 2, y + TILE_SIZE // 2, "orc_strong", respawn_time=45000)
                    map_data['enemy_spawns'].append(sp)

                elif char == 'g':  # Goblin
                    sp = EnemySpawnPoint(x + TILE_SIZE // 2, y + TILE_SIZE // 2, "goblin", respawn_time=20000)
                    map_data['enemy_spawns'].append(sp)

        # Sync global list for game loop
        enemy_spawn_points = map_data['enemy_spawns']

        print(f"Map parsing complete: {len(enemy_spawn_points)} enemy spawn points found")
        for i, sp in enumerate(enemy_spawn_points, 1):
            print(f"  Spawn {i}: {sp.enemy_type} at ({sp.x}, {sp.y})")

    except FileNotFoundError:
        print(f"Could not load dungeon map: {dungeon1}")
        map_data = create_fallback_dungeon_with_enemies()
        enemy_spawn_points = map_data['enemy_spawns']

    return map_data

def apply_map_data(map_data):
    """Apply loaded map data to game globals."""
    global tree_rects, house_list, stone_rects, flower_tiles, leaf_tiles
    global npc_rect, miner_npc_rect, dungeon_portal, player_pos, map_offset_x, map_offset_y
    global boss1_portal
    
    # Clear existing data
    tree_rects.clear()
    house_list.clear() 
    stone_rects.clear()
    flower_tiles.clear()
    leaf_tiles.clear()
    
    # Apply borders (trees)
    tree_rects.extend(map_data['borders'])
    
    # Apply tiles
    for tile in map_data['tiles']:
        if tile['type'] == 'stone':
            stone_rects.append(tile['rect'])
        elif tile['type'] == 'flower':
            flower_tiles.append(tile['pos'])
        elif tile['type'] == 'leaf':
            leaf_tiles.append(tile['pos'])
    
    # Apply entities
    for entity in map_data['entities']:
        x, y = entity['pos']
        if entity['type'] == 'house':
            house_rect = pygame.Rect(x, y, TILE_SIZE * 2, TILE_SIZE * 2)
            house_list.append(house_rect)
            tree_rects.append(house_rect)  # Houses are also collision objects
        elif entity['type'] == 'portal':
            dungeon_portal = pygame.Rect(x, y, 50, 50)
            tree_rects.append(dungeon_portal)
        elif entity['type'] == 'boss1_portal':
            boss1_portal = pygame.Rect(x, y, 50, 50)
            tree_rects.append(boss1_portal)
        elif entity['type'] == 'npc':
            npc_rect = pygame.Rect(x, y, PLAYER_SIZE * 4, PLAYER_SIZE * 4)
        elif entity['type'] == 'miner':
            miner_npc_rect = pygame.Rect(x, y, PLAYER_SIZE, PLAYER_SIZE)
    
    # Set player spawn position
    spawn_x, spawn_y = map_data['spawn_point']
    map_offset_x = spawn_x - WIDTH // 2
    map_offset_y = spawn_y - HEIGHT // 2
    player_pos.center = (WIDTH // 2, HEIGHT // 2)
def create_default_map_data():
    """Create default map if file loading fails."""
    return {
        'tiles': [],
        'entities': [],
        'spawn_point': (WIDTH // 2, HEIGHT // 2),
        'borders': []
    }
# --- INIT ---
def init():
    """Initializes Pygame and sets up the screen."""
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Not Pokemon - Enhanced")
    
    # Initialize music system
    init_music()
    
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
def save_game_data(slot_number):
    """Save current game state to a file."""
    save_data = {
        'player': {
            'level': player.level,
            'health': player.health,
            'max_health': player.max_health,
            'damage': player.damage,
            'experience': player.experience,
            'experience_to_next': player.experience_to_next,
            'position': {'x': player_pos.x, 'y': player_pos.y}
        },
        'world': {
            'current_level': current_level,
            'map_offset_x': map_offset_x,
            'map_offset_y': map_offset_y
        },
        'inventory': [[{'name': item.name, 'count': item.count, 'category': item.category, 'damage': item.damage} if item else None 
                      for item in row] for row in inventory],
        'equipment': {
            'weapon': {'name': equipment_slots['weapon'].name, 'category': equipment_slots['weapon'].category, 'damage': equipment_slots['weapon'].damage} if equipment_slots['weapon'] else None
        },
        'quests': {
            'npc_quest_active': npc_quest_active,
            'npc_quest_completed': npc_quest_completed,
            'miner_quest_active': miner_quest_active,
            'miner_quest_completed': miner_quest_completed
        },
        'timestamp': pygame.time.get_ticks()
    }
    
    try:
        with open(f"save_slot_{slot_number}.json", 'w') as f:
            json.dump(save_data, f, indent=2)
        print(f"Game saved to slot {slot_number}")
        return True
    except Exception as e:
        print(f"Failed to save: {e}")
        return False

def load_game_data(slot_number):
    """Load game state from a file."""
    try:
        with open(f"save_slot_{slot_number}.json", 'r') as f:
            save_data = json.load(f)
        
        # Restore player data
        player.level = save_data['player']['level']
        player.health = save_data['player']['health']
        player.max_health = save_data['player']['max_health']
        player.damage = save_data['player']['damage']
        player.experience = save_data['player']['experience']
        player.experience_to_next = save_data['player']['experience_to_next']
        
        # Restore world state
        global current_level, map_offset_x, map_offset_y, player_pos
        current_level = save_data['world']['current_level']
        map_offset_x = save_data['world']['map_offset_x']
        map_offset_y = save_data['world']['map_offset_y']
        player_pos.x = save_data['player']['position']['x']
        player_pos.y = save_data['player']['position']['y']
        
        # Restore inventory
        global inventory
        for row in range(4):
            for col in range(4):
                item_data = save_data['inventory'][row][col]
                if item_data:
                    # You'll need to recreate the item with proper image
                    inventory[row][col] = recreate_item_from_data(item_data)
                else:
                    inventory[row][col] = None
        
        # Restore equipment
        weapon_data = save_data['equipment']['weapon']
        if weapon_data:
            equipment_slots['weapon'] = recreate_item_from_data(weapon_data)
        else:
            equipment_slots['weapon'] = None
            
        # Restore quest states
        global npc_quest_active, npc_quest_completed, miner_quest_active, miner_quest_completed
        npc_quest_active = save_data['quests']['npc_quest_active']
        npc_quest_completed = save_data['quests']['npc_quest_completed']
        miner_quest_active = save_data['quests']['miner_quest_active']
        miner_quest_completed = save_data['quests']['miner_quest_completed']
        
        print(f"Game loaded from slot {slot_number}")
        return True
        
    except FileNotFoundError:
        print(f"No save file found in slot {slot_number}")
        return False
    except Exception as e:
        print(f"Failed to load save: {e}")
        return False

def recreate_item_from_data(item_data):
    """Recreate an Item object from saved data."""
    # You'll need access to your assets to get the proper image
    # For now, create a basic item - you may need to modify this
    return Item(item_data['name'], None, item_data['count'], item_data['category'], item_data['damage'])

def load_save_slots():
    """Check which save slots have data."""
    global save_slots
    for i in range(4):
        try:
            with open(f"save_slot_{i+1}.json", 'r') as f:
                save_data = json.load(f)
                save_slots[i] = {
                    'level': save_data['player']['level'],
                    'timestamp': save_data['timestamp']
                }
        except:
            save_slots[i] = None

def start_new_game():
    """Initialize a new game with default values."""
    global current_level, map_offset_x, map_offset_y, player_pos
    global inventory, equipment_slots, npc_quest_active, npc_quest_completed
    global miner_quest_active, miner_quest_completed
    
    # Reset player
    player.level = 1
    player.health = PLAYER_MAX_HEALTH
    player.max_health = PLAYER_MAX_HEALTH
    player.damage = PLAYER_BASE_DAMAGE
    player.defense = PLAYER_BASE_DEFENSE
    player.experience = 0
    player.experience_to_next = 100
    
    # Reset world
    current_level = "world"
    map_offset_x = 0
    map_offset_y = 0
    player_pos.center = (WIDTH // 2, HEIGHT // 2)
    
    # Reset inventory and equipment
    inventory = [[None for _ in range(4)] for _ in range(4)]
    equipment_slots = {
    "weapon": None,
    "helmet": None, 
    "armor": None,
    "boots": None,
    "ring1": None,
    "ring2": None,
    "amulet": None,
    "shield": None
}
    
    # Reset quests
    npc_quest_active = False
    npc_quest_completed = False
    miner_quest_active = False
    miner_quest_completed = False
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

def load_attack_frames():
    """Loads attack frames from Player_action.png sheet."""
    try:
        sheet = pygame.image.load("Player_action.png").convert_alpha()
        cell_size = 32
        attack_frames = {"down": [], "right": [], "left": [], "up": []}

        # --- Down attack (row 0, col 1) ---
        rect = pygame.Rect(1 * cell_size, 0 * cell_size, cell_size, cell_size)
        down = sheet.subsurface(rect)
        attack_frames["down"].append(pygame.transform.scale(down, (PLAYER_SIZE, PLAYER_SIZE)))

        # --- Right attack (row 1, col 1) ---
        rect = pygame.Rect(1 * cell_size, 1 * cell_size, cell_size, cell_size)
        right = sheet.subsurface(rect)
        right_scaled = pygame.transform.scale(right, (PLAYER_SIZE, PLAYER_SIZE))
        left_scaled = pygame.transform.flip(right_scaled, True, False)
        attack_frames["right"].append(right_scaled)
        attack_frames["left"].append(left_scaled)

        # --- Up attack (row 2, col 1) ---
        rect = pygame.Rect(1 * cell_size, 2 * cell_size, cell_size, cell_size)
        up = sheet.subsurface(rect)
        attack_frames["up"].append(pygame.transform.scale(up, (PLAYER_SIZE, PLAYER_SIZE)))

        # Pad each with duplicates so you can animate smoother
        for key in attack_frames:
            attack_frames[key] = attack_frames[key] * 4  # repeat to make 4 frames

    except Exception as e:
        print("Error loading attack frames:", e)
        fallback = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE))
        fallback.fill((255, 0, 0))
        attack_frames = {
            "down": [fallback] * 4,
            "right": [fallback] * 4,
            "left": [fallback] * 4,
            "up": [fallback] * 4
        }

    return attack_frames




def load_enemy_frames():
    """Load and scale all enemy animation frames."""
    frames = {}

    try:
        # --- ORC FRAMES ---
        orc_sheet = pygame.image.load("orc-attack01.png").convert_alpha()
        total_frames = 6
        frame_width = orc_sheet.get_width() // total_frames
        frame_height = orc_sheet.get_height()

        orc_frames = []
        for i in range(total_frames):
            frame_rect = pygame.Rect(i * frame_width, 0, frame_width, frame_height)
            frame_surface = frame_rect_to_surface(orc_sheet, frame_rect)
            frame_surface = pygame.transform.scale(frame_surface, (PLAYER_SIZE * 4, PLAYER_SIZE * 4))
            orc_frames.append(frame_surface)

        frames["orc"] = orc_frames

    except Exception as e:
        print("Error loading orc frames:", e)
        # Fallback brown squares if sprite sheet fails
        fallback_frame = pygame.Surface((PLAYER_SIZE * 4, PLAYER_SIZE * 4))
        fallback_frame.fill((139, 69, 19))
        frames["orc"] = [fallback_frame] * 4

    # Add more enemies here in the future (goblins, bosses, etc.)
    # Example template:
    # frames["goblin"] = [...]

    print("Enemy frames loaded:", {etype: len(flist) for etype, flist in frames.items()})
    return frames

def frame_rect_to_surface(sheet, rect):
    """Helper to extract a subsurface safely."""
    return sheet.subsurface(rect).copy()

def load_assets():
    """Loads all game assets, items, NPCs, UI icons, tiles, and boss room assets."""

    # --- Utility ---
    def create_fallback_surface(size, color):
        surf = pygame.Surface(size)
        surf.fill(color)
        return surf

    def try_load_image(path, size=None, color=(255, 0, 255)):
        """Tries to load an image; falls back to colored surface if missing."""
        try:
            img = pygame.image.load(path).convert_alpha()
            if size:
                img = pygame.transform.scale(img, size)
            return img
        except:
            return create_fallback_surface(size if size else (32, 32), color)

    # --- Tiles ---
    grass_image = try_load_image(os.path.join("Tiles", "grass_middle.png"), (TILE_SIZE, TILE_SIZE), (34, 139, 34))
    tree_image = try_load_image(os.path.join("Tiles", "tree.png"), (TILE_SIZE + 5, TILE_SIZE + 5), (101, 67, 33))
    house_image = try_load_image(os.path.join("Tiles", "house.png"), (TILE_SIZE * 2, TILE_SIZE * 2), (139, 69, 19))
    house1_image = try_load_image(os.path.join("Tiles", "house1.png"), (TILE_SIZE * 2, TILE_SIZE * 2), (160, 82, 45))

    # --- Outdoor Stuff (sheet) ---
    try:
        sheet = pygame.image.load("OutdoorStuff.PNG").convert_alpha()
        flower_positions = [(0, 144), (16, 144)]
        flower_images = [
            pygame.transform.scale(sheet.subsurface(pygame.Rect(x, y, 16, 16)), (30, 30))
            for (x, y) in flower_positions
        ]
        leaf_image = pygame.transform.scale(sheet.subsurface(pygame.Rect(0, 0, 16, 16)), (25, 25))
        log_image = pygame.transform.scale(sheet.subsurface(pygame.Rect(4, 110, 24, 24)), (TILE_SIZE, TILE_SIZE))
    except:
        flower_images = [
            create_fallback_surface((30, 30), (255, 192, 203)),
            create_fallback_surface((30, 30), (255, 20, 147))
        ]
        leaf_image = create_fallback_surface((25, 25), (34, 139, 34))
        log_image = create_fallback_surface((TILE_SIZE, TILE_SIZE), (139, 69, 19))

    # --- Items ---
    potion_image = try_load_image("PotionR.png", (TILE_SIZE, TILE_SIZE), (150, 0, 150))
    coin_image = try_load_image("Coin.png", (TILE_SIZE, TILE_SIZE), (255, 215, 0))
    axe_image = try_load_image("axe.png", (TILE_SIZE, TILE_SIZE), (139, 69, 19))
    pickaxe_image = try_load_image("pickaxe.png", (TILE_SIZE, TILE_SIZE), (105, 105, 105))
    stone_image = try_load_image("stone.png", (TILE_SIZE // 2, TILE_SIZE // 2), (150, 150, 150))
    ore_image = try_load_image("ore.png", (TILE_SIZE // 2, TILE_SIZE // 2), (139, 69, 19))
    chest_image = try_load_image("chest.png", (TILE_SIZE, TILE_SIZE), (139, 69, 19))
    helmet_image = try_load_image("helmet.png", (TILE_SIZE, TILE_SIZE), (105, 105, 105))
    boots_image = try_load_image("boots.png", (TILE_SIZE, TILE_SIZE), (101, 67, 33))
    # --- UI Icons ---
    backpack_icon = try_load_image("bag.png", (ICON_SIZE, ICON_SIZE), (101, 67, 33))
    crafting_icon = try_load_image("craft.png", (ICON_SIZE, ICON_SIZE), (160, 82, 45))
    equipment_icon = try_load_image("equipped.png", (ICON_SIZE, ICON_SIZE), (105, 105, 105))

    # --- NPCs ---
    try:
        soldier_sheet = pygame.image.load("soldier.png").convert_alpha()
        npc_image = pygame.transform.scale(
            soldier_sheet.subsurface(pygame.Rect(0, 0, 100, 100)),
            (PLAYER_SIZE * 4, PLAYER_SIZE * 4)
        )
    except:
        npc_image = create_fallback_surface((PLAYER_SIZE * 4, PLAYER_SIZE * 4), (255, 255, 0))

    try:
        miner_sheet = pygame.image.load("npc1.png").convert_alpha()
        frame_width = miner_sheet.get_width() // 8
        frame_height = miner_sheet.get_height()
        miner_image = pygame.transform.scale(
            miner_sheet.subsurface(pygame.Rect(0, 0, frame_width, frame_height)),
            (PLAYER_SIZE, PLAYER_SIZE)
        )
    except:
        miner_image = create_fallback_surface((PLAYER_SIZE, PLAYER_SIZE), (160, 82, 45))

    # --- Portal & Dungeon ---
    boss1_portal = try_load_image("boss1_portal.png", (50, 50), (128, 0, 128))
    portal_image = try_load_image("cave.png", (50, 50), (64, 0, 128))
    dungeon_wall_image = try_load_image("wall.png", (TILE_SIZE, TILE_SIZE), (64, 64, 64))
    dungeon_floor_image = try_load_image("caveFloor.png", (TILE_SIZE, TILE_SIZE), (32, 32, 32))

    # --- Interiors ---
    try:
        interiors = [
            pygame.transform.scale(pygame.image.load("indoor2.png").convert_alpha(), (WIDTH, HEIGHT)),
            pygame.transform.scale(pygame.image.load("indoor3.png").convert_alpha(), (WIDTH, HEIGHT))
        ]
    except:
        interiors = [
            create_fallback_surface((WIDTH, HEIGHT), (101, 67, 33)),
            create_fallback_surface((WIDTH, HEIGHT), (139, 69, 19))
        ]


    # --- Items as objects ---
    log_item = Item("Log", log_image)
    axe_item = Item("Axe", axe_image, category="Weapon", damage=20)
    pickaxe_item = Item("Pickaxe", pickaxe_image, category="Weapon", damage=15)
    stone_item = Item("Stone", stone_image)
    ore_item = Item("Ore", ore_image)
    flower_item = Item("Flower", flower_images[0])
    potion_item = Item("Potion", potion_image)
    coin_item = Item("Coin", coin_image)
    chest_item = Item("Chest Armor", chest_image, category="Armor", damage=0, defense=10)
    helmet_item = Item("Helmet", helmet_image, category="Helmet", damage=0, defense=5)
    boots_item = Item("Boots", boots_image, category="Boots", damage=0, defense=5)
    # --- Boss Door Frames ---
    boss_door_frames = load_boss_door_frames()

    # --- Build dictionary ---
    assets = {
        # Tiles
        "grass": grass_image,
        "tree": tree_image,
        "house": house_image,
        "house1": house1_image,
        "interiors": interiors,
        "flowers": flower_images,
        "leaf": leaf_image,

        # Portal / Dungeon
        "boss1_portal": boss1_portal,
        "portal": portal_image,
        "dungeon_wall": dungeon_wall_image,
        "dungeon_floor": dungeon_floor_image,

        # Fonts
        "font": pygame.font.SysFont(None, 36),
        "small_font": pygame.font.SysFont(None, 24),
        "large_font": pygame.font.SysFont(None, 48),

        # UI
        "backpack_icon": backpack_icon,
        "crafting_icon": crafting_icon,
        "equipment_icon": equipment_icon,

        # Items
        "log_item": log_item,
        "axe_item": axe_item,
        "pickaxe_item": pickaxe_item,
        "stone_item": stone_item,
        "ore_item": ore_item,
        "stone_img": stone_image,
        "ore_img": ore_image,
        "flower_item": flower_item,
        "potion_item": potion_item,
        "coin_item": coin_item,
        "chest_item": chest_item,
        "helmet_item": helmet_item,
        "boots_item": boots_item,
        # NPCs
        "npc_image": npc_image,
        "miner_image": miner_image,

        # Boss
        "boss_door_frames": boss_door_frames,
    }

    return assets


def load_boss_door_frames():
    """Load the boss door frames from the sprite sheet."""
    try:
        door_sheet = pygame.image.load("boss1_portal.png").convert_alpha()
        frame_width = door_sheet.get_width() // 12
        frame_height = door_sheet.get_height()

        closed_door_rect = pygame.Rect(0, 0, frame_width, frame_height)
        closed_door_frame = door_sheet.subsurface(closed_door_rect).copy()

        door_size = (TILE_SIZE * 2, TILE_SIZE * 2)
        closed_door_scaled = pygame.transform.scale(closed_door_frame, door_size)

        return {
            "closed": closed_door_scaled,
            "frame_width": frame_width,
            "frame_height": frame_height
        }
    except:
        fallback_door = pygame.Surface((TILE_SIZE * 2, TILE_SIZE * 2))
        fallback_door.fill((100, 50, 150))
        return {
            "closed": fallback_door,
            "frame_width": 64,
            "frame_height": 64
        }



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
def setup_indoor_colliders():
    """Set up collision boundaries for indoor areas."""
    global indoor_colliders
    indoor_colliders[:] = [
        pygame.Rect(0, 0, WIDTH, 100),           # top
        pygame.Rect(0, HEIGHT-10, WIDTH, 10),   # bottom
        pygame.Rect(0, 0, 10, HEIGHT),          # left
        pygame.Rect(WIDTH-10, 0, 10, HEIGHT)    # right
    ]
def create_fallback_dungeon_with_enemies():
    """Create a fallback dungeon with enemy spawns if file loading fails."""
    print("Creating fallback dungeon with enemies...")
    
    map_data = {
        'walls': [],
        'ore_deposits': [],
        'spawn_point': (5 * TILE_SIZE, 5 * TILE_SIZE),
        'exit_point': pygame.Rect(25 * TILE_SIZE, 25 * TILE_SIZE, TILE_SIZE * 2, TILE_SIZE * 2),
        'boss_portal': None,
        'enemy_spawns': []
    }
    
    # Create walls around the border
    for x in range(30):
        map_data['walls'].append(pygame.Rect(x * TILE_SIZE, 0, TILE_SIZE, TILE_SIZE))  # Top
        map_data['walls'].append(pygame.Rect(x * TILE_SIZE, 29 * TILE_SIZE, TILE_SIZE, TILE_SIZE))  # Bottom
    
    for y in range(1, 29):
        map_data['walls'].append(pygame.Rect(0, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))  # Left
        map_data['walls'].append(pygame.Rect(29 * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))  # Right
    
    # Add some ore deposits
    ore_positions = [(10, 10), (15, 8), (20, 12), (8, 18), (22, 20)]
    for x, y in ore_positions:
        offset = (TILE_SIZE - (TILE_SIZE // 2)) // 2
        map_data['ore_deposits'].append(pygame.Rect(x * TILE_SIZE + offset, y * TILE_SIZE + offset, TILE_SIZE // 2, TILE_SIZE // 2))
    
    # Add enemy spawn points
    enemy_spawn_positions = [
        (10, 15, "orc"),
        (20, 10, "orc"), 
        (15, 20, "goblin"),
        (8, 12, "orc"),
        (25, 15, "orc")
    ]
    
    for x, y, enemy_type in enemy_spawn_positions:
        spawn_point = EnemySpawnPoint(x * TILE_SIZE, y * TILE_SIZE, enemy_type, respawn_time=25000)
        map_data['enemy_spawns'].append(spawn_point)
        print(f"Added fallback {enemy_type} spawn at ({x * TILE_SIZE}, {y * TILE_SIZE})")
    
    return map_data
def setup_dungeon_with_enemy_spawns(filename="dungeon1.txt"):
    global dungeon_walls, stone_rects, boss1_portal, dungeon_exit, enemies, enemy_spawn_points

    print(f"Setting up dungeon: {filename}")

    # Clear existing data (DO THIS ONCE)
    dungeon_walls.clear()
    boss1_portal = None
    enemies.clear()
    enemy_spawn_points.clear()
    stone_rects.clear()  # Clear dungeon stones
    
    # Load the enhanced map
    map_data = load_dungeon_map_with_enemies(filename)
    
    # Apply the data
    dungeon_walls.extend(map_data['walls'])
    stone_rects.extend(map_data['ore_deposits'])
    dungeon_exit = map_data['exit_point']
    enemy_spawn_points.extend(map_data['enemy_spawns'])
    
    print(f"Dungeon setup - {len(enemy_spawn_points)} spawn points loaded")
    
    # Set boss portal if it exists
    if map_data.get('boss_portal'):
        boss1_portal = map_data['boss_portal']
    
    # Initial enemy spawning - spawn immediately
    current_time = pygame.time.get_ticks()
    spawned_count = 0
    
    for spawn_point in enemy_spawn_points:
        spawn_point.last_spawn_time = 0  # Force immediate spawn
        enemy = spawn_point.spawn_enemy(current_time)
        if enemy:
            spawned_count += 1
            print(f"Spawned {enemy.type} at ({enemy.rect.x}, {enemy.rect.y})")
    
    print(f"Total enemies spawned: {spawned_count}")
    print(f"Enemies list size: {len(enemies)}")
    
    # Return spawn point
    spawn_x, spawn_y = map_data['spawn_point']
    spawn_x += 100
    spawn_x = max(2 * TILE_SIZE, min(spawn_x, (DUNGEON_SIZE-3) * TILE_SIZE))
    spawn_y = max(2 * TILE_SIZE, min(spawn_y, (DUNGEON_SIZE-3) * TILE_SIZE))
    
    return (spawn_x, spawn_y)

def setup_colliders():
    """Generates the world colliders for the current level."""
    global tree_rects, house_list, indoor_colliders, flower_tiles, leaf_tiles, stone_rects
    global npc_rect, dungeon_portal, miner_npc_rect

    if current_level == "world":
        # Try to load current map, fallback to procedural generation
        if hasattr(setup_colliders, 'current_map'):
            map_data = load_text_map(setup_colliders.current_map)
            apply_map_data(map_data)
        else:
            # Try to load default map, fallback to generated world
            try:
                map_data = load_text_map("forest.txt")
                if map_data and (map_data['tiles'] or map_data['entities'] or map_data['borders']):
                    apply_map_data(map_data)
                else:
                    generate_default_world()  # Use the function we defined above
            except:
                generate_default_world()  # Use the function we defined above
                
    # Setup indoor colliders for houses
    setup_indoor_colliders()
    
    # Setup dungeon if needed (but don't clear existing dungeon setup)
    if current_level == "dungeon" and not dungeon_walls:
        setup_dungeon()
    
    # Setup dungeon if needed (but don't clear existing dungeon setup)
    if current_level == "dungeon" and not dungeon_walls:
        setup_dungeon()
def draw_main_menu(screen, assets):
    """Draw the main menu screen with enhanced mouse hover effects."""
    screen.fill((20, 30, 40))  # Dark blue background
    
    # Get mouse position for hover effects
    mouse_pos = pygame.mouse.get_pos()
    
    # Title
    title_text = assets["large_font"].render("Adventure Game", True, (255, 255, 255))
    title_rect = title_text.get_rect(center=(WIDTH // 2, HEIGHT // 4))
    screen.blit(title_text, title_rect)
    
    # Menu options with enhanced hover effects
    menu_options = ["New Game", "Load Game", "Exit"]
    
    for i, option in enumerate(menu_options):
        # Determine colors based on selection and hover
        if i == menu_selected_option:
            text_color = (255, 255, 0)  # Yellow when selected
            bg_color = (50, 50, 100)   # Blue background
        else:
            text_color = (255, 255, 255)  # White when not selected
            bg_color = None
        
        option_text = assets["font"].render(option, True, text_color)
        option_rect = option_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + i * 50))
        
        # Draw background for selected option
        if bg_color:
            bg_rect = option_rect.inflate(40, 20)
            pygame.draw.rect(screen, bg_color, bg_rect, border_radius=10)
        
        screen.blit(option_text, option_rect)
        
        # Draw selection border
        if i == menu_selected_option:
            pygame.draw.rect(screen, (255, 255, 0), option_rect.inflate(20, 10), 2, border_radius=5)

def draw_save_select_menu(screen, assets):
    """Draw the save slot selection screen."""
    screen.fill((30, 20, 40))  # Different background
    
    # Title
    title_text = assets["large_font"].render("Select Save Slot", True, (255, 255, 255))
    title_rect = title_text.get_rect(center=(WIDTH // 2, HEIGHT // 4))
    screen.blit(title_text, title_rect)
    
    # Save slots
    for i in range(4):
        slot_y = HEIGHT // 2 + i * 60 - 120
        slot_rect = pygame.Rect(WIDTH // 2 - 200, slot_y, 400, 50)
        
        # Highlight selected slot
        color = (100, 100, 100) if i == selected_save_slot - 1 else (50, 50, 50)
        pygame.draw.rect(screen, color, slot_rect)
        pygame.draw.rect(screen, (255, 255, 255), slot_rect, 2)
        
        # Slot content
        if save_slots[i]:
            slot_text = f"Slot {i+1}: Level {save_slots[i]['level']}"
        else:
            slot_text = f"Slot {i+1}: Empty"
            
        text_surf = assets["font"].render(slot_text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=slot_rect.center)
        screen.blit(text_surf, text_rect)
    
    # Instructions
    instruction_text = assets["small_font"].render("Press ENTER to select, ESC to go back", True, (200, 200, 200))
    instruction_rect = instruction_text.get_rect(center=(WIDTH // 2, HEIGHT - 50))
    screen.blit(instruction_text, instruction_rect)
    # --- Indoor colliders ---
    setup_indoor_colliders()

    # --- Setup dungeon if needed ---
    if not dungeon_walls:
        setup_dungeon()
        boss_door_rect = boss1_portal
def load_map(map_name):
    """Load a specific map by name."""
    setup_colliders.current_map = f"{map_name}.txt"
    setup_colliders()
    print(f"Loaded map: {map_name}")
def handle_boss_room_state(screen, assets):
    """Handle boss room game state."""
    # For now, redirect to playing state with a fixed dt
    dt = 16  # Approximately 60 FPS
    handle_playing_state(screen, assets, dt)
def generate_default_world():
    """Generate a basic world if map loading fails."""
    global tree_rects, house_list, stone_rects, flower_tiles, leaf_tiles
    global npc_rect, miner_npc_rect, dungeon_portal
    
    # Clear existing
    tree_rects.clear()
    house_list.clear()
    stone_rects.clear()
    flower_tiles.clear()
    leaf_tiles.clear()
    
    # Create basic world layout
    # Trees around border
    for x in range(0, 40):
        tree_rects.append(pygame.Rect(x * TILE_SIZE, 0, TILE_SIZE, TILE_SIZE))  # Top
        tree_rects.append(pygame.Rect(x * TILE_SIZE, 39 * TILE_SIZE, TILE_SIZE, TILE_SIZE))  # Bottom
    
    for y in range(1, 39):
        tree_rects.append(pygame.Rect(0, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))  # Left
        tree_rects.append(pygame.Rect(39 * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))  # Right
    
    # Add some scattered trees
    for _ in range(20):
        x = random.randint(3, 36) * TILE_SIZE
        y = random.randint(3, 36) * TILE_SIZE
        tree_rects.append(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))
    
    # Add stones
    for _ in range(15):
        x = random.randint(2, 37) * TILE_SIZE
        y = random.randint(2, 37) * TILE_SIZE
        stone_rects.append(pygame.Rect(x, y, TILE_SIZE//2, TILE_SIZE//2))
    
    # Add houses
    house_list.append(pygame.Rect(10 * TILE_SIZE, 10 * TILE_SIZE, TILE_SIZE * 2, TILE_SIZE * 2))
    house_list.append(pygame.Rect(30 * TILE_SIZE, 15 * TILE_SIZE, TILE_SIZE * 2, TILE_SIZE * 2))
    
    # Add NPCs
    npc_rect = pygame.Rect(15 * TILE_SIZE, 20 * TILE_SIZE, PLAYER_SIZE * 4, PLAYER_SIZE * 4)
    miner_npc_rect = pygame.Rect(25 * TILE_SIZE, 25 * TILE_SIZE, PLAYER_SIZE, PLAYER_SIZE)
    
    # Add dungeon portal
    dungeon_portal = pygame.Rect(20 * TILE_SIZE, 30 * TILE_SIZE, 50, 50)
    
    # Add flowers
    for _ in range(10):
        fx = random.randint(2, 37) * TILE_SIZE + 10
        fy = random.randint(2, 37) * TILE_SIZE + 10
        flower_tiles.append((fx, fy, random.randint(0, 1)))
    
    print("Generated default world")
def give_starting_items(assets):
    """Adds initial items to the inventory."""
    for _ in range(20):
        add_item_to_inventory(assets["stone_item"])
    
    add_item_to_inventory(assets["axe_item"])
    add_item_to_inventory(assets["pickaxe_item"])

# COMPLETE BUG FIXES - Replace these functions in your code

def spawn_enemy_in_dungeon():
    """Spawn an enemy in a valid location in the dungeon."""
    global last_enemy_spawn, enemies

    current_time = pygame.time.get_ticks()
    if current_time - last_enemy_spawn < 3000:
        return

    if len(enemies) >= MAX_ENEMIES:
        return

    # Try to find a safe spawn position
    for attempt in range(50):
        # Spawn in a smaller, safer area
        spawn_x = random.randint(5 * TILE_SIZE, (DUNGEON_SIZE - 5) * TILE_SIZE)
        spawn_y = random.randint(5 * TILE_SIZE, (DUNGEON_SIZE - 5) * TILE_SIZE)
        
        test_rect = pygame.Rect(spawn_x, spawn_y, PLAYER_SIZE, PLAYER_SIZE)
        
        # Check if position is safe
        collision = False
        player_world_rect = get_player_world_rect()
        
        # Check walls
        for wall in dungeon_walls:
            if test_rect.colliderect(wall):
                collision = True
                break
        
        # Check stones/ore
        if not collision:
            for stone in stone_rects:
                if test_rect.colliderect(stone):
                    collision = True
                    break
        
        # Check distance from player (don't spawn too close)
        if not collision:
            distance = math.hypot(spawn_x - player_world_rect.centerx, 
                                spawn_y - player_world_rect.centery)
            if distance < 150:
                collision = True
        
        if not collision:
            enemy = Enemy(spawn_x, spawn_y, "orc")
            enemies.append(enemy)
            last_enemy_spawn = current_time
            print(f"Spawned orc at ({spawn_x}, {spawn_y})")
            return
    
    print("Could not find safe spawn position for enemy")

def handle_combat(current_time):
    """Enhanced combat system that handles boss fights and regular enemies."""
    global current_level, map_offset_x, map_offset_y, player_pos
    
    player_world_rect = get_player_world_rect()
    player.rect = player_world_rect

    # Enemies attacking player
    for enemy in enemies[:]:  # Create a copy to avoid modification during iteration
        if isinstance(enemy, Boss):
            # Special boss attack handling
            if enemy.attack_player(player_world_rect, current_time):
                # Boss attacks can have different damage multipliers based on phase
                base_damage = enemy.damage
                
                # Phase-based damage scaling
                if enemy.phase == 2:
                    if "Double Strike" in [text.text for text in floating_texts]:
                        base_damage = int(base_damage * 1.5)  # Double strike bonus
                elif enemy.phase == 3:
                    if "Berserker Strike" in [text.text for text in floating_texts]:
                        base_damage = int(base_damage * 1.8)  # Berserker bonus
                
                # Apply damage
                if player.take_damage(base_damage, current_time):
                    handle_player_death()
                    return
        else:
            # Regular enemy attack
            if enemy.attack_player(player_world_rect, current_time):
                if player.take_damage(enemy.damage, current_time):
                    handle_player_death()
                    return

def handle_player_death():
    """Handle what happens when player dies."""
    global current_level, map_offset_x, map_offset_y, player_pos
    
    print("You died!")
    
    # Always respawn at the world spawn point regardless of where player died
    current_level = "world"
    
    # Get the player spawn point from map data
    # You can either load it from your map file or use a default
    try:
        # Try to load spawn from current map
        map_data = load_text_map("forest.txt")  # or whatever your main map is called
        spawn_world_x, spawn_world_y = map_data['spawn_point']
    except:
        # Fallback spawn point if map loading fails
        spawn_world_x = WIDTH // 2
        spawn_world_y = HEIGHT // 2
    
    # Set camera to center on spawn location
    map_offset_x = spawn_world_x - WIDTH // 2
    map_offset_y = spawn_world_y - HEIGHT // 2
    
    # Player screen position stays centered
    player_pos.center = (WIDTH // 2, HEIGHT // 2)
    
    # Restore some health and clear enemies
    player.health = player.max_health // 2
    enemies.clear()
    
    print(f"Respawned at player spawn ({spawn_world_x}, {spawn_world_y})")

def handle_boss_combat_feedback():
    """Add special visual effects and feedback for boss fights."""
    for enemy in enemies:
        if isinstance(enemy, Boss):
            # Screen shake effect during boss phase changes
            if hasattr(enemy, 'last_phase_change'):
                time_since_phase_change = pygame.time.get_ticks() - enemy.last_phase_change
                if time_since_phase_change < 500:  # Screen shake for 0.5 seconds
                    shake_intensity = max(0, 10 - (time_since_phase_change / 25))
                    # You can implement screen shake by slightly offsetting the camera
                    # This is just a placeholder for the concept
                    pass

def draw_boss_health_bar(screen, assets, boss):
    """Draw a special health bar for the boss at the top of the screen."""
    if not isinstance(boss, Boss):
        return
        
    # Boss health bar at top of screen
    bar_width = WIDTH - 100
    bar_height = 20
    bar_x = 50
    bar_y = 50
    
    # Background
    bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
    pygame.draw.rect(screen, (60, 0, 0), bg_rect)
    pygame.draw.rect(screen, (255, 255, 255), bg_rect, 3)
    
    # Health bar with phase-based colors
    health_ratio = boss.health / boss.max_health
    health_width = int(bar_width * health_ratio)
    
    # Color based on phase
    if boss.phase == 1:
        health_color = (200, 100, 100)  # Light red
    elif boss.phase == 2:
        health_color = (255, 150, 0)    # Orange
    else:  # Phase 3
        health_color = (255, 50, 50)    # Bright red
    
    health_rect = pygame.Rect(bar_x, bar_y, health_width, bar_height)
    pygame.draw.rect(screen, health_color, health_rect)
    
    # Boss name and phase
    name_text = f"{boss.name} - Phase {boss.phase}"
    text_surf = assets["font"].render(name_text, True, (255, 255, 255))
    text_rect = text_surf.get_rect(center=(WIDTH // 2, bar_y - 15))
    screen.blit(text_surf, text_rect)
    
    # Health numbers
    health_text = f"{boss.health}/{boss.max_health}"
    health_surf = assets["small_font"].render(health_text, True, (255, 255, 255))
    health_text_rect = health_surf.get_rect(center=(WIDTH // 2, bar_y + bar_height // 2))
    screen.blit(health_surf, health_text_rect)

def update_boss_room_enemies(dt, current_time, player_world_rect, obstacles):
    """Special update function for boss room enemies."""
    for enemy in enemies[:]:  # Create copy for safe iteration
        if isinstance(enemy, Boss):
            # Update boss with enhanced AI
            enemy.update(dt, current_time, player_world_rect, obstacles)
            
            # Check if boss is defeated
            if enemy.health <= 0:
                # Boss victory!
                floating_texts.append(FloatingText(
                    "VICTORY!",
                    (WIDTH // 2, HEIGHT // 2),
                    color=(255, 215, 0),
                    lifetime=5000
                ))
                
                # Give boss rewards
                player.gain_experience(enemy.experience_reward)
                
                # Maybe spawn some treasure or unlock something
                print(f"Boss defeated! Gained {enemy.experience_reward} experience!")
                
                # Remove boss from enemies list
                enemies.remove(enemy)
                
                # Could trigger end-game sequence or unlock new areas
                
        else:
            # Regular enemy update
            enemy.update(dt, current_time, player_world_rect, obstacles)


def handle_boss_room_interactions(event, player_pos, assets):
    """Handle interactions specific to the boss room."""
    global current_level, map_offset_x, map_offset_y
    
    if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
        # Exit door
        exit_door = pygame.Rect(WIDTH // 2 - 40, HEIGHT - 50, 80, 40)
        if player_pos.colliderect(exit_door.inflate(20, 20)):
            # Return to dungeon
            current_level = "dungeon"
            
            # Spawn back at boss door location in dungeon
            if boss1_portal:
                spawn_x = boss1_portal.centerx
                spawn_y = boss1_portal.centery + 100  # Slightly below the door
            else:
                spawn_x = 20 * TILE_SIZE
                spawn_y = 15 * TILE_SIZE
            
            map_offset_x = spawn_x - WIDTH // 2
            map_offset_y = spawn_y - HEIGHT // 2
            player_pos.center = (WIDTH // 2, HEIGHT // 2)
            
            print("Returned to dungeon from boss room")
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
                # FIXED: Copy ALL attributes including defense
                new_item = Item(
                    item_to_add.name, 
                    item_to_add.image, 
                    count=1,
                    category=item_to_add.category, 
                    damage=item_to_add.damage,
                    defense=item_to_add.defense  # This was missing!
                )
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
    """Enhanced equip function that handles different equipment types."""
    global equipment_slots
    
    if not item_to_equip:
        return False
        
    # FIXED: Updated slot mapping to match your actual item names
    slot_mapping = {
        # Weapons
        "Weapon": "weapon",
        "Axe": "weapon", 
        "Pickaxe": "weapon",
        "Sword": "weapon",

        # Armor - FIXED: Added "Chest Armor" mapping
        "Helmet": "helmet",
        "Chest Armor": "armor",  # This was missing!
        "Armor": "armor",   # Keep as alias
        "Boots": "boots",

        # Accessories
        "Ring": "ring1",
        "Amulet": "amulet",
        "Shield": "shield"
    }

    # Find appropriate slot
    target_slot = None
    if hasattr(item_to_equip, 'category') and item_to_equip.category in slot_mapping:
        target_slot = slot_mapping[item_to_equip.category]
    elif item_to_equip.name in slot_mapping:
        target_slot = slot_mapping[item_to_equip.name]
    
    if not target_slot:
        print(f"Cannot equip {item_to_equip.name} - no suitable slot found")
        print(f"Item category: {getattr(item_to_equip, 'category', 'None')}")  # Debug info
        return False
    
    # Handle rings specially
    if target_slot.startswith("ring"):
        if equipment_slots["ring1"] is None:
            target_slot = "ring1"
        elif equipment_slots["ring2"] is None:
            target_slot = "ring2"
        else:
            print("Both ring slots are occupied")
            return False
    
    # If slot is occupied, return old item to inventory first
    if equipment_slots[target_slot] is not None:
        old_item = equipment_slots[target_slot]
        if not add_item_to_inventory(old_item):
            print("Inventory is full, cannot swap equipment")
            return False
    
    # Equip the new item
    equipment_slots[target_slot] = item_to_equip
    print(f"{item_to_equip.name} equipped to {target_slot} slot!")
    print(f"Defense value: {item_to_equip.defense}")  # Debug info
    return True

def unequip_item_from_slot(slot_name):
    """Unequip item from a specific slot."""
    global equipment_slots  # Make sure we can access the global equipment_slots
    
    item_to_unequip = equipment_slots.get(slot_name)
    if item_to_unequip:
        if add_item_to_inventory(item_to_unequip):
            equipment_slots[slot_name] = None
            print(f"{item_to_unequip.name} unequipped from {slot_name}!")
            return True
        else:
            print("Inventory is full, cannot unequip.")
    return False
# Fixed inventory click handling in main game loop
def handle_inventory_click(mouse_pos):
    """Handle clicking on inventory slots to equip items."""
    global inventory  # Make sure we can access the global inventory
    
    if not show_inventory:
        return False
        
    for row in range(4):
        for col in range(4):
            slot_x = INVENTORY_X + INVENTORY_GAP + col * (INVENTORY_SLOT_SIZE + INVENTORY_GAP)
            slot_y = INVENTORY_Y + 40 + INVENTORY_GAP + row * (INVENTORY_SLOT_SIZE + INVENTORY_GAP)
            slot_rect = pygame.Rect(slot_x, slot_y, INVENTORY_SLOT_SIZE, INVENTORY_SLOT_SIZE)
            
            if slot_rect.collidepoint(mouse_pos):
                item_to_equip = inventory[row][col]
                if item_to_equip:
                    # Check if item can be equipped
                    if (hasattr(item_to_equip, 'category') and item_to_equip.category in ["Weapon", "Armor"]) or \
                       item_to_equip.name in ["Axe", "Pickaxe", "Sword", "Helmet", "Chest", "Boots"]:
                        if equip_item(item_to_equip):
                            inventory[row][col] = None  # Remove from inventory
                            print(f"Equipped {item_to_equip.name}")
                        return True
                    else:
                        print(f"{item_to_equip.name} cannot be equipped")
                return True
    return False


def handle_equipment_click(mouse_pos, slot_rects):
    """Handle clicking on equipment slots to unequip items."""
    if not show_equipment:
        return
        
    for slot_name, slot_rect in slot_rects.items():
        if slot_rect.collidepoint(mouse_pos):
            unequip_item_from_slot(slot_name)
            return True
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
def draw_health_bar(screen, x, y, current_health, max_health, width=100, height=10):
    """Draws a health bar at the specified position."""
    # Background (red)
    bg_rect = pygame.Rect(x, y, width, height)
    pygame.draw.rect(screen, (139, 0, 0), bg_rect)
    
    # Health (green)
    health_ratio = max(0, current_health / max_health)
    health_width = int(width * health_ratio)
    health_rect = pygame.Rect(x, y, health_width, height)
    pygame.draw.rect(screen, (0, 139, 0), health_rect)
    
    # Border
    pygame.draw.rect(screen, (255, 255, 255), bg_rect, 1)

def draw_player_stats(screen, assets, player_frames, attack_frames, chopping_frames):
    """Draws player stats in the top-left corner with player portrait."""
    y_offset = 10
    
    # Draw player portrait (small version of current frame)
    portrait_size = 32
    portrait_rect = pygame.Rect(10, y_offset, portrait_size, portrait_size)
    
    # Get current player frame with bounds checking
    if is_attacking:
        frames = attack_frames[last_direction]
        frame_index = min(player_frame_index, len(frames) - 1)  # Clamp to valid range
        current_frame = frames[frame_index]

    elif is_chopping or is_mining:
        chop_direction = last_direction if last_direction in chopping_frames else "down"
        frames = chopping_frames[chop_direction]
        frame_index = min(player_frame_index, len(frames) - 1)  # Clamp to valid range
        current_frame = frames[frame_index]
    else:
        frame_set = player_frames.get(current_direction, player_frames["idle"])
        frame_index = min(player_frame_index, len(frame_set) - 1)  # Clamp to valid range
        current_frame = frame_set[frame_index]
    
    # Scale and draw portrait
    portrait_frame = pygame.transform.scale(current_frame, (portrait_size, portrait_size))
    screen.blit(portrait_frame, portrait_rect)
    
    # Draw border around portrait
    pygame.draw.rect(screen, (255, 255, 255), portrait_rect, 2)
    
    # Health bar (moved right to make room for portrait)
    health_bar_x = portrait_rect.right + 10
    draw_health_bar(screen, health_bar_x, y_offset, player.health, player.max_health, 120, 15)
    health_text = f"Health: {player.health}/{player.max_health}"
    text_surf = assets["small_font"].render(health_text, True, (255, 255, 255))
    screen.blit(text_surf, (health_bar_x + 130, y_offset))
    y_offset += 25
    
    # FIXED: Show damage and defense
    equipped_weapon = equipment_slots.get("weapon")
    total_damage = player.get_total_damage(equipped_weapon)
    total_defense = player.get_total_defense()
    
    stats_text = f"Level {player.level} | Damage: {total_damage} | Defense: {total_defense}"
    text_surf = assets["small_font"].render(stats_text, True, (255, 255, 255))
    screen.blit(text_surf, (health_bar_x, y_offset))
def draw_level_up_notification(screen, assets):
    """Draws level up notification in the center of screen."""
    if not show_level_up:
        return
    
    # Create pulsing effect based on timer
    pulse = math.sin(level_up_timer / 200.0) * 0.3 + 1.0
    
    # Level up text
    level_text = assets["large_font"].render(level_up_text, True, (255, 215, 0))  # Gold
    text_rect = level_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
    
    # Scale text for pulse effect
    scaled_width = int(text_rect.width * pulse)
    scaled_height = int(text_rect.height * pulse)
    scaled_text = pygame.transform.scale(level_text, (scaled_width, scaled_height))
    scaled_rect = scaled_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
    
    # Background glow effect
    glow_rect = scaled_rect.inflate(40, 20)
    glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
    glow_surf.fill((255, 215, 0, 50))
    screen.blit(glow_surf, glow_rect)
    
    screen.blit(scaled_text, scaled_rect)
    
    # Stats increase text
    stats_text = f"Health +{15 + (player.level * 2)} | Damage +{3 + (player.level // 2)}"
    stats_surf = assets["small_font"].render(stats_text, True, (200, 255, 200))
    stats_rect = stats_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10))
    screen.blit(stats_surf, stats_rect)

def draw_experience_bar(screen, assets):
    """Draws the experience/level progress bar at the bottom of the screen."""
    bar_height = 25
    bar_y = HEIGHT - bar_height - 5
    bar_width = WIDTH - 20
    bar_x = 10
    
    # Background
    bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
    pygame.draw.rect(screen, (40, 40, 40), bg_rect)
    pygame.draw.rect(screen, (255, 255, 255), bg_rect, 2)
    
    # Experience progress
    if player.experience_to_next > 0:
        exp_ratio = player.experience / player.experience_to_next
        exp_width = int(bar_width * exp_ratio)
        exp_rect = pygame.Rect(bar_x, bar_y, exp_width, bar_height)
        
        # Gradient effect for XP bar
        for i in range(bar_height):
            color_intensity = 100 + int(155 * (1 - i / bar_height))
            line_color = (0, 0, color_intensity)
            if exp_width > 0:
                pygame.draw.line(screen, line_color, 
                               (bar_x, bar_y + i), 
                               (bar_x + exp_width, bar_y + i))
    
    # Text overlay
    exp_text = f"Level {player.level} - XP: {player.experience}/{player.experience_to_next}"
    text_surf = assets["small_font"].render(exp_text, True, (255, 255, 255))
    text_rect = text_surf.get_rect(center=(WIDTH // 2, bar_y + bar_height // 2))
    screen.blit(text_surf, text_rect)

def draw_player_coordinates(screen, font):
    """Draws the player's current world coordinates in the bottom-left corner."""
    player_rect = get_player_world_rect()
    coord_text = f"Player: ({player_rect.x}, {player_rect.y}) - Level: {current_level}"
    text_surf = font.render(coord_text, True, (255, 255, 255))
    screen.blit(text_surf, (10, HEIGHT - 30))

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
    
    # Draw stones
    for stone in stone_rects:
        screen.blit(assets["stone_img"], (stone.x - map_offset_x, stone.y - map_offset_y))

    # Draw trees
    for tree in tree_rects:
        screen.blit(assets["tree"], (tree.x - map_offset_x - tree_size_diff // 6, tree.y - map_offset_y - tree_size_diff // 6))

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
# Add these functions to your code

def setup_dungeon_with_enemy_spawns(filename="dungeon1.txt"):
    """Setup dungeon with enemy spawn points from map."""
    global dungeon_walls, stone_rects, boss1_portal, dungeon_exit, enemies, enemy_spawn_points

    print(f"\n=== SETTING UP DUNGEON: {filename} ===")

    # Clear existing data ONCE at the start
    dungeon_walls.clear()
    boss1_portal = None
    enemies.clear()
    enemy_spawn_points.clear()
    stone_rects.clear()
    
    # Load the map with enemy spawn points
    map_data = load_dungeon_map_with_enemies(filename)
    
    print(f"Map loaded: {len(map_data['enemy_spawns'])} spawn points found")
    
    # Apply map data
    dungeon_walls.extend(map_data['walls'])
    stone_rects.extend(map_data['ore_deposits'])
    dungeon_exit = map_data['exit_point']
    enemy_spawn_points.extend(map_data['enemy_spawns'])
    
    if map_data.get('boss_portal'):
        boss1_portal = map_data['boss_portal']
    
    # Spawn initial enemies
    current_time = pygame.time.get_ticks()
    spawned_count = 0
    
    for spawn_point in enemy_spawn_points:
        spawn_point.last_spawn_time = 0  # Force immediate spawn
        enemy = spawn_point.spawn_enemy(current_time)
        if enemy:
            spawned_count += 1
            print(f"✓ Spawned {enemy.type} at ({enemy.rect.x}, {enemy.rect.y})")
    
    print(f"Total spawned: {spawned_count}, Enemies list: {len(enemies)}")
    print("=== DUNGEON SETUP COMPLETE ===\n")
    
    # Return spawn point
    spawn_x, spawn_y = map_data['spawn_point']
    spawn_x += 100
    spawn_x = max(2 * TILE_SIZE, min(spawn_x, (DUNGEON_SIZE-3) * TILE_SIZE))
    spawn_y = max(2 * TILE_SIZE, min(spawn_y, (DUNGEON_SIZE-3) * TILE_SIZE))
    
    return (spawn_x, spawn_y)


def get_shop_items(assets):
    """Returns the items available in the shop with their prices."""
    return {
        "Potion": {"item": assets["potion_item"], "buy_price": 15, "sell_price": 8},
        "Log": {"item": assets["log_item"], "buy_price": 5, "sell_price": 2},
        "Stone": {"item": assets["stone_item"], "buy_price": 8, "sell_price": 3},
        "Ore": {"item": assets["ore_item"], "buy_price": 20, "sell_price": 12},
        "Flower": {"item": assets["flower_item"], "buy_price": 10, "sell_price": 4},
    }

def draw_vendor_gui(screen, assets):
    """Draws the vendor/shop GUI."""
    if not show_vendor_gui:
        return
    
    global buy_button_rects, sell_button_rects
    buy_button_rects = {}
    sell_button_rects = {}
    
    # Main panel
    panel_width = 600
    panel_height = 400
    panel_x = (WIDTH - panel_width) // 2
    panel_y = (HEIGHT - panel_height) // 2
    panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
    
    pygame.draw.rect(screen, (101, 67, 33), panel_rect)
    pygame.draw.rect(screen, (255, 255, 255), panel_rect, 3)
    
    # Header
    header_rect = pygame.Rect(panel_x, panel_y, panel_width, 40)
    pygame.draw.rect(screen, (50, 33, 16), header_rect)
    header_text = assets["font"].render("Marcus's Trading Post", True, (255, 215, 0))
    screen.blit(header_text, header_text.get_rect(center=header_rect.center))
    
    # Tab buttons
    tab_width = 80
    tab_height = 30
    tab_y = panel_y + 45
    
    buy_tab_rect = pygame.Rect(panel_x + 20, tab_y, tab_width, tab_height)
    sell_tab_rect = pygame.Rect(panel_x + 110, tab_y, tab_width, tab_height)
    
    # Draw buy tab
    buy_color = (0, 120, 0) if vendor_tab == "buy" else (60, 60, 60)
    pygame.draw.rect(screen, buy_color, buy_tab_rect)
    pygame.draw.rect(screen, (255, 255, 255), buy_tab_rect, 2)
    buy_text = assets["small_font"].render("Buy", True, (255, 255, 255))
    screen.blit(buy_text, buy_text.get_rect(center=buy_tab_rect.center))
    
    # Draw sell tab
    sell_color = (120, 0, 0) if vendor_tab == "sell" else (60, 60, 60)
    pygame.draw.rect(screen, sell_color, sell_tab_rect)
    pygame.draw.rect(screen, (255, 255, 255), sell_tab_rect, 2)
    sell_text = assets["small_font"].render("Sell", True, (255, 255, 255))
    screen.blit(sell_text, sell_text.get_rect(center=sell_tab_rect.center))
    
    # Player coins display
    coin_count = get_item_count("Coin")
    coin_text = f"Coins: {coin_count}"
    coin_surf = assets["small_font"].render(coin_text, True, (255, 215, 0))
    screen.blit(coin_surf, (panel_x + panel_width - 120, tab_y + 5))
    
    # Content area
    content_y = tab_y + tab_height + 10
    content_height = panel_height - (content_y - panel_y) - 10
    
    shop_items = get_shop_items(assets)
    
    if vendor_tab == "buy":
        draw_buy_content(screen, assets, panel_x, content_y, panel_width, shop_items, coin_count)
    else:
        draw_sell_content(screen, assets, panel_x, content_y, panel_width, shop_items)
    
    # Store tab rects for clicking
    buy_button_rects["buy_tab"] = buy_tab_rect
    buy_button_rects["sell_tab"] = sell_tab_rect

def draw_buy_content(screen, assets, panel_x, content_y, panel_width, shop_items, coin_count):
    """Draws the buy tab content."""
    global buy_button_rects
    
    y_offset = content_y + 10
    item_height = 50
    
    for item_name, item_data in shop_items.items():
        item_rect = pygame.Rect(panel_x + 20, y_offset, panel_width - 40, item_height)
        
        # Can afford check
        can_afford = coin_count >= item_data["buy_price"]
        
        # Item background
        bg_color = (0, 80, 0) if can_afford else (80, 40, 40)
        pygame.draw.rect(screen, bg_color, item_rect)
        pygame.draw.rect(screen, (255, 255, 255), item_rect, 1)
        
        # Item icon
        icon_rect = pygame.Rect(panel_x + 30, y_offset + 5, 40, 40)
        item_image = pygame.transform.scale(item_data["item"].image, (40, 40))
        screen.blit(item_image, icon_rect)
        
        # Item name and price
        name_text = assets["small_font"].render(item_name, True, (255, 255, 255))
        screen.blit(name_text, (panel_x + 80, y_offset + 10))
        
        price_text = assets["small_font"].render(f"Price: {item_data['buy_price']} coins", True, (255, 215, 0))
        screen.blit(price_text, (panel_x + 80, y_offset + 25))
        
        # Buy button
        buy_button = pygame.Rect(panel_x + panel_width - 120, y_offset + 10, 80, 30)
        button_color = (0, 150, 0) if can_afford else (100, 100, 100)
        pygame.draw.rect(screen, button_color, buy_button)
        pygame.draw.rect(screen, (255, 255, 255), buy_button, 1)
        
        button_text = "Buy" if can_afford else "No Coins"
        text_surf = assets["small_font"].render(button_text, True, (255, 255, 255))
        screen.blit(text_surf, text_surf.get_rect(center=buy_button.center))
        
        buy_button_rects[item_name] = buy_button
        y_offset += item_height + 5

def draw_sell_content(screen, assets, panel_x, content_y, panel_width, shop_items):
    """Draws the sell tab content."""
    global sell_button_rects
    
    y_offset = content_y + 10
    item_height = 50
    
    for item_name, item_data in shop_items.items():
        player_count = get_item_count(item_name)
        if player_count == 0:
            continue  # Don't show items player doesn't have
        
        item_rect = pygame.Rect(panel_x + 20, y_offset, panel_width - 40, item_height)
        
        # Item background
        pygame.draw.rect(screen, (80, 0, 0), item_rect)
        pygame.draw.rect(screen, (255, 255, 255), item_rect, 1)
        
        # Item icon
        icon_rect = pygame.Rect(panel_x + 30, y_offset + 5, 40, 40)
        item_image = pygame.transform.scale(item_data["item"].image, (40, 40))
        screen.blit(item_image, icon_rect)
        
        # Item name, count, and sell price
        name_text = assets["small_font"].render(f"{item_name} (x{player_count})", True, (255, 255, 255))
        screen.blit(name_text, (panel_x + 80, y_offset + 10))
        
        price_text = assets["small_font"].render(f"Sell for: {item_data['sell_price']} coins each", True, (255, 215, 0))
        screen.blit(price_text, (panel_x + 80, y_offset + 25))
        
        # Sell button
        sell_button = pygame.Rect(panel_x + panel_width - 120, y_offset + 10, 80, 30)
        pygame.draw.rect(screen, (150, 0, 0), sell_button)
        pygame.draw.rect(screen, (255, 255, 255), sell_button, 1)
        
        button_text = "Sell"
        text_surf = assets["small_font"].render(button_text, True, (255, 255, 255))
        screen.blit(text_surf, text_surf.get_rect(center=sell_button.center))
        
        sell_button_rects[item_name] = sell_button
        y_offset += item_height + 5

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
            "Thanks for the potions! I've set up a trading post here.",
            "I can buy and sell various goods you might need.",
            "Press [SPACE] to open shop, or [ESC] to close."
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

def draw_tooltip(screen, font, text, position):
    # Render text
    tooltip_surface = font.render(text, True, (255, 255, 255))
    tooltip_rect = tooltip_surface.get_rect(topleft=position)

    # Draw background rectangle
    pygame.draw.rect(screen, (0, 0, 0), tooltip_rect.inflate(6, 6))
    
    # Blit text on top
    screen.blit(tooltip_surface, tooltip_rect)

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

        # Mouse hover tooltips for other objects...
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
        # Inside dungeon: Boss door check (proximity-based, not mouse hover)
        if boss1_portal and player_world_rect.colliderect(boss1_portal.inflate(30, 30)):
            boss_screen = world_to_screen_rect(boss1_portal)
            tooltip_text = "Boss Door [e]"
            tooltip_pos = (boss_screen.x, boss_screen.y)
        
        # Exit portal tooltip if near
        elif dungeon_exit and player_world_rect.colliderect(dungeon_exit.inflate(20, 20)):
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

        # Enemy tooltips on mouse hover
        if tooltip_text is None:
            for enemy in enemies:
                enemy_screen = world_to_screen_rect(enemy.rect)
                if enemy_screen.collidepoint(mouse_pos):
                    tooltip_text = f"{enemy.type.title()} [SPACE to attack]"
                    tooltip_pos = (enemy_screen.x, enemy_screen.y)
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
    """Draws the smithing crafting options with armor."""
    global axe_button_rect, pickaxe_button_rect, chest_button_rect, helmet_button_rect, boots_button_rect
    
    button_width, button_height, gap = 180, 50, 20
    log_count = get_item_count("Log")
    stone_count = get_item_count("Stone")
    
    # Calculate positions for 5 items (2 columns)
    col1_x = CRAFTING_X + gap
    col2_x = CRAFTING_X + gap + button_width + gap
    
    # Weapons (left column) - use logs
    axe_button_rect = pygame.Rect(col1_x, content_y + gap, button_width, button_height)
    req_logs_axe = 5
    
    pickaxe_button_rect = pygame.Rect(col1_x, content_y + gap + (button_height + gap), button_width, button_height)
    req_logs_pickaxe = 10
    
    # Armor (right column) - use stones with higher requirements
    helmet_button_rect = pygame.Rect(col2_x, content_y + gap, button_width, button_height)
    req_stone_helmet = 8  # Increased from 2
    
    chest_button_rect = pygame.Rect(col2_x, content_y + gap + (button_height + gap), button_width, button_height)
    req_stone_chest = 15  # Increased from 2
    
    boots_button_rect = pygame.Rect(col2_x, content_y + gap + 2 * (button_height + gap), button_width, button_height)
    req_stone_boots = 6   # Increased from 2
    
    # Define all craftable items
    buttons = [
        # Weapons (use logs)
        (axe_button_rect, "axe", req_logs_axe, assets["axe_item"], "Log", log_count),
        (pickaxe_button_rect, "pickaxe", req_logs_pickaxe, assets["pickaxe_item"], "Log", log_count),
        
        # Armor (use stones)
        (helmet_button_rect, "helmet", req_stone_helmet, assets["helmet_item"], "Stone", stone_count),
        (chest_button_rect, "chest", req_stone_chest, assets["chest_item"], "Stone", stone_count),
        (boots_button_rect, "boots", req_stone_boots, assets["boots_item"], "Stone", stone_count),
    ]
    
    # Draw all buttons
    for rect, item_name, required_amount, item_obj, material_type, material_count in buttons:
        can_craft = material_count >= required_amount
        
        if is_crafting and item_to_craft and item_to_craft.name.lower().replace(" ", "") == item_name.replace("_", ""):
            progress = (crafting_timer / CRAFTING_TIME_MS) * 100
            text_to_display = f"Crafting... {int(progress)}%"
            color = (120, 120, 120)
        elif is_hovering == item_name:
            text_to_display = f"{item_obj.name}: {material_count}/{required_amount} {material_type}"
            color = (0, 100, 0) if can_craft else (50, 50, 50)
        else:
            text_to_display = f"Craft {item_obj.name}"
            color = (0, 150, 0) if can_craft else (70, 70, 70)

        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, (150, 150, 150), rect, 2)
        
        # Use smaller font for longer text
        text_surface = assets["small_font"].render(text_to_display, True, (255, 255, 255))
        
        # Center the text, but handle text that might be too wide
        text_rect = text_surface.get_rect()
        if text_rect.width > rect.width - 10:
            # Scale down text if too wide
            scale_factor = (rect.width - 10) / text_rect.width
            new_width = int(text_rect.width * scale_factor)
            new_height = int(text_rect.height * scale_factor)
            text_surface = pygame.transform.scale(text_surface, (new_width, new_height))
        
        text_rect = text_surface.get_rect(center=rect.center)
        screen.blit(text_surface, text_rect)

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
    """Draws the expanded equipment GUI with 2 rows, 4 columns and stats display."""
    global equipment_slots  # Access global equipment slots

    # --- Panel background ---
    panel_rect = pygame.Rect(EQUIPMENT_X, EQUIPMENT_Y, EQUIPMENT_PANEL_WIDTH + 100, EQUIPMENT_PANEL_HEIGHT + 40)
    pygame.draw.rect(screen, (101, 67, 33), panel_rect)          # Dark wood background
    pygame.draw.rect(screen, (255, 255, 255), panel_rect, 3)     # White outline

    # --- Header ---
    header_rect = pygame.Rect(EQUIPMENT_X, EQUIPMENT_Y, panel_rect.width, 40)
    pygame.draw.rect(screen, (50, 33, 16), header_rect)
    header_text = assets["font"].render("Equipment", True, (255, 215, 0))  # Gold text
    screen.blit(header_text, header_text.get_rect(center=header_rect.center))

    # --- Equipment slot layout ---
    slot_names = [
        ["weapon", "helmet", "armor", "boots"],   # Top row
        ["ring1", "ring2", "amulet", "shield"]    # Bottom row
    ]

    slot_labels = {
        "weapon": "Weapon", "helmet": "Helmet", "armor": "Chest", "boots": "Boots",
        "ring1": "Ring", "ring2": "Ring", "amulet": "Amulet", "shield": "Shield"
    }

    slot_rects = {}
    start_y = EQUIPMENT_Y + 60

    for row in range(EQUIPMENT_ROWS):
        for col in range(EQUIPMENT_COLS):
            slot_x = EQUIPMENT_X + EQUIPMENT_GAP + col * (EQUIPMENT_SLOT_SIZE + EQUIPMENT_GAP + 20)
            slot_y = start_y + row * (EQUIPMENT_SLOT_SIZE + EQUIPMENT_GAP + 28)

            slot_rect = pygame.Rect(slot_x, slot_y, EQUIPMENT_SLOT_SIZE, EQUIPMENT_SLOT_SIZE)
            slot_name = slot_names[row][col]

            # Slot background
            pygame.draw.rect(screen, (60, 60, 60), slot_rect)       # Dark slot bg
            pygame.draw.rect(screen, (200, 200, 200), slot_rect, 2) # Silver outline

            # Draw equipped item
            equipped_item = equipment_slots.get(slot_name)
            if equipped_item and equipped_item.image:
                item_image = pygame.transform.scale(equipped_item.image, (EQUIPMENT_SLOT_SIZE, EQUIPMENT_SLOT_SIZE))
                screen.blit(item_image, slot_rect)

            # Slot label
            label_text = assets["small_font"].render(slot_labels[slot_name], True, (255, 255, 255))
            label_rect = label_text.get_rect(centerx=slot_rect.centerx, top=slot_rect.bottom + 4)
            screen.blit(label_text, label_rect)

            # Store for click handling
            slot_rects[slot_name] = slot_rect

    # --- Stats box ---
    stats_y = start_y + (EQUIPMENT_ROWS * (EQUIPMENT_SLOT_SIZE + EQUIPMENT_GAP + 28)) + 10
    stats_rect = pygame.Rect(EQUIPMENT_X + 10, stats_y, panel_rect.width - 20, 60)
    pygame.draw.rect(screen, (30, 30, 30), stats_rect)      # Dark gray
    pygame.draw.rect(screen, (180, 180, 180), stats_rect, 2)

    # --- Calculate equipment bonuses ---
    total_damage_bonus = 0
    total_defense_bonus = 0

    for item in equipment_slots.values():
        if item:
            total_damage_bonus += getattr(item, 'damage', 0)
            total_defense_bonus += getattr(item, 'defense', 0)
    
    player_total_defense = player.get_total_defense()
    equipped_weapon = equipment_slots.get("weapon")
    weapon_name = equipped_weapon.name if equipped_weapon else "None"
    # --- Render stats text (multi-line) ---
    stats_lines = [
        f"Main Hand: {weapon_name} | Damage Bonus: +{total_damage_bonus}",
        f"Defense: {player_total_defense} (+{total_defense_bonus} from equipment)"
    ]

    line_height = assets["small_font"].get_height() + 2
    for i, line in enumerate(stats_lines):
        text_surf = assets["small_font"].render(line, True, (255, 255, 255))
        text_rect = text_surf.get_rect(midleft=(stats_rect.left + 10, stats_rect.top + 10 + i * line_height))
        screen.blit(text_surf, text_rect)

    return slot_rects

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

def draw_ability_bar(screen, assets):
    """Enhanced ability bar with better visuals and more abilities."""
    current_time = pygame.time.get_ticks()
    
    # Define abilities
    abilities = [
        {
            'key': '1',
            'name': 'Attack',
            'color': (200, 50, 50),
            'available': player.can_attack(current_time) and not is_attacking,
            'cooldown': max(0, COMBAT_COOLDOWN - (current_time - player.last_attack_time)) if not player.can_attack(current_time) else 0
        },
        {
            'key': '2', 
            'name': 'Block',
            'color': (50, 50, 200),
            'available': not is_attacking,
            'cooldown': 0
        },
        {
            'key': '3',
            'name': 'Dash',
            'color': (50, 200, 200),
            'available': (current_time - dash_cooldown > 3000) and not is_attacking,
            'cooldown': max(0, 3000 - (current_time - dash_cooldown)) if current_time - dash_cooldown <= 3000 else 0
        },
        {
            'key': 'H',
            'name': 'Heal',
            'color': (50, 200, 50),
            'available': get_item_count("Potion") > 0,
            'cooldown': 0
        }
    ]
    
    # Bar setup - bigger buttons
    button_size = 50
    button_gap = 12
    bar_width = len(abilities) * button_size + (len(abilities) - 1) * button_gap
    bar_height = button_size + 25
    
    # Position at bottom center
    bar_x = (WIDTH - bar_width) // 2
    bar_y = HEIGHT - bar_height - 80
    
    # Background panel
    panel_rect = pygame.Rect(bar_x - 15, bar_y - 15, bar_width + 30, bar_height + 30)
    pygame.draw.rect(screen, (30, 30, 40), panel_rect)
    pygame.draw.rect(screen, (255, 255, 255), panel_rect, 2)
    
    # Draw ability buttons
    for i, ability in enumerate(abilities):
        button_x = bar_x + i * (button_size + button_gap)
        button_y = bar_y
        button_rect = pygame.Rect(button_x, button_y, button_size, button_size)
        
        # Button color based on availability
        if ability['available']:
            button_color = ability['color']
            text_color = (255, 255, 255)
            display_text = ability['key']
        else:
            button_color = (60, 60, 60)
            text_color = (150, 150, 150)
            if ability['cooldown'] > 0:
                cooldown_seconds = ability['cooldown'] / 1000.0
                display_text = f"{cooldown_seconds:.1f}"
            else:
                display_text = ability['key']
        
        # Draw button
        pygame.draw.rect(screen, button_color, button_rect)
        pygame.draw.rect(screen, (200, 200, 200), button_rect, 2)
        
        # Cooldown overlay
        if ability['cooldown'] > 0:
            if ability['name'] == 'Attack':
                cooldown_ratio = ability['cooldown'] / COMBAT_COOLDOWN
            elif ability['name'] == 'Dash':
                cooldown_ratio = ability['cooldown'] / 3000
            else:
                cooldown_ratio = 0
                
            overlay_height = int(button_size * cooldown_ratio)
            if overlay_height > 0:
                overlay_rect = pygame.Rect(button_x, button_y + (button_size - overlay_height), 
                                         button_size, overlay_height)
                overlay = pygame.Surface((button_size, overlay_height))
                overlay.set_alpha(120)
                overlay.fill((0, 0, 0))
                screen.blit(overlay, overlay_rect)
        
        # Button text
        text_surf = assets["font"].render(display_text, True, text_color)
        text_rect = text_surf.get_rect(center=button_rect.center)
        screen.blit(text_surf, text_rect)
        
        # Ability name
        name_surf = assets["small_font"].render(ability['name'], True, (200, 200, 200))
        name_rect = name_surf.get_rect(centerx=button_rect.centerx, top=button_rect.bottom + 3)
        screen.blit(name_surf, name_rect)
        
        # Show potion count for heal
        if ability['name'] == 'Heal':
            potion_count = get_item_count("Potion")
            if potion_count > 0:
                count_surf = assets["small_font"].render(str(potion_count), True, (255, 255, 0))
                count_rect = count_surf.get_rect(bottomright=(button_rect.right - 2, button_rect.bottom - 2))
                screen.blit(count_surf, count_rect)
# --- MAIN GAME LOGIC ---
def handle_movement(keys):
    """Enhanced movement that tracks direction for better combat."""
    global current_direction, last_direction, player_movement_history
    
    dx = dy = 0
    new_direction = None
    
    if keys[pygame.K_a]:
        dx -= PLAYER_SPEED
        new_direction = "left"
    if keys[pygame.K_d]:
        dx += PLAYER_SPEED
        new_direction = "right"
    if keys[pygame.K_w]:
        dy -= PLAYER_SPEED
        new_direction = "up"
    if keys[pygame.K_s]:
        dy += PLAYER_SPEED
        new_direction = "down"
    
    # Update directions and track movement
    if new_direction:
        current_direction = new_direction
        last_direction = new_direction
        
        # Track recent movement for better attacks
        current_time = pygame.time.get_ticks()
        player_movement_history.append((new_direction, current_time))
        
        # Keep only recent movement (last 500ms)
        player_movement_history = [
            (direction, timestamp) for direction, timestamp in player_movement_history 
            if current_time - timestamp < 500
        ]
    else:
        current_direction = "idle"
    
    return dx, dy

def handle_dash(current_time):
    """Simple dash ability"""
    global dash_cooldown, is_dashing, map_offset_x, map_offset_y
    
    if current_time - dash_cooldown < 3000:  # 3 second cooldown
        return False
    
    if is_attacking:
        return False
    
    # Get dash direction
    dash_direction = "down"  # default
    if player_movement_history:
        dash_direction = player_movement_history[-1][0]
    
    # Dash distance
    dash_amount = 80
    
    # Apply dash movement
    if dash_direction == "up":
        map_offset_y -= dash_amount
    elif dash_direction == "down":
        map_offset_y += dash_amount
    elif dash_direction == "left":
        map_offset_x -= dash_amount
    elif dash_direction == "right":
        map_offset_x += dash_amount
    
    dash_cooldown = current_time
    
    # Visual feedback
    floating_texts.append(FloatingText(
        "Dash!",
        (player_pos.x, player_pos.y - 20),
        color=(100, 255, 255),
        lifetime=500
    ))
    
    print(f"Dashed {dash_direction}!")
    return True

def handle_block():
    """Simple block that adds defense"""
    # Add temporary defense boost
    player.add_status_effect("block", 1000, defense=15)
    
    floating_texts.append(FloatingText(
        "Block!",
        (player_pos.x, player_pos.y - 20),
        color=(100, 100, 255),
        lifetime=500
    ))
    
    print("Blocking! +15 Defense for 1 second")

def handle_collision(new_world_rect):
    """Checks for collision with world objects depending on current level."""
    if current_level == "world":
        if any(new_world_rect.colliderect(r) for r in tree_rects + stone_rects):
            return True
        return False
    elif current_level == "dungeon":
        if any(new_world_rect.colliderect(r) for r in dungeon_walls + stone_rects):
            return True
        return False
    elif current_level == "boss_room":
        # Allow free movement except for walls loaded from map
        if any(new_world_rect.colliderect(r) for r in boss_room_walls):
            return True
        return False
    else:  # house
        return any(new_world_rect.colliderect(r) for r in indoor_colliders)


def check_house_entry(world_rect):
    """Checks if the player is near a house door in the world."""
    for i, h in enumerate(house_list):
        if world_rect.colliderect(h.inflate(20, 20)):
            return i
    return None


def use_potion():
    """Uses a potion from inventory to heal the player."""
    if get_item_count("Potion") > 0:
        remove_item_from_inventory("Potion", 1)
        heal_amount = 50
        player.heal(heal_amount)
        print(f"Used potion! Healed {heal_amount} HP. Current health: {player.health}/{player.max_health}")
        return True
    else:
        print("No potions available!")
        return False


def handle_main_menu_events(screen, assets, dt):
    global game_state, menu_selected_option
    
    # menu music
    play_music("main_menu")

    # Get mouse position for hover detection
    mouse_pos = pygame.mouse.get_pos()
    
    # Define menu option rectangles (you'll need these for click detection)
    menu_options = ["New Game", "Load Game", "Exit"]
    option_rects = []

    for i, option in enumerate(menu_options):
        option_text = assets["font"].render(option, True, (255, 255, 255))
        option_rect = option_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + i * 50))
        option_rects.append(option_rect)
    
    # Check for mouse hover to update selected option
    for i, rect in enumerate(option_rects):
        if rect.collidepoint(mouse_pos):
            menu_selected_option = i
            break
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            # Keyboard navigation
            if event.key == pygame.K_w or event.key == pygame.K_UP:
                menu_selected_option = (menu_selected_option - 1) % 3
            elif event.key == pygame.K_s or event.key == pygame.K_DOWN:
                menu_selected_option = (menu_selected_option + 1) % 3
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                execute_menu_option()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Mouse click handling
            if event.button == 1:  # Left mouse button
                for i, rect in enumerate(option_rects):
                    if rect.collidepoint(event.pos):
                        menu_selected_option = i
                        execute_menu_option()
                        break
    
    draw_main_menu(screen, assets)
    pygame.display.flip()

def execute_save_slot_selection():
    """Execute the selected save slot."""
    global game_state
    
    if load_game_data(selected_save_slot):
        game_state = "playing"
        setup_colliders()
    else:
        start_new_game()
        game_state = "playing"

def execute_menu_option():
    """Execute the selected menu option."""
    global game_state
    
    if menu_selected_option == 0:  # New Game
        start_new_game()
        game_state = "playing"
    elif menu_selected_option == 1:  # Load Game
        game_state = "save_select"
    elif menu_selected_option == 2:  # Exit
        pygame.quit()
        sys.exit()

def handle_save_select_events(screen, assets, dt):
    global game_state, selected_save_slot
    
    # Get mouse position
    mouse_pos = pygame.mouse.get_pos()
    
    # Define save slot rectangles
    slot_rects = []
    for i in range(4):
        slot_y = HEIGHT // 2 + i * 60 - 120
        slot_rect = pygame.Rect(WIDTH // 2 - 200, slot_y, 400, 50)
        slot_rects.append(slot_rect)
    
    # Check for mouse hover
    for i, rect in enumerate(slot_rects):
        if rect.collidepoint(mouse_pos):
            selected_save_slot = i + 1
            break
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            # Keyboard navigation
            if event.key == pygame.K_UP:
                selected_save_slot = max(1, selected_save_slot - 1)
            elif event.key == pygame.K_DOWN:
                selected_save_slot = min(4, selected_save_slot + 1)
            elif event.key == pygame.K_RETURN:
                execute_save_slot_selection()
            elif event.key == pygame.K_ESCAPE:
                game_state = "main_menu"
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Mouse click handling
            if event.button == 1:  # Left mouse button
                for i, rect in enumerate(slot_rects):
                    if rect.collidepoint(event.pos):
                        selected_save_slot = i + 1
                        execute_save_slot_selection()
                        break
    
    draw_save_select_menu(screen, assets)
    pygame.display.flip()

def main():
    """Main game state manager."""
    global game_state, menu_selected_option, selected_save_slot
    screen, clock = init()
    assets = load_assets()
    load_save_slots()

    while True:
        dt = clock.tick(60)
        if game_state == "main_menu":
            handle_main_menu_events(screen, assets, dt)
        elif game_state == "save_select":
            handle_save_select_events(screen, assets, dt)
        elif game_state == "playing":
            handle_playing_state(screen, assets, dt)
        elif game_state == "boss_room":
            handle_boss_room_state(screen, assets)
def handle_boss_door(player_world_rect, assets):
    """Checks for boss door interaction inside dungeon."""
    global current_level

    if boss_door and player_world_rect.colliderect(boss_door.inflate(20, 20)):
        # Show tooltip
        font = assets["small_font"]
        text = font.render("Press E to enter Boss Room", True, (255, 255, 255))
        screen = pygame.display.get_surface()
        screen.blit(text, (boss_door.x, boss_door.y - 30))

        keys = pygame.key.get_pressed()
        if keys[pygame.K_e]:
            # Switch to boss room
            spawn_point = setup_boss_room()
            player_pos.center = spawn_point
            current_level = "boss_room"
            print("Entered the Boss Room!")
# UPDATED handle_playing_state function - Replace the entire function
def handle_playing_state(screen, assets, dt):
    """Handle the main game when actually playing - FIXED VERSION."""
    global map_offset_x, map_offset_y, current_level, current_house_index
    global player_frame_index, player_frame_timer, current_direction, last_direction
    global show_inventory, show_crafting, show_equipment, crafting_tab
    global is_chopping, chopping_timer, chopping_target_tree, is_swinging
    global is_crafting, crafting_timer, item_to_craft
    global is_mining, mining_timer, mining_target_stone
    global is_attacking, attack_timer
    global player_pos
    global show_npc_dialog, npc_quest_active, npc_quest_completed
    global show_miner_dialog, miner_quest_active, miner_quest_completed
    global npc_idle_timer, npc_idle_offset_y, npc_idle_direction
    global miner_idle_timer, miner_idle_offset_y, miner_idle_direction
    global show_level_up, level_up_timer, level_up_text
    global show_vendor_gui, vendor_tab
    global enemies, enemy_spawn_points
    global equipment_slots
    global show_pause_menu, pause_menu_selected_option

    # Load frames if not already loaded
    if not hasattr(handle_playing_state, 'frames_loaded'):
        global enemy_frames
        handle_playing_state.player_frames = load_player_frames()
        handle_playing_state.chopping_frames = load_chopping_frames()
        handle_playing_state.attack_frames = load_attack_frames()
        handle_playing_state.enemy_frames = load_enemy_frames()
        handle_playing_state.frames_loaded = True
        
        # Initialize world if first time
        setup_colliders()
        give_starting_items(assets)
        load_map("forest")

    # Get frames
    player_frames = handle_playing_state.player_frames
    chopping_frames = handle_playing_state.chopping_frames
    attack_frames = handle_playing_state.attack_frames
    enemy_frames = handle_playing_state.enemy_frames

    # Animation variables
    attack_animation_duration = 400
    current_time = pygame.time.get_ticks()

    # Update player
    player.update(dt, current_time)

    # Update level up notification timer
    if show_level_up:
        level_up_timer += dt
        if level_up_timer > 3000:
            show_level_up = False
            level_up_timer = 0

    # Music handling
    if current_level == "world":
        play_music("forest")
    elif current_level == "dungeon":
        play_music("dungeon")
    elif current_level == "boss_room":
        play_music("boss_room")
    elif current_level == "house":
        if current_music not in ["forest", None]:
            fade_out_music(2000)

    # UI Hover State
    is_hovering = None
    mouse_pos = pygame.mouse.get_pos()
    if show_crafting:
        if crafting_tab == "smithing":
            if axe_button_rect and axe_button_rect.collidepoint(mouse_pos):
                is_hovering = "axe"
            elif pickaxe_button_rect and pickaxe_button_rect.collidepoint(mouse_pos):
                is_hovering = "pickaxe"
            elif helmet_button_rect and helmet_button_rect.collidepoint(mouse_pos):
                is_hovering = "helmet"
            elif chest_button_rect and chest_button_rect.collidepoint(mouse_pos):
                is_hovering = "chest"
            elif boots_button_rect and boots_button_rect.collidepoint(mouse_pos):
                is_hovering = "boots"
        elif crafting_tab == "alchemy":
            if potion_button_rect and potion_button_rect.collidepoint(mouse_pos):
                is_hovering = "potion"

    # FIXED: Enemy spawning and updates
    if current_level == "dungeon":
        # Debug enemy spawning every 3 seconds
        if pygame.time.get_ticks() % 3000 < 50:
            print(f"Dungeon status: {len(enemies)} enemies active, {len(enemy_spawn_points)} spawn points")
            if len(enemies) == 0 and len(enemy_spawn_points) > 0:
                print("WARNING: No enemies but spawn points exist!")

        # Use enhanced enemy spawning
        update_enemy_spawns()

        # Update enemies
        player_world_rect = get_player_world_rect()
        obstacles = dungeon_walls + stone_rects
        for enemy in enemies[:]:  # Use slice copy for safe iteration
            enemy.update(dt, current_time, player_world_rect, obstacles)
            
            # Remove dead enemies
            if enemy.health <= 0 and enemy in enemies:
                enemies.remove(enemy)
                print(f"Removed dead {enemy.type}")

        # Handle combat in dungeon
        handle_combat(current_time)

    elif current_level == "boss_room":
        player_world_rect = get_player_world_rect()
        obstacles = boss_room_walls + stone_rects
        update_boss_room_enemies(dt, current_time, player_world_rect, obstacles)
        handle_combat(current_time)

    # Event Handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if show_pause_menu:
            handle_pause_menu_input(event, assets)
            continue

        if current_level == "boss_room":
            handle_boss_room_interactions(event, player_pos, assets)

        if event.type == pygame.KEYDOWN:
            # Combat controls
            if event.key == pygame.K_1 or event.key == pygame.K_SPACE:
                if player.can_attack(current_time) and not is_attacking:
                    is_attacking = True
                    attack_timer = 0

                    player_world_rect = get_player_world_rect()
                    ATTACK_RANGE = 48
                    attack_box = player_world_rect.inflate(ATTACK_RANGE, ATTACK_RANGE)

                    equipped_weapon = equipment_slots.get("weapon")
                    base_damage = player.get_total_damage(equipped_weapon)
                    hit_any = False

                    for enemy in enemies[:]:
                        if attack_box.colliderect(enemy.rect):
                            hit_any = True
                            if enemy.take_damage(base_damage):
                                player.gain_experience(enemy.experience_reward)
                                enemies.remove(enemy)
                                print(f"Defeated {enemy.type}! Gained {enemy.experience_reward} XP")
                            print(f"Hit {enemy.type} for {base_damage} dmg!")

                    if not hit_any:
                        print("Attack missed!")

                    player.last_attack_time = current_time

            # Ability keys
            elif event.key == pygame.K_2:
                handle_block()
            elif event.key == pygame.K_3:
                handle_dash(current_time)
            elif event.key == pygame.K_h:
                use_potion()

            # DEBUG KEY for testing enemy spawning
            elif event.key == pygame.K_t:
                if current_level == "dungeon":
                    print("=== TESTING ENEMY SPAWN ===")
                    print(f"Current enemies: {len(enemies)}")
                    print(f"Current spawn points: {len(enemy_spawn_points)}")
                    # Force spawn enemies for testing
                    current_time = pygame.time.get_ticks()
                    for spawn_point in enemy_spawn_points:
                        spawn_point.last_spawn_time = 0
                        result = spawn_point.spawn_enemy(current_time)
                        if result:
                            print(f"Force spawned {result.type}")
            
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

            # World interactions
            player_world_rect = get_player_world_rect()

            if event.key == pygame.K_e:
                # WORLD LEVEL
                if current_level == "world":
                    # Enter Dungeon - FIXED
                    if dungeon_portal and player_world_rect.colliderect(dungeon_portal.inflate(20, 20)):
                        print("Entering dungeon...")
            
                        # Setup dungeon FIRST (this clears enemies internally)
                        spawn_point = setup_dungeon_with_enemy_spawns("dungeon1.txt")
            
                        # THEN change level and position player
                        current_level = "dungeon"
                        player_pos.center = (WIDTH // 2, HEIGHT // 2)
                        map_offset_x = spawn_point[0] - WIDTH // 2
                        map_offset_y = spawn_point[1] - HEIGHT // 2
            
                        # Debug: verify enemies spawned
                        print(f"Dungeon entered - {len(enemies)} enemies active, {len(enemy_spawn_points)} spawn points")
                        for i, enemy in enumerate(enemies):
                            print(f"  Enemy {i+1}: {enemy.type} at ({enemy.rect.x}, {enemy.rect.y})")

                    # Enter House
                    elif check_house_entry(player_world_rect) is not None:
                        house_index = check_house_entry(player_world_rect)
                        current_level = "house"
                        current_house_index = house_index
                        player_pos.size = (PLAYER_SIZE_INDOOR, PLAYER_SIZE_INDOOR)
                        player_pos.center = (WIDTH // 2, HEIGHT // 2)
                        setup_indoor_colliders()

                    # Talk to NPCs
                    elif npc_rect and player_world_rect.colliderect(npc_rect.inflate(20, 20)):
                        show_npc_dialog = True
                    elif miner_npc_rect and player_world_rect.colliderect(miner_npc_rect.inflate(20, 20)):
                        show_miner_dialog = True

                    # Resource gathering
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
                            _handle_other_resources(player_world_rect, assets)
                    elif equipment_slots["weapon"] and equipment_slots["weapon"].name == "Pickaxe":
                        for stone in list(stone_rects):
                            if player_world_rect.colliderect(stone.inflate(20, 20)):
                                is_mining = True
                                mining_target_stone = stone
                                mining_timer = 0
                                current_direction = "idle"
                                break
                        else:
                            _handle_flower_picking(player_world_rect, assets)
                    else:
                        _handle_flower_picking(player_world_rect, assets)

                # DUNGEON LEVEL
                elif current_level == "dungeon":
                    # Exit to world
                    if dungeon_exit and player_world_rect.colliderect(dungeon_exit.inflate(20, 20)):
                        current_level = "world"
                        portal_x = 25 * TILE_SIZE
                        portal_y = 38 * TILE_SIZE
                        map_offset_x = portal_x - WIDTH // 2
                        map_offset_y = portal_y - HEIGHT // 2 + 100
                        player_pos.center = (WIDTH // 2, HEIGHT // 2)
                        enemies.clear()
                        enemy_spawn_points.clear()

                    # Enter Boss Room
                    elif boss1_portal and player_world_rect.colliderect(boss1_portal.inflate(20, 20)):
                        current_level = "boss_room"
                        enemies.clear()
                        spawn_point = setup_boss_room()
                        map_offset_x = 0
                        map_offset_y = 0
                        player_pos.center = spawn_point
                        print("Entered Boss Room!")

                    # Mine ore in dungeon
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

                # HOUSE LEVEL
                elif current_level == "house":
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
                    npc_quest_active = True
                    show_npc_dialog = False
                    print("Quest accepted! Bring 3 potions to Soldier Marcus.")
                elif npc_quest_active and get_item_count("Potion") >= potions_needed:
                    remove_item_from_inventory("Potion", potions_needed)
                    for _ in range(10):
                        add_item_to_inventory(assets["coin_item"])
                    npc_quest_completed = True
                    npc_quest_active = False
                    show_npc_dialog = False
                    print("Quest completed! You received 10 coins as a reward!")
                elif npc_quest_completed:
                    show_npc_dialog = False
                    show_vendor_gui = True
                    vendor_tab = "buy"

            if event.key == pygame.K_SPACE and show_miner_dialog:
                if not miner_quest_active and not miner_quest_completed:
                    miner_quest_active = True
                    show_miner_dialog = False
                    print("Quest accepted! Gather 10 ore from the dungeon for Miner Gareth.")
                elif miner_quest_active and get_item_count("Ore") >= ore_needed:
                    remove_item_from_inventory("Ore", ore_needed)
                    for _ in range(15):
                        add_item_to_inventory(assets["coin_item"])
                    miner_quest_completed = True
                    miner_quest_active = False
                    show_miner_dialog = False
                    print("Quest completed! You received 15 coins as a reward!")

            if event.key == pygame.K_ESCAPE:
                if show_npc_dialog or show_miner_dialog:
                    show_npc_dialog = False
                    show_miner_dialog = False
                elif show_vendor_gui:
                    show_vendor_gui = False
                elif not (show_inventory or show_crafting or show_equipment):
                    show_pause_menu = True
                    pause_menu_selected_option = 0

        # Mouse click handling
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            _handle_mouse_clicks(event, assets, screen, dt)

    # Game State Updates
    _update_npc_animations(dt)
    _update_crafting(current_time, assets, dt)
    _update_animations(dt, player_frames, attack_frames, chopping_frames, attack_animation_duration)

    # Player Movement
    if not _is_ui_blocking_movement():
        keys = pygame.key.get_pressed()
        dx, dy = handle_movement(keys)
        _handle_player_movement(dx, dy)

    # Drawing
    _draw_game_world(screen, assets, enemy_frames)
    _draw_player(screen, player_frames, attack_frames, chopping_frames)
    _draw_ui_elements(screen, assets, player_frames, attack_frames, chopping_frames, is_hovering)
    _handle_game_over(screen, assets)

    pygame.display.flip()

# Helper functions to clean up the main function
def _handle_other_resources(player_world_rect, assets):
    """Handle mining and flower picking when player has axe."""
    global equipment_slots, is_mining, mining_target_stone, mining_timer, current_direction
    
    if equipment_slots["weapon"] and equipment_slots["weapon"].name == "Pickaxe":
        for stone in list(stone_rects):
            if player_world_rect.colliderect(stone.inflate(20, 20)):
                is_mining = True
                mining_target_stone = stone
                mining_timer = 0
                current_direction = "idle"
                break
        else:
            _handle_flower_picking(player_world_rect, assets)
    else:
        _handle_flower_picking(player_world_rect, assets)

def _handle_flower_picking(player_world_rect, assets):
    """Handle flower picking."""
    for fx, fy, idx in list(flower_tiles):
        flower_rect = pygame.Rect(fx, fy, 30, 30)
        if player_world_rect.colliderect(flower_rect.inflate(10, 10)):
            add_item_to_inventory(assets["flower_item"])
            flower_tiles.remove((fx, fy, idx))
            print("Picked a flower!")
            break

def _handle_mouse_clicks(event, assets, screen):
    """Handle all mouse click events."""
    if show_vendor_gui:
        _handle_vendor_clicks(event, assets)
    elif show_crafting and not is_crafting:
        _handle_crafting_clicks(event, assets)
    elif show_equipment:
        equipment_slot_rects = draw_equipment_panel(screen, assets)
        handle_equipment_click(event.pos, equipment_slot_rects)
    elif show_inventory:
        handle_inventory_click(event.pos)

def _handle_vendor_clicks(event, assets):
    """Handle vendor GUI clicks."""
    global vendor_tab
    
    if "buy_tab" in buy_button_rects and buy_button_rects["buy_tab"].collidepoint(event.pos):
        vendor_tab = "buy"
    elif "sell_tab" in buy_button_rects and buy_button_rects["sell_tab"].collidepoint(event.pos):
        vendor_tab = "sell"
    elif vendor_tab == "buy":
        _handle_buy_transactions(event, assets)
    elif vendor_tab == "sell":
        _handle_sell_transactions(event, assets)

def _handle_buy_transactions(event, assets):
    """Handle buying items from vendor."""
    shop_items = get_shop_items(assets)
    coin_count = get_item_count("Coin")
    
    for item_name, button_rect in buy_button_rects.items():
        if item_name in ["buy_tab", "sell_tab"]:
            continue
        if button_rect.collidepoint(event.pos):
            item_data = shop_items[item_name]
            if coin_count >= item_data["buy_price"]:
                remove_item_from_inventory("Coin", item_data["buy_price"])
                add_item_to_inventory(item_data["item"])
                print(f"Bought {item_name} for {item_data['buy_price']} coins!")
            else:
                print("Not enough coins!")
            break

def _handle_sell_transactions(event, assets):
    """Handle selling items to vendor."""
    shop_items = get_shop_items(assets)
    
    for item_name, button_rect in sell_button_rects.items():
        if button_rect.collidepoint(event.pos):
            if get_item_count(item_name) > 0:
                remove_item_from_inventory(item_name, 1)
                item_data = shop_items[item_name]
                for _ in range(item_data["sell_price"]):
                    add_item_to_inventory(assets["coin_item"])
                print(f"Sold {item_name} for {item_data['sell_price']} coins!")
            break

def _handle_crafting_clicks(event, assets):
    """Handle crafting GUI clicks."""
    global crafting_tab, is_crafting, crafting_timer, item_to_craft
    
    if smithing_tab_rect and smithing_tab_rect.collidepoint(event.pos):
        crafting_tab = "smithing"
    elif alchemy_tab_rect and alchemy_tab_rect.collidepoint(event.pos):
        crafting_tab = "alchemy"
    elif crafting_tab == "smithing":
        _handle_smithing_crafting(event, assets)
    elif crafting_tab == "alchemy":
        _handle_alchemy_crafting(event, assets)

def _handle_smithing_crafting(event, assets):
    """Handle smithing crafting clicks."""
    global is_crafting, crafting_timer, item_to_craft
    
    crafting_recipes = [
        (axe_button_rect, "Log", 5, assets["axe_item"], "Axe"),
        (pickaxe_button_rect, "Log", 10, assets["pickaxe_item"], "Pickaxe"),
        (helmet_button_rect, "Stone", 8, assets["helmet_item"], "Helmet"),
        (chest_button_rect, "Stone", 15, assets["chest_item"], "Chest Armor"),
        (boots_button_rect, "Stone", 6, assets["boots_item"], "Boots")
    ]
    
    for button_rect, material, cost, item_obj, item_name in crafting_recipes:
        if button_rect and button_rect.collidepoint(event.pos):
            if get_item_count(material) >= cost:
                is_crafting = True
                crafting_timer = 0
                item_to_craft = item_obj
                remove_item_from_inventory(material, cost)
                print(f"Crafting {item_name}...")
            else:
                print(f"Not enough {material.lower()}!")
            break

def _handle_alchemy_crafting(event, assets):
    """Handle alchemy crafting clicks."""
    global is_crafting, crafting_timer, item_to_craft
    
    if potion_button_rect and potion_button_rect.collidepoint(event.pos):
        if get_item_count("Flower") >= 3:
            is_crafting = True
            crafting_timer = 0
            item_to_craft = assets["potion_item"]
            remove_item_from_inventory("Flower", 3)
            print("Brewing a Potion...")
        else:
            print("Not enough flowers!")

def _update_npc_animations(dt):
    """Update NPC idle animations."""
    global npc_idle_timer, npc_idle_direction, npc_idle_offset_y
    global miner_idle_timer, miner_idle_direction, miner_idle_offset_y
    
    # NPC idle animation
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

def _update_crafting(current_time, assets, dt):  
    """Update crafting progress."""
    global is_crafting, crafting_timer, item_to_craft
    
    if is_crafting:
        crafting_timer += dt  # Now dt is defined as a parameter
        
        if crafting_timer >= CRAFTING_TIME_MS:
            if add_item_to_inventory(item_to_craft):
                print(f"Crafting complete! {item_to_craft.name} added to inventory.")
            else:
                print("Crafting failed: Inventory is full.")
            is_crafting = False
            item_to_craft = None
            crafting_timer = 0  # Reset timer

def _update_animations(dt, player_frames, attack_frames, chopping_frames, attack_animation_duration):
    """Update player animations."""
    global is_attacking, attack_timer, player_frame_timer, player_frame_index, current_direction
    global is_chopping, chopping_timer, chopping_target_tree, is_swinging
    global is_mining, mining_timer, mining_target_stone
    global swing_delay, idle_chop_delay, player_frame_delay
    
    # Attack animation
    if is_attacking:
        attack_timer += dt
        player_frame_timer += dt
        if player_frame_timer >= swing_delay:
            attack_direction = last_direction if last_direction in attack_frames else "down"
            max_frames = len(attack_frames[attack_direction])
            player_frame_index = (player_frame_index + 1) % max_frames
            player_frame_timer = 0

        if attack_timer >= attack_animation_duration:
            is_attacking = False
            attack_timer = 0
            player_frame_index = 0
            current_direction = "idle"

    # Chopping animation
    elif is_chopping:
        chopping_timer += dt
        player_frame_timer += dt
        if player_frame_timer > idle_chop_delay:
            is_swinging = True
            if player_frame_timer >= swing_delay:
                chop_direction = last_direction if last_direction in chopping_frames else "down"
                max_frames = len(chopping_frames[chop_direction])
                player_frame_index = (player_frame_index + 1) % max_frames
                player_frame_timer = 0

        if chopping_timer >= CHOPPING_DURATION:
            _complete_chopping(current_time, assets)

    # Mining animation  
    elif is_mining:
        mining_timer += dt
        player_frame_timer += dt
        if player_frame_timer > idle_chop_delay:
            is_swinging = True
            if player_frame_timer >= swing_delay:
                chop_direction = last_direction if last_direction in chopping_frames else "down"
                max_frames = len(chopping_frames[chop_direction])
                player_frame_index = (player_frame_index + 1) % max_frames
                player_frame_timer = 0

        if mining_timer >= MINING_DURATION:
            _complete_mining(current_time, assets)

    # Normal animation state update
    else:
        player_frame_timer += dt
        if current_direction == "idle":
            player_frame_index = 0
        elif player_frame_timer > player_frame_delay:
            frame_set = player_frames.get(current_direction, player_frames["idle"])
            max_frames = len(frame_set)
            player_frame_index = (player_frame_index + 1) % max_frames
            player_frame_timer = 0

def _complete_chopping(current_time, assets):
    """Complete tree chopping action."""
    global is_chopping, is_swinging, chopping_timer, chopping_target_tree, current_direction
    
    if chopping_target_tree in tree_rects:
        tree_rects.remove(chopping_target_tree)
        chopped_trees[(chopping_target_tree.x, chopping_target_tree.y, 
                      chopping_target_tree.width, chopping_target_tree.height)] = current_time
        add_item_to_inventory(assets["log_item"])
        print("Chopped a tree! Gained a log.")
    
    is_chopping = False
    is_swinging = False
    chopping_timer = 0
    chopping_target_tree = None
    current_direction = "idle"

def _complete_mining(current_time, assets):
    """Complete stone/ore mining action."""
    global is_mining, is_swinging, mining_timer, mining_target_stone, current_direction
    
    if mining_target_stone in stone_rects:
        stone_rects.remove(mining_target_stone)
        chopped_stones[(mining_target_stone.x, mining_target_stone.y,
                       mining_target_stone.width, mining_target_stone.height)] = current_time
        
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

def _update_respawns(current_time):
    """Update resource respawn timers."""
    # Tree respawning
    for tree_rect_tuple, time_chopped in list(chopped_trees.items()):
        tree_rect = pygame.Rect(tree_rect_tuple)
        if current_time - time_chopped > RESPAWN_TIME:
            tree_rects.append(tree_rect)
            del chopped_trees[tree_rect_tuple]

    # Stone respawning
    for stone_rect_tuple, time_mined in list(chopped_stones.items()):
        stone_rect = pygame.Rect(stone_rect_tuple)
        if current_time - time_mined > RESPAWN_TIME:
            stone_rects.append(stone_rect)
            del chopped_stones[stone_rect_tuple]

def _is_ui_blocking_movement():
    """Check if any UI is blocking player movement."""
    return (show_inventory or show_crafting or show_equipment or 
            is_chopping or is_mining or is_attacking or 
            show_npc_dialog or show_miner_dialog)

def _handle_player_movement(dx, dy):
    """Handle player movement based on current level."""
    global map_offset_x, map_offset_y, player_pos, last_direction, current_direction
    
    if current_level == "world" or current_level == "dungeon":
        new_player_world_rect = get_player_world_rect().move(dx, dy)
        if not handle_collision(new_player_world_rect):
            map_offset_x += dx
            map_offset_y += dy
            if dx != 0 or dy != 0:
                last_direction = current_direction
    else:  # current_level == "house" or "boss_room"
        new_player_pos = player_pos.move(dx, dy)
        if not handle_collision(new_player_pos):
            player_pos = new_player_pos
            if dx != 0 or dy != 0:
                last_direction = current_direction
def draw_dungeon(screen, assets, enemy_frames):
    """Draws the dungeon level with enemies and boss door."""
    dungeon_width = 30
    dungeon_height = 30
    
    # Draw floor tiles
    for x in range(dungeon_width):
        for y in range(dungeon_height):
            screen.blit(assets["dungeon_floor"], (x * TILE_SIZE - map_offset_x, y * TILE_SIZE - map_offset_y))
    
    # Draw dungeon walls
    for wall in dungeon_walls:
        screen.blit(assets["dungeon_wall"], (wall.x - map_offset_x, wall.y - map_offset_y))
    
    # Draw ore deposits
    for ore in stone_rects:
        screen.blit(assets["ore_img"], (ore.x - map_offset_x, ore.y - map_offset_y))
    
    # Draw boss door if it exists
    if boss1_portal and current_level == "dungeon":
        boss_door_image = assets["boss_door_frames"]["closed"]
        screen.blit(boss_door_image, (boss1_portal.x - map_offset_x, boss1_portal.y - map_offset_y))
    
    # Draw enemies
    for enemy in enemies:
        enemy_screen_rect = world_to_screen_rect(enemy.rect)
        if 0 <= enemy_screen_rect.x <= WIDTH and 0 <= enemy_screen_rect.y <= HEIGHT:
            if enemy.type in enemy_frames and len(enemy_frames[enemy.type]) > 0:
                frame = enemy_frames[enemy.type][enemy.frame_index % len(enemy_frames[enemy.type])]
                screen.blit(frame, enemy_screen_rect)
        
            # Draw enemy health bar
            if enemy.health < enemy.max_health:
                bar_y = enemy_screen_rect.y - 10
                draw_health_bar(screen, enemy_screen_rect.x, bar_y, enemy.health, enemy.max_health, enemy.rect.width, 5)
    
    # Draw exit portal
    if dungeon_exit:
        screen.blit(assets["portal"], (dungeon_exit.x - map_offset_x, dungeon_exit.y - map_offset_y))
    
    # Update floating texts
    for text in floating_texts[:]:
        text.update()
        if not text.is_alive():
            floating_texts.remove(text)
        else:
            text.draw(screen, assets["small_font"], map_offset_x, map_offset_y)

def _draw_game_world(screen, assets, enemy_frames):
    """Draw the appropriate game world based on current level."""
    screen.fill((0, 0, 0))
    
    if current_level == "world":
        draw_world(screen, assets)
    elif current_level == "dungeon":
        draw_dungeon(screen, assets, enemy_frames)
    elif current_level == "boss_room":
        draw_boss_room(screen, assets)
    else:  # house
        screen.blit(assets["interiors"][current_house_index], (0, 0))

def _draw_player(screen, player_frames, attack_frames, chopping_frames):
    """Draw the player with appropriate animations."""
    player_size_current = player_pos.width
    
    if is_attacking:
        attack_direction = last_direction if last_direction in attack_frames else "down"
        frame_index = min(player_frame_index, len(attack_frames[attack_direction]) - 1)
        scaled_frame = pygame.transform.scale(attack_frames[attack_direction][frame_index], 
                                            (player_size_current, player_size_current))
        screen.blit(scaled_frame, player_pos)
    elif is_chopping or is_mining:
        chop_direction = last_direction if last_direction in chopping_frames else "down"
        frame_index = min(player_frame_index, len(chopping_frames[chop_direction]) - 1)
        scaled_frame = pygame.transform.scale(chopping_frames[chop_direction][frame_index], 
                                            (player_size_current, player_size_current))
        screen.blit(scaled_frame, player_pos)
    else:
        frame_set = player_frames.get(current_direction, player_frames["idle"])
        frame_index = min(player_frame_index, len(frame_set) - 1)
        scaled_frame = pygame.transform.scale(frame_set[frame_index], 
                                            (player_size_current, player_size_current))
        screen.blit(scaled_frame, player_pos)

def _draw_ui_elements(screen, assets, player_frames, attack_frames, chopping_frames, is_hovering):
    """Draw all UI elements."""
    # Main UI
    draw_player_stats(screen, assets, player_frames, attack_frames, chopping_frames)
    draw_experience_bar(screen, assets)
    draw_hud(screen, assets)
    draw_ability_bar(screen, assets)
    draw_tooltip_for_nearby_objects(screen, assets["small_font"])

    # Dialogs
    draw_npc_dialog(screen, assets)
    draw_miner_dialog(screen, assets)

    # UI Panels (drawn in order of priority)
    if show_pause_menu:
        draw_pause_menu(screen, assets)
    if show_inventory:
        draw_inventory(screen, assets)
    if show_crafting:
        draw_crafting_panel(screen, assets, is_hovering)
    if show_equipment:
        draw_equipment_panel(screen, assets)
    if show_vendor_gui:
        draw_vendor_gui(screen, assets)
    
    # Notifications
    draw_level_up_notification(screen, assets)
    
    # Debug info
    draw_player_coordinates(screen, assets["small_font"])

def _handle_game_over(screen, assets):
    """Handle game over screen and restart logic."""
    global current_level, map_offset_x, map_offset_y, player_pos, enemies, inventory, equipment_slots
    
    if player.health <= 0:
        game_over_text = assets["large_font"].render("GAME OVER", True, (255, 0, 0))
        restart_text = assets["font"].render("Press R to restart or ESC to quit", True, (255, 255, 255))
        screen.blit(game_over_text, game_over_text.get_rect(center=(WIDTH//2, HEIGHT//2 - 50)))
        screen.blit(restart_text, restart_text.get_rect(center=(WIDTH//2, HEIGHT//2 + 50)))
        
        keys = pygame.key.get_pressed()
        if keys[pygame.K_r]:
            # Restart game
            player.health = player.max_health
            player.level = 1
            player.experience = 0
            player.experience_to_next = 100
            current_level = "world"
            map_offset_x = 0
            map_offset_y = 0
            player_pos.center = (WIDTH // 2, HEIGHT // 2)
            enemies.clear()
            inventory = [[None for _ in range(4)] for _ in range(4)]
            equipment_slots = {
                "weapon": None,
                "helmet": None,
                "armor": None,
                "boots": None,
                "ring1": None,
                "ring2": None,
                "amulet": None,
                "shield": None
            }
            give_starting_items(assets)
            setup_colliders()
        elif keys[pygame.K_ESCAPE]:
            pygame.quit()
            sys.exit()

# Additional helper function for the enhanced enemy spawning system
def update_enemy_spawns():
    """Enhanced enemy spawning with better debugging and enemy management."""
    if current_level != "dungeon":
        return
        
    current_time = pygame.time.get_ticks()
    total_enemies_before = len(enemies)
    
    for spawn_point in enemy_spawn_points:
        # Clean up dead enemy references
        if spawn_point.current_enemy and spawn_point.current_enemy not in enemies:
            print(f"Cleaning up dead {spawn_point.enemy_type} reference at spawn ({spawn_point.x}, {spawn_point.y})")
            spawn_point.current_enemy = None
        
        # Try to spawn new enemy
        if spawn_point.can_spawn(current_time):
            new_enemy = spawn_point.spawn_enemy(current_time)
            if new_enemy:
                print(f"Successfully spawned {new_enemy.type} at ({new_enemy.rect.x}, {new_enemy.rect.y})")
    
    total_enemies_after = len(enemies)
    if total_enemies_after > total_enemies_before:
        print(f"Enemy count increased from {total_enemies_before} to {total_enemies_after}")

main()