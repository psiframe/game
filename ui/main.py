import os
import pygame

pygame.init()

# --- DYNAMIC FILE PATH SETUP ---
# This finds the exact directory your script lives in
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

BOTTOM = 720
RIGHT = 1080
TILE_SIZE = 45
GRID_COLUMNS = RIGHT // TILE_SIZE
GRID_ROWS = BOTTOM // TILE_SIZE

screen = pygame.display.set_mode((1080, 720))
pygame.display.set_caption('Quantum Mining Tycoon')
clock = pygame.time.Clock()
game_state = "start"
start_transition_at = None

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


class Transition:
    def __init__(self):
        transition_path = os.path.join(ASSETS_DIR, "transition.jpg")
        self.image = pygame.image.load(transition_path).convert_alpha()
        self.image = pygame.transform.scale(self.image, (RIGHT * 2, self.image.get_height() * 2 * RIGHT // self.image.get_width()))
        self.rect = self.image.get_rect(midtop=(RIGHT // 2, BOTTOM))
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

        for tile_name, file_name in tile_files.items():
            tile_path = os.path.join(ASSETS_DIR, file_name)
            image = pygame.image.load(tile_path).convert_alpha()
            self.tiles[tile_name] = pygame.transform.scale(
                image, (TILE_SIZE, TILE_SIZE)
            )

        # Each string identifies the image used for one cell in the grid.
        base_layout = [
            ["base2", "base2", "gold", "base2", "base2", "gold", "base2", "base2", "gold", "base2", "base2", "base2"],
            ["base2", "gold", "gold_broken", "base", "base", "base", "gold", "base", "base", "gold", "base2", "base2"],
            ["base", "base", "base", "base", "gold", "base", "base", "base", "gold_broken", "base", "base", "base"],
            ["base", "broken", "base", "gold", "base", "base2", "base2", "gold", "base", "base", "broken", "base"],
            ["base2", "base", "gold", "base", "base", "gold_broken", "base", "base", "base", "gold", "base", "base2"],
            ["base", "base", "base", "broken", "base", "base", "gold", "base", "broken", "base", "base", "gold"],
            ["base2", "gold", "base", "base", "base2", "base", "base", "gold_broken", "base", "base", "base2", "base"],
            ["base", "base", "gold", "base2", "base", "broken", "base", "base", "gold", "base", "base", "base2"],
        ]
        self.layout = [
            expanded_row
            for row in base_layout
            for expanded_row in (row, row)
        ]
        self.layout = [
            [tile_name for tile_name in row for tile_name in (tile_name, tile_name)]
            for row in self.layout
        ]
        self.y = float(BOTTOM)
        self.velocity = 0.0
        self.is_transitioning = False

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

    def draw(self, surface, y=None):
        map_y = self.y if y is None else y
        for row_index, row in enumerate(self.layout):
            for column_index, tile_name in enumerate(row):
                tile = self.tiles[tile_name]
                position = (
                    column_index * TILE_SIZE,
                    round(map_y + row_index * TILE_SIZE),
                )
                surface.blit(tile, position)


miner = Miner(350, 250)
start_button = Btn(screen.get_width() // 2, screen.get_height() // 2)
transition_animation = Transition()
tile_map = TileMap()
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

    screen.blit(background, (0, 0))

    if game_state == "play":
        tile_map.draw(screen)
        miner.draw(screen)
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
    elif game_state == "pause":
        pass
    else:
        pass    

    pygame.display.update()
    clock.tick(60)

pygame.quit()
