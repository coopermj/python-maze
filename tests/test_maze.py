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

MARGIN = 70


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


def grid_to_px(k, maze):
    return MARGIN + (k // 2) * (maze.cell_size + maze.wall_size) + (maze.wall_size if k % 2 else 0)


def pixel_outside(maze, coord, distance):
    """The image pixel `distance` px outside the maze, centered on the border opening at grid `coord`."""
    y, x = coord
    cy = grid_to_px(y, maze) + maze.cell_size // 2
    cx = grid_to_px(x, maze) + maze.cell_size // 2
    if y == 0:
        cy = MARGIN - distance
    elif y == len(maze.m) - 1:
        cy = grid_to_px(y, maze) + maze.wall_size + distance
    elif x == 0:
        cx = MARGIN - distance
    else:
        cx = grid_to_px(x, maze) + maze.wall_size + distance
    return maze.image.getpixel((cx, cy))


class TestStartAndEnd(unittest.TestCase):
    def mazes(self):
        for optimize in (False, True):
            for seed in range(30):
                random.seed(seed)
                yield LineMaze(6, 6, optimize=optimize)

    def test_entrance_and_exit_are_the_border_openings(self):
        exit_sides = set()
        for maze in self.mazes():
            self.assertEqual(set(border_openings(maze)), {maze.entrance, maze.exit})
            self.assertEqual(maze.entrance[0], 0)
            exit_sides.add('top/bottom' if maze.exit[0] in (0, len(maze.m) - 1) else 'side')
        self.assertEqual(exit_sides, {'top/bottom', 'side'})

    def test_start_arrow_is_green_and_end_arrow_is_red(self):
        for maze in self.mazes():
            for solved in (False, True):
                maze.draw(solved=solved, show=False)
                r, g, b = pixel_outside(maze, maze.entrance, 10)
                self.assertTrue(g > 100 and r < 100 and b < 100, f"start pixel {(r, g, b)}")
                r, g, b = pixel_outside(maze, maze.exit, 10)
                self.assertTrue(r > 150 and g < 100 and b < 100, f"end pixel {(r, g, b)}")


def passages(maze, cell):
    y, x = cell
    m = maze.m
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ny, nx = y + 2 * dy, x + 2 * dx
        if 0 < ny < len(m) and 0 < nx < len(m[0]) and m[y + dy][x + dx] != maze.filled_wall:
            yield ny, nx


def distances(maze, start):
    d = {start: 0}
    queue = [start]
    for cell in queue:
        for n in passages(maze, cell):
            if n not in d:
                d[n] = d[cell] + 1
                queue.append(n)
    return d


def inner_cell(maze, border):
    """The maze cell just inside a border opening."""
    y, x = border
    return (1 if y == 0 else len(maze.m) - 2 if y == len(maze.m) - 1 else y,
            1 if x == 0 else len(maze.m[0]) - 2 if x == len(maze.m[0]) - 1 else x)


def edge_cells(maze):
    h, w = len(maze.m), len(maze.m[0])
    return [(y, x) for y in range(1, h, 2) for x in range(1, w, 2) if y in (1, h - 2) or x in (1, w - 2)]


def false_runs(maze):
    """For each wrong turn off the solution path, the longest walk down it before a dead end."""
    on_path = lambda c: maze.m[c[0]][c[1]] == maze.solved_path
    runs = []
    for y in range(1, len(maze.m), 2):
        for x in range(1, len(maze.m[0]), 2):
            if not on_path((y, x)):
                continue
            for branch in passages(maze, (y, x)):
                if on_path(branch):
                    continue
                longest, stack = 0, [(branch, (y, x), 1)]
                while stack:
                    cell, prev, depth = stack.pop()
                    longest = max(longest, depth)
                    stack += [(n, cell, depth + 1) for n in passages(maze, cell) if n != prev]
                runs.append(longest)
    return runs


def seeded_mazes(count=20, size=30, **kwargs):
    for seed in range(count):
        random.seed(seed)
        yield LineMaze(size, size, optimize=True, **kwargs)


class TestTwist(unittest.TestCase):
    def test_default_twist_makes_long_false_runs(self):
        runs = [r for maze in seeded_mazes() for r in false_runs(maze)]
        self.assertGreaterEqual(sum(runs) / len(runs), 10)

    def test_default_twist_makes_wandering_solution(self):
        lengths = [maze.length for maze in seeded_mazes()]
        self.assertGreaterEqual(sum(lengths) / len(lengths), 180)

    def test_more_twist_makes_longer_solutions(self):
        averages = [sum(m.length for m in seeded_mazes(twist=t)) / 20 for t in (0.0, 0.5, 1.0)]
        self.assertEqual(averages, sorted(averages))
        self.assertGreater(averages[2], 2 * averages[0])

    def test_twist_outside_zero_to_one_is_rejected(self):
        for twist in (-0.1, 1.1):
            with self.assertRaises(ValueError):
                LineMaze(5, 5, twist=twist)

    def test_generate_mazes_uses_twist(self):
        self.assertEqual(generate_mazes(6, 6, 2, 1, twist=0.25).twist, 0.25)


class TestSmartMode(unittest.TestCase):
    def test_entrance_and_exit_are_farthest_apart_pair(self):
        for maze in seeded_mazes(count=10, size=12):
            entrance, exit_ = inner_cell(maze, maze.entrance), inner_cell(maze, maze.exit)
            edges = edge_cells(maze)
            best = max(max(d for c, d in distances(maze, top).items() if c in edges)
                       for top in edges if top[0] == 1)
            self.assertEqual(distances(maze, entrance)[exit_], best)


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
                    self.assertEqual(img.size, (6 * 23 + 4 + 2 * MARGIN, 4 * 23 + 4 + 2 * MARGIN))

    def test_line_maze_saves_maze_and_solution(self):
        self.assert_saves_maze_and_solution(line_maze.main, ['-S'])

    def test_multithreaded_maze_saves_maze_and_solution(self):
        self.assert_saves_maze_and_solution(multithreaded_maze.main, ['-T', '2'])

    def test_line_maze_cli_makes_winding_maze(self):
        # A comb of straight corridors has horizontal passages in only one row
        with tempfile.TemporaryDirectory() as d:
            maze = quiet(line_maze.main, ['-H', '20', '-W', '20', '-I', '1', '-o', os.path.join(d, 'maze.png')])
        m = maze.m
        rows_with_side_passages = [
            i for i in range(1, len(m) - 1, 2)
            if any(m[i][j] == maze.open_wall for j in range(2, len(m[0]) - 2, 2))
        ]
        self.assertGreater(len(rows_with_side_passages), 10)

    def test_twist_flag_is_used(self):
        with tempfile.TemporaryDirectory() as d:
            maze = quiet(line_maze.main, ['-H', '5', '-W', '5', '-I', '1', '-t', '0.3', '-o', os.path.join(d, 'maze.png')])
        self.assertEqual(maze.twist, 0.3)

    def test_rejects_twist_outside_zero_to_one(self):
        for main in (line_maze.main, multithreaded_maze.main):
            for value in ('-0.5', '1.5', 'abc'):
                err = io.StringIO()
                with self.assertRaises(SystemExit), contextlib.redirect_stderr(err):
                    main(['-t', value])
                self.assertIn('argument -t/--twist', err.getvalue())

    def test_rejects_non_positive_arguments(self):
        for main in (line_maze.main, multithreaded_maze.main):
            for flag in ('-H', '-W', '-I'):
                with self.assertRaises(SystemExit):
                    quiet(main, [flag, '0'])
        with self.assertRaises(SystemExit):
            quiet(multithreaded_maze.main, ['-T', '0'])


if __name__ == '__main__':
    unittest.main()
