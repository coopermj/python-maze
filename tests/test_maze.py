import contextlib
import io
import os
import random
import sys
import tempfile
import threading
import unittest

from PIL import Image

from python_maze_generator import line_maze, multithreaded_maze
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

    def test_small_mazes_have_exactly_entrance_and_exit(self):
        for h, w in [(1, 1), (1, 3), (3, 1), (2, 2), (2, 5)]:
            for optimize in (False, True):
                for seed in range(20):
                    random.seed(seed)
                    maze = LineMaze(h, w, optimize=optimize)
                    self.assertEqual(len(border_openings(maze)), 2, f"{h}x{w} optimize={optimize} seed {seed}")

    def test_non_positive_size_is_rejected(self):
        for h, w in [(0, 5), (5, 0), (-1, 5)]:
            with self.assertRaises(ValueError):
                LineMaze(h, w)


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


def quiet(fn, *args):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*args)


class TestCli(unittest.TestCase):
    def assert_saves_maze_and_solution(self, main, extra_args):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'maze.png')
            quiet(main, ['-H', '4', '-W', '6', '-I', '2', '-o', out] + extra_args)
            for path in (out, os.path.join(d, 'maze_solution.png')):
                with Image.open(path) as img:
                    self.assertEqual(img.size, (6 * 23 + 4, 4 * 23 + 4))

    def test_line_maze_saves_maze_and_solution(self):
        self.assert_saves_maze_and_solution(line_maze.main, ['-S'])

    def test_multithreaded_maze_saves_maze_and_solution(self):
        self.assert_saves_maze_and_solution(multithreaded_maze.main, ['-T', '2'])

    def test_rejects_non_positive_arguments(self):
        for main in (line_maze.main, multithreaded_maze.main):
            for flag in ('-H', '-W', '-I'):
                with self.assertRaises(SystemExit):
                    quiet(main, [flag, '0'])
        with self.assertRaises(SystemExit):
            quiet(multithreaded_maze.main, ['-T', '0'])


if __name__ == '__main__':
    unittest.main()
