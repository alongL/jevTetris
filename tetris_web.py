"""
Web-based Real-Time Tetris AI Demo powered by Official TypeSafe JEV API.
Directory: jevTetris/
Runs on http://localhost:8095 (or configurable port)
"""

import os
import json
import time
import random
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, List

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typesafe_sdk import TypeSafeClient, Choice
from tetris_engine import (
    ROWS, COLS, PIECES, PIECE_COLORS,
    drop_piece, simulate_placement, evaluate_board, get_candidate_moves
)
from tetris_client import get_official_jev_client, MODEL_NAME, BASE_URL

# Optional local client for comparison
try:
    from openjev_sdk import get_openjev_client
    LOCAL_CLIENT = get_openjev_client(os.environ.get("OPENJEV_BASE_URL", "http://10.10.27.105:8088"))
except Exception:
    LOCAL_CLIENT = None

OFFICIAL_CLIENT = get_official_jev_client()


PORT = int(os.environ.get("PORT", 8092))

HTML_CONTENT = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TypeSafe 官方 JEV 俄罗斯方块 AI</title>
    <style>
        :root {
            --bg: #0d1117;
            --panel-bg: #161b22;
            --border: #30363d;
            --accent: #58a6ff;
            --accent-green: #3fb950;
            --accent-purple: #bc8cff;
            --accent-orange: #f0883e;
            --accent-red: #f85149;
            --text-main: #f0f6fc;
            --text-muted: #8b949e;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", monospace;
        }

        body {
            background-color: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 24px 16px;
        }

        header {
            text-align: center;
            margin-bottom: 20px;
        }

        .title {
            font-size: 26px;
            font-weight: 700;
            letter-spacing: 0.5px;
            background: linear-gradient(135deg, #58a6ff, #bc8cff, #3fb950);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 6px;
        }

        .subtitle {
            font-size: 13px;
            color: var(--text-muted);
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            background: rgba(88, 166, 255, 0.15);
            border: 1px solid rgba(88, 166, 255, 0.4);
            border-radius: 12px;
            color: var(--accent);
            font-size: 12px;
            font-weight: 600;
            margin-top: 8px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--accent);
            box-shadow: 0 0 8px var(--accent);
            animation: pulse 1.8s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.85); }
        }

        .main-container {
            display: flex;
            gap: 24px;
            max-width: 1060px;
            width: 100%;
            justify-content: center;
            align-items: flex-start;
        }

        /* Tetris Board Column */
        .tetris-column {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
        }

        .board-wrapper {
            position: relative;
            background: #090d13;
            border: 2px solid #30363d;
            border-radius: 10px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6), 0 0 20px rgba(88, 166, 255, 0.15);
            padding: 6px;
        }

        canvas#tetrisCanvas {
            display: block;
            background: #06090e;
            border-radius: 6px;
        }

        /* Controls */
        .controls-card {
            display: flex;
            gap: 8px;
            background: var(--panel-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 8px 12px;
            width: 100%;
            justify-content: center;
        }

        button {
            background: #21262d;
            color: var(--text-main);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 8px 14px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        button:hover {
            background: #30363d;
            border-color: #8b949e;
        }

        button.primary {
            background: #238636;
            border-color: rgba(240, 246, 252, 0.1);
            color: #ffffff;
        }

        button.primary:hover {
            background: #2ea043;
        }

        /* Engine Switcher */
        .backend-switcher {
            display: flex;
            align-items: center;
            gap: 8px;
            background: var(--panel-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 6px 12px;
            width: 100%;
            font-size: 12px;
            color: var(--text-muted);
            justify-content: space-between;
        }

        .backend-switcher select {
            background: #0d1117;
            color: var(--text-main);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
        }

        /* Info & AI Column */
        .side-column {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 16px;
            max-width: 480px;
        }

        .card {
            background: var(--panel-bg);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
        }

        .card-title {
            font-size: 13px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--text-muted);
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        /* Metrics Row */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
        }

        .metric-box {
            background: #0d1117;
            border: 1px solid #21262d;
            border-radius: 8px;
            padding: 10px 8px;
            text-align: center;
        }

        .metric-label {
            font-size: 11px;
            color: var(--text-muted);
            margin-bottom: 4px;
        }

        .metric-value {
            font-size: 18px;
            font-weight: 700;
            color: #58a6ff;
            font-family: monospace;
        }

        .metric-value.green { color: var(--accent-green); }
        .metric-value.purple { color: var(--accent-purple); }
        .metric-value.orange { color: var(--accent-orange); }

        /* Next piece preview */
        .next-preview-box {
            display: flex;
            align-items: center;
            justify-content: center;
            background: #0d1117;
            border: 1px solid #21262d;
            border-radius: 8px;
            height: 70px;
            margin-bottom: 12px;
        }

        canvas#nextCanvas {
            display: block;
        }

        /* Probability Bars */
        .prob-item {
            margin-bottom: 12px;
        }

        .prob-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
            margin-bottom: 4px;
        }

        .prob-name {
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .prob-name.winner {
            color: var(--accent-green);
        }

        .prob-pct {
            font-family: monospace;
            font-weight: 700;
            color: var(--text-muted);
        }

        .prob-pct.winner {
            color: var(--accent-green);
        }

        .bar-container {
            width: 100%;
            height: 10px;
            background: #21262d;
            border-radius: 5px;
            overflow: hidden;
            position: relative;
        }

        .bar-fill {
            height: 100%;
            border-radius: 5px;
            background: #388bfd;
            transition: width 0.25s ease-out;
        }

        .bar-fill.winner {
            background: linear-gradient(90deg, #238636, #3fb950);
            box-shadow: 0 0 10px rgba(63, 185, 80, 0.6);
        }

        .prob-desc {
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 3px;
            line-height: 1.3;
        }

        /* Speed Control */
        .speed-bar {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: var(--text-muted);
        }

        .speed-bar select {
            background: #21262d;
            color: var(--text-main);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 12px;
        }

        /* Latency Badge */
        .latency-badge {
            background: rgba(188, 140, 255, 0.15);
            border: 1px solid rgba(188, 140, 255, 0.4);
            color: var(--accent-purple);
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-family: monospace;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <header>
        <div class="title">🕹️ TypeSafe 官方 JEV 俄罗斯方块 AI</div>
        <div class="subtitle">采用官方 TypeSafe SDK (Choice API) 真实云端推理与落点决策</div>
        <div class="status-badge" id="serviceBadge">
            <span class="status-dot"></span>
            <span id="serviceLabel">TypeSafe 官方 API (https://api.typesafe.ai / jev-latest)</span>
        </div>
    </header>

    <div class="main-container">
        <!-- Tetris Board -->
        <div class="tetris-column">
            <div class="board-wrapper">
                <canvas id="tetrisCanvas" width="280" height="560"></canvas>
            </div>
            <div class="controls-card">
                <button id="btnPlayPause" class="primary" onclick="togglePlayPause()">⏸️ 暂停</button>
                <button onclick="stepOnce()">⏭️ 单步 (Step)</button>
                <button onclick="resetGame()">🔄 重置</button>
            </div>
            
            <div class="backend-switcher">
                <span>API 后端:</span>
                <select id="backendSelect" onchange="changeBackend()">
                    <option value="official" selected>🌐 官方 JEV (api.typesafe.ai)</option>
                    <option value="local">💻 本地 OpenJEV (10.10.27.105:8088)</option>
                </select>
            </div>

            <div class="speed-bar">
                <span>下落节奏:</span>
                <select id="speedSelect" onchange="changeSpeed()">
                    <option value="800">🐢 慢速观察 (800ms)</option>
                    <option value="400" selected>⚡ 标速流畅 (400ms)</option>
                    <option value="150">🚀 快速推演 (150ms)</option>
                    <option value="50">🏎️ 极速冲刺 (50ms)</option>
                </select>
            </div>
        </div>

        <!-- AI Decision HUD -->
        <div class="side-column">
            <!-- Metrics Row -->
            <div class="metrics-grid">
                <div class="metric-box">
                    <div class="metric-label">得分 (Score)</div>
                    <div id="statScore" class="metric-value">0</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">消行 (Lines)</div>
                    <div id="statLines" class="metric-value green">0</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">已落子 (Pieces)</div>
                    <div id="statPieces" class="metric-value purple">0</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">AI 延迟</div>
                    <div id="statLatency" class="metric-value orange">-- ms</div>
                </div>
            </div>

            <!-- Next Piece Box -->
            <div class="card">
                <div class="card-title">
                    <span>下一个方块 (Next Piece)</span>
                    <span id="currentPieceLabel" class="latency-badge">当前: -</span>
                </div>
                <div class="next-preview-box">
                    <canvas id="nextCanvas" width="120" height="60"></canvas>
                </div>
            </div>

            <!-- AI Candidates Card -->
            <div class="card">
                <div class="card-title">
                    <span>JEV 实时候选决策分布 (Choice API)</span>
                    <span id="decisionLatencyBadge" class="latency-badge">jev-latest</span>
                </div>
                <div id="candidatesList">
                    <div style="color: var(--text-muted); font-size: 13px; text-align: center; padding: 20px;">
                        正在等待官方 JEV 决策...
                    </div>
                </div>
            </div>

            <!-- AI State Prompt Card -->
            <div class="card">
                <div class="card-title">
                    <span>TypeSafe System One 评估状态</span>
                </div>
                <div id="promptViewer" style="font-family: monospace; font-size: 11px; color: var(--text-muted); background: #0d1117; padding: 10px; border-radius: 6px; max-height: 130px; overflow-y: auto; white-space: pre-wrap;">
等待生成策略...
                </div>
            </div>
        </div>
    </div>

    <script>
        const COLS = 10;
        const ROWS = 20;
        const BLOCK_SIZE = 28;

        const PIECES = {
            'I': [[[1, 1, 1, 1]], [[1], [1], [1], [1]]],
            'O': [[[1, 1], [1, 1]]],
            'T': [
                [[0, 1, 0], [1, 1, 1]],
                [[1, 0], [1, 1], [1, 0]],
                [[1, 1, 1], [0, 1, 0]],
                [[0, 1], [1, 1], [0, 1]]
            ],
            'S': [[[0, 1, 1], [1, 1, 0]], [[1, 0], [1, 1], [0, 1]]],
            'Z': [[[1, 1, 0], [0, 1, 1]], [[0, 1], [1, 1], [1, 0]]],
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
        };

        const PIECE_COLORS = {
            'I': '#00f0f0',
            'O': '#f0f000',
            'T': '#a000f0',
            'S': '#00f000',
            'Z': '#f00000',
            'J': '#0050f0',
            'L': '#f0a000'
        };

        const PIECE_NAMES = ['I', 'J', 'L', 'O', 'S', 'T', 'Z'];

        // Game State
        let board = Array.from({ length: ROWS }, () => Array(COLS).fill(0));
        let bag = [];
        let currentPiece = null;
        let nextPiece = null;
        let score = 0;
        let lines = 0;
        let piecesPlaced = 0;

        let isRunning = true;
        let isProcessing = false;
        let stepDelay = 400;
        let mainTimer = null;
        let activeBackend = 'official';

        // Active Falling Piece at top
        let activePiece = null;

        const canvas = document.getElementById('tetrisCanvas');
        const ctx = canvas.getContext('2d');
        const nextCanvas = document.getElementById('nextCanvas');
        const nextCtx = nextCanvas.getContext('2d');

        function getNextFromBag() {
            if (bag.length === 0) {
                bag = [...PIECE_NAMES];
                for (let i = bag.length - 1; i > 0; i--) {
                    const j = Math.floor(Math.random() * (i + 1));
                    [bag[i], bag[j]] = [bag[j], bag[i]];
                }
            }
            return bag.pop();
        }

        function spawnPiece() {
            currentPiece = nextPiece || getNextFromBag();
            nextPiece = getNextFromBag();

            const shape = PIECES[currentPiece][0];
            const w = shape[0].length;
            const startCol = Math.floor((COLS - w) / 2);

            activePiece = {
                piece: currentPiece,
                rotation: 0,
                col: startCol,
                row: 0, // <--- 严格置于最顶部
                targetCol: startCol,
                targetRot: 0,
                landingRow: -1,
                aiDecided: false
            };

            updateUI();
            draw();
            drawNext();
        }

        function initGame() {
            board = Array.from({ length: ROWS }, () => Array(COLS).fill(0));
            score = 0;
            lines = 0;
            piecesPlaced = 0;
            bag = [];
            nextPiece = getNextFromBag();
            spawnPiece();
        }

        function updateUI() {
            document.getElementById('statScore').innerText = score;
            document.getElementById('statLines').innerText = lines;
            document.getElementById('statPieces').innerText = piecesPlaced;
            document.getElementById('currentPieceLabel').innerText = `当前: ${currentPiece}`;
        }

        function drawBlock(cCtx, x, y, color, isGhost = false) {
            const px = x * BLOCK_SIZE;
            const py = y * BLOCK_SIZE;
            const size = BLOCK_SIZE - 1;

            if (isGhost) {
                cCtx.strokeStyle = color;
                cCtx.lineWidth = 1.5;
                cCtx.strokeRect(px + 1.5, py + 1.5, size - 2, size - 2);
                cCtx.fillStyle = color + "26"; // 15% opacity
                cCtx.fillRect(px + 2, py + 2, size - 3, size - 3);
            } else {
                cCtx.fillStyle = color;
                cCtx.fillRect(px, py, size, size);

                // Highlight shine
                cCtx.fillStyle = 'rgba(255, 255, 255, 0.3)';
                cCtx.fillRect(px, py, size, 3);
                cCtx.fillRect(px, py, 3, size);

                // Shadow edge
                cCtx.fillStyle = 'rgba(0, 0, 0, 0.4)';
                cCtx.fillRect(px + size - 3, py, 3, size);
                cCtx.fillRect(px, py + size - 3, size, 3);
            }
        }

        function draw() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Draw grid lines
            ctx.strokeStyle = '#161d28';
            ctx.lineWidth = 0.5;
            for (let c = 0; c <= COLS; c++) {
                ctx.beginPath();
                ctx.moveTo(c * BLOCK_SIZE, 0);
                ctx.lineTo(c * BLOCK_SIZE, ROWS * BLOCK_SIZE);
                ctx.stroke();
            }
            for (let r = 0; r <= ROWS; r++) {
                ctx.beginPath();
                ctx.moveTo(0, r * BLOCK_SIZE);
                ctx.lineTo(COLS * BLOCK_SIZE, r * BLOCK_SIZE);
                ctx.stroke();
            }

            // Draw placed blocks on the board
            for (let r = 0; r < ROWS; r++) {
                for (let c = 0; c < COLS; c++) {
                    const val = board[r][c];
                    if (val !== 0) {
                        const pName = typeof val === 'string' ? val : PIECE_NAMES[(val - 1) % PIECE_NAMES.length];
                        const color = PIECE_COLORS[pName] || '#58a6ff';
                        drawBlock(ctx, c, r, color, false);
                    }
                }
            }

            if (!activePiece) return;

            const pColor = PIECE_COLORS[activePiece.piece] || '#ffffff';

            // 1. Draw Ghost Piece at bottom if landingRow is determined
            if (activePiece.aiDecided && activePiece.landingRow >= 0) {
                const ghostShape = PIECES[activePiece.piece][activePiece.targetRot];
                for (let dr = 0; dr < ghostShape.length; dr++) {
                    for (let dc = 0; dc < ghostShape[dr].length; dc++) {
                        if (ghostShape[dr][dc]) {
                            drawBlock(ctx, activePiece.targetCol + dc, activePiece.landingRow + dr, pColor, true);
                        }
                    }
                }
            }

            // 2. Draw Active Falling Piece (Solid piece starting at row 0 at the top!)
            const activeShape = PIECES[activePiece.piece][activePiece.rotation];
            for (let dr = 0; dr < activeShape.length; dr++) {
                for (let dc = 0; dc < activeShape[dr].length; dc++) {
                    if (activeShape[dr][dc]) {
                        const r = Math.floor(activePiece.row) + dr;
                        const c = activePiece.col + dc;
                        if (r >= 0 && r < ROWS && c >= 0 && c < COLS) {
                            drawBlock(ctx, c, r, pColor, false);
                        }
                    }
                }
            }
        }

        function drawNext() {
            nextCtx.clearRect(0, 0, nextCanvas.width, nextCanvas.height);
            if (!nextPiece) return;

            const shape = PIECES[nextPiece][0];
            const color = PIECE_COLORS[nextPiece] || '#58a6ff';
            const h = shape.length;
            const w = shape[0].length;
            const bSize = 20;

            const offsetX = Math.floor((nextCanvas.width - w * bSize) / 2);
            const offsetY = Math.floor((nextCanvas.height - h * bSize) / 2);

            for (let r = 0; r < h; r++) {
                for (let c = 0; c < w; c++) {
                    if (shape[r][c]) {
                        const px = offsetX + c * bSize;
                        const py = offsetY + r * bSize;
                        nextCtx.fillStyle = color;
                        nextCtx.fillRect(px, py, bSize - 1, bSize - 1);
                        nextCtx.fillStyle = 'rgba(255, 255, 255, 0.3)';
                        nextCtx.fillRect(px, py, bSize - 1, 2);
                    }
                }
            }
        }

        async function fetchAIDecision() {
            if (!activePiece) return null;

            const res = await fetch('/api/tetris_move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    board: board,
                    piece: activePiece.piece,
                    backend: activeBackend
                })
            });

            const data = await res.json();
            if (data.error) {
                alert("AI 决策异常: " + data.error);
                isRunning = false;
                updatePlayButton();
                return null;
            }

            document.getElementById('statLatency').innerText = `${data.latency_ms} ms`;
            document.getElementById('decisionLatencyBadge').innerText = `${data.latency_ms} ms (${data.model || 'jev-latest'})`;
            renderCandidates(data.candidates, data.chosen.key, data.probabilities);
            document.getElementById('promptViewer').innerText = data.state_prompt || "";

            return data.chosen;
        }

        function renderCandidates(candidates, winnerKey, probabilities) {
            const container = document.getElementById('candidatesList');
            container.innerHTML = '';

            candidates.forEach(c => {
                const isWinner = c.key === winnerKey;
                const prob = probabilities[c.key] || 0.0;
                const pct = (prob * 100).toFixed(1);

                const div = document.createElement('div');
                div.className = 'prob-item';
                div.innerHTML = `
                    <div class="prob-header">
                        <span class="prob-name ${isWinner ? 'winner' : ''}">
                            ${isWinner ? '⭐' : '▪️'} <strong>${c.key}</strong> (列 ${c.col}, 旋 ${c.rotation})
                        </span>
                        <span class="prob-pct ${isWinner ? 'winner' : ''}">${pct}%</span>
                    </div>
                    <div class="bar-container">
                        <div class="bar-fill ${isWinner ? 'winner' : ''}" style="width: ${Math.max(1, prob * 100)}%"></div>
                    </div>
                    <div class="prob-desc">${c.description}</div>
                `;
                container.appendChild(div);
            });
        }

        // Animate piece smoothly dropping from row 0 down to landingRow
        function animateDropToLanding(onComplete) {
            if (!activePiece || activePiece.landingRow < 0) {
                onComplete();
                return;
            }

            const targetRow = activePiece.landingRow;
            const startRow = activePiece.row;
            const totalDistance = targetRow - startRow;

            if (totalDistance <= 0) {
                activePiece.row = targetRow;
                draw();
                onComplete();
                return;
            }

            const steps = Math.min(12, Math.max(3, totalDistance));
            const frameDelay = Math.max(12, Math.floor((stepDelay * 0.7) / steps));
            let currentStep = 0;

            const dropInterval = setInterval(() => {
                currentStep++;
                activePiece.row = startRow + (totalDistance * currentStep) / steps;
                draw();

                if (currentStep >= steps) {
                    clearInterval(dropInterval);
                    activePiece.row = targetRow;
                    draw();
                    onComplete();
                }
            }, frameDelay);
        }

        function commitActivePiece() {
            if (!activePiece) return;

            const shape = PIECES[activePiece.piece][activePiece.rotation];
            const pName = activePiece.piece;
            const landing_r = activePiece.landingRow;
            const col = activePiece.col;

            // Place permanently on board
            for (let dr = 0; dr < shape.length; dr++) {
                for (let dc = 0; dc < shape[dr].length; dc++) {
                    if (shape[dr][dc]) {
                        board[landing_r + dr][col + dc] = pName;
                    }
                }
            }

            // Check full rows
            const keptRows = board.filter(row => !row.every(cell => cell !== 0));
            const cleared = ROWS - keptRows.length;
            while (keptRows.length < ROWS) {
                keptRows.unshift(Array(COLS).fill(0));
            }
            board = keptRows;

            if (cleared > 0) {
                lines += cleared;
                const scoresTable = { 1: 100, 2: 300, 3: 500, 4: 800 };
                score += (scoresTable[cleared] || (cleared * 200));
            }

            piecesPlaced++;
            activePiece = null;

            updateUI();
            draw();
        }

        async function runPieceCycle() {
            if (!isRunning || isProcessing) return;
            isProcessing = true;

            try {
                if (!activePiece) {
                    spawnPiece();
                }

                draw();

                const chosen = await fetchAIDecision();
                if (!chosen) {
                    isProcessing = false;
                    return;
                }

                activePiece.targetCol = chosen.col;
                activePiece.targetRot = chosen.rotation;
                activePiece.landingRow = chosen.landing_r;
                activePiece.rotation = chosen.rotation;
                activePiece.col = chosen.col;
                activePiece.aiDecided = true;
                draw();

                await new Promise(r => setTimeout(r, Math.max(60, Math.floor(stepDelay * 0.3))));
                await new Promise(resolve => animateDropToLanding(resolve));

                commitActivePiece();
                spawnPiece();

            } catch (err) {
                console.error("Game cycle error:", err);
            } finally {
                isProcessing = false;
                if (isRunning) {
                    mainTimer = setTimeout(runPieceCycle, Math.max(30, Math.floor(stepDelay * 0.2)));
                }
            }
        }

        async function stepOnce() {
            if (isProcessing) return;
            isRunning = false;
            updatePlayButton();
            if (mainTimer) clearTimeout(mainTimer);

            if (!activePiece) {
                spawnPiece();
                return;
            }

            if (!activePiece.aiDecided) {
                const chosen = await fetchAIDecision();
                if (chosen) {
                    activePiece.targetCol = chosen.col;
                    activePiece.targetRot = chosen.rotation;
                    activePiece.landingRow = chosen.landing_r;
                    activePiece.rotation = chosen.rotation;
                    activePiece.col = chosen.col;
                    activePiece.aiDecided = true;
                    draw();
                }
            } else {
                await new Promise(resolve => animateDropToLanding(resolve));
                commitActivePiece();
                spawnPiece();
            }
        }

        function togglePlayPause() {
            isRunning = !isRunning;
            updatePlayButton();
            if (isRunning) {
                runPieceCycle();
            } else if (mainTimer) {
                clearTimeout(mainTimer);
                mainTimer = null;
            }
        }

        function updatePlayButton() {
            const btn = document.getElementById('btnPlayPause');
            if (isRunning) {
                btn.className = "primary";
                btn.innerText = "⏸️ 暂停";
            } else {
                btn.className = "";
                btn.innerText = "▶️ 继续播放";
            }
        }

        function changeSpeed() {
            const sel = document.getElementById('speedSelect');
            stepDelay = parseInt(sel.value, 10);
        }

        function changeBackend() {
            const sel = document.getElementById('backendSelect');
            activeBackend = sel.value;
            const label = document.getElementById('serviceLabel');
            if (activeBackend === 'official') {
                label.innerText = 'TypeSafe 官方 API (https://api.typesafe.ai / jev-latest)';
            } else {
                label.innerText = '本地 OpenJEV 服务 (10.10.27.105:8088 / openjev-1.5b)';
            }
        }

        function resetGame() {
            if (mainTimer) clearTimeout(mainTimer);
            initGame();
            if (isRunning) {
                runPieceCycle();
            }
        }

        // Start game on page load
        window.addEventListener('load', () => {
            initGame();
            runPieceCycle();
        });
    </script>
</body>
</html>
"""


class TetrisHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/tetris_move":
            try:
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len).decode("utf-8")
                req_data = json.loads(body)

                board = req_data.get("board", [])
                piece = req_data.get("piece", "I")
                backend = req_data.get("backend", "official")

                candidates = get_candidate_moves(board, piece)
                if not candidates:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "No valid placements (Game Over)"}).encode())
                    return

                criteria = {c["key"]: c["description"] for c in candidates}
                state = (
                    f"Tetris Placement Decision:\n"
                    f"Current Falling Piece: {piece}-tetromino.\n"
                    f"Candidate Placements:\n" + "\n".join(f"- {k}: {v}" for k, v in criteria.items())
                )

                t0 = time.perf_counter()
                if backend == "local":
                    client = LOCAL_CLIENT
                    model_to_use = "openjev-1.5b"
                else:
                    client = OFFICIAL_CLIENT
                    model_to_use = MODEL_NAME  # 'jev-latest'

                resp = client.system_one(
                    state=state,
                    questions={
                        "best_move": Choice(
                            instructions="Which candidate placement is the best strategic move to clear lines, avoid creating holes, and keep the board height low?",
                            criteria=criteria
                        )
                    },
                    model=model_to_use
                )
                latency_ms = (time.perf_counter() - t0) * 1000

                choice_ans = resp.choices["best_move"]
                chosen_key = choice_ans.choice
                chosen_cand = next((c for c in candidates if c["key"] == chosen_key), candidates[0])

                response_payload = {
                    "chosen": chosen_cand,
                    "confidence": choice_ans.confidence,
                    "probabilities": choice_ans.probabilities,
                    "candidates": candidates,
                    "latency_ms": round(latency_ms, 1),
                    "model": model_to_use,
                    "state_prompt": state
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response_payload).encode("utf-8"))

            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def run_server():
    server = HTTPServer(("0.0.0.0", PORT), TetrisHandler)
    print(f"🎮 Official TypeSafe JEV Tetris AI Server started at http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()


if __name__ == "__main__":
    run_server()
