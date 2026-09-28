import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from python_maze_generator.line_maze import DEFAULT_TWIST, LineMaze, output_maze, positive_int, twist_value
import time
import argparse


def build_maze(h, w, twist):
    # Runs in a worker process, which doesn't inherit the parent's recursion limit
    sys.setrecursionlimit(10**6)
    return LineMaze(h, w, optimize=True, twist=twist)


def generate_mazes(height, width, iterations, threads, twist=DEFAULT_TWIST) -> LineMaze:
    """Generate `iterations` optimized mazes across `threads` worker processes and return the longest."""
    if threads < 1:
        raise ValueError("threads must be at least 1")
    if iterations < 1:
        raise ValueError("iterations must be at least 1")
    best = None
    pool = ProcessPoolExecutor(max_workers=threads)
    try:
        futures = [pool.submit(build_maze, height, width, twist) for _ in range(iterations)]
        for done, future in enumerate(as_completed(futures), 1):
            m = future.result()
            if best is None or m.length > best.length:
                best = m
            print(f"\rMazes yet to generate: {iterations - done}. Best: {best.length}  ", end="", flush=True)
        print()
    finally:
        pool.shutdown(cancel_futures=True)
    return best


def main(argv=None):
    sys.setrecursionlimit(10**6)
    a = argparse.ArgumentParser()
    a.add_argument('-H', '--height', default=50, type=positive_int, help='how high to make the maze')
    a.add_argument('-W', '--width', default=50, type=positive_int, help='how wide to make the maze')
    a.add_argument('-I', '--iterations', default=100, type=positive_int, help='how many times to try')
    a.add_argument('-T', '--threads', default=10, type=positive_int, help='how many worker processes to use')
    a.add_argument('-t', '--twist', default=DEFAULT_TWIST, type=twist_value,
                   help=f'0 to 1: higher makes longer dead ends and a more winding solution (default {DEFAULT_TWIST})')
    a.add_argument('-o', '--output', help='save the maze to this PNG (and the solution next to it) instead of showing it')
    args = a.parse_args(argv)
    start = time.time()
    best_maze = generate_mazes(args.height, args.width, args.iterations, args.threads, args.twist)
    end = time.time()
    output_maze(best_maze, args.output)
    e_time = round(end - start, 2)
    a_time = round(e_time / args.iterations, 4)
    print(f"Generated {args.iterations} {args.height} by {args.width} mazes in {e_time} seconds "
          f"using {args.threads} processes, average {a_time} seconds, solution length: {best_maze.length}")


if __name__ == '__main__':
    main()
