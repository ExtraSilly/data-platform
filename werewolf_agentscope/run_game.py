"""Entry point – chay mot van Ma Soi."""

import sys
import os

# Fix encoding cho Windows terminal
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# Dam bao import dung package khi chay tu thu muc goc
sys.path.insert(0, os.path.dirname(__file__))

from game.game_engine import run_game

if __name__ == "__main__":
    print("Game started")
    run_game()

