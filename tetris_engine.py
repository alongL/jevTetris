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


def simulate_placement(board: List[List[int]], shape: List[List[int]], col: int, landing_r: int) -> Tuple[List[List[int]], int, int]:
    """Simulate placing shape at col, landing_r. Returns (new_board, lines_cleared, eroded_piece_cells)."""
    h = len(shape)
    w = len(shape[0])
    new_board = [row[:] for row in board]
    piece_cells_cleared = 0

    for dr in range(h):
        for dc in range(w):
            if shape[dr][dc]:
                new_board[landing_r + dr][col + dc] = 1

    kept_rows = []
    lines_cleared = 0
    for r in range(ROWS):
        if all(cell != 0 for cell in new_board[r]):
            lines_cleared += 1
            if landing_r <= r < landing_r + h:
                dr = r - landing_r
                for dc in range(w):
                    if shape[dr][dc]:
                        piece_cells_cleared += 1
        else:
            kept_rows.append(new_board[r])

    while len(kept_rows) < ROWS:
        kept_rows.insert(0, [0] * COLS)

    eroded_piece_cells = lines_cleared * piece_cells_cleared
    return kept_rows, lines_cleared, eroded_piece_cells


def evaluate_board(board: List[List[int]], lines_cleared: int = 0, landing_height: float = 0.0, eroded_piece_cells: int = 0) -> Dict[str, Any]:
    """Calculate institutional Dellacherie + structural features."""
    col_heights = [0] * COLS
    for c in range(COLS):
        for r in range(ROWS):
            if board[r][c] != 0:
                col_heights[c] = ROWS - r
                break

    max_height = max(col_heights)
    aggregate_height = sum(col_heights)
    bumpiness = sum(abs(col_heights[c] - col_heights[c + 1]) for c in range(COLS - 1))

    # Holes & deep holes
    holes = 0
    for c in range(COLS):
        block_found = False
        for r in range(ROWS):
            if board[r][c] != 0:
                block_found = True
            elif block_found and board[r][c] == 0:
                holes += 1

    # Row transitions (horizontal smoothness)
    row_trans = 0
    for r in range(ROWS):
        prev = 1  # grid border is solid
        for c in range(COLS):
            curr = 1 if board[r][c] != 0 else 0
            if curr != prev:
                row_trans += 1
            prev = curr
        if prev != 1:
            row_trans += 1

    # Col transitions (vertical smoothness & overhangs)
    col_trans = 0
    for c in range(COLS):
        prev = 1  # floor is solid
        for r in range(ROWS - 1, -1, -1):
            curr = 1 if board[r][c] != 0 else 0
            if curr != prev:
                col_trans += 1
            prev = curr
        if prev != 0:
            col_trans += 1

    # Well sums
    well_sum = 0
    for c in range(COLS):
        for r in range(ROWS):
            if board[r][c] == 0:
                left_wall = 1 if c == 0 or board[r][c - 1] != 0 else 0
                right_wall = 1 if c == COLS - 1 or board[r][c + 1] != 0 else 0
                if left_wall and right_wall:
                    w_depth = 1
                    for r_sub in range(r + 1, ROWS):
                        if board[r_sub][c] == 0:
                            w_depth += 1
                        else:
                            break
                    well_sum += w_depth

    # Dynamic regime: Emergency defense mode if height >= 11
    is_emergency = max_height >= 11
    if is_emergency:
        # Survival mode: massive reward for clearing lines, brutal penalty on height & holes
        score = (
            -5.5 * landing_height
            + (lines_cleared * 18.0)
            + (eroded_piece_cells * 4.0)
            - (row_trans * 4.0)
            - (col_trans * 12.0)
            - ((holes ** 1.6) * 14.0)
            - (well_sum * 4.0)
            - (max_height * 3.5)
        )
    else:
        # Standard Dellacherie weights
        score = (
            -4.500158825082766 * landing_height
            + 3.4181268101392694 * eroded_piece_cells
            - 3.2178882868487753 * row_trans
            - 9.348695305445199 * col_trans
            - (holes * 8.5)
            - 3.3855972247263626 * well_sum
            - (max_height * 0.5)
        )

    return {
        "col_heights": col_heights,
        "max_height": max_height,
        "aggregate_height": aggregate_height,
        "bumpiness": bumpiness,
        "holes": holes,
        "row_trans": row_trans,
        "col_trans": col_trans,
        "well_sum": well_sum,
        "is_emergency": is_emergency,
        "dellacherie_score": score
    }


def _best_move_score(board: List[List[int]], piece_type: str) -> float:
    """Helper to compute best possible move score for 2-ply lookahead."""
    rotations = PIECES[piece_type]
    best_score = -1e9
    for rot_idx, shape in enumerate(rotations):
        w = len(shape[0])
        h = len(shape)
        for col in range(COLS - w + 1):
            landing_r, valid = drop_piece(board, shape, col)
            if not valid or landing_r < 0:
                continue
            sim_b, lines, eroded = simulate_placement(board, shape, col, landing_r)
            landing_h = (ROWS - landing_r) - (h / 2.0)
            features = evaluate_board(sim_b, lines, landing_h, eroded)
            if features["dellacherie_score"] > best_score:
                best_score = features["dellacherie_score"]
    return best_score if best_score > -1e8 else -500.0


def get_candidate_moves(board: List[List[int]], piece_type: str, next_piece: str = None) -> List[Dict[str, Any]]:
    """Generate all valid moves for the piece, evaluate with Dellacherie + optional 2-ply lookahead, and select top strategic candidates."""
    rotations = PIECES[piece_type]
    all_moves = []

    # Check board initial state
    init_features = evaluate_board(board)
    current_emergency = init_features["is_emergency"]

    for rot_idx, shape in enumerate(rotations):
        w = len(shape[0])
        h = len(shape)
        for col in range(COLS - w + 1):
            landing_r, valid = drop_piece(board, shape, col)
            if not valid or landing_r < 0:
                continue

            sim_board, lines, eroded = simulate_placement(board, shape, col, landing_r)
            landing_height = (ROWS - landing_r) - (h / 2.0)
            features = evaluate_board(sim_board, lines, landing_height, eroded)

            score = features["dellacherie_score"]

            # 2-ply lookahead: evaluate how good next_piece can play on this simulated board
            if next_piece and next_piece in PIECES:
                future_score = _best_move_score(sim_board, next_piece)
                score = score + 0.6 * future_score

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
                "is_emergency": current_emergency,
                "heuristic_score": round(score, 2)
            })

    if not all_moves:
        return []

    # Sort descending by heuristic score
    all_moves.sort(key=lambda m: m["heuristic_score"], reverse=True)

    candidates = []
    best = all_moves[0]
    candidates.append(best)

    # Alternative good move with different column
    for m in all_moves[1:]:
        if m["col"] != best["col"] and m["holes"] == best["holes"]:
            candidates.append(m)
            break

    # Move with different rotation
    for m in all_moves[1:]:
        if m["rotation"] != best["rotation"] and m not in candidates:
            candidates.append(m)
            break

    # Suboptimal / contrast move
    worse_moves = [m for m in all_moves if m["holes"] > best["holes"] or m["max_height"] > best["max_height"] + 1]
    if worse_moves:
        candidates.append(worse_moves[-1] if len(worse_moves) > 2 else worse_moves[0])

    for m in all_moves:
        if len(candidates) >= 4:
            break
        if m not in candidates:
            candidates.append(m)

    # Enrich descriptions with strategic intent
    for i, c in enumerate(candidates):
        rot_name = f"rot {c['rotation']}"
        lines_desc = f"Clears {c['lines_cleared']} lines" if c['lines_cleared'] > 0 else "Clears 0 lines"
        holes_desc = "0 holes (clean surface)" if c['holes'] == 0 else f"{c['holes']} trapped holes"
        height_desc = f"height {c['max_height']}"
        
        prefix = "🚨 [EMERGENCY CLEARANCE] " if c["is_emergency"] else ""
        c["key"] = f"Move_{chr(65+i)}"
        c["description"] = (
            f"{prefix}Col {c['col']} ({rot_name}): {lines_desc}, {holes_desc}, {height_desc}, score {c['heuristic_score']}."
        )

    return candidates

