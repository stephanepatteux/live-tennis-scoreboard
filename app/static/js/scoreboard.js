(function () {
  "use strict";

  var board = document.getElementById("scoreboard");
  if (!board) return;

  var scoreUrl = board.dataset.scoreUrl;
  var pointUrl = board.dataset.pointUrl;
  var resetUrl = board.dataset.resetUrl;
  var banner = document.getElementById("banner");

  function render(state) {
    var rows = board.querySelectorAll("tbody tr[data-player]");
    rows.forEach(function (row) {
      var idx = parseInt(row.dataset.player, 10);
      var player = state.players[idx];
      if (!player) return;

      var gamesCell = row.querySelector('[data-field="games"]');
      var pointCell = row.querySelector('[data-field="point"]');
      if (gamesCell) gamesCell.textContent = player.games;
      if (pointCell && pointCell.textContent !== String(player.point)) {
        pointCell.textContent = player.point;
        pointCell.classList.remove("flash");
        // Force reflow so the animation restarts on each change.
        void pointCell.offsetWidth;
        pointCell.classList.add("flash");
      }
    });

    var scoreButtons = board.querySelectorAll(".score-btn");
    if (state.winner) {
      banner.hidden = false;
      banner.textContent = "🏆 " + state.winner + " wins the match!";
      scoreButtons.forEach(function (b) { b.disabled = true; });
    } else {
      banner.hidden = true;
      scoreButtons.forEach(function (b) { b.disabled = false; });
      if (state.in_tiebreak) {
        banner.hidden = false;
        banner.textContent = "Tiebreak in progress";
      } else if (state.deuce) {
        banner.hidden = false;
        banner.textContent = "Deuce";
      }
    }
  }

  function postJson(url, body) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : "{}",
    }).then(function (r) { return r.json(); });
  }

  board.querySelectorAll(".score-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      postJson(pointUrl, { player: parseInt(btn.dataset.player, 10) }).then(render);
    });
  });

  var resetBtn = document.getElementById("reset-btn");
  if (resetBtn) {
    resetBtn.addEventListener("click", function () {
      postJson(resetUrl).then(function (state) {
        // A completed-set column may have appeared/disappeared, so reload to
        // rebuild the table structure, then continue live updates.
        window.location.reload();
      });
    });
  }

  // Keep the board live even if scored from another tab/device.
  function poll() {
    fetch(scoreUrl)
      .then(function (r) { return r.json(); })
      .then(render)
      .catch(function () { /* transient network error; try again next tick */ });
  }
  setInterval(poll, 2000);
})();
