"""
High-Definition Lossless Video & Crisp GIF Generator for TypeSafe JEV Tetris AI.
Captures lossless browser frames and compiles into universally-compatible H.264 MP4 and crystal-clear GIF.
"""

import os
import sys
import time
import shutil
import subprocess
import threading
from http.server import HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tetris_web import TetrisHandler
from playwright.sync_api import sync_playwright

RECORD_PORT = 8099
FFMPEG_BIN = os.path.expanduser("~/.local/bin/ffmpeg")
if not os.path.exists(FFMPEG_BIN):
    FFMPEG_BIN = "ffmpeg"


def start_server():
    server = HTTPServer(("127.0.0.1", RECORD_PORT), TetrisHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    return server


def record_hd_demo(duration_seconds=12, fps=12, output_mp4="tetris_demo.mp4", output_gif="tetris_demo.gif"):
    print("=" * 70)
    print("🎬 启动高精度无损录制流程 (100% 原始画质逐帧采集)...")
    print("=" * 70)

    server = start_server()
    frames_dir = os.path.join(os.path.dirname(__file__), "_frames_temp")
    if os.path.exists(frames_dir):
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir, exist_ok=True)

    total_frames = int(duration_seconds * fps)
    frame_interval = 1.0 / fps

    print(f"1. 🌐 启动本地服务端 (Port {RECORD_PORT})")
    print(f"2. 📸 开始以 {fps} FPS 连续采集 {total_frames} 帧高清画面 (约 {duration_seconds} 秒)...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        # Perfectly fit the main UI container (1120x760)
        page = browser.new_page(viewport={"width": 1120, "height": 760})
        page.goto(f"http://127.0.0.1:{RECORD_PORT}")

        # Let game initialize and drop first piece
        time.sleep(1.0)

        t_start = time.time()
        for i in range(total_frames):
            frame_path = os.path.join(frames_dir, f"frame_{i:04d}.png")
            page.screenshot(path=frame_path)

            target_time = t_start + (i + 1) * frame_interval
            sleep_time = target_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)

            if i % fps == 0 or i == total_frames - 1:
                pct = int((i + 1) / total_frames * 100)
                print(f"   • 采集进度: {pct}% ({i+1}/{total_frames} 帧)", end="\r")

        print("\n3. ⏹️ 帧序列采集完成！正在关闭浏览器...")
        browser.close()

    server.shutdown()

    # 4. Compile into MP4
    mp4_path = os.path.join(os.path.dirname(__file__), output_mp4)
    print(f"4. 🎞️ 正在合成通用 H.264 MP4 视频 (CRF 17, 包含音频轨, 移动端全兼容): {mp4_path}")

    # Standard universally compatible MP4:
    # - H.264 High Profile, yuv420p
    # - movflags +faststart (can be opened immediately anywhere)
    # - Silent AAC stereo audio track (ensures QuickTime, Windows Media, and web players don't crash)
    cmd_mp4 = [
        FFMPEG_BIN, "-y",
        "-framerate", str(fps),
        "-i", os.path.join(frames_dir, "frame_%04d.png"),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "17",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        mp4_path
    ]
    subprocess.run(cmd_mp4, check=True)

    # 5. Compile into crystal-clear GIF
    gif_path = os.path.join(os.path.dirname(__file__), output_gif)
    print(f"5. 🎨 正在生成超清晰 GIF (双通道调色板优化, 无模糊噪点): {gif_path}")

    # Use high-quality 2-pass palette generation without aggressive downscaling
    # Scale width to 900 for high resolution text readability
    filter_palette = "scale=920:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128:reserve_transparent=0:stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=3"
    cmd_gif = [
        FFMPEG_BIN, "-y",
        "-framerate", str(fps),
        "-i", os.path.join(frames_dir, "frame_%04d.png"),
        "-vf", filter_palette,
        gif_path
    ]
    subprocess.run(cmd_gif, check=True)

    # 6. Clean temp frames
    shutil.rmtree(frames_dir, ignore_errors=True)

    mp4_kb = os.path.getsize(mp4_path) // 1024
    gif_kb = os.path.getsize(gif_path) // 1024

    print("\n" + "=" * 70)
    print("🎉 高清制作完成！")
    print(f"   📹 MP4 视频: {mp4_path} ({mp4_kb} KB, 通用播放器/微信/浏览器均可秒开)")
    print(f"   🖼️ GIF 动图: {gif_path} ({gif_kb} KB, 极度清晰，字迹分明)")
    print("=" * 70)


if __name__ == "__main__":
    dur = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    record_hd_demo(duration_seconds=dur, fps=12)
