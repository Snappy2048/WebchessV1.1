// FULL, CLEAN, FINAL APP.JS

let board = [];
let selectedFrom = null;
let validMoves = [];
let gameStarted = false;
let difficulty = "medium";
let playerName = "";

document.addEventListener("DOMContentLoaded", () => {
  const boardEl = document.getElementById("board");

  // Build 8×8 board (row 0 = top)
  for (let r = 0; r < 8; r++) {
    for (let f = 0; f < 8; f++) {
      const sq = document.createElement("div");
      sq.className = "square " + ((r + f) % 2 === 0 ? "light" : "dark");
      sq.dataset.index = f + 8 * r;
      sq.addEventListener("click", onSquareClick);
      boardEl.appendChild(sq);
      board.push(sq);
    }
  }

  document.getElementById("startBtn").addEventListener("click", startGame);
  document.getElementById("endBtn").addEventListener("click", endGame);

  document.getElementById("difficulty").addEventListener("change", (e) => {
    if (!gameStarted) {
      difficulty = e.target.value;
    }
  });

  drawBoard();
  loadLogs();
  setInterval(loadLogs, 30000);
});

/* -----------------------------------------------------------
   START GAME
----------------------------------------------------------- */
async function startGame() {
  const nameInput = document.getElementById("playerName");
  playerName = nameInput.value.trim();

  if (!playerName) {
    alert("Please enter your name before starting.");
    return;
  }

  await fetch("/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ player: playerName }),
  });

  gameStarted = true;

  // 🔒 Lock difficulty during game
  document.getElementById("difficulty").disabled = true;

  drawBoard();
}

/* -----------------------------------------------------------
   END GAME
----------------------------------------------------------- */
async function endGame() {
  if (!gameStarted) {
    alert("No game is running.");
    return;
  }

  const confirmEnd = confirm("End current game?");
  if (!confirmEnd) return;

  await fetch("/end", { method: "POST" });

  gameStarted = false;

  // 🔓 Unlock difficulty after ending
  document.getElementById("difficulty").disabled = false;

  drawBoard();
  loadLogs();
}

/* -----------------------------------------------------------
   DRAW BOARD
----------------------------------------------------------- */
async function drawBoard() {
  const res = await fetch("/get_state");
  const data = await res.json();
  const fen = (data.fen || "").split(" ")[0];

  if (!fen) return console.error("Invalid FEN:", data);

  const ranks = fen.split("/");

  board.forEach((sq) => (sq.textContent = ""));

  // r = 0 is TOP of screen --> should be rank 8
  for (let r = 0; r < 8; r++) {
    const row = ranks[7 - r];   // <-- THIS fixes orientation
    let file = 0;

    for (const symbol of row) {
      if (!isNaN(symbol)) {
        file += parseInt(symbol, 10);
      } else {
        const index = file + 8 * r;
        board[index].textContent = pieceUnicode(symbol);
        file++;
      }
    }
  }
}

/* -----------------------------------------------------------
   UNICODE PIECES
----------------------------------------------------------- */
function pieceUnicode(p) {
  const map = {
    r: "♜", n: "♞", b: "♝", q: "♛", k: "♚", p: "♟",
    R: "♖", N: "♘", B: "♗", Q: "♕", K: "♔", P: "♙"
  };
  return map[p] || "";
}

/* -----------------------------------------------------------
   SQUARE CLICK LOGIC
----------------------------------------------------------- */
function onSquareClick(e) {
  if (!gameStarted) return;

  const index = parseInt(e.target.dataset.index);

  if (selectedFrom === null) {
    selectedFrom = index;
    showValidMoves(index);
  } else if (validMoves.includes(index)) {
    makeMove(selectedFrom, index);
    selectedFrom = null;
    validMoves = [];
    clearDots();
  } else {
    selectedFrom = null;
    validMoves = [];
    clearDots();
  }
}

/* -----------------------------------------------------------
   COORD HELPERS
----------------------------------------------------------- */
function idxToAlg(i) {
  const file = String.fromCharCode(97 + (i % 8));
  const rank = Math.floor(i / 8) + 1;
  return file + rank;
}

function algToIdx(alg) {
  const f = alg.charCodeAt(0) - 97;
  const r = parseInt(alg[1], 10) - 1;
  return f + r * 8;
}

/* -----------------------------------------------------------
   VALID MOVES
----------------------------------------------------------- */
async function showValidMoves(fromIndex) {
  const res = await fetch(`/valid_moves/${idxToAlg(fromIndex)}`);
  const data = await res.json();

  validMoves = (data.moves || []).map((m) => algToIdx(m.slice(2, 4)));
  drawDots(validMoves);
}

/* -----------------------------------------------------------
   DOT DRAWING
----------------------------------------------------------- */
function drawDots(list) {
  clearDots();
  list.forEach((i) => {
    const dot = document.createElement("div");
    dot.className = "dot";
    board[i].appendChild(dot);
  });
}

function clearDots() {
  document.querySelectorAll(".dot").forEach((d) => d.remove());
}

/* -----------------------------------------------------------
   MAKE MOVE
----------------------------------------------------------- */
async function makeMove(from, to) {
  const res = await fetch("/player_move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      move: idxToAlg(from) + idxToAlg(to),
      difficulty,
      player: playerName,
    }),
  });

  const data = await res.json();
  drawBoard();

  if (data.status === "finished") {
    alert("Game Over!\n" + data.result);
    gameStarted = false;

    // 🔓 Unlock difficulty here too
    document.getElementById("difficulty").disabled = false;

    loadLogs();
  }
}

/* -----------------------------------------------------------
   SIDEBAR LOGS
----------------------------------------------------------- */
async function loadLogs() {
  const box = document.getElementById("logContent");
  const res = await fetch("/logs");
  const text = await res.text();
  box.textContent = text || "No game logs yet.";
  box.scrollTop = box.scrollHeight;
}
