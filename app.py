from flask import Flask, jsonify, render_template, request
import chess
import chess.engine
import random
import datetime
import os
import platform

app = Flask(__name__)

# --- Global state ---
board = chess.Board()
player_name = None

# ---------------------------------------------
# Cross-platform results path
# ---------------------------------------------
if os.name == "nt":  # Windows local
    RESULTS_PATH = r"C:\Users\aadit\OneDrive\Documents\webchess_V1\results.txt"
else:  # Render / Linux
    RESULTS_PATH = "/tmp/results.txt"


# ---------------------------------------------
# INDEX PAGE
# ---------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------
# CURRENT STATE
# ---------------------------------------------
@app.route("/get_state")
def get_state():
    return jsonify({
        "fen": board.fen(),
        "turn": "white" if board.turn == chess.WHITE else "black",
        "game_over": board.is_game_over(),
        "player": player_name
    })


# ---------------------------------------------
# START GAME
# ---------------------------------------------
@app.route("/start", methods=["POST"])
def start_game():
    global board, player_name
    board = chess.Board()
    data = request.get_json() or {}
    player_name = data.get("player", "Guest")
    print("New game started by:", player_name)

    return jsonify({
        "status": "started",
        "player": player_name,
        "fen": board.fen()
    })


# ---------------------------------------------
# END GAME (RESET)
# ---------------------------------------------
@app.route("/end", methods=["POST"])
def end_game():
    global board
    board = chess.Board()
    print("Game manually ended and reset.")
    return jsonify({"status": "reset", "fen": board.fen()})


# ---------------------------------------------
# GET VALID MOVES FOR ONE SQUARE
# ---------------------------------------------
@app.route("/valid_moves/<square>")
def valid_moves(square):
    try:
        sq = chess.parse_square(square)
        moves = [m.uci() for m in board.legal_moves if m.from_square == sq]
        return jsonify({"moves": moves})
    except Exception as e:
        print("Move error:", e)
        return jsonify({"moves": []})


# ---------------------------------------------
# MAIN PLAYER MOVE LOGIC  (SAFE & CORRECT)
# ---------------------------------------------
@app.route("/player_move", methods=["POST"])
def player_move():
    global board

    data = request.get_json() or {}
    move_uci = data.get("move")
    difficulty = data.get("difficulty", "medium")
    player = data.get("player", "Guest")

    if not move_uci:
        return jsonify({"status": "error", "message": "Missing move", "fen": board.fen()})

    # --------------------------
    # PLAYER MOVE
    # --------------------------
    try:
        move = chess.Move.from_uci(move_uci)
        if move not in board.legal_moves:
            return jsonify({"status": "illegal", "fen": board.fen()})
        board.push(move)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "fen": board.fen()})

    # If PLAYER ends game
    if board.is_game_over():
        result_text = get_result_text(player, difficulty)
        log_result(result_text)
        return jsonify({
            "status": "finished",
            "result": result_text,
            "fen": board.fen()
        })

    # --------------------------
    # AI MOVE
    # --------------------------
    ai_move = get_ai_move(difficulty)

    if ai_move is None:
        # Safety fallback
        return jsonify({
            "status": "ok",
            "ai": None,
            "fen": board.fen()
        })

    board.push(ai_move)

    # If AI ends game
    if board.is_game_over():
        result_text = get_result_text(player, difficulty)
        log_result(result_text)
        return jsonify({
            "status": "finished",
            "result": result_text,
            "fen": board.fen()
        })

    # Regular response
    return jsonify({
        "status": "ok",
        "ai": ai_move.uci(),
        "fen": board.fen()
    })


# ---------------------------------------------
# AI MOVE LOGIC
# ---------------------------------------------
def get_ai_move(level="medium"):
    global board

    is_windows = (os.name == "nt")
    on_render = platform.system() == "Linux"

    think_times = {"easy": 0.1, "medium": 0.5, "hard": 1.5}
    think_time = think_times.get(level, 0.5)

    # --- WINDOWS LOCAL STOCKFISH ---
    if is_windows and not on_render:
        engine_path = r"C:\Users\aadit\OneDrive\Documents\webchess_V1\stockfish-windows-x86-64-avx2.exe"
        try:
            if os.path.exists(engine_path):
                with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
                    result = engine.play(board, chess.engine.Limit(time=think_time))
                    return result.move
        except Exception as e:
            print("Stockfish error fallback:", e)

    # --- FALLBACK (Render or Stockfish missing)
    legal = list(board.legal_moves)
    return random.choice(legal) if legal else None


# ---------------------------------------------
# LOG RESULT OF EACH GAME
# ---------------------------------------------
def get_result_text(player, difficulty):
    res = board.result()
    status = (
        "White wins" if res == "1-0" else
        "Black wins" if res == "0-1" else
        "Draw"
    )

    return (
        f"Game ended at {datetime.datetime.now()}\n"
        f"Player: {player}\n"
        f"Difficulty: {difficulty}\n"
        f"Result: {status} ({res})\n"
        f"Final FEN: {board.fen()}\n"
        "--------------------------------------------------\n"
    )


def log_result(text):
    try:
        os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
        with open(RESULTS_PATH, "a", encoding="utf-8") as f:
            f.write(text)
        print("Saved result to:", RESULTS_PATH)
    except Exception as e:
        print("Write log error:", e)


# ---------------------------------------------
# RETURN GAME LOG
# ---------------------------------------------
@app.route("/logs")
def get_logs():
    try:
        if not os.path.exists(RESULTS_PATH):
            return "No games yet."
        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading log: {e}"


# ---------------------------------------------
# RUN APP
# ---------------------------------------------
if __name__ == "__main__":
    # Accessible on LAN or Render
    app.run(host="0.0.0.0", port=5000, debug=True)
