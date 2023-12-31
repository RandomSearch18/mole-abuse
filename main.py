from __future__ import annotations
import random
from typing import Callable, Optional, Tuple
from collections import deque
from enum import Enum
import math
from pathlib import Path

import pygame
from pygame import Color
from pygame.event import Event


class Theme:
    """Colors used by the game, labeled according to their purpose

    - Based on Dracula theme
    - See https://draculatheme.com/contribute#color-palette
    """

    BACKGROUND = Color("#282A36")
    FOREGROUND = Color("#F8F8F2")
    RED = Color("#FF5555")
    YELLOW = Color("#F1FA8C")


class Corner(Enum):
    TOP_LEFT = (0, 0)
    TOP_RIGHT = (1, 0)
    BOTOM_LEFT = (0, 1)
    BOTOM_RIGHT = (1, 1)


class Edge(Enum):
    TOP = (0, -1)
    BOTTOM = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)


class PointSpecifier:
    outer_corner: Corner
    self_corner: Optional[Corner]

    def resolve(
        self, game: Game
    ) -> Tuple[float, float]:
        raise NotImplementedError()

    def move_left(self, pixels: float):
        raise NotImplementedError()

    def move_right(self, pixels: float):
        raise NotImplementedError()

    def move_up(self, pixels: float):
        raise NotImplementedError()

    def move_down(self, pixels: float):
        raise NotImplementedError()

    def on_window_resize(self, event: Event):
        """Responds to a window resize event to keep the position within window bounds"""
        pass

    def calculate_offest_to_corner(
        self, object_width: float, object_height: float, corner_to: Corner
    ) -> Tuple[float, float]:
        corner_from = self.self_corner

        if corner_from == corner_to:
            return (0, 0)

        corner_to_x, corner_to_y = corner_to.value
        if corner_from is None:
            # Calculating from center
            x_multiplier = 1 if corner_to_x == 1 else -1
            y_multiplier = 1 if corner_to_y == 1 else -1
            offset_x = (object_width / 2) * x_multiplier
            offset_y = (object_height / 2) * y_multiplier
            return (offset_x, offset_y)

        corner_from_x, corner_from_y = corner_from.value
        x_multiplier = corner_to_x - corner_from_x
        y_multiplier = corner_to_y - corner_from_y
        offset_x = object_width * x_multiplier
        offset_y = object_height * y_multiplier

        return (offset_x, offset_y)

    def calculate_top_left(self, game: Game, object_width: float, object_height: float):
        return self.find_corner(Corner.TOP_LEFT, game, object_width, object_height)

    def find_corner(
        self, corner: Corner, game: Game, object_width: float, object_height: float
    ):
        x, y = self.resolve(game)
        offset_x, offset_y = self.calculate_offest_to_corner(
            object_width, object_height, corner
        )
        top_left_x = x + offset_x
        top_left_y = y + offset_y
        return (top_left_x, top_left_y)


class PixelsPoint(PointSpecifier):
    def __init__(
        self,
        x: float,
        y: float,
        outer_corner: Corner = Corner.TOP_LEFT,
        self_corner: Optional[Corner] = None,
    ):
        """Create a new pixel-based point specifier

        @x: The number of pixels horizontally away from the outer corner that the point should be at
        @y: The number of pixels vertically away from the outer corner that the point should be at
        @outer_corner: The corner of the parent box (i.e. the game window) that the point is placed relative to
        @self_corner: If this point represents an object's position, the corner of said object that this coordinate represents. \
        Defaults to `None`, which means this point represents the object's centre (or isn't attached to any object).
        """
        self.x = x
        self.y = y
        self.outer_corner = outer_corner
        self.self_corner = self_corner

    def resolve(self, game: Game) -> Tuple[float, float]:
        outer_width = game.window_box().width
        outer_height = game.window_box().height
        multiplier_x, multiplier_y = self.outer_corner.value

        # Coordinates of the window corner that we're working relative to
        base_x_coordinate = multiplier_x * outer_width
        base_y_coordinate = multiplier_y * outer_height

        # Calculate the number of pixels away from the corner that we should be at
        x_offset = -self.x if multiplier_x else +self.x
        y_offset = -self.y if multiplier_y else +self.y

        # Calculate the desired coordinates of the top-left of our object
        actual_x_coordinate = base_x_coordinate + x_offset
        actual_y_coordinate = base_y_coordinate + y_offset

        # print(actual_x_coordinate, actual_y_coordinate)
        return (actual_x_coordinate, actual_y_coordinate)

    def move_right(self, pixels: float):
        x_corner = self.outer_corner.value[0]
        pixel_movement = -pixels if x_corner else +pixels
        self.x += pixel_movement

    def move_left(self, pixels: float):
        x_corner = self.outer_corner.value[0]
        pixel_movement = +pixels if x_corner else -pixels
        self.x += pixel_movement

    def move_down(self, pixels: float):
        y_corner = self.outer_corner.value[1]
        pixel_movement = -pixels if y_corner else +pixels
        self.y += pixel_movement

    def move_up(self, pixels: float):
        y_corner = self.outer_corner.value[1]
        pixel_movement = +pixels if y_corner else -pixels
        self.y += pixel_movement

    def on_window_resize(self, event):
        pass


class PercentagePoint(PointSpecifier):
    def __init__(
        self,
        x: float,
        y: float,
        outer_corner: Corner = Corner.TOP_LEFT,
        self_corner: Optional[Corner] = None,
    ):
        self.x = x
        self.y = y
        self.outer_corner = outer_corner
        self.self_corner = self_corner
        self.object = object

    def resolve(
        self, game: Game, width: float = 0, height: float = 0
    ) -> Tuple[float, float]:
        outer_box = game.window_box()
        x_pixels = self.x * outer_box.width
        y_pixels = self.y * outer_box.height

        pixels_point = PixelsPoint(
            x_pixels, y_pixels, self.outer_corner, self.self_corner
        )
        return pixels_point.resolve(game)

    def on_window_resize(self, event):
        # We don't need to do anything on window resize
        # since the percentage positions will still be valid
        pass


class Box:
    def __init__(self, x1: float, y1: float, x2: float, y2: float):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

        self.width = x2 - x1
        self.height = y2 - y1

    @property
    def top(self) -> float:
        return self.y1

    @property
    def bottom(self) -> float:
        return self.y2

    @property
    def left(self) -> float:
        return self.x1

    @property
    def right(self) -> float:
        return self.x2

    def center(self) -> Tuple[float, float]:
        """Calculates the coordinates of the center of the box"""
        center_x = self.left + self.width / 2
        center_y = self.top + self.height / 2

        return (center_x, center_y)

    def is_inside(self, outer_box: Box, allowed_margin=0.0) -> bool:
        is_within_x = (
            outer_box.left - self.left <= allowed_margin
            and self.right - outer_box.right <= allowed_margin
        )

        is_within_y = (
            outer_box.top - self.top <= allowed_margin
            and self.bottom - outer_box.bottom <= allowed_margin
        )

        return is_within_x and is_within_y

    def intersects_with_point(self, coordinates: Tuple[float, float]):
        other_x, other_y = coordinates
        is_within_x = self.x1 <= other_x <= self.x2
        is_within_y = self.y1 <= other_y <= self.y2
        return is_within_x and is_within_y

    def is_outside(self, other_box: Box) -> bool:
        is_outside_x = self.right < other_box.left or self.left > other_box.right

        is_outside_y = self.bottom < other_box.top or self.top > other_box.bottom

        return is_outside_x or is_outside_y


class Game:
    def __init__(self, max_fps):
        # Window display config
        self.theme = Theme
        self.background_color = self.theme.BACKGROUND

        # Initilise the display surface
        self.surface = pygame.display.set_mode((600, 400), pygame.RESIZABLE)
        pygame.display.set_caption("Mole Abuse")

        # Initialise other game components
        self.max_fps = max_fps
        self.clock = pygame.time.Clock()
        self.exited = False
        self.objects: list[GameObject] = []
        self.old_window_dimensions = (self.width(), self.height())
        self.key_action_callbacks = {}
        self.key_up_callbacks = {}
        self.is_paused = False
        self.recent_frame_times = deque(maxlen=10)

        # Set up default keybinds
        self.keybinds = {}

        pygame.init()

    def width(self) -> int:
        """Returns the width of the window, in pixels"""
        return self.surface.get_width()

    def height(self) -> int:
        """Returns the height of the window, in pixels"""
        return self.surface.get_height()

    def window_box(self) -> Box:
        """Calculates the box that represents the size of the window"""
        x1 = 0
        y1 = 0
        x2 = self.width()
        y2 = self.height()

        return Box(x1, y1, x2, y2)

    def on_event(self, event):
        # print(event)
        if event.type == pygame.QUIT:
            self.exited = True
        elif event.type == pygame.VIDEORESIZE:
            event.old_dimensions = self.old_window_dimensions
            for object in self.objects:
                object.position.on_window_resize(event)
            self.old_window_dimensions = (self.width(), self.height())

        # Keyboard input
        elif event.type == pygame.KEYDOWN:
            if event.key in self.keybinds:
                action = self.keybinds[event.key]
                self.trigger_key_action(action, event)
        elif event.type == pygame.KEYUP:
            if event.key in self.key_up_callbacks:
                callback = self.key_up_callbacks[event.key]
                callback()

        # Mouse clicks
        elif event.type == pygame.MOUSEBUTTONUP:
            click_x, click_y = event.pos
            for object in self.objects:
                if object.collision_box().intersects_with_point(event.pos):
                    # Run any on-click callbacks for the object
                    for callback in object.on_click_tasks:
                        callback(event)

    def trigger_key_action(self, action: str, event: pygame.event.Event):
        if action not in self.key_action_callbacks:
            return
        action_callback = self.key_action_callbacks[action]
        on_key_up = action_callback(event)
        self.key_up_callbacks[event.key] = lambda: on_key_up(event)

    def on_key_action(self, action: str):
        def decorator(callback):
            self.key_action_callbacks[action] = callback

        return decorator

    def milliseconds_per_frame(self):
        """Returns average time taken to compute, render, and draw the last 10 frames"""
        times = self.recent_frame_times
        if not len(times):
            # Default to 0 if we haven't recorded any frame times yet
            return 0
        sum = 0
        for time in times:
            sum += time
        average = sum / len(times)
        return average

    def execute_tick(self):
        """Updates the states and positions of all game objects.

        - One tick should happen every frame
        - Runs the event handlers for any events emitted since the last tick
        - Runs the tick tasks for each game object
        - This is essentially the computational/"logical server" side of the game
        """
        for event in pygame.event.get():
            self.on_event(event)

        # Handle dead moles
        if not self.current_mole.alive:
            self.objects.remove(self.current_mole)
            print("New mole!")
            self.current_mole = Mole(game=self)
            self.objects.append(self.current_mole)
        
        # Update the objects
        if not self.is_paused:
            for object in self.objects:
                object.run_tick_tasks()
        else:
            # Always update the FPS counter
            self.fps_counter.run_tick_tasks()

    def draw_frame(self):
        """Redraws the screen, ready for the display to be refreshed

        - This should happen every frame
        - Should be called after objects have ticked but before the display is updated
        - This is the graphical/"logical client" side of the game
        """
        # Clear the entire surface
        self.surface.fill(self.background_color)

        # Draw each object
        for object in self.objects:
            object.draw()

    def update_display(self):
        pygame.display.update()

    def game_session(self):
        self.score = 0
        
        self.fps_counter = FPSCounter(game=self)
        self.objects.append(self.fps_counter)
        self.objects.append(ScoreCounter(game=self))

        self.current_mole = Mole(game=self)
        self.objects.append(self.current_mole)

        while not self.exited:
            self.execute_tick()
            self.draw_frame()
            self.update_display()

            self.recent_frame_times.append(self.clock.get_rawtime())
            self.clock.tick(self.max_fps)

        self.objects.clear()
        self.key_action_callbacks.clear()
        self.key_up_callbacks.clear()


class Texture:
    def __init__(self, width, height):
        self.base_width = width
        self.base_height = height

    def height(self) -> float:
        return self.base_height

    def width(self) -> float:
        return self.base_width

    def draw_at(self, top_left: PointSpecifier):
        pass


class PlainColorTexture(Texture):
    def __init__(self, game: Game, color: Color, width, height):
        self.game = game
        self.color = color
        super().__init__(width, height)

    def draw_at(self, position: PointSpecifier):
        x1, y1 = position.calculate_top_left(self.game, self.width(), self.height())

        pygame.draw.rect(
            self.game.surface,
            self.color,
            [x1, y1, self.width(), self.height()],
        )


class TextTexture(Texture):
    def width(self) -> float:
        return self.current_rect.width

    def height(self) -> float:
        return self.current_rect.height

    def get_content(self):
        provided_content = self._get_content()
        if isinstance(provided_content, str):
            return (provided_content, self.game.theme.FOREGROUND)
        return provided_content

    def render_text(self, start_x: float, start_y: float):
        """Computes a surface and bounding rect for the text, but doesn't draw it to the screen"""
        text_content, text_color = self.get_content()
        use_antialiasing = True
        text_surface = self.font.render(text_content, use_antialiasing, text_color)

        text_rect = text_surface.get_rect()
        text_rect.left = math.floor(start_x)
        text_rect.top = math.floor(start_y)

        return text_surface, text_rect

    def __init__(
        self,
        game: Game,
        get_content: Callable[[], str | Tuple[str, Color]],
        font: pygame.font.Font,
        get_color: Optional[Callable[[], Color]] = None,
    ):
        self.game = game
        self._get_content = get_content
        self.font = font
        self.get_color = get_color or (lambda: self.game.theme.FOREGROUND)
        self.current_rect = self.render_text(0, 0)[1]
        super().__init__(self.width(), self.height())

    def draw_at(self, position: PointSpecifier):
        start_x, start_y = position.calculate_top_left(
            self.game, self.width(), self.height()
        )
        text_surface, text_rect = self.render_text(start_x, start_y)
        self.current_rect = text_rect
        self.game.surface.blit(text_surface, text_rect)


class ImageTexture(Texture):
    def __init__(self, game, image):
        self.game = game
        self.image = image

        width = self.image.get_width()
        height = self.image.get_height()
        super().__init__(width, height)

    def draw_at(self, position: PointSpecifier):
        start_x, start_y = position.calculate_top_left(
            self.game, self.width(), self.height()
        )
        self.game.surface.blit(self.image, (start_x, start_y))


class GameObject:
    def height(self) -> float:
        return self.texture.height()

    def width(self) -> float:
        return self.texture.width()

    def spawn_point(self) -> PointSpecifier:
        raise NotImplementedError()

    def reset(self):
        """Moves the object to its initial position (spawn point)"""
        spawn_point = self.spawn_point()
        self.position = spawn_point

    def __init__(
        self,
        texture: Texture,
        solid=True,
    ):
        assert hasattr(self, "game")
        assert isinstance(self.game, Game)
        self.game: Game = self.game
        self.tick_tasks: list[Callable] = []
        self.on_click_tasks: list[Callable[[Event], None]] = []
        self.texture = texture
        self.is_solid = solid
        self.spawned_at = pygame.time.get_ticks()
        self.reset()

    def draw(self):
        raise NotImplementedError()

    def run_tick_tasks(self):
        for callback in self.tick_tasks:
            callback()

    def age(self) -> float:
        """Returns milliseconds since this game object was initialised"""
        current_time = pygame.time.get_ticks()
        return current_time - self.spawned_at
    
    def calculate_center_bounds(self, parent_width: float, parent_height: float) -> Box:
        """Calculates the box of possible positions for the center point of this object"""
        x_padding = self.width() / 2
        y_padding = self.height() / 2

        x1 = 0 + x_padding
        x2 = parent_width - x_padding
        y1 = 0 + y_padding
        y2 = parent_height - y_padding

        return Box(x1, y1, x2, y2)

    def collision_box(self) -> Box:
        """Calculates the visual bounding box (i.e. collision box) for this object"""
        x1, y1 = self.position.calculate_top_left(
            self.game, self.width(), self.height()
        )
        x2 = x1 + self.width()
        y2 = y1 + self.height()

        return Box(x1, y1, x2, y2)

    def calculate_position_percentage(self, bounds: Box) -> Tuple[float, float]:
        """Calculates the position of the center of the object, returning coordinates in the form (x, y)

        - Coordinates are scaled from 0.0 to 1.0 to represent percentage relative to the provided bounding box
        """
        center_x, center_y = self.collision_box().center()

        # Calculate the percentage position of the center relative to the bounding box
        percentage_x = (center_x - bounds.left) / bounds.width
        percentage_y = (center_y - bounds.top) / bounds.height

        return percentage_x, percentage_y

    def map_relative_position_to_box(
        self,
        position_percentage: Tuple[float, float],
        new_center_point_bounds: Box,
    ) -> Tuple[float, float]:
        """Calculates the new center point based on the saved percentage and the new bounding box dimensions"""
        limit = new_center_point_bounds

        # Calculate the new center based on the percentage and the new bounding box
        new_center_x = limit.left + limit.width * position_percentage[0]
        new_center_y = limit.top + limit.height * position_percentage[1]

        return new_center_x, new_center_y

    def is_within_window(self, allowed_margin=0.0):
        window = self.game.window_box()
        return self.collision_box().is_inside(window, allowed_margin)

    def is_outside_window(self):
        window = self.game.window_box()
        return self.collision_box().is_outside(window)

    def coordinates(self):
        return self.position.resolve(self.game)

    def closest_window_edge(self) -> Edge:
        outer_box = self.game.window_box()
        our_x, our_y = self.coordinates()
        distances = {
            Edge.TOP: abs(outer_box.top - our_y),
            Edge.BOTTOM: abs(outer_box.bottom - our_y),
            Edge.LEFT: abs(outer_box.left - our_x),
            Edge.RIGHT: abs(outer_box.right - our_x),
        }
        closest_edge = min(distances, key=distances.get)
        return closest_edge
        

class Velocity:
    def on_tick(self):
        x_movement = self.x
        y_movement = self.y

        self.object.position.move_right(x_movement)
        self.object.position.move_down(y_movement)

    def __init__(self, game_object: GameObject, base_speed: float):
        # Magnitudes of velocity, measured in pixels/tick
        self.x = 0
        self.y = 0

        # The speed that the object will travel at by default (pixels/tick)
        self.base_speed = base_speed

        self.object = game_object
        self.object.tick_tasks.append(self.on_tick)

    def shove_x(self, multiplier=1.0):
        self.x = self.base_speed * multiplier

    def shove_y(self, multiplier=1.0):
        self.y = self.base_speed * multiplier
    
class FPSCounter(GameObject):
    def draw(self):
        self.texture.draw_at(self.position)

    def calculate_color(self, fps: float) -> pygame.Color:
        color = self.game.theme
        if fps < game.max_fps / 2:
            return color.RED
        if math.floor(fps) < game.max_fps:
            return color.YELLOW
        return color.FOREGROUND

    def get_content(self) -> Tuple[str, Color]:
        fps = self.game.clock.get_fps()
        color = self.calculate_color(fps)
        return f"{fps:.0f} FPS", color

    def __init__(self, game: Game):
        self.game = game
        self.font = pygame.font.Font("freesansbold.ttf", 12)
        self.spawn_point = lambda: PixelsPoint(
            x=0, y=0, outer_corner=Corner.TOP_RIGHT, self_corner=Corner.TOP_RIGHT
        )
        texture = TextTexture(game, self.get_content, self.font)

        super().__init__(texture=texture)


# class FrameTimeCounter(GameObject):
#     def tick(self):
#         pass

#     def init(self):
#         self.memorized_frame_time = None

class ScoreCounter(GameObject):
    def draw(self):
        self.texture.draw_at(self.position)

    def get_content(self) -> str:
        return f"Score: {self.game.score}"

    def __init__(self, game: Game):
        self.game = game
        self.font = pygame.font.Font("freesansbold.ttf", 20)
        self.spawn_point = lambda: PixelsPoint(
            x=5, y=5, outer_corner=Corner.TOP_LEFT, self_corner=Corner.TOP_LEFT
        )
        texture = TextTexture(game, self.get_content, self.font)

        super().__init__(texture=texture)

class Mole(GameObject):
    def draw(self):
        self.texture.draw_at(self.position)

    def generate_spawn_position(self, outer_size: float, margin: float) -> int:
        lower_bound = math.ceil(margin)
        upper_bound = math.floor(outer_size - margin)
        # print(f"Margin {margin}, range {lower_bound}..{upper_bound}")
        return random.randint(lower_bound, upper_bound)

    def spawn_point(self) -> PointSpecifier:
        #print("Mole dimensions", self.width(), self.height())
        x = self.generate_spawn_position(self.game.width(), self.width() / 2)
        y = self.generate_spawn_position(self.game.height(), self.height() / 2)
        return PixelsPoint(x, y)

    def handle_whack(self, event: Event):
        self.alive = False
        self.game.score += 1

    def check_age(self):
        if self.age() < self.max_age:
            return

        # Start a death 'animation' by shoving the mole towards the nearest edge
        target_edge_x, target_edge_y = self.closest_window_edge().value
        self.velocity.shove_x(target_edge_x)
        self.velocity.shove_y(target_edge_y)

    def check_if_offscreen(self):
        """Kill the mole if it goes offscreen, since its death animation has finished"""
        if self.is_birth_animation == True:
            return
        if not self.is_outside_window():
            return
        self.alive = False

        # Reduce the score by 1 since the player missed this mole, haha take the L
        if self.game.score > 0:
            self.game.score -= 1

    def set_pre_birth_positon(self):
        target_edge = self.closest_window_edge()
        if target_edge == Edge.LEFT:
            self.position.x = 0 - self.width()
        if target_edge == Edge.RIGHT:
            self.position.x = self.game.width() + self.width()
        if target_edge == Edge.TOP:
            self.position.y = 0 - self.height()
        if target_edge == Edge.BOTTOM:
            self.position.y = self.game.height() + self.height()

    def do_birth_animation(self):
        # nearest_corner_x, nearest_corner_y = self.closest_window_edge().value
        # if nearest_corner_x != 0:
        #     if self.position.x == -1:
        self.is_birth_animation = True
        self.set_pre_birth_positon()
        # Move onto the screen (towards the target edge) until it reaches its spawn point
        target_edge_x, target_edge_y = self.closest_window_edge().value
        self.velocity.shove_x(-target_edge_x)
        self.velocity.shove_y(-target_edge_y)
        print(self.position.x, self.position.y, "+ velocity", self.velocity.x, self.velocity.y)
    
    def __init__(self, game: Game) -> None:
        self.game = game
        # Mole image adapted from the Mullvad VPN logo: https://mullvad.net/en/press
        texture_image = pygame.image.load(Path("assets", "mole.svg"))
        texture = ImageTexture(game=game, image=texture_image)
        super().__init__(texture=texture)
        self.on_click_tasks.append(self.handle_whack)
        self.tick_tasks.extend([self.check_age, self.check_if_offscreen])
        self.is_birth_animation = False
        self.alive = True
        self.max_age = 1.5 * 1000 # 1.5 seconds in ms
        self.velocity = Velocity(self, 20)
        self.do_birth_animation()


# Starts a session of the game in a window running at 60 fps
game = Game(max_fps=60)
game.game_session()
