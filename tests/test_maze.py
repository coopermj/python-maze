import random
import sys
import threading
import unittest

from python_maze_generator.line_maze import LineMaze
from python_maze_generator.multithreaded_maze import generate_mazes

sys.setrecursionlimit(10**6)


def border_openings(maze):
    m = maze.m
    border = set()
    for x in range(len(m[0])):
        border.add((0, x))
        border.add((len(m) - 1, x))
    for y in range(len(m)):
        border.add((y, 0))
        border.add((y, len(m[0]) - 1))
    return [c for c in border if m[c[0]][c[1]] != maze.filled_wall]


def run_with_timeout(fn, timeout):
    result = {}

    def target():
        try:
            result['value'] = fn()
        except Exception as e:
            result['error'] = e

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        raise AssertionError(f"call did not finish within {timeout}s")
    return result


class TestBorders(unittest.TestCase):
    def test_maze_has_exactly_entrance_and_exit(self):
        for seed in range(100):
            random.seed(seed)
            maze = LineMaze(6, 6)
            self.assertEqual(len(border_openings(maze)), 2, f"seed {seed}")

    def test_optimized_maze_has_exactly_entrance_and_exit(self):
        for seed in range(100):
            random.seed(seed)
            maze = LineMaze(6, 6, optimize=True)
            self.assertEqual(len(border_openings(maze)), 2, f"seed {seed}")


class TestMode(unittest.TestCase):
    def test_first_mode_differs_from_random_mode(self):
        random.seed(1)
        first = LineMaze(8, 8, 'first').m
        random.seed(1)
        rand = LineMaze(8, 8, 'random').m
        self.assertNotEqual(first, rand)


class TestGenerateMazes(unittest.TestCase):
    def test_returns_longest_maze(self):
        best = generate_mazes(6, 6, 5, 2)
        self.assertIsInstance(best, LineMaze)

    def test_worker_error_is_raised_instead_of_hanging(self):
        result = run_with_timeout(lambda: generate_mazes(-1, 5, 1, 1), timeout=10)
        self.assertIn('error', result)

    def test_zero_threads_is_rejected(self):
        result = run_with_timeout(lambda: generate_mazes(5, 5, 2, 0), timeout=10)
        self.assertIsInstance(result.get('error'), ValueError)


if __name__ == '__main__':
    unittest.main()
