# python-maze

Generates a PNG maze. Thanks to [Orestis Zekai](https://medium.com/swlh/fun-with-python-1-maze-generator-931639b4fb7e) for the original algorithm.

## Install

```
pip install python_maze_generator
```

This installs two commands, `line-maze` and `multithreaded-maze`. From a checkout, you can also run them as
`python -m python_maze_generator.line_maze` and `python -m python_maze_generator.multithreaded_maze`.

## Included Maze Types


### Line maze
- Grid with separate wall segments
- Makes 2 images -- one solved, one unsolved. They open in your image viewer, or pass `-o maze.png` to save
  them as `maze.png` and `maze_solution.png`
- The start and end are marked with green START and red END arrows in a margin around the maze
- Every grid square is usable as a maze cell
- Can make more interesting maze generation by adding iterations
  - Iteration is currently very simple -- it's set to maximize the length of the solved path
- Smart Mode: picks the entrance on the top wall and the exit on any wall that are farthest apart
  through the maze, so the solution is as long as possible
- Twist (`-t`, 0 to 1, default 0.9): how long and winding the corridors are. Higher values give long
  dead ends and a solution that wanders and snakes back; lower values give a bushier maze with short
  dead ends and a more direct solution
- Usage:
```
usage: line-maze [-h] [-H HEIGHT] [-W WIDTH] [-S] [-I ITERATIONS] [-t TWIST] [-o OUTPUT]

options:
  -h, --help            show this help message and exit
  -H, --height HEIGHT   how high to make the maze
  -W, --width WIDTH     how wide to make the maze
  -S, --smart           optimize the maze by being smart
  -I, --iterations ITERATIONS
                        how many times to try
  -t, --twist TWIST     0 to 1: higher makes longer dead ends and a more winding solution (default
                        0.9)
  -o, --output OUTPUT   save the maze to this PNG (and the solution next to it) instead of showing
                        it
```
### Multithreaded Line Maze Generator
- Generates line mazes, using smart mode
- Spreads the work across several processes, so it uses all your CPU cores
- Defaults are:
  - 50 by 50 maze
  - iterated 100 times
  - 10 worker processes
- Currently the best maze generator in this repo. 
- Usage:
```
usage: multithreaded-maze [-h] [-H HEIGHT] [-W WIDTH] [-I ITERATIONS] [-T THREADS] [-t TWIST]
                          [-o OUTPUT]

options:
  -h, --help            show this help message and exit
  -H, --height HEIGHT   how high to make the maze
  -W, --width WIDTH     how wide to make the maze
  -I, --iterations ITERATIONS
                        how many times to try
  -T, --threads THREADS
                        how many worker processes to use
  -t, --twist TWIST     0 to 1: higher makes longer dead ends and a more winding solution (default
                        0.9)
  -o, --output OUTPUT   save the maze to this PNG (and the solution next to it) instead of showing
                        it
```

#### Line Maze Example:
![A Line Maze generated with multithreaded-maze](https://raw.githubusercontent.com/nattyboyme3/python-maze/main/examples/50x50_maze.PNG "Multi-Threaded Line Maze Example")

#### Line Maze Solution:
![The solution of the line maze above](https://raw.githubusercontent.com/nattyboyme3/python-maze/main/examples/50x50_maze_solution.PNG "Line Maze Solution Example")

### Square maze
- Kept for historical purposes only. Don't use this. It probably doesn't even work.
- Grid
- Solving/Optimization isn't working yet
- Uses grid squares for walls
- Usage:
  `python square_maze.py <maze_width> <maze_height>`

## Fair warning: 
__This code is horribly inefficient, and large mazes take quite a long time to generate, especially if they are run through many iterations__ 
