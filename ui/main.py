import os
import random
import sys
import pygame
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quantum_backend import Layout as QuantumLayout, NoiseConfig, run_batch
from economy import Economy, upgrade_price
from entities import Inspector as QuantumInspector, Storage

pygame.init()

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
pygame.display.set_caption('Quantum Mining Tycoon')
clock = pygame.time.Clock()
game_state = "start"
start_transition_at = None
font = pygame.font.Font(None, 28)
large_font = pygame.font.Font(None, 42)

# Generate absolute path for background image
sky_path = os.path.join(ASSETS_DIR, "sky.jpg")
background = pygame.image.load(sky_path).convert()


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

    def move_to(self, position, delta_seconds):
        target_x, target_y = position
        self.rect.centerx += round((target_x - self.rect.centerx) * min(1.0, delta_seconds * 4.0))
        self.rect.centery += round((target_y - self.rect.centery) * min(1.0, delta_seconds * 4.0))

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
            if self.rng.random() < 0.05:
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
                    self.gold_quantities[(row_index, column_index)] = self.rng.randint(3, 10)

    def gold_targets_in_row(self, row_index):
        return [
            column_index
            for column_index, tile_name in enumerate(self.layout[row_index])
            if tile_name == "gold"
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
            self.miner_position = (
                self.miner_position[0],
                TILE_SIZE // 2 + round(self.scroll_offset),
            )
            if self.scroll_offset <= -TILE_SIZE:
                self.layout.pop(0)
                self.layout.append(self.create_row())
                self.refresh_gold_quantities()
                self.scroll_offset = 0.0
                self.scroll_velocity = 0.0
                self.is_scrolling = False
                self.set_current_row()
            return

        if not self.mining_targets:
            self.start_row_scroll()
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
            if self.mining_index >= len(self.mining_targets):
                self.start_row_scroll()

    def start_row_scroll(self):
        self.is_scrolling = True
        self.scroll_offset = 0.0
        self.scroll_velocity = 0.0

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
                target = (row_index, column_index)
                if target in self.gold_quantities and self.gold_quantities[target] > 0:
                    amount = font.render(
                        f"x{self.gold_quantities[target]}", True, (255, 245, 150)
                    )
                    label_x = position[0] + 4
                    label_y = max(145, position[1] + 4)
                    surface.blit(amount, (label_x, label_y))


class MineController:
    STORAGE_X = 55
    TRAVEL_SECONDS = 2.4
    MINING_SECONDS = 1.8
    BROKEN_FRAME_AT = 0.75

    def __init__(self, tile_map):
        self.tile_map = tile_map
        self.storage = Storage(capacity=9999)
        self.economy = Economy(credits=100)
        # Speeds are deliberately conservative at the start so the round trip
        # and mining animation are easy to follow.
        self.speeds = [0.45, 0.45]
        self.inspectors = [False, False]
        self.rows = [0, 1]
        self.states = ["idle", "idle"]
        self.timers = [0.0, 0.0]
        self.targets = [None, None]
        self.loads = [0, 0]
        self.selected = 0
        self.rejected_loads = 0
        self.silent_errors = 0
        self.total_actions = 0
        self.total_real_ore = 0
        self.last_quality = 1.0
        self.batch = ()
        self.batch_index = 0
        self.cache_layout()

    def cache_layout(self):
        layout = QuantumLayout(
            miner_speeds=tuple(self.speeds),
            depth=max(1, round(max(self.speeds))),
            inspectors=sum(self.inspectors),
        )
        self.batch = run_batch(
            layout,
            shots=1000,
            noise=NoiseConfig(bit_flip=0.025, depolarizing=0.01, seed=7),
            use_aer=True,
        )
        self.batch_index = 0

    def selected_speed(self):
        return self.speeds[self.selected]

    def selected_inspector(self):
        return self.inspectors[self.selected]

    def price(self, upgrade):
        levels = self.economy.levels or {}
        return upgrade_price(upgrade, levels.get(upgrade, 0))

    def buy(self, upgrade):
        if upgrade == "inspector" and self.inspectors[self.selected]:
            return False
        price = self.price(upgrade)
        if self.economy.credits < price:
            return False
        self.economy.credits -= price
        self.economy.levels[upgrade] = self.economy.levels.get(upgrade, 0) + 1
        if upgrade == "miner":
            self.speeds.append(0.45)
            self.inspectors.append(False)
            self.rows.append(len(self.rows))
            self.states.append("idle")
            self.timers.append(0.0)
            self.targets.append(None)
            self.loads.append(0)
        elif upgrade == "speed":
            self.speeds[self.selected] += 0.25
        else:
            self.inspectors[self.selected] = True
        self.cache_layout()
        return True

    def choose_target(self, miner_index):
        row_index = self.rows[miner_index]
        if row_index >= len(self.tile_map.layout):
            return None
        for column_index, tile_name in enumerate(self.tile_map.layout[row_index]):
            if tile_name == "gold" and self.tile_map.gold_quantities.get(
                (row_index, column_index), 0
            ) > 0:
                return column_index
        return None

    def all_assigned_rows_empty(self):
        return all(self.choose_target(index) is None for index in range(len(self.rows)))

    def outcome(self, miner_index):
        row = self.batch[self.batch_index % len(self.batch)]
        self.batch_index += 1
        inspector_index = sum(self.inspectors[:miner_index])
        return row[miner_index][0], row[miner_index][1] if self.inspectors[miner_index] else False

    def deliver(self, miner_index):
        data_bit, flagged = self.outcome(miner_index)
        self.total_actions += 1
        if data_bit:
            self.silent_errors += not flagged
            self.last_quality = self.total_real_ore / max(1, self.total_actions)
        elif flagged:
            self.rejected_loads += 1
        else:
            self.total_real_ore += 1
            self.storage.deposit(1)
            self.economy.credits += 1
            self.last_quality = self.total_real_ore / max(1, self.total_actions)
        if flagged:
            self.states[miner_index] = "rejected"
            self.timers[miner_index] = 0.0
        else:
            self.states[miner_index] = "searching"

    def travel_duration(self, miner_index):
        return self.TRAVEL_SECONDS / max(0.1, self.speeds[miner_index])

    def start_next_trip(self, miner_index):
        target = self.choose_target(miner_index)
        self.targets[miner_index] = target
        self.timers[miner_index] = 0.0
        if target is None:
            self.states[miner_index] = "idle"
        else:
            self.states[miner_index] = "moving"

    def remap_rows_after_scroll(self):
        last_row = len(self.tile_map.layout) - 1
        for index, row in enumerate(self.rows):
            self.rows[index] = last_row if row == 0 else row - 1
            self.targets[index] = None
            self.timers[index] = 0.0
            if self.states[index] == "idle":
                self.states[index] = "searching"

    def visual_position(self, miner_index):
        row = self.rows[miner_index]
        # The tilemap scrolls beneath the miners; actors stay on their row layer.
        y = row * TILE_SIZE + TILE_SIZE // 2
        storage_position = (self.STORAGE_X, y)
        target = self.targets[miner_index]
        if target is None:
            return storage_position

        target_position = (target * TILE_SIZE + TILE_SIZE // 2, y)
        state = self.states[miner_index]
        if state == "moving":
            progress = min(1.0, self.timers[miner_index] / self.travel_duration(miner_index))
            return (
                round(storage_position[0] + (target_position[0] - storage_position[0]) * progress),
                y,
            )
        if state == "returning":
            progress = min(1.0, self.timers[miner_index] / self.travel_duration(miner_index))
            return (
                round(target_position[0] + (storage_position[0] - target_position[0]) * progress),
                y,
            )
        if state == "mining":
            return target_position
        return storage_position

    def update(self, delta_seconds):
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
                self.timers[index] += delta_seconds
                row = self.rows[index]
                column = self.targets[index]
                if self.timers[index] >= self.BROKEN_FRAME_AT:
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
                    self.states[index] = "returning"
                    self.timers[index] = 0.0
            elif self.states[index] == "returning":
                self.timers[index] += delta_seconds
                if self.timers[index] >= self.travel_duration(index):
                    self.deliver(index)
                    self.timers[index] = 0.0

        if any(state == "idle" for state in self.states) and not self.tile_map.is_scrolling:
            self.tile_map.start_row_scroll()


def draw_text(surface, text, position, color=(255, 255, 255), selected_font=None):
    surface.blit((selected_font or font).render(text, True, color), position)


visual_miners = [Miner(110, TILE_SIZE // 2), Miner(110, TILE_SIZE + TILE_SIZE // 2)]
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
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif game_state == "start" and start_transition_at is None:
            if start_button.was_clicked(event):
                game_state = "transition"
                start_transition_at = pygame.time.get_ticks()
                tile_map.begin_transition(transition_animation.rect.bottom)
        elif game_state == "play" and event.type == pygame.KEYDOWN:
            if pygame.K_1 <= event.key <= pygame.K_9:
                selected = event.key - pygame.K_1
                if selected < len(visual_miners):
                    mine.selected = selected
            upgrades = {pygame.K_m: "miner", pygame.K_s: "speed", pygame.K_i: "inspector"}
            if event.key in upgrades:
                if mine.buy(upgrades[event.key]) and upgrades[event.key] == "miner":
                    visual_miners.append(
                        Miner(110, len(visual_miners) * TILE_SIZE + TILE_SIZE // 2)
                    )
        elif game_state == "play" and event.type == pygame.MOUSEBUTTONDOWN:
            for index, visual_miner in enumerate(visual_miners):
                if visual_miner.rect.collidepoint(event.pos):
                    mine.selected = index

    screen.blit(background, (0, 0))

    if game_state == "play":
        delta_seconds = clock.get_time() / 1000.0
        mine.update(delta_seconds)
        tile_map.draw(screen)
        for index, visual_miner in enumerate(visual_miners):
            visual_miner.set_position(mine.visual_position(index))
            visual_miner.draw(screen)
            if mine.inspectors[index]:
                inspector_sprite.draw(
                    screen,
                    (visual_miner.rect.centerx - 50, visual_miner.rect.centery),
                )
        for row in mine.rows:
            storage_sprite.draw(
                screen,
                (mine.STORAGE_X, row * TILE_SIZE + TILE_SIZE // 2),
            )
        panel_width = 760
        panel_height = 175
        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel.fill((10, 10, 18, 210))
        panel_position = (10, BOTTOM - panel_height - 10)
        screen.blit(panel, panel_position)
        selected = mine.selected
        panel_x, panel_y = panel_position
        draw_text(screen, f"Gold: {mine.economy.credits}", (panel_x + 15, panel_y + 12), selected_font=large_font)
        draw_text(screen, f"Purity: {mine.last_quality:.0%}  Accepted: {mine.total_real_ore / max(1, mine.total_actions):.0%}", (panel_x + 260, panel_y + 22))
        draw_text(screen, f"Miners: {len(visual_miners)}  Selected: {selected + 1}", (panel_x + 15, panel_y + 62))
        draw_text(screen, f"Speed: {mine.selected_speed():.0f}  Inspector: {'yes' if mine.selected_inspector() else 'no'}  State: {mine.states[selected]}", (panel_x + 15, panel_y + 90))
        draw_text(screen, f"Rejected: {mine.rejected_loads}  Silent errors: {mine.silent_errors}", (panel_x + 15, panel_y + 118))
        draw_text(screen, f"[M] Miner ${mine.price('miner')}  [S] Speed ${mine.price('speed')}  [I] Inspector ${mine.price('inspector')}", (panel_x + 15, panel_y + 146), (255, 220, 100))
        draw_text(screen, "[1-9] Select miner", (panel_x + 535, panel_y + 62), (255, 220, 100))
    elif game_state == "start":
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
    elif game_state == "pause":
        pass
    else:
        pass    

    pygame.display.update()
    clock.tick(60)

pygame.quit()
