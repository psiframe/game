import os
import random
import sys
import math
import pygame
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quantum_backend import Layout as QuantumLayout, NoiseConfig, run_batch
from economy import Economy, upgrade_price
from entities import Inspector as QuantumInspector, Storage
import sfx

pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()
sfx.init()

# --- DYNAMIC FILE PATH SETUP ---
# This finds the exact directory your script lives in
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

BOTTOM = 720
RIGHT = 1080
TILE_SIZE = 45
GRID_COLUMNS = (RIGHT // TILE_SIZE)
GRID_ROWS = (BOTTOM // TILE_SIZE) + 1

screen = pygame.display.set_mode((1080, 720))
pygame.display.set_caption("Quantum Mining Tycoon")
clock = pygame.time.Clock()
game_state = "start"
start_transition_at = None
font = pygame.font.Font(None, 28)
large_font = pygame.font.Font(None, 42)
title_font = pygame.font.Font(None, 96)
subtitle_font = pygame.font.Font(None, 34)
GAME_TITLE = "Quantum Mining Tycoon"
REFRESH_COOLDOWN = 120.0

# Generate absolute path for background image
sky_path = os.path.join(ASSETS_DIR, "sky.jpg")
background = pygame.transform.scale(pygame.image.load(sky_path).convert(), (RIGHT, BOTTOM))


class Btn:
    def __init__(self, x, y):
        button_path = os.path.join(ASSETS_DIR, "btn.png")
        hover_button_path = os.path.join(ASSETS_DIR, "btn_hover.png")

        self.image = pygame.image.load(button_path).convert_alpha()
        self.hover_image = pygame.image.load(hover_button_path).convert_alpha()
        self.rect = self.image.get_rect(center=(x, y))

    def is_hovered(self):
        return self.rect.collidepoint(pygame.mouse.get_pos())

    def was_clicked(self, event):
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )

    def draw(self, surface):
        image = self.hover_image if self.is_hovered() else self.image
        surface.blit(image, self.rect)

    def draw_labeled(self, surface, label, enabled=True):
        if not enabled:
            disabled = self.image.copy()
            disabled.fill((70, 70, 70, 170), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(disabled, self.rect)
        else:
            self.draw(surface)
        text = font.render(label, True, (255, 255, 255))
        surface.blit(text, text.get_rect(center=self.rect.center))


class ManagementButton:
    def __init__(self, x, y, label, size=(190, 36)):
        self.label = label
        self.rect = pygame.Rect(0, 0, *size)
        self.rect.center = (x, y)

    def is_hovered(self):
        return self.rect.collidepoint(pygame.mouse.get_pos())

    def was_clicked(self, event):
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )

    def draw(self, surface, enabled=True):
        hovered = enabled and self.is_hovered()
        if not enabled:
            fill_color = (55, 55, 65)
            border_color = (95, 95, 105)
            text_color = (145, 145, 150)
        elif hovered:
            fill_color = (65, 125, 165)
            border_color = (220, 245, 255)
            text_color = (255, 255, 255)
        else:
            fill_color = (35, 75, 105)
            border_color = (145, 205, 235)
            text_color = (235, 245, 255)

        pygame.draw.rect(surface, fill_color, self.rect, border_radius=7)
        pygame.draw.rect(surface, border_color, self.rect, width=2, border_radius=7)
        text = font.render(self.label, True, text_color)
        surface.blit(text, text.get_rect(center=self.rect.center))


class Miner:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 100
        self.height = 100
        self.color = (255, 0, 0)
        
        # Generate absolute path for miner image
        miner_path = os.path.join(ASSETS_DIR, "try_miner.png")
        self.image = pygame.image.load(miner_path).convert_alpha()
        self.image = pygame.transform.scale(self.image, (self.width, self.height))
        print(f"SUCCESS: Loaded miner image from {miner_path}")
            
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        
    def draw(self, surface):
        surface.blit(self.image, self.rect)

    def move_to(self, position):
        target_x, target_y = position

        self.rect.centerx += int(target_x > self.rect.centerx) * self.speed
        self.rect.centerx -= int(target_x < self.rect.centerx) * self.speed
        self.rect.centery += int(target_y > self.rect.centery) * self.speed
        self.rect.centery -= int(target_y < self.rect.centery) * self.speed

    def set_position(self, position):
        self.rect.center = position


class Sprite:
    def __init__(self, path, size):
        self.image = pygame.image.load(path).convert_alpha()
        self.image = pygame.transform.scale(self.image, size)
        self.rect = self.image.get_rect()

    def draw(self, surface, center):
        self.rect.center = center
        surface.blit(self.image, self.rect)


class Transition:
    def __init__(self):
        transition_path = os.path.join(ASSETS_DIR, "transition.jpg")
        self.image = pygame.image.load(transition_path).convert_alpha()
        self.image = pygame.transform.scale(self.image, (RIGHT * 2, self.image.get_height() * 2 * RIGHT // self.image.get_width()))
        self.rect = self.image.get_rect(midtop=(RIGHT // 2, BOTTOM))
        print(f"Dimensions: {self.image.get_width()}x{self.image.get_height()}")
        self.speed = 0.0
        self.target_speed = 600.0

    def draw(self, surface):
        surface.blit(self.image, self.rect)

    def animate(self, surface, delta_seconds):
        easing = min(1.0, delta_seconds * 4.0)
        self.speed += (self.target_speed - self.speed) * easing
        self.rect.y -= round(self.speed * delta_seconds)


class TileMap:
    def __init__(self):
        tile_files = {
            "base": "rock_base.png",
            "base2": "rock_base2.png",
            "gold": "rock_gold.png",
            "gold_broken": "rock_gold_broken.png",
            "broken": "rock_broken.png",
            "empty": "empty.png",
        }
        self.tiles = {}
        self.rng = random.Random()

        for tile_name, file_name in tile_files.items():
            tile_path = os.path.join(ASSETS_DIR, file_name)
            image = pygame.image.load(tile_path).convert_alpha()
            self.tiles[tile_name] = pygame.transform.scale(
                image, (TILE_SIZE, TILE_SIZE)
            )

        self.layout = [
            self.create_row()
            for _ in range(GRID_ROWS)
        ]
        self.error = 0.05
        self.left_to_scroll_layers_total = len(self.layout) - 1
        self.mining_targets = []
        self.mining_index = 0
        self.mining_phase = "moving"
        self.mining_timer = 0.0
        self.mining_row = 0
        self.scroll_offset = 0.0
        self.scroll_velocity = 0.0
        self.is_scrolling = False
        self.y = float(BOTTOM)
        self.velocity = 0.0
        self.is_transitioning = False
        self.gold_quantities = {}
        self.miner_position = (RIGHT // 2, BOTTOM // 2)
        self.mining_started = False
        self.refresh_gold_quantities()
        self.set_current_row()

    def create_row(self):
        # The broken gold sprite is reserved for the active mining animation.
        other_tiles = ("base", "base2", "broken", "empty")
        row = []
        for column_index in range(GRID_COLUMNS):
            if self.rng.random() < 0.15:
                tile_name = "gold"
            else:
                tile_name = self.rng.choice(other_tiles)
            row.append(tile_name)
        return row

    def refresh_gold_quantities(self):
        self.gold_quantities = {}
        for row_index, row in enumerate(self.layout):
            for column_index, tile_name in enumerate(row):
                if tile_name == "gold":
                    self.gold_quantities[(row_index, column_index)] = 1

    def gold_targets_in_row(self, row_index):
        return [
            column_index
            for column_index, tile_name in enumerate(self.layout[row_index])
            if tile_name == "gold" or tile_name == "rock_base" and self.rng.random() < self.error
        ]

    def set_current_row(self):
        self.mining_targets = self.gold_targets_in_row(0)
        self.mining_index = 0
        self.mining_phase = "moving"
        self.mining_timer = 0.0

    def begin_transition(self, transition_bottom):
        self.y = float(transition_bottom - 300)
        self.velocity = 0.0
        self.is_transitioning = True

    def animate(self, delta_seconds, leading_velocity):
        if not self.is_transitioning:
            return

        distance_remaining = max(0.0, self.y)
        slowdown_distance = BOTTOM / 2.5
        slowdown = min(1.0, distance_remaining / slowdown_distance)
        target_velocity = leading_velocity * slowdown
        easing = min(1.0, delta_seconds * 5.0)
        self.velocity += (target_velocity - self.velocity) * easing
        self.y -= self.velocity * delta_seconds

        if self.y <= 0.0:
            self.y = 0.0
            self.velocity = 0.0
            self.is_transitioning = False

    def start_mining(self):
        self.mining_started = True

    def update_mining(self, delta_seconds):
        if not self.mining_started:
            return

        if self.is_scrolling:
            self.scroll_velocity += (220.0 - self.scroll_velocity) * min(1.0, delta_seconds * 6.0)
            self.scroll_offset -= self.scroll_velocity * delta_seconds

            # The offset moves from 0 down to -TILE_SIZE, then one row is
            # replaced. Keep the velocity so the scroll stays smooth.
            if self.scroll_offset <= -TILE_SIZE:
                self.layout.pop(0)
                self.layout.append(self.create_row())
                self.refresh_gold_quantities()
                self.scroll_offset += TILE_SIZE
                self.left_to_scroll_layers_total -= 1

                if self.left_to_scroll_layers_total <= 0:
                    self.is_scrolling = False
                    self.scroll_offset = 0.0
                    self.scroll_velocity = 0.0
                self.set_current_row()
            return

        self.left_to_scroll_layers_total = len(self.layout) - 1

        if not self.mining_targets:
            return

        column_index = self.mining_targets[self.mining_index]
        row_index = 0
        self.miner_position = (
            column_index * TILE_SIZE + TILE_SIZE // 2,
            row_index * TILE_SIZE + TILE_SIZE // 2,
        )
        self.mining_timer += delta_seconds

        if self.mining_phase == "moving" and self.mining_timer >= 1.0:
            self.mining_phase = "mining"
            self.mining_timer = 0.0
        elif self.mining_phase == "mining" and self.mining_timer >= 0.9:
            self.layout[row_index][column_index] = "gold_broken"
            self.mining_phase = "depleted"
            self.mining_timer = 0.0
        elif self.mining_phase == "depleted" and self.mining_timer >= 0.8:
            self.layout[row_index][column_index] = "empty"
            self.gold_quantities[(row_index, column_index)] = 0
            self.mining_index += 1
            self.mining_phase = "moving"
            self.mining_timer = 0.0

    def start_row_scroll(self):
        if self.is_scrolling:
            return
        # Reset the row counter on every refresh. Without this, the first
        # refresh leaves it at 0 and every later refresh scrolls one row only.
        self.left_to_scroll_layers_total = len(self.layout) - 1
        self.is_scrolling = True
        self.scroll_offset = 0.0
        self.scroll_velocity = 0.0
        sfx.play("refresh")

    def draw(self, surface, y=None):
        map_y = self.y + self.scroll_offset if y is None else y
        for row_index, row in enumerate(self.layout):
            for column_index, tile_name in enumerate(row):
                tile = self.tiles[tile_name]
                position = (
                    column_index * TILE_SIZE,
                    round(map_y + row_index * TILE_SIZE),
                )
                surface.blit(tile, position)


class MineController:
    STORAGE_POSITION = (RIGHT // 2, BOTTOM // 2)
    BASE_MOVE_SPEED = 45.0
    MINING_SECONDS = 1.8
    BROKEN_FRAME_AT = 0.75

    def __init__(self, tile_map):
        self.tile_map = tile_map
        self.storage = Storage(capacity=9999)
        self.economy = Economy(credits=50)
        # Speeds are deliberately conservative at the start so the round trip
        # and mining animation are easy to follow.
        self.global_speed = 0.45
        self.speeds = [self.global_speed]
        self.error = 0.05
        self.rng = random.Random(7)
        self.inspectors = [False]
        self.rows = list(range(len(self.speeds)))
        self.states = ["idle"]
        self.timers = [0.0]
        self.targets = [None]
        self.target_is_rock = [False]
        self.loads = [0]
        self.selected = None
        self.rejected_loads = 0
        self.silent_errors = 0
        self.total_actions = 0
        self.total_real_ore = 0
        self.total_gold_ore = 0
        self.total_delivered_loads = 0
        self.last_quality = 1.0
        self.storage_pulse_timer = 0.0
        self.storage_pulse_color = (80, 255, 100)
        self.storage_pulse_is_rock = False
        self.inspector_pulse_timers = [0.0]
        self.batch = ()
        self.batch_index = 0

    def selected_speed(self):
        return self.speeds[self.selected] if self.selected is not None else 0.0

    def selected_inspector(self):
        return self.inspectors[self.selected] if self.selected is not None else False

    def price(self, upgrade):
        levels = self.economy.levels or {}
        return upgrade_price(upgrade, levels.get(upgrade, 0))

    def buy(self, upgrade):
        if upgrade == "inspector":
            if self.selected is None:
                try:
                    self.selected = self.inspectors.index(False)
                except ValueError:
                    return False
            elif self.inspectors[self.selected]:
                return False
        price = self.price(upgrade)
        if self.economy.credits < price:
            return False
        self.economy.credits -= price
        self.economy.levels[upgrade] = self.economy.levels.get(upgrade, 0) + 1
        if upgrade == "miner":
            self.speeds.append(self.global_speed)
            self.inspectors.append(False)
            self.rows.append(len(self.rows))
            self.states.append("idle")
            self.timers.append(0.0)
            self.targets.append(None)
            self.target_is_rock.append(False)
            self.loads.append(0)
            self.inspector_pulse_timers.append(0.0)
        elif upgrade == "speed":
            self.global_speed += 0.25
            self.speeds = [self.global_speed for _ in self.speeds]
            self.error = min(0.95, self.error + 0.05)
        else:
            self.inspectors[self.selected] = True
        return True

    def sell_selected_miner(self):
        if self.selected is None or len(self.speeds) < 2:
            return False
        index = self.selected
        self.economy.credits += 20
        self.economy.levels["miner"] = max(
            0,
            self.economy.levels.get("miner", 0) - 1,
        )
        for values in (
            self.speeds,
            self.inspectors,
            self.rows,
            self.states,
            self.timers,
            self.targets,
            self.target_is_rock,
            self.loads,
            self.inspector_pulse_timers,
        ):
            values.pop(index)
        self.selected = None
        return True

    def sell_selected_inspector(self):
        if self.selected is None or not self.inspectors[self.selected]:
            return False
        self.inspectors[self.selected] = False
        self.economy.credits += 20
        self.economy.levels["inspector"] = max(
            0,
            self.economy.levels.get("inspector", 0) - 1,
        )
        return True

    def choose_target(self, miner_index):
        row_index = self.rows[miner_index]
        if row_index >= len(self.tile_map.layout) - 1:
            return None, False
        gold_targets = []
        for column_index, tile_name in enumerate(self.tile_map.layout[row_index]):
            if tile_name == "gold" and self.tile_map.gold_quantities.get(
                (row_index, column_index), 0
            ) > 0:
                gold_targets.append(column_index)
        rock_tiles = {"base", "base2"}
        rock_targets = [
            column_index
            for column_index, tile_name in enumerate(self.tile_map.layout[row_index])
            if tile_name in rock_tiles
        ]
        if rock_targets and self.rng.random() < self.error:
            return self.rng.choice(rock_targets), True
        if gold_targets:
            return gold_targets[0], False
        return None, False

    def advance_row(self, miner_index):
        next_row = self.rows[miner_index] + len(self.rows)
        if next_row >= len(self.tile_map.layout) - 1:
            self.states[miner_index] = "idle"
            self.targets[miner_index] = None
            self.target_is_rock[miner_index] = False
            self.timers[miner_index] = 0.0
            return False
        self.rows[miner_index] = next_row
        self.targets[miner_index] = None
        self.timers[miner_index] = 0.0
        self.states[miner_index] = "searching"
        return True

    def all_assigned_rows_empty(self):
        return all(self.choose_target(index)[0] is None for index in range(len(self.rows)))

    def outcome(self, miner_index):
        is_rock = self.rng.random() < self.error
        flagged = (
            is_rock
            and self.inspectors[miner_index]
            and self.rng.random() < min(0.95, 0.65 + self.error)
        )
        return is_rock, flagged

    def deliver(self, miner_index):
        is_rock = self.loads[miner_index] == "rock"
        flagged = (
            is_rock
            and self.inspectors[miner_index]
            and self.rng.random() < min(0.95, 0.65 + self.error)
        )
        self.total_actions += 1
        if is_rock and flagged:
            self.rejected_loads += 1
            self.inspector_pulse_timers[miner_index] = 0.7
            sfx.play("reject")
        elif is_rock:
            self.silent_errors += 1
            sfx.play("error")
            self.total_delivered_loads += 1
            self.last_quality = self.total_real_ore / max(1, self.total_delivered_loads)
        else:
            self.total_real_ore += 1
            self.total_gold_ore += 1
            self.total_delivered_loads += 1
            self.storage.deposit(1)
            self.last_quality = self.total_real_ore / self.total_delivered_loads
            self.economy.credits += 20.0 * self.last_quality
            sfx.play("gold")
        if not flagged:
            self.storage_pulse_timer = 0.7
            self.storage_pulse_is_rock = is_rock
            self.storage_pulse_color = (255, 70, 70) if is_rock else (80, 255, 100)
        self.loads[miner_index] = 0
        if is_rock and flagged:
            self.states[miner_index] = "rejected"
            self.timers[miner_index] = 0.0
        else:
            self.states[miner_index] = "searching"

    def move_speed(self, miner_index):
        return self.BASE_MOVE_SPEED * (self.speeds[miner_index] / 0.45)

    def travel_duration(self, miner_index):
        target = self.targets[miner_index]
        if target is None:
            return 0.0
        row = self.rows[miner_index]
        target_position = (
            target * TILE_SIZE + TILE_SIZE // 2,
            row * TILE_SIZE + TILE_SIZE // 2,
        )
        distance = (
            (target_position[0] - self.STORAGE_POSITION[0]) ** 2
            + (target_position[1] - self.STORAGE_POSITION[1]) ** 2
        ) ** 0.5
        return distance / self.move_speed(miner_index)

    def start_next_trip(self, miner_index):
        target, is_rock = self.choose_target(miner_index)
        while target is None and self.advance_row(miner_index):
            target, is_rock = self.choose_target(miner_index)
        self.targets[miner_index] = target
        self.target_is_rock[miner_index] = is_rock
        self.timers[miner_index] = 0.0
        if target is None:
            self.states[miner_index] = "idle"
        else:
            self.states[miner_index] = "moving"

    def remap_rows_after_scroll(self):
        for index, row in enumerate(self.rows):
            # A refresh can interrupt a trip; bank the carried load instead of losing it.
            if self.loads[index]:
                self.deliver(index)
            self.rows[index] = index
            self.targets[index] = None
            self.target_is_rock[index] = False
            self.timers[index] = 0.0
            self.states[index] = "searching"

    def visual_position(self, miner_index):
        row = self.rows[miner_index]
        y = row * TILE_SIZE + TILE_SIZE // 2
        storage_position = self.STORAGE_POSITION
        target = self.targets[miner_index]
        if target is None:
            return storage_position

        target_position = (target * TILE_SIZE + TILE_SIZE // 2, y)
        state = self.states[miner_index]
        if state == "moving":
            progress = min(1.0, self.timers[miner_index] / self.travel_duration(miner_index))
            return (
                round(storage_position[0] + (target_position[0] - storage_position[0]) * progress),
                round(storage_position[1] + (target_position[1] - storage_position[1]) * progress),
            )
        if state == "returning":
            progress = min(1.0, self.timers[miner_index] / self.travel_duration(miner_index))
            return (
                round(target_position[0] + (storage_position[0] - target_position[0]) * progress),
                round(target_position[1] + (storage_position[1] - target_position[1]) * progress),
            )
        if state == "mining":
            return target_position
        return storage_position

    def update(self, delta_seconds):
        self.storage_pulse_timer = max(0.0, self.storage_pulse_timer - delta_seconds)
        self.inspector_pulse_timers = [
            max(0.0, timer - delta_seconds)
            for timer in self.inspector_pulse_timers
        ]
        if self.tile_map.is_scrolling:
            self.tile_map.update_mining(delta_seconds)
            if not self.tile_map.is_scrolling:
                self.remap_rows_after_scroll()
            return

        for index in range(len(self.rows)):
            if self.states[index] == "rejected":
                self.timers[index] += delta_seconds
                if self.timers[index] >= 0.5:
                    self.states[index] = "searching"
                continue

            if self.states[index] in ("idle", "searching"):
                self.start_next_trip(index)
                continue
            if self.states[index] == "moving":
                self.timers[index] += delta_seconds
                if self.timers[index] >= self.travel_duration(index):
                    self.states[index] = "mining"
                    self.timers[index] = 0.0
            elif self.states[index] == "mining":
                previous_timer = self.timers[index]
                self.timers[index] += delta_seconds
                if previous_timer < self.BROKEN_FRAME_AT <= self.timers[index]:
                    sfx.play("mine")
                row = self.rows[index]
                column = self.targets[index]
                if column is None:
                    self.states[index] = "idle"
                    self.timers[index] = 0.0
                    continue
                if self.timers[index] >= self.BROKEN_FRAME_AT:
                    if self.target_is_rock[index]:
                        if self.tile_map.layout[row][column] in ("base", "base2", "broken"):
                            self.tile_map.layout[row][column] = "broken"
                    elif self.tile_map.layout[row][column] == "gold":
                        self.tile_map.layout[row][column] = "gold_broken"
                if self.timers[index] >= self.MINING_SECONDS:
                    quantity_key = (row, column)
                    quantity = self.tile_map.gold_quantities.get(quantity_key, 0)
                    if quantity > 0:
                        self.tile_map.gold_quantities[quantity_key] = 0
                        self.tile_map.layout[row][column] = "empty"
                        self.loads[index] = 1
                    else:
                        self.tile_map.layout[row][column] = "empty"
                    if self.target_is_rock[index]:
                        self.loads[index] = "rock"
                    self.target_is_rock[index] = False
                    self.states[index] = "returning"
                    self.timers[index] = 0.0
            elif self.states[index] == "returning":
                self.timers[index] += delta_seconds
                if self.timers[index] >= self.travel_duration(index):
                    self.deliver(index)
                    self.timers[index] = 0.0

        if all(state == "idle" for state in self.states) and not self.tile_map.is_scrolling:
            self.tile_map.start_row_scroll()


def draw_text(surface, text, position, color=(255, 255, 255), selected_font=None):
    surface.blit((selected_font or font).render(text, True, color), position)


visual_miners = [Miner(110, TILE_SIZE // 2)]
inspector_sprite = Sprite(
    os.path.join(ASSETS_DIR, "inspector.webp"), (32, 32)
)
storage_sprite = Sprite(
    os.path.join(ASSETS_DIR, "storage.webp"), (72, 72)
)
start_button = Btn(screen.get_width() // 2, screen.get_height() // 2)
transition_animation = Transition()
tile_map = TileMap()
mine = MineController(tile_map)
management_button_x = RIGHT - 105
sell_miner_button = ManagementButton(management_button_x, BOTTOM - 109, "Sell miner $20")
sell_inspector_button = ManagementButton(
    management_button_x,
    BOTTOM - 67,
    "Sell inspector $20",
)
refresh_map_button = ManagementButton(management_button_x, BOTTOM - 25, "Refresh map")
pause_button = ManagementButton(RIGHT - 75, 28, "Pause [P]", size=(130, 36))
seconds_since_scroll = 0.0
running = True


def toggle_pause():
    global game_state
    game_state = "pause" if game_state == "play" else "play"
    pause_button.label = "Resume [P]" if game_state == "pause" else "Pause [P]"
    sfx.play("pause")


def draw_title_screen(surface):
    title = title_font.render(GAME_TITLE, True, (255, 215, 90))
    shadow = title_font.render(GAME_TITLE, True, (20, 20, 30))
    title_rect = title.get_rect(center=(RIGHT // 2, BOTTOM // 2 - 220))
    surface.blit(shadow, title_rect.move(4, 4))
    surface.blit(title, title_rect)
    subtitle = subtitle_font.render(
        "Mine gold. Fight quantum errors. Decide when protection pays off.",
        True,
        (235, 245, 255),
    )
    subtitle_shadow = subtitle_font.render(
        "Mine gold. Fight quantum errors. Decide when protection pays off.",
        True,
        (20, 20, 30),
    )
    subtitle_rect = subtitle.get_rect(center=(RIGHT // 2, BOTTOM // 2 - 150))
    surface.blit(subtitle_shadow, subtitle_rect.move(2, 2))
    surface.blit(subtitle, subtitle_rect)
    controls_text = "[M] Miner   [S] Speed   [I] Inspector   [1-9] Select   [P] Pause   [N] Sound"
    controls = font.render(controls_text, True, (255, 220, 100))
    controls_rect = controls.get_rect(center=(RIGHT // 2, BOTTOM - 60))
    surface.blit(font.render(controls_text, True, (20, 20, 30)), controls_rect.move(2, 2))
    surface.blit(controls, controls_rect)


def draw_pause_overlay(surface):
    shade = pygame.Surface((RIGHT, BOTTOM), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 150))
    surface.blit(shade, (0, 0))
    paused = title_font.render("PAUSED", True, (255, 255, 255))
    surface.blit(paused, paused.get_rect(center=(RIGHT // 2, BOTTOM // 2 - 30)))
    sound_state = "on" if sfx.is_on() else "off"
    hint = subtitle_font.render(
        f"[P] or [Esc] Resume      [N] Sound: {sound_state}",
        True,
        (255, 220, 100),
    )
    surface.blit(hint, hint.get_rect(center=(RIGHT // 2, BOTTOM // 2 + 35)))
    pause_button.draw(surface)


while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif game_state == "start" and start_transition_at is None:
            if start_button.was_clicked(event):
                sfx.play("start")
                game_state = "transition"
                start_transition_at = pygame.time.get_ticks()
                tile_map.begin_transition(transition_animation.rect.bottom)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_n:
            sfx.toggle()
            sfx.play("click")
        elif (
            game_state in ("play", "pause")
            and event.type == pygame.KEYDOWN
            and event.key in (pygame.K_p, pygame.K_ESCAPE)
        ):
            toggle_pause()
        elif game_state in ("play", "pause") and pause_button.was_clicked(event):
            toggle_pause()
        elif game_state == "play" and event.type == pygame.KEYDOWN:
            if pygame.K_1 <= event.key <= pygame.K_9:
                selected = event.key - pygame.K_1
                if selected < len(visual_miners):
                    mine.selected = selected
                    sfx.play("click")
            upgrades = {pygame.K_m: "miner", pygame.K_s: "speed", pygame.K_i: "inspector"}
            if event.key in upgrades:
                if mine.buy(upgrades[event.key]):
                    sfx.play("buy")
                    if upgrades[event.key] == "miner":
                        visual_miners.append(
                            Miner(110, len(visual_miners) * TILE_SIZE + TILE_SIZE // 2)
                        )
                else:
                    sfx.play("denied")
        elif game_state == "play" and event.type == pygame.MOUSEBUTTONDOWN:
            selected_before_click = mine.selected
            if sell_miner_button.was_clicked(event):
                if mine.sell_selected_miner() and selected_before_click is not None:
                    visual_miners.pop(selected_before_click)
                    sfx.play("buy")
                else:
                    sfx.play("denied")
                continue
            if sell_inspector_button.was_clicked(event):
                sfx.play("buy" if mine.sell_selected_inspector() else "denied")
                continue
            if refresh_map_button.was_clicked(event):
                if seconds_since_scroll >= REFRESH_COOLDOWN and not tile_map.is_scrolling:
                    tile_map.start_row_scroll()
                    seconds_since_scroll = 0.0
                else:
                    sfx.play("denied")
                continue
            mine.selected = None
            for index, visual_miner in enumerate(visual_miners):
                if visual_miner.rect.collidepoint(event.pos):
                    mine.selected = index
                    break

    screen.blit(background, (0, 0))

    if game_state in ("play", "pause"):
        if game_state == "play":
            delta_seconds = clock.get_time() / 1000.0
            was_scrolling = tile_map.is_scrolling
            mine.update(delta_seconds)
            if was_scrolling and not tile_map.is_scrolling:
                seconds_since_scroll = 0.0
            elif not tile_map.is_scrolling:
                seconds_since_scroll += delta_seconds
        tile_map.draw(screen)
        for index, visual_miner in enumerate(visual_miners):
            visual_miner.set_position(mine.visual_position(index))
            if index == mine.selected:
                glow_rect = visual_miner.rect.inflate(10, 10)
                pygame.draw.rect(screen, (255, 255, 255), glow_rect, 2, border_radius=6)
            visual_miner.draw(screen)
            if mine.inspectors[index]:
                inspector_x = visual_miner.rect.centerx - 50
                inspector_y = visual_miner.rect.centery
                if mine.inspector_pulse_timers[index] > 0.0:
                    progress = 1.0 - mine.inspector_pulse_timers[index] / 0.7
                    pulse_surface = pygame.Surface((100, 100), pygame.SRCALPHA)
                    pulse_alpha = max(0, int(190 * (1.0 - progress)))
                    pulse_radius = int(12 + 28 * progress)
                    pygame.draw.circle(
                        pulse_surface,
                        (255, 220, 60, pulse_alpha),
                        (50, 50),
                        pulse_radius,
                        4,
                    )
                    screen.blit(pulse_surface, (inspector_x - 50, inspector_y - 50))
                    vibration = (1.0 - progress) * 3.0
                    inspector_x += round(math.sin(progress * 80.0) * vibration)
                    inspector_y += round(math.cos(progress * 73.0) * vibration)
                inspector_sprite.draw(
                    screen,
                    (inspector_x, inspector_y),
                )
        storage_x, storage_y = mine.STORAGE_POSITION
        storage_offset_x = 0
        storage_offset_y = 0
        if mine.storage_pulse_timer > 0.0:
            progress = 1.0 - mine.storage_pulse_timer / 0.7
            pulse_surface = pygame.Surface((180, 180), pygame.SRCALPHA)
            pulse_alpha = max(0, int(180 * (1.0 - progress)))
            pulse_radius = int(32 + 48 * progress)
            pygame.draw.circle(
                pulse_surface,
                (*mine.storage_pulse_color, pulse_alpha),
                (90, 90),
                pulse_radius,
                5,
            )
            screen.blit(
                pulse_surface,
                (storage_x - 90, storage_y - 90),
            )
            if mine.storage_pulse_is_rock:
                vibration = (1.0 - progress) * 3.0
                storage_offset_x = round(math.sin(progress * 80.0) * vibration)
                storage_offset_y = round(math.cos(progress * 73.0) * vibration)
        storage_sprite.draw(
            screen,
            (storage_x + storage_offset_x, storage_y + storage_offset_y),
        )
        panel_width = 760
        panel_height = 175
        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel.fill((10, 10, 18, 210))
        panel_position = (10, BOTTOM - panel_height - 10)
        screen.blit(panel, panel_position)
        selected = mine.selected
        panel_x, panel_y = panel_position
        draw_text(screen, f"Credits: ${mine.economy.credits:.0f}", (panel_x + 15, panel_y + 12), selected_font=large_font)
        draw_text(screen, f"Gold ore: {mine.total_gold_ore}", (panel_x + 260, panel_y + 12))
        draw_text(screen, f"Purity: {mine.last_quality:.0%}  Accepted: {mine.total_real_ore / max(1, mine.total_actions):.0%}", (panel_x + 260, panel_y + 42))
        selected_label = str(selected + 1) if selected is not None else "none"
        selected_details = (
            f"Speed: {mine.selected_speed():.2f}  "
            f"Inspector: {'yes' if mine.selected_inspector() else 'no'}  "
            f"State: {mine.states[selected]}"
            if selected is not None
            else "Speed: --  Inspector: --  State: --"
        )
        draw_text(screen, f"Miners: {len(visual_miners)}  Selected: {selected_label}", (panel_x + 15, panel_y + 62))
        draw_text(screen, selected_details, (panel_x + 15, panel_y + 90))
        draw_text(screen, f"Rejected: {mine.rejected_loads}  Silent errors: {mine.silent_errors}", (panel_x + 15, panel_y + 118))
        draw_text(screen, f"[M] Miner ${mine.price('miner')}  [S] Speed ${mine.price('speed')}  [I] Inspector ${mine.price('inspector')}", (panel_x + 15, panel_y + 146), (255, 220, 100))
        draw_text(screen, "[1-9] Select miner", (panel_x + 535, panel_y + 62), (255, 220, 100))
        sell_miner_button.draw(
            screen,
            mine.selected is not None and len(visual_miners) >= 2,
        )
        sell_inspector_button.draw(
            screen,
            mine.selected is not None and mine.selected_inspector(),
        )
        # Show the cooldown so a disabled button doesn't look broken.
        remaining = max(0, math.ceil(REFRESH_COOLDOWN - seconds_since_scroll))
        if tile_map.is_scrolling:
            refresh_map_button.label = "Refreshing..."
        elif remaining > 0:
            refresh_map_button.label = f"Refresh in {remaining // 60}:{remaining % 60:02d}"
        else:
            refresh_map_button.label = "Refresh map"
        refresh_map_button.draw(
            screen,
            remaining == 0 and not tile_map.is_scrolling,
        )
        if game_state == "pause":
            draw_pause_overlay(screen)
        else:
            pause_button.draw(screen)
    elif game_state == "start":
        draw_title_screen(screen)
        start_button.draw(screen)
    elif game_state == "transition":
        delta_seconds = clock.get_time() / 1000.0
        transition_animation.animate(screen, delta_seconds)
        tile_map.animate(delta_seconds, transition_animation.speed)
        tile_map.draw(screen)
        transition_animation.draw(screen)
        if not tile_map.is_transitioning:
            game_state = "play"
            start_transition_at = None
            tile_map.start_mining()

    pygame.display.update()
    clock.tick(60)

pygame.quit()
