import sys
from queue import Queue, Empty
from python_maze_generator.line_maze import LineMaze
from threading import Thread
import time
import argparse


def build_maze(q, output_length, output_maze, errors, h, w):
    while True:
        try:
            job_id = q.get(block=False)
        except Empty:
            return
        try:
            m = LineMaze(h, w, optimize=True)
            output_length[job_id] = m.length
            output_maze[job_id] = m
        except Exception as e:
            errors.append(e)
        finally:
            q.task_done()


def generate_mazes(height, width, iterations, threads) -> LineMaze:
    if threads < 1:
        raise ValueError("threads must be at least 1")
    if iterations < 1:
        raise ValueError("iterations must be at least 1")
    q = Queue(maxsize=0)
    errors = list()
    lengths = list()
    mazes = list()
    for x in range(iterations):
        lengths.append(None)
        mazes.append(None)
        q.put(x)
    for thread in range(threads):
        worker = Thread(target=build_maze, args=(q, lengths, mazes, errors, height, width))
        worker.daemon = True
        worker.start()
        time.sleep(0.1)
    while q.unfinished_tasks > 0:
        time.sleep(3)
        any_finished = [x for x in lengths if x]
        if any_finished:
            print(f"Mazes yet to generate: {q.qsize()}. Best: {max(any_finished)}")
    if errors:
        raise errors[0]
    best = 0
    for i in range(len(lengths)):
        if lengths[i] > lengths[best]:
            best = i
    return mazes[best]


if __name__ == '__main__':
    sys.setrecursionlimit(10**6)
    a = argparse.ArgumentParser()
    a.add_argument('-H', '--height', default=50, type=int, help='how high to make the maze')
    a.add_argument('-W', '--width', default=50, type=int, help='how wide to make the maze')
    a.add_argument('-I', '--iterations', default=100, type=int, help='how many times to try')
    a.add_argument('-T', '--threads', default=10, type=int, help='how many threads to spawn')
    args = a.parse_args()
    start = time.time()
    best_maze = generate_mazes(args.height, args.width, args.iterations, args.threads)
    end = time.time()
    best_maze.draw(solved=True)
    best_maze.draw(solved=False)
    e_time = round(end - start, 2)
    a_time = round(e_time / args.iterations, 4)
    print(f"Generated {args.iterations} {args.height} by {args.width} mazes in {e_time} seconds "
          f"using {args.threads} threads, average {a_time} seconds, solution length: {best_maze.length}")