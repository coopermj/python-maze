import argparse
import colorama
import os
import random
from collections import deque
from PIL import Image, ImageDraw, ImageFont
from anytree import Node, walker
import sys


debug = True


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {value}")
    return number


DEFAULT_TWIST = 0.9


def twist_value(value):
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"must be a number from 0 to 1, got {value}")
    if not 0 <= number <= 1:
        raise argparse.ArgumentTypeError(f"must be from 0 to 1, got {value}")
    return number


class LineMaze:
    def __init__(self, h, w, optimize=False, twist=DEFAULT_TWIST):
        """Build an h by w maze.

        twist (0 to 1) is how often carving continues from the newest cell: higher values give
        longer dead ends and a solution that winds back and forth, lower values a bushier maze.
        """
        if h < 1 or w < 1:
            raise ValueError(f"maze must be at least 1x1, got {h}x{w}")
        if not 0 <= twist <= 1:
            raise ValueError(f"twist must be from 0 to 1, got {twist}")
        self.maze_w = w
        self.maze_h = h
        self.undefined_wall = 'u'
        self.unevaluated_cell = 'U'
        self.current_cell = 'C'
        self.neighbor_cell = 'N'
        self.cell = ' '
        self.filled_wall = 'E'
        self.open_wall = ','
        self.solved_path = 'O'
        self.m = None
        self.twist = twist
        self.entrance = None
        self.exit = None
        try:
            self.build()
            self.define_maze(self.maze_h, self.maze_w)
            if optimize:
                self.finish(self.maze_w, make_openings=False)
                self.length = self.optimize()
            else:
                self.finish(self.maze_w)
                self.length = self.solve()
        except Exception as e:
            self.print()
            pass
            raise e
        # Image Stuff
        self.image = None
        self.cell_size = 20
        self.wall_size = 3
        self.margin = 70
        self.start_color = (0, 150, 0)
        self.end_color = (200, 0, 0)

    @staticmethod
    def coord_name(coord):
        return f"{str(coord[0])},{str(coord[1])}"

    @staticmethod
    def get_rand_cell_coord(s: int):
        r = 0
        while LineMaze.is_even(r):
            r = random.randint(0, s*2)
        return r

    @staticmethod
    def is_even(x: int):
        return x % 2 == 0

    @staticmethod
    def is_odd(x: int):
        return not LineMaze.is_even(x)

    @staticmethod
    def distance_between(cell_1, cell_2):
        pass

    def get_contents(self, y: int, x: int):
        return self.m[y][x]

    def set_contents(self, y: int, x: int, c):
        self.m[y][x] = c

    def set_contents_obj(self, coords, content=None):
        if not content:
            self.set_contents(coords[0], coords[1], coords[2])
        else:
            self.set_contents(coords[0], coords[1], content)

    def get_adj_cells(self, y, x, include_borders=False):
        return_list = list()
        if LineMaze.is_odd(x) and LineMaze.is_odd(y):
            # North == Y - 2, assuming y > 2
            if y > 2:
                try:
                    return_list.append((y-2, x, self.get_contents(y-2, x)))
                except IndexError:
                    print("Something went wrong")
            # Top row? Check the border:
            if y == 1:
                try:
                    return_list.append((y-1, x, self.get_contents(y-1, x)))
                except IndexError:
                    print("Something went wrong")
            # South == Y + 2, assuming y < (len(m)-1)
            if y < (len(self.m)-2):
                try:
                    return_list.append((y+2, x, self.get_contents(y+2, x)))
                except IndexError:
                    print("Something went wrong")
            # Bottom row? Check the border:
            if y == (len(self.m)-2):
                try:
                    return_list.append((y+1, x, self.get_contents(y+1, x)))
                except IndexError:
                    print("Something went wrong")
            # West == X -2 , assuming x > 2
            if x > 2:
                try:
                    return_list.append((y, x-2, self.get_contents(y, x-2)))
                except IndexError:
                    print("Something went wrong")
            # East == X + 2, assuming x < (len(m[0]-1)
            if x < (len(self.m[0])-2):
                try:
                    return_list.append((y, x+2, self.get_contents(y, x+2)))
                except IndexError:
                    print("Something went wrong")
        else:
            # we are in the entrance or exit
            if include_borders:
                # Bottom -- one up
                if y == (len(self.m)-1):
                    try:
                        return_list.append((y-1, x, self.get_contents(y-1, x)))
                    except IndexError:
                        print("Something went wrong")
                # Top -- one up
                if y == 0:
                    try:
                        return_list.append((y+1, x, self.get_contents(y+1, x)))
                    except IndexError:
                        print("Something went wrong")
        return return_list

    def get_adj_cells_equal(self, y, x, c, include_borders=False):
        cell_list = self.get_adj_cells(y, x, include_borders)
        return_list = list()
        for i in cell_list:
            if i[2] == c:
                return_list.append(i)
        return return_list

    def build(self):
        self.m = list()
        for i in range(0, self.maze_h*2+1):
            self.m.append(list())
            for j in range(0, self.maze_w*2+1):
                if LineMaze.is_even(j) and LineMaze.is_even(i):
                    self.m[i].append(self.filled_wall)
                elif LineMaze.is_even(j) or LineMaze.is_even(i):
                    self.m[i].append(self.undefined_wall)
                else:
                    self.m[i].append(self.unevaluated_cell)

    def open_interposing_wall(self, cell_1, cell_2):
        if LineMaze.is_even(cell_1[0]) or LineMaze.is_even(cell_1[1]) \
                or LineMaze.is_even(cell_2[0]) or LineMaze.is_even(cell_2[1]):
            raise RuntimeError("Trying to do stuff that's not cells")
        # Cell 2 is North of Cell 1 X's equal, Cell 2's y == Cell 1' Y - 2
        # wall coords = Cell 1 X, Cell 1 Y - 1
        if cell_1[1] == cell_2[1] and cell_1[0]-2 == cell_2[0]:
            self.set_contents(cell_1[0]-1, cell_1[1], self.open_wall)
            return
        # Cell 2 is South of Cell 1 X's equal, Cell 2's y == Cell 1' Y + 2
        # wall coords = Cell 1 X, Cell 1 Y + 1
        if cell_1[1] == cell_2[1] and cell_1[0]+2 == cell_2[0]:
            self.set_contents(cell_1[0]+1, cell_1[1], self.open_wall)
            return
        # Cell 2 is West of Cell 1 Y's equal, Cell 2's X == Cell 1' X - 2
        # wall coords = Cell 1 X-1, Cell 1 Y
        if cell_1[0] == cell_2[0] and cell_1[1]-2 == cell_2[1]:
            self.set_contents(cell_1[0], cell_1[1]-1, self.open_wall)
            return
        # Cell 2 is East of Cell 1 Y's equal, Cell 2's X == Cell 1' X + 2
        # wall coords = Cell 1 X+1, Cell 1 Y
        if cell_1[0] == cell_2[0] and cell_1[1]+2 == cell_2[1]:
            self.set_contents(cell_1[0], cell_1[1]+1, self.open_wall)
            return
        raise RuntimeError("Somehow these weren't adjacent")

    def print(self):
        for i in range(0, len(self.m)):
            for j in range(0, len(self.m[0])):
                if self.m[i][j] == self.undefined_wall:
                    print(colorama.Back.WHITE, f'{self.m[i][j]}', end="")
                if self.m[i][j] == self.unevaluated_cell:
                    print(colorama.Back.LIGHTWHITE_EX, f'{self.m[i][j]}', end="")
                if self.m[i][j] == self.cell:
                    print(colorama.Back.GREEN, f'{self.m[i][j]}', end="")
                if self.m[i][j] == self.filled_wall:
                    print(colorama.Back.BLACK, f'{self.m[i][j]}', end="")
                if self.m[i][j] == self.open_wall:
                    print(colorama.Back.LIGHTGREEN_EX, f'{self.m[i][j]}', end="")
                if self.m[i][j] == self.current_cell:
                    print(colorama.Back.RED, f'{self.m[i][j]}', end="")
                if self.m[i][j] == self.neighbor_cell:
                    print(colorama.Back.LIGHTBLUE_EX, f'{self.m[i][j]}', end="")
                if self.m[i][j] == self.solved_path:
                    print(colorama.Back.BLUE, f'{self.m[i][j]}', end="")
            print('\n', end="")

    def define_maze(self, h, w):
        # Growing tree: keep a list of cells still being carved. Carve onward from the newest one
        # with probability `twist` (long winding corridors), otherwise branch from a random one.
        start = (LineMaze.get_rand_cell_coord(h), LineMaze.get_rand_cell_coord(w))
        self.set_contents(start[0], start[1], self.cell)
        active = [start]
        while active:
            i = len(active) - 1 if random.random() < self.twist else random.randrange(len(active))
            here = active[i]
            options = self.get_adj_cells_equal(here[0], here[1], self.unevaluated_cell)
            if not options:
                active.pop(i)
                continue
            there = random.choice(options)
            self.set_contents(there[0], there[1], self.cell)
            self.open_interposing_wall(here, there)
            active.append((there[0], there[1]))

    def finish(self, w, make_openings=True):
        for i in range(0, len(self.m)):
            for j in range(0, len(self.m[0])):
                if self.m[i][j] == self.undefined_wall:
                    self.m[i][j] = self.filled_wall
        if make_openings:
            # Entrance
            top_x = self.get_rand_cell_coord(w)
            self.set_contents(0, top_x, self.cell)
            self.entrance = (0, top_x)
            # Exit
            bottom_x = self.get_rand_cell_coord(w)
            self.set_contents(len(self.m)-1, bottom_x, self.cell)
            self.exit = (len(self.m)-1, bottom_x)

    def find_entrance(self):
        entrance_x = None
        for i in range(0, len(self.m[0])-1):
            if self.m[0][i] == self.cell:
                entrance_x = i
        return 0, entrance_x

    def find_exit(self):
        bottom = len(self.m)-1
        exit_x = None
        for i in range(0, len(self.m[0])-1):
            if self.m[bottom][i] == self.cell:
                exit_x = i
        return bottom, exit_x

    def solve(self):
        en = self.find_entrance()
        root = Node(LineMaze.coord_name(en), coord=en)
        ex = self.find_exit()
        exit_node = self.walk_recurse(root, ex)
        if not exit_node:
            pass
        return self.write_solved_path(root, exit_node)

    def write_solved_path(self, root, exit_node):
        w = walker.Walker()
        path = w.walk(root, exit_node)
        count = 0
        for i in path[0]:
            self.set_contents_obj(i.coord, self.solved_path)
            count += 1
        if path[1]:
            self.set_contents_obj(path[1].coord, self.solved_path)
            count += 1
        for j in path[2]:
            self.set_contents_obj(j.coord, self.solved_path)
            count += 1
        return count

    def passages(self, cell):
        """The cells reachable in one step from `cell` through open walls."""
        y, x = cell
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + 2 * dy, x + 2 * dx
            if 0 < ny < len(self.m) and 0 < nx < len(self.m[0]) and self.get_contents(y + dy, x + dx) == self.open_wall:
                yield ny, nx

    def paths_from(self, start):
        """Breadth-first walk from `start`: each reachable cell's distance and the cell it was reached from."""
        distance = {start: 0}
        came_from = {start: None}
        queue = deque([start])
        while queue:
            cell = queue.popleft()
            for n in self.passages(cell):
                if n not in distance:
                    distance[n] = distance[cell] + 1
                    came_from[n] = cell
                    queue.append(n)
        return distance, came_from

    def optimize(self):
        # Pick the top-row entrance and edge exit that are farthest apart through the maze
        best = None
        for x in range(1, len(self.m[0]), 2):
            distance, came_from = self.paths_from((1, x))
            far = max((c for c in distance if self.is_on_edge(c)), key=distance.get)
            if best is None or distance[far] > best[0]:
                best = (distance[far], (1, x), far, came_from)
        _, top, far, came_from = best
        self.entrance = (0, top[1])
        self.set_contents(0, top[1], self.solved_path)
        count = 1
        cell = far
        while cell:
            self.set_contents(cell[0], cell[1], self.solved_path)
            count += 1
            cell = came_from[cell]
        self.open_exit(far)
        return count

    def open_exit(self, coord):
        # Open the first border wall next to this edge cell that isn't already open,
        # so a cell that is also the entrance gets a separate exit.
        candidates = list()
        if coord[0] == 1:
            candidates.append((coord[0]-1, coord[1]))
        if coord[0] == len(self.m)-2:
            candidates.append((coord[0]+1, coord[1]))
        if coord[1] == 1:
            candidates.append((coord[0], coord[1]-1))
        if coord[1] == len(self.m[0])-2:
            candidates.append((coord[0], coord[1]+1))
        for wall in candidates:
            if self.get_contents(wall[0], wall[1]) == self.filled_wall:
                self.set_contents(wall[0], wall[1], self.solved_path)
                self.exit = wall
                return
        raise RuntimeError(f"Bad Exit selected: {LineMaze.coord_name(coord)}")

    def walk_recurse(self, here: Node, maze_exit: tuple):
        for i in self.get_adj_cells_equal(here.coord[0], here.coord[1], self.cell, True):
            if here.parent and LineMaze.coord_name(i) == LineMaze.coord_name(here.parent.coord):
                continue
            if not self.cells_connected(i, here.coord):
                continue
            new_node = Node(LineMaze.coord_name(i), coord=i, parent=here)
            pass
            if LineMaze.coord_name(i) == LineMaze.coord_name(maze_exit):
                return new_node
            else:
                result = self.walk_recurse(new_node, maze_exit)
                if result:
                    return result

    def is_on_edge(self, coord):
        return coord[0] == 1 or coord[1] == 1 or coord[0] == len(self.m)-2 or coord[1] == len(self.m[0])-2

    def cells_connected(self, cell_1, cell_2):
        # Handle the borders -- cells are directly adjacent
        if abs(cell_1[0] - cell_2[0]) == 1 or abs(cell_1[1] - cell_2[1]) == 1:
            return True
        if LineMaze.is_even(cell_1[0]) or LineMaze.is_even(cell_1[1]) or \
                LineMaze.is_even(cell_2[0]) or LineMaze.is_even(cell_2[1]):
            raise RuntimeError("Trying to do stuff that's not cells or borders")
        # Cell 2 is North of Cell 1 -- X's equal, Cell 2's y == Cell 1' Y - 2
        # wall coords = Cell 1 X, Cell 1 Y - 1
        if cell_1[1] == cell_2[1] and cell_1[0]-2 == cell_2[0]:
            return self.get_contents(cell_1[0]-1, cell_1[1]) == self.open_wall
        # Cell 2 is South of Cell 1 X's equal, Cell 2's y == Cell 1' Y + 2
        # wall coords = Cell 1 X, Cell 1 Y + 1
        if cell_1[1] == cell_2[1] and cell_1[0]+2 == cell_2[0]:
            return self.get_contents(cell_1[0]+1, cell_1[1]) == self.open_wall
        # Cell 2 is West of Cell 1 Y's equal, Cell 2's X == Cell 1' X - 2
        # wall coords = Cell 1 X-1, Cell 1 Y
        if cell_1[0] == cell_2[0] and cell_1[1]-2 == cell_2[1]:
            return self.get_contents(cell_1[0], cell_1[1]-1) == self.open_wall
        # Cell 2 is East of Cell 1 Y's equal, Cell 2's X == Cell 1' X + 2
        # wall coords = Cell 1 X+1, Cell 1 Y
        if cell_1[0] == cell_2[0] and cell_1[1]+2 == cell_2[1]:
            return self.get_contents(cell_1[0], cell_1[1]+1) == self.open_wall
        raise RuntimeError("Somehow these weren't adjacent")

    def set_up_image(self):
        height = (self.maze_h * (self.cell_size + self.wall_size)) + self.wall_size + 1
        width = (self.maze_w * (self.cell_size + self.wall_size)) + self.wall_size + 1
        self.image = Image.new(mode='RGB', size=(width + 2 * self.margin, height + 2 * self.margin), color='white')
        # The maze itself is drawn as white passages on a black background
        drawing = ImageDraw.Draw(self.image)
        drawing.rectangle([(self.margin, self.margin), (self.margin + width - 1, self.margin + height - 1)], fill='black')

    def show_image(self):
        self.image.show()

    def draw(self, solved=False, show=True):
        self.set_up_image()
        y_index = self.margin
        for i in range(0, len(self.m)):
            x_index = self.margin
            for j in range(0, len(self.m[0])):
                cell_contents = self.get_contents(i, j)
                write = False
                is_point = None
                is_vert = None
                is_horiz = None
                color = 'white'
                x_end = None
                y_end = None
                # Always XY
                start = (x_index, y_index)
                is_wall = LineMaze.is_even(i) or LineMaze.is_even(j)
                if is_wall:
                    if cell_contents == self.open_wall or cell_contents == self.cell or \
                            cell_contents == self.solved_path:
                        write = True
                    is_point = LineMaze.is_even(i) and LineMaze.is_even(j)
                    is_vert = LineMaze.is_odd(i)
                    is_horiz = LineMaze.is_odd(j)
                    if is_point:
                        x_end = x_index + self.wall_size
                        y_end = y_index + self.wall_size
                    elif is_vert:
                        x_end = x_index + self.wall_size
                        y_end = y_index + self.cell_size
                    elif is_horiz:
                        x_end = x_index + self.cell_size
                        y_end = y_index + self.wall_size
                    else:
                        print("This should not be possible")
                        pass
                else:
                    write = True
                    x_end = x_index + self.cell_size
                    y_end = y_index + self.cell_size
                end = (x_end, y_end)
                if write:
                    if cell_contents == self.solved_path and solved:
                        color = 'red'
                    drawing = ImageDraw.Draw(self.image)
                    drawing.rectangle([start, end], fill=color, outline=color)
                    del drawing
                # Update indices
                x_index = x_end
            y_index = y_end
        self.draw_markers()
        if show:
            self.show_image()

    def grid_to_px(self, k):
        # Pixel offset of grid row/column k: walls are wall_size wide, cells are cell_size wide
        return self.margin + (k // 2) * (self.cell_size + self.wall_size) + (self.wall_size if LineMaze.is_odd(k) else 0)

    def opening_geometry(self, coord):
        """For a border opening, return its center point on the outer wall edge and the outward direction."""
        y, x = coord
        center_y = self.grid_to_px(y) + self.cell_size // 2
        center_x = self.grid_to_px(x) + self.cell_size // 2
        if y == 0:
            return (center_x, self.margin), (0, -1)
        if y == len(self.m) - 1:
            return (center_x, self.grid_to_px(y) + self.wall_size), (0, 1)
        if x == 0:
            return (self.margin, center_y), (-1, 0)
        return (self.grid_to_px(x) + self.wall_size, center_y), (1, 0)

    @staticmethod
    def marker_font():
        try:
            return ImageFont.load_default(size=18)
        except TypeError:
            # Pillow < 10.1 only has the small fixed-size bitmap font
            return ImageFont.load_default()

    def draw_markers(self):
        drawing = ImageDraw.Draw(self.image)
        font = LineMaze.marker_font()
        placed = list()
        for coord, text, color, pointing_in in ((self.entrance, "START", self.start_color, True),
                                                (self.exit, "END", self.end_color, False)):
            if coord is None:
                continue
            (ex, ey), (dx, dy) = self.opening_geometry(coord)
            # Arrow shaft runs from 4px to 40px outside the wall
            near = (ex + dx * 4, ey + dy * 4)
            far = (ex + dx * 40, ey + dy * 40)
            drawing.line([near, far], fill=color, width=4)
            tip, base = (near, (ex + dx * 16, ey + dy * 16)) if pointing_in else \
                (far, (ex + dx * 28, ey + dy * 28))
            # Arrowhead: a triangle with its point at `tip`
            px, py = -dy * 8, dx * 8
            drawing.polygon([tip, (base[0] + px, base[1] + py), (base[0] - px, base[1] - py)], fill=color)
            left, top, right, bottom = drawing.textbbox((0, 0), text, font=font)
            tw, th = right - left, bottom - top
            if dy:
                # Top or bottom: label past the end of the arrow
                lx = ex - tw // 2
                ly = ey - 48 - th if dy < 0 else ey + 46
            else:
                # Left or right side: label above the arrow
                lx = ex + dx * 22 - tw // 2
                ly = ey - 14 - th
            for other in placed:
                # Nudge apart from a label already placed on the same line
                if abs(ly - other[1]) < th + 4 and lx < other[0] + other[2] + 6 and other[0] < lx + tw + 6:
                    lx = other[0] + other[2] + 6 if lx >= other[0] else other[0] - tw - 6
            lx = max(2, min(lx, self.image.width - tw - 2))
            ly = max(2, min(ly, self.image.height - th - 2))
            drawing.text((lx - left, ly - top), text, fill=color, font=font)
            placed.append((lx, ly, tw))

    def save_image(self, path, solved=False):
        self.draw(solved=solved, show=False)
        self.image.save(path)


def solution_path(output):
    root, ext = os.path.splitext(output)
    return f"{root}_solution{ext or '.png'}"


def output_maze(maze, output=None):
    if output:
        maze.save_image(output, solved=False)
        maze.save_image(solution_path(output), solved=True)
        print(f"saved {output} and {solution_path(output)}")
    else:
        maze.draw(solved=True)
        maze.draw(solved=False)


def main(argv=None):
    sys.setrecursionlimit(10**6)
    a = argparse.ArgumentParser()
    a.add_argument('-H', '--height', default=50, type=positive_int, help='how high to make the maze')
    a.add_argument('-W', '--width', default=50, type=positive_int, help='how wide to make the maze')
    a.add_argument('-S', '--smart', action="store_true", help='optimize the maze by being smart')
    a.add_argument('-I', '--iterations', default=5, type=positive_int, help='how many times to try')
    a.add_argument('-t', '--twist', default=DEFAULT_TWIST, type=twist_value,
                   help=f'0 to 1: higher makes longer dead ends and a more winding solution (default {DEFAULT_TWIST})')
    a.add_argument('-o', '--output', help='save the maze to this PNG (and the solution next to it) instead of showing it')
    args = a.parse_args(argv)
    best_maze = None
    best_length = 0
    for maze in range(0, args.iterations):
        m = LineMaze(args.height, args.width, optimize=args.smart, twist=args.twist)
        length = m.length
        if not best_maze or length > best_length:
            best_maze = m
            best_length = length
            print(f"\nnew best: {length}")
        else:
            print('.', end='')
    print("\n")
    output_maze(best_maze, args.output)
    print(f"done: best quality {best_maze.length}")
    return best_maze


if __name__ == '__main__':
    main()
