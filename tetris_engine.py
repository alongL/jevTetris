"""
Tetris Engine & AI Heuristic Candidate Generator for OpenJEV System One.
Grid: 10 columns x 20 rows. 0 = empty, 1..7 = piece colors.
"""

import copy
import time
from typing import List, Tuple, Dict, Any

PIECES = {
    'I': [
        [[1, 1, 1, 1]],
        [[1], [1], [1], [1]]
    ],
    'O': [
        [[1, 1], [1, 1]]
    ],
    'T': [
        [[0, 1, 0], [1, 1, 1]],
        [[1, 0], [1, 1], [1, 0]],
        [[1, 1, 1], [0, 1, 0]],
        [[0, 1], [1, 1], [0, 1]]
    ],
    'S': [
        [[0, 1, 1], [1, 1, 0]],
        [[1, 0], [1, 1], [0, 1]]
    ],
    'Z': [
        [[1, 1, 0], [0, 1, 1]],
        [[0, 1], [1, 1], [1, 0]]
    ],
    'J': [
        [[1, 0, 0], [1, 1, 1]],
        [[1, 1], [1, 0], [1, 0]],
        [[1, 1, 1], [0, 0, 1]],
        [[0, 1], [0, 1], [1, 1]]
    ],
    'L': [
        [[0, 0, 1], [1, 1, 1]],
        [[1, 0], [1, 0], [1, 1]],
        [[1, 1, 1], [1, 0, 0]],
        [[1, 1], [0, 1], [0, 1]]
    ]
}

PIECE_COLORS = {
    'I': '#00f0f0',  # Cyan
    'O': '#f0f000',  # Yellow
    'T': '#a000f0',  # Purple
    'S': '#00f000',  # Green
    'Z': '#f00000',  # Red
    'J': '#0000f0',  # Blue
    'L': '#f0a000'   # Orange
}

ROWS = 20
COLS = 10


def drop_piece(board: List[List[int]], shape: List[List[int]], col: int) -> Tuple[int, bool]:
    """Find landing row for piece shape at column col. Return (row, valid)."""
    h = len(shape)
    w = len(shape[0])
    if col < 0 or col + w > COLS:
        return -1, False

    landing_r = -1
    for r in range(ROWS - h + 1):
        # Check collision
        collides = False
        for dr in range(h):
            for dc in range(w):
                if shape[dr][dc] and board[r + dr][col + dc] != 0:
                    collides = True
                    break
            if collides:
                break
        if collides:
            break
        landing_r = r

    if landing_r == -1:
        return -1, False
    return landing_r, True


def simulate_placement(board: List[List[int]], shape: List[List[int]], col: int, landing_r: int) -> Tuple[List[List[int]], int]:
    """Simulate placing shape at col, landing_r and clear lines. Return (new_board, lines_cleared)."""
    h = len(shape)
    w = len(shape[0])
    new_board = [row[:] for row in board]

    for dr in range(h):
        for dc in range(w):
            if shape[dr][dc]:
                new_board[landing_r + dr][col + dc] = 1

    # Clear lines
    kept_rows = [row for row in new_board if not all(cell != 0 for cell in row)]
    cleared = ROWS - len(kept_rows)
    while len(kept_rows) < ROWS:
        kept_rows.insert(0, [0] * COLS)

    return kept_rows, cleared


def evaluate_board(board: List[List[int]]) -> Dict[str, Any]:
    """Calculate standard Tetris heuristic features."""
    col_heights = [0] * COLS
    for c in range(COLS):
        for r in range(ROWS):
            if board[r][c] != 0:
                col_heights[c] = ROWS - r
                break

    max_height = max(col_heights)
    aggregate_height = sum(col_heights)

    bumpiness = sum(abs(col_heights[c] - col_heights[c + 1]) for c in range(COLS - 1))

    holes = 0
    for c in range(COLS):
        block_found = False
        for r in range(ROWS):
            if board[r][c] != 0:
                block_found = True
            elif block_found and board[r][c] == 0:
                holes += 1

    return {
        "col_heights": col_heights,
        "max_height": max_height,
        "aggregate_height": aggregate_height,
        "bumpiness": bumpiness,
        "holes": holes
    }


def get_candidate_moves(board: List[List[int]], piece_type: str) -> List[Dict[str, Any]]:
    """Generate all valid moves for the piece and select top strategic candidates."""
    rotations = PIECES[piece_type]
    all_moves = []

    for rot_idx, shape in enumerate(rotations):
        w = len(shape[0])
        h = len(shape)
        for col in range(COLS - w + 1):
            landing_r, valid = drop_piece(board, shape, col)
            if not valid or landing_r < 0:
                continue

            sim_board, lines = simulate_placement(board, shape, col, landing_r)
            features = evaluate_board(sim_board)

            # Pierre Dellacherie style weighted score
            # Landing height is relative to bottom
            landing_height = (ROWS - landing_r) - (h / 2.0)
            score = (
                (lines * 3.4)
                - (features["holes"] * 4.0)
                - (features["bumpiness"] * 0.4)
                - (features["max_height"] * 0.8)
                - (features["aggregate_height"] * 0.2)
                - (landing_height * 0.1)
            )

            all_moves.append({
                "piece": piece_type,
                "rotation": rot_idx,
                "col": col,
                "landing_r": landing_r,
                "lines_cleared": lines,
                "holes": features["holes"],
                "max_height": features["max_height"],
                "bumpiness": features["bumpiness"],
                "aggregate_height": features["aggregate_height"],
                "heuristic_score": round(score, 3)
            })

    if not all_moves:
        return []

    # Sort descending by heuristic score
    all_moves.sort(key=lambda m: m["heuristic_score"], reverse=True)

    # We want 3-4 candidates with varied characteristics:
    # 1. Best overall move
    # 2. Alternative good move (different column)
    # 3. Different rotation or higher bumpiness
    # 4. A suboptimal or risky move (creates hole or spikes height)
    candidates = []
    
    # 1. Best move
    best = all_moves[0]
    candidates.append(best)

    # 2. Strong alternative with different column
    for m in all_moves[1:]:
        if m["col"] != best["col"] and m["holes"] == best["holes"]:
            candidates.append(m)
            break

    # 3. Move with different rotation if available
    for m in all_moves[1:]:
        if m["rotation"] != best["rotation"] and m not in candidates:
            candidates.append(m)
            break

    # 4. If we have a move that creates holes or is noticeably worse, include as contrast
    worse_moves = [m for m in all_moves if m["holes"] > best["holes"] or m["max_height"] > best["max_height"] + 1]
    if worse_moves:
        candidates.append(worse_moves[-1] if len(worse_moves) > 2 else worse_moves[0])

    # If still fewer than 4 candidates, fill with next best unique moves
    for m in all_moves:
        if len(candidates) >= 4:
            break
        if m not in candidates:
            candidates.append(m)

    # Enrich each candidate with a clear natural language description
    for i, c in enumerate(candidates):
        rot_name = f"rot {c['rotation']}"
        lines_desc = f"Clears {c['lines_cleared']} lines" if c['lines_cleared'] > 0 else "Clears 0 lines"
        holes_desc = "creates 0 holes (clean)" if c['holes'] == 0 else f"creates {c['holes']} trapped holes"
        height_desc = f"keeps max height at {c['max_height']}"
        bump_desc = f"bumpiness {c['bumpiness']}"
        
        c["key"] = f"Move_{chr(65+i)}"
        c["description"] = (
            f"Col {c['col']} ({rot_name}): {lines_desc}, {holes_desc}, {height_desc}, {bump_desc}."
        )

    return candidates

