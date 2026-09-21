"""
Terminal Tetris AI Demo powered by Official TypeSafe JEV API.
Directory: jevTetris/
"""

import sys
import os
import time
import random
from typing import List, Dict, Any

from typesafe_sdk import Choice
from tetris_engine import (
    ROWS, COLS, PIECES, drop_piece, simulate_placement,
    evaluate_board, get_candidate_moves
)
from tetris_client import get_official_jev_client, MODEL_NAME

CLIENT = get_official_jev_client()

PIECE_NAMES = ['I', 'J', 'L', 'O', 'S', 'T', 'Z']

# ANSI Colors
COLORS = {
    'I': '\033[96m█\033[0m',  # Cyan
    'J': '\033[94m█\033[0m',  # Blue
    'L': '\033[33m█\033[0m',  # Yellow/Orange
    'O': '\033[93m█\033[0m',  # Bright Yellow
    'S': '\033[92m█\033[0m',  # Green
    'T': '\033[95m█\033[0m',  # Magenta
    'Z': '\033[91m█\033[0m',  # Red
    'GHOST': '\033[90m░\033[0m',
    'EMPTY': '\033[90m·\033[0m',
}


def render_board(board: List[List[int]], current_piece: str, chosen_move: Dict[str, Any] = None, ghost: bool = True):
    display = [[COLORS['EMPTY'] for _ in range(COLS)] for _ in range(ROWS)]
    
    # Fill placed blocks
    for r in range(ROWS):
        for c in range(COLS):
            val = board[r][c]
            if val != 0:
                p_char = PIECE_NAMES[(val - 1) % len(PIECE_NAMES)]
                display[r][c] = COLORS.get(p_char, '█')

    # Draw ghost piece at bottom if chosen_move
    if chosen_move and ghost:
        shape = PIECES[chosen_move['piece']][chosen_move['rotation']]
        col = chosen_move['col']
        landing_r = chosen_move['landing_r']
        for dr in range(len(shape)):
            for dc in range(len(shape[0])):
                if shape[dr][dc] and 0 <= landing_r + dr < ROWS and 0 <= col + dc < COLS:
                    if display[landing_r + dr][col + dc] == COLORS['EMPTY']:
                        display[landing_r + dr][col + dc] = COLORS['GHOST']

    # Draw current falling piece AT THE TOP (row 0)
    if chosen_move:
        shape = PIECES[chosen_move['piece']][chosen_move['rotation']]
        col = chosen_move['col']
        p_color = COLORS.get(chosen_move['piece'], '█')
        for dr in range(len(shape)):
            for dc in range(len(shape[0])):
                if shape[dr][dc] and 0 <= dr < ROWS and 0 <= col + dc < COLS:
                    display[dr][col + dc] = p_color

    lines = []
    lines.append("   " + " ".join(str(c) for c in range(COLS)))
    lines.append("  ┌" + "──" * COLS + "┐")
    for r in range(ROWS):
        row_str = " ".join(display[r])
        lines.append(f"{r:2d}│ {row_str} │")
    lines.append("  └" + "──" * COLS + "┘")
    return "\n".join(lines)


def get_ai_decision(board: List[List[int]], piece: str) -> Dict[str, Any]:
    candidates = get_candidate_moves(board, piece)
    if not candidates:
        return {"error": "Game Over"}

    criteria = {c["key"]: c["description"] for c in candidates}
    state = (
        f"Tetris Placement Decision:\n"
        f"Current Piece: {piece}-tetromino.\n"
        f"Candidate Moves:\n" + "\n".join(f"- {k}: {v}" for k, v in criteria.items())
    )

    t0 = time.perf_counter()
    try:
        resp = CLIENT.system_one(
            state=state,
            questions={
                "best_move": Choice(
                    instructions="Which candidate placement is the best strategic move to clear lines, avoid creating holes, and keep the board height low?",
                    criteria=criteria
                )
            },
            model=MODEL_NAME
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        choice_ans = resp.choices["best_move"]
        chosen_key = choice_ans.choice

        chosen_cand = next((c for c in candidates if c["key"] == chosen_key), candidates[0])
        return {
            "chosen": chosen_cand,
            "confidence": choice_ans.confidence,
            "probabilities": choice_ans.probabilities,
            "candidates": candidates,
            "latency_ms": round(latency_ms, 1)
        }
    except Exception as e:
        latency_ms = (time.perf_counter() - t0) * 1000
        return {
            "chosen": candidates[0],
            "confidence": 1.0,
            "probabilities": {candidates[0]["key"]: 1.0},
            "candidates": candidates,
            "latency_ms": round(latency_ms, 1),
            "error": str(e)
        }


def run_terminal_game(max_pieces: int = 5, delay: float = 0.5):
    board = [[0] * COLS for _ in range(ROWS)]
    score = 0
    total_lines = 0
    piece_count = 0
    
    bag = []

    def next_piece():
        nonlocal bag
        if not bag:
            bag = PIECE_NAMES[:]
            random.shuffle(bag)
        return bag.pop()

    current_piece = next_piece()
    upcoming_piece = next_piece()

    print("\033[2J\033[H")  # Clear screen
    print("==================================================================")
    print("  🌐 Official TypeSafe JEV API (https://api.typesafe.ai) Tetris  ")
    print("==================================================================")

    while piece_count < max_pieces:
        piece_count += 1
        ai_res = get_ai_decision(board, current_piece)
        if "error" in ai_res and ai_res["error"] == "Game Over":
            print("\n💥 GAME OVER! No valid placements remaining.")
            break

        chosen = ai_res["chosen"]
        latency = ai_res["latency_ms"]
        probs = ai_res["probabilities"]

        print("\033[H")
        board_art = render_board(board, current_piece, chosen, ghost=True)
        
        side_hud = [
            f"=== Tetris AI HUD ===",
            f"API: TypeSafe Official Cloud",
            f"Endpoint: https://api.typesafe.ai",
            f"Model: {MODEL_NAME}",
            f"Inference Latency: \033[93m{latency:.1f} ms\033[0m",
            f"Score: {score} | Lines: {total_lines}",
            f"Pieces: {piece_count}/{max_pieces}",
            f"Current Piece: \033[93m{current_piece}\033[0m",
            f"Next Piece:    \033[96m{upcoming_piece}\033[0m",
            f"------------------------------------",
            f"Chosen Move: \033[92m{chosen['key']}\033[0m (Col {chosen['col']}, Rot {chosen['rotation']})",
            f"Confidence: {ai_res['confidence']*100:.1f}%",
            f"------------------------------------",
            f"Official JEV Probabilities:"
        ]
        for c in ai_res["candidates"]:
            prob = probs.get(c["key"], 0.0)
            bar_len = int(prob * 18)
            bar = "█" * bar_len + "░" * (18 - bar_len)
            is_chosen = "⭐" if c["key"] == chosen["key"] else "  "
            side_hud.append(f"{is_chosen} {c['key']} [{bar}] {prob*100:5.1f}%")

        board_lines = board_art.split("\n")
        max_rows = max(len(board_lines), len(side_hud))
        for i in range(max_rows):
            b_line = board_lines[i] if i < len(board_lines) else " " * 26
            h_line = side_hud[i] if i < len(side_hud) else ""
            print(f"{b_line:<28}  {h_line}")

        time.sleep(delay)

        # Place piece permanently on board
        shape = PIECES[chosen["piece"]][chosen["rotation"]]
        piece_idx = PIECE_NAMES.index(chosen["piece"]) + 1
        new_board, cleared = simulate_placement(board, shape, chosen["col"], chosen["landing_r"])
        
        for dr in range(len(shape)):
            for dc in range(len(shape[0])):
                if shape[dr][dc]:
                    board[chosen["landing_r"] + dr][chosen["col"] + dc] = piece_idx

        # Clear lines
        kept_rows = [row for row in board if not all(cell != 0 for cell in row)]
        cleared_lines = ROWS - len(kept_rows)
        while len(kept_rows) < ROWS:
            kept_rows.insert(0, [0] * COLS)
        board = kept_rows

        if cleared_lines > 0:
            total_lines += cleared_lines
            line_scores = {1: 100, 2: 300, 3: 500, 4: 800}
            score += line_scores.get(cleared_lines, cleared_lines * 200)

        current_piece = upcoming_piece
        upcoming_piece = next_piece()

    print(f"\nCompleted! Final Score: {score}, Total Lines Cleared: {total_lines}, Pieces Placed: {piece_count}")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    run_terminal_game(max_pieces=count, delay=0.5)
