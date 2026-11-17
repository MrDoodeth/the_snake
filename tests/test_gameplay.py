"""Проверки правил игры, управления и инкрементальной отрисовки."""

from types import SimpleNamespace
from unittest.mock import Mock

import pygame
import pytest

from conftest import StopInfiniteLoop


@pytest.fixture
def game(_the_snake, monkeypatch):
    """Подготовить поверхность даже после завершения другого игрового цикла."""
    pygame.init()
    monkeypatch.setattr(
        _the_snake, 'screen',
        pygame.display.set_mode(
            (_the_snake.SCREEN_WIDTH, _the_snake.SCREEN_HEIGHT)
        ),
    )
    pygame.event.clear()
    return _the_snake


def test_initial_state(game):
    """Новая змейка состоит из головы в центре и движется вправо."""
    snake = game.Snake()
    assert snake.positions == [game.CENTER_POSITION]
    assert snake.position == snake.get_head_position()
    assert snake.length == 1
    assert snake.direction == game.RIGHT
    assert snake.next_direction is None
    assert snake.last is None


@pytest.mark.parametrize('start, direction, expected', [
    ((0, 0), (0, -1), (0, 460)),
    ((0, 460), (0, 1), (0, 0)),
    ((0, 0), (-1, 0), (620, 0)),
    ((620, 0), (1, 0), (0, 0)),
])
def test_movement_and_wrapping(game, start, direction, expected):
    """Каждый шаг равен клетке, включая переход через все четыре границы."""
    snake = game.Snake()
    snake.positions = [start]
    snake.direction = direction
    snake.move()
    assert snake.positions == [expected]
    assert snake.position == expected
    assert snake.last == start


def test_move_retains_length_and_records_tail(game):
    """При обычном движении удаляется только последний сегмент."""
    snake = game.Snake()
    snake.positions = [(40, 0), (20, 0), (0, 0)]
    snake.length = 3
    snake.move()
    assert snake.positions == [(60, 0), (40, 0), (20, 0)]
    assert snake.last == (0, 0)


def test_growth_is_immediate_and_does_not_erase_tail(game):
    """Рост сохраняет прежний хвост уже в кадре поедания яблока."""
    snake = game.Snake()
    old_head = snake.get_head_position()
    snake.move()
    snake.grow()
    assert snake.length == len(snake.positions) == 2
    assert snake.positions[-1] == old_head
    assert snake.last is None
    snake.move()
    assert len(snake.positions) == 2


def test_move_supports_pending_growth(game):
    """Увеличение длины перед движением также оставляет хвост на месте."""
    snake = game.Snake()
    snake.length += 1
    snake.move()
    assert len(snake.positions) == 2
    assert snake.last is None


def test_base_draw_does_not_render(game, monkeypatch):
    """Базовый объект не знает свою фигуру и ничего не рисует."""
    draw_mock = Mock()
    monkeypatch.setattr(pygame.draw, 'rect', draw_mock)
    game.GameObject().draw()
    draw_mock.assert_not_called()


def test_update_direction_rejects_direct_reverse(game):
    """Метод обновления тоже защищает от противоположного направления."""
    snake = game.Snake()
    snake.next_direction = game.LEFT
    snake.update_direction()
    assert snake.direction == game.RIGHT
    assert snake.next_direction is None


def test_reset_clears_round_state(game):
    """Сброс убирает тело, отложенный поворот и старый след."""
    snake = game.Snake()
    snake.move()
    snake.grow()
    snake.next_direction = game.UP
    snake.reset()
    assert snake.positions == [game.CENTER_POSITION]
    assert snake.position == game.CENTER_POSITION
    assert snake.length == 1
    assert snake.direction in game.DIRECTIONS
    assert snake.next_direction is None
    assert snake.last is None


def test_apple_uses_only_free_cells(game):
    """Единственная свободная клетка выбирается и при создании, и позднее."""
    free_cell = (0, 0)
    occupied = game.ALL_CELLS - {free_cell}
    apple = game.Apple(occupied)
    assert apple.position == free_cell
    apple.randomize_position(game.ALL_CELLS - {(20, 20)})
    assert apple.position == (20, 20)


def test_apple_stays_on_grid(game):
    """Повторные размещения яблока не выходят за поле и не занимают змейку."""
    snake = game.Snake()
    apple = game.Apple(snake.positions)
    for _ in range(100):
        assert apple.position in game.ALL_CELLS
        assert apple.position not in snake.positions
        apple.randomize_position(snake.positions)


def test_full_board_hides_apple(game):
    """На заполненном поле нет случайного выбора из пустой коллекции."""
    apple = game.Apple(game.ALL_CELLS)
    assert apple.position is None
    apple.draw()


@pytest.mark.parametrize('key, direction, expected', [
    (pygame.K_UP, (1, 0), (0, -1)),
    (pygame.K_DOWN, (1, 0), (0, 1)),
    (pygame.K_LEFT, (0, -1), (-1, 0)),
    (pygame.K_RIGHT, (0, -1), (1, 0)),
    (pygame.K_LEFT, (1, 0), (1, 0)),
    (pygame.K_RIGHT, (-1, 0), (-1, 0)),
    (pygame.K_UP, (0, 1), (0, 1)),
    (pygame.K_DOWN, (0, -1), (0, -1)),
    (pygame.K_a, (1, 0), (1, 0)),
])
def test_keyboard_turns(game, key, direction, expected):
    """Стрелки поворачивают змейку, но не разворачивают её назад."""
    snake = game.Snake()
    snake.direction = direction
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
    game.handle_keys(snake)
    snake.update_direction()
    assert snake.direction == expected
    assert snake.next_direction is None


def test_multiple_keys_cannot_reverse_within_frame(game):
    """Быстрые нажатия вверх-влево не разворачивают движение вправо."""
    snake = game.Snake()
    for key in (pygame.K_UP, pygame.K_LEFT):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
    game.handle_keys(snake)
    snake.update_direction()
    assert snake.direction == game.UP


@pytest.mark.parametrize('event', [
    pygame.event.Event(pygame.QUIT),
    pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE),
])
def test_exit_events(game, event):
    """Закрытие окна и Escape завершают обработку событий."""
    pygame.event.post(event)
    with pytest.raises(SystemExit):
        game.handle_keys(game.Snake())


def test_draw_erases_tail_and_preserves_head(game):
    """После шага старая клетка чёрная, а новая голова зелёная."""
    snake = game.Snake()
    game.screen.fill(game.BOARD_BACKGROUND_COLOR)
    snake.draw()
    old_head = snake.get_head_position()
    snake.move()
    snake.draw()
    for position, color in (
        (old_head, game.BOARD_BACKGROUND_COLOR),
        (snake.get_head_position(), game.SNAKE_COLOR),
    ):
        pixel = (position[0] + 2, position[1] + 2)
        assert game.screen.get_at(pixel)[:3] == color


@pytest.fixture
def run_frame(game, monkeypatch):
    """Выполнить ровно один шаг настоящего цикла с заданными объектами."""
    def run(snake, apple):
        """Остановить второй шаг и проверить освобождение ресурсов."""
        monkeypatch.setattr(game, 'Snake', lambda: snake)
        monkeypatch.setattr(game, 'Apple', lambda occupied: apple)
        monkeypatch.setattr(game, 'handle_keys', lambda snake: None)
        monkeypatch.setattr(game, 'clock', SimpleNamespace(
            tick=Mock(side_effect=[None, StopInfiniteLoop])
        ))
        quit_mock = Mock()
        monkeypatch.setattr(pygame, 'quit', quit_mock)
        with pytest.raises(StopInfiniteLoop):
            game.main()
        quit_mock.assert_called_once_with()
    return run


def test_main_eats_apple(game, run_frame):
    """Цикл увеличивает змейку и переносит съеденное яблоко вне тела."""
    snake = game.Snake()
    apple = game.Apple(snake.positions)
    apple.position = (game.CENTER_POSITION[0] + game.GRID_SIZE,
                      game.CENTER_POSITION[1])
    run_frame(snake, apple)
    assert snake.length == len(snake.positions) == 2
    assert apple.position not in snake.positions
    assert 'Рекорд: 2' in pygame.display.get_caption()[0]


def test_main_resets_self_collision(game, run_frame):
    """Самоукус сбрасывает тело и удаляет его след с экрана."""
    snake = game.Snake()
    snake.positions = [(20, 20), (20, 40), (40, 40), (40, 20), (60, 20)]
    snake.length = len(snake.positions)
    apple = game.Apple(snake.positions)
    apple.position = (0, 0)
    run_frame(snake, apple)
    assert snake.positions == [game.CENTER_POSITION]
    assert snake.length == 1
    assert apple.position not in snake.positions
    assert game.screen.get_at((42, 22))[:3] == game.BOARD_BACKGROUND_COLOR


def test_main_allows_moving_into_vacated_tail(game, run_frame):
    """Клетка уходящего хвоста свободна и не вызывает ложный самоукус."""
    snake = game.Snake()
    snake.positions = [(20, 20), (20, 40), (40, 40), (40, 20)]
    snake.length = len(snake.positions)
    apple = game.Apple(snake.positions)
    apple.position = (0, 0)
    run_frame(snake, apple)
    assert snake.length == 4
    assert snake.get_head_position() == (40, 20)
    assert game.screen.get_at((42, 22))[:3] == game.SNAKE_COLOR


def test_main_restarts_completed_board(game, run_frame):
    """Заполнение поля начинает новый раунд, сохраняя рекорд."""
    snake = game.Snake()
    head = game.CENTER_POSITION
    target = (head[0] + game.GRID_SIZE, head[1])
    snake.positions = [head] + sorted(game.ALL_CELLS - {head, target})
    snake.length = len(snake.positions)
    apple = game.Apple(snake.positions)
    run_frame(snake, apple)
    assert snake.length == 1
    assert apple.position in game.ALL_CELLS - set(snake.positions)
    assert f'Рекорд: {len(game.ALL_CELLS)}' in pygame.display.get_caption()[0]
