"""Классическая змейка с переходом через границы игрового поля."""

from random import choice

import pygame

SCREEN_WIDTH, SCREEN_HEIGHT = 640, 480
GRID_SIZE = 20
GRID_WIDTH = SCREEN_WIDTH // GRID_SIZE
GRID_HEIGHT = SCREEN_HEIGHT // GRID_SIZE
CENTER_POSITION = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
ALL_CELLS = frozenset(
    (x * GRID_SIZE, y * GRID_SIZE)
    for x in range(GRID_WIDTH)
    for y in range(GRID_HEIGHT)
)

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)
DIRECTIONS = (UP, DOWN, LEFT, RIGHT)
TURNS = {
    (pygame.K_UP, LEFT): UP,
    (pygame.K_UP, RIGHT): UP,
    (pygame.K_DOWN, LEFT): DOWN,
    (pygame.K_DOWN, RIGHT): DOWN,
    (pygame.K_LEFT, UP): LEFT,
    (pygame.K_LEFT, DOWN): LEFT,
    (pygame.K_RIGHT, UP): RIGHT,
    (pygame.K_RIGHT, DOWN): RIGHT,
}

BOARD_BACKGROUND_COLOR = (0, 0, 0)
BORDER_COLOR = (93, 216, 228)
APPLE_COLOR = (255, 0, 0)
SNAKE_COLOR = (0, 255, 0)
SPEED = 20
GAME_TITLE = 'Изгиб Питона'

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), 0, 32)
pygame.display.set_caption(GAME_TITLE)
clock = pygame.time.Clock()


class GameObject:
    """Базовый игровой объект с позицией и цветом."""

    def __init__(self, body_color=None):
        """Разместить объект в центре поля и сохранить его цвет."""
        self.position = CENTER_POSITION
        self.body_color = body_color

    def draw(self):
        """Определить интерфейс отрисовки для дочерних классов."""
        pass

    def draw_cell(self, position, color, border=True):
        """Нарисовать одну клетку с необязательной рамкой."""
        rect = pygame.Rect(position, (GRID_SIZE, GRID_SIZE))
        pygame.draw.rect(screen, color, rect)
        if border:
            pygame.draw.rect(screen, BORDER_COLOR, rect, 1)


class Apple(GameObject):
    """Яблоко, появляющееся только в свободных клетках."""

    def __init__(self, occupied_positions=()):
        """Выбрать начальную позицию вне переданных занятых клеток."""
        super().__init__(APPLE_COLOR)
        self.randomize_position(occupied_positions)

    def randomize_position(self, occupied_positions=()):
        """Выбрать свободную клетку или скрыть яблоко на полном поле."""
        free_cells = ALL_CELLS.difference(occupied_positions)
        self.position = choice(tuple(free_cells)) if free_cells else None

    def draw(self):
        """Нарисовать яблоко, если для него нашлось место."""
        if self.position is not None:
            self.draw_cell(self.position, self.body_color)


class Snake(GameObject):
    """Змейка, хранящая координаты сегментов от головы до хвоста."""

    def __init__(self):
        """Создать змейку из одного сегмента, движущуюся вправо."""
        super().__init__(SNAKE_COLOR)
        self.reset(RIGHT)

    def update_direction(self):
        """Применить отложенный поворот без возможности разворота."""
        if self.next_direction in DIRECTIONS:
            opposite = (-self.direction[0], -self.direction[1])
            if self.next_direction != opposite:
                self.direction = self.next_direction
        self.next_direction = None

    def move(self):
        """Переместить голову на клетку и запомнить удалённый хвост."""
        x, y = self.get_head_position()
        dx, dy = self.direction
        self.position = (
            (x + dx * GRID_SIZE) % SCREEN_WIDTH,
            (y + dy * GRID_SIZE) % SCREEN_HEIGHT,
        )
        self.positions.insert(0, self.position)
        self.last = (
            self.positions.pop() if len(self.positions) > self.length else None
        )

    def grow(self):
        """Увеличить длину, сохранив хвост уже на шаге поедания яблока."""
        self.length += 1
        if self.last is not None:
            self.positions.append(self.last)
            self.last = None

    def draw(self):
        """Стереть покинутую клетку и нарисовать новую голову."""
        if self.last is not None and self.last not in self.positions:
            self.draw_cell(self.last, BOARD_BACKGROUND_COLOR, border=False)
        self.draw_cell(self.get_head_position(), self.body_color)

    def get_head_position(self):
        """Вернуть координаты головы змейки."""
        return self.positions[0]

    def reset(self, direction=None):
        """Вернуть змейку в центр и по умолчанию выбрать случайный курс."""
        self.position = CENTER_POSITION
        self.length = 1
        self.positions = [self.position]
        self.direction = choice(DIRECTIONS) if direction is None else direction
        self.next_direction = None
        self.last = None


def handle_keys(game_object):
    """Обработать стрелки, закрытие окна и выход по клавише Escape."""
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            raise SystemExit
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                raise SystemExit
            # Все события кадра сравниваются с текущим, а не будущим курсом.
            # Поэтому быстрые нажатия не позволяют развернуться в своё тело.
            game_object.next_direction = TURNS.get(
                (event.key, game_object.direction), game_object.next_direction
            )


def main():
    """Запустить игру и освобождать ресурсы Pygame при выходе."""
    pygame.init()
    snake = Snake()
    apple = Apple(snake.positions)
    best_length = snake.length
    screen.fill(BOARD_BACKGROUND_COLOR)
    snake.draw()
    apple.draw()
    pygame.display.update()

    try:
        while True:
            clock.tick(SPEED)
            handle_keys(snake)
            snake.update_direction()
            snake.move()

            if snake.get_head_position() == apple.position:
                snake.grow()
                best_length = max(best_length, snake.length)
                apple.randomize_position(snake.positions)

            if (snake.get_head_position() in snake.positions[1:]
                    or apple.position is None):
                snake.reset()
                apple.randomize_position(snake.positions)
                screen.fill(BOARD_BACKGROUND_COLOR)

            snake.draw()
            apple.draw()
            pygame.display.set_caption(
                f'{GAME_TITLE} | Длина: {snake.length} | Рекорд: {best_length}'
            )
            pygame.display.update()
    finally:
        pygame.quit()


if __name__ == '__main__':
    main()
