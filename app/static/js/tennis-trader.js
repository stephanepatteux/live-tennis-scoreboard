(function () {
  "use strict";

  var API = "/api/tennis/live";
  var REFRESH_MS = 8000;
  var FLASH_MS = 1600;

  var KEYS = {
    tour: "ttb-tour",
    strategies: "ttb-strategies",
    pinned: "ttb-pinned",
    surfaces: "ttb-surfaces",
    singles: "ttb-singles",
    watchOnly: "ttb-watch-only",
    compact: "ttb-compact",
    sound: "ttb-sound",
    sort: "ttb-sort",
    watchlist: "ttb-watchlist",
    odds: "ttb-odds",
    more: "ttb-more-open",
  };

  var page = document.getElementById("ttb-page");
  var board = document.getElementById("ttb-board");
  var statusEl = document.getElementById("ttb-status");
  var refreshBtn = document.getElementById("ttb-refresh");
  var popoutBtn = document.getElementById("ttb-popout");
  var filtersEl = document.getElementById("ttb-filters");
  var searchEl = document.getElementById("ttb-search");
  var sortEl = document.getElementById("ttb-sort");
  var moreEl = document.getElementById("ttb-more");
  var moreBtn = document.getElementById("ttb-more-btn");
  var toastsEl = document.getElementById("ttb-toasts");
  var isEmbed =
    typeof location !== "undefined" &&
    /(?:^|[?&])embed=1(?:&|$)/.test(location.search || "");

  var timer = null;
  var clockTimer = null;
  var inFlight = false;
  var pendingForce = false;
  var lastMatches = [];
  var lastMeta = { updated_at: null, cached: false, alert_count: 0 };
  var lastPaintFp = "";
  var prevAlertMap = {};
  var flashUntil = {};
  var scoreSeen = {};
  var updatedAt = {};
  var reduceMotion =
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var tour = "all";
  var strategies = [];
  var pinned = [];
  var surfaces = [];
  var singlesOnly = false;
  var watchOnly = false;
  var compact = false;
  var soundOn = false;
  var moreOpen = false;
  var sortMode = "alerts";
  var searchQ = "";
  var watchlist = [];
  var oddsByMatch = {};

  function readJson(key, fallback) {
    try {
      var raw = localStorage.getItem(key);
      if (raw == null) return fallback;
      return JSON.parse(raw);
    } catch (e) {
      return fallback;
    }
  }

  function migrateTour(value) {
    if (value === "men") return "atp";
    if (value === "women") return "wta";
    if (value === "atp" || value === "wta" || value === "all") return value;
    return "all";
  }

  try {
    var storedTour = localStorage.getItem(KEYS.tour) || localStorage.getItem("ttb-gender");
    tour = migrateTour(storedTour || "all");
    strategies = readJson(KEYS.strategies, []);
    pinned = readJson(KEYS.pinned, []);
    surfaces = readJson(KEYS.surfaces, []);
    singlesOnly = localStorage.getItem(KEYS.singles) === "1";
    watchOnly = localStorage.getItem(KEYS.watchOnly) === "1";
    compact = localStorage.getItem(KEYS.compact) === "1";
    soundOn = localStorage.getItem(KEYS.sound) === "1";
    moreOpen = localStorage.getItem(KEYS.more) === "1";
    sortMode = localStorage.getItem(KEYS.sort) || "alerts";
    watchlist = readJson(KEYS.watchlist, []).map(String);
    oddsByMatch = readJson(KEYS.odds, {}) || {};
    if (!Array.isArray(strategies)) strategies = [];
    if (!Array.isArray(pinned)) pinned = [];
    if (!Array.isArray(surfaces)) surfaces = [];
    if (!Array.isArray(watchlist)) watchlist = [];
  } catch (e) {}

  if (isEmbed) {
    document.documentElement.classList.add("ttb-embed");
    if (document.body) document.body.classList.add("ttb-embed");
    if (page) page.classList.add("ttb-page--embed");
    // Second-monitor popup defaults to compact unless the user already turned it on.
    if (!compact) compact = true;
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function savePrefs() {
    try {
      localStorage.setItem(KEYS.tour, tour);
      localStorage.setItem(KEYS.strategies, JSON.stringify(strategies));
      localStorage.setItem(KEYS.pinned, JSON.stringify(pinned));
      localStorage.setItem(KEYS.surfaces, JSON.stringify(surfaces));
      localStorage.setItem(KEYS.singles, singlesOnly ? "1" : "0");
      localStorage.setItem(KEYS.watchOnly, watchOnly ? "1" : "0");
      localStorage.setItem(KEYS.compact, compact ? "1" : "0");
      localStorage.setItem(KEYS.sound, soundOn ? "1" : "0");
      localStorage.setItem(KEYS.more, moreOpen ? "1" : "0");
      localStorage.setItem(KEYS.sort, sortMode);
      localStorage.setItem(KEYS.watchlist, JSON.stringify(watchlist));
      localStorage.setItem(KEYS.odds, JSON.stringify(oddsByMatch));
    } catch (e) {}
  }

  function setChip(btn, on) {
    btn.classList.toggle("is-active", on);
    btn.setAttribute("aria-pressed", on ? "true" : "false");
  }

  function syncMoreUi() {
    if (moreEl) {
      if (moreOpen) moreEl.removeAttribute("hidden");
      else moreEl.setAttribute("hidden", "");
    }
    if (moreBtn) {
      setChip(moreBtn, moreOpen);
      moreBtn.setAttribute("aria-expanded", moreOpen ? "true" : "false");
      var n =
        strategies.length +
        pinned.length +
        surfaces.length +
        (singlesOnly ? 1 : 0) +
        (watchOnly ? 1 : 0) +
        (soundOn ? 1 : 0);
      moreBtn.textContent = n ? "More filters (" + n + ")" : "More filters";
    }
  }

  function syncChipUi() {
    if (!filtersEl) return;
    filtersEl.querySelectorAll("[data-tour]").forEach(function (btn) {
      setChip(btn, btn.getAttribute("data-tour") === tour);
    });
    filtersEl.querySelectorAll("[data-strategy]").forEach(function (btn) {
      setChip(btn, strategies.indexOf(btn.getAttribute("data-strategy")) !== -1);
    });
    filtersEl.querySelectorAll("[data-pin]").forEach(function (btn) {
      setChip(btn, pinned.indexOf(btn.getAttribute("data-pin")) !== -1);
    });
    filtersEl.querySelectorAll("[data-surface]").forEach(function (btn) {
      setChip(btn, surfaces.indexOf(btn.getAttribute("data-surface")) !== -1);
    });
    filtersEl.querySelectorAll("[data-toggle]").forEach(function (btn) {
      var t = btn.getAttribute("data-toggle");
      if (t === "more" || t === "clear") return;
      var on =
        (t === "singles" && singlesOnly) ||
        (t === "watchlist" && watchOnly) ||
        (t === "compact" && compact) ||
        (t === "sound" && soundOn);
      setChip(btn, on);
    });
    if (sortEl) sortEl.value = sortMode;
    if (page) page.classList.toggle("ttb-page--compact", compact);
    syncMoreUi();
  }

  function matchTour(m) {
    var t = m.tour || m.gender || "unknown";
    if (t === "men") return "atp";
    if (t === "women") return "wta";
    return t;
  }

  function scoreFingerprint(m) {
    return [
      m.sets_p1,
      m.sets_p2,
      m.games_p1,
      m.games_p2,
      m.points_p1,
      m.points_p2,
      m.server,
      m.is_tiebreak ? 1 : 0,
      (m.alerts || []).join(","),
      m.win_prob_p1,
    ].join("|");
  }

  function trackScoreChanges(matches) {
    var now = Date.now();
    matches.forEach(function (m) {
      var id = String(m.id);
      var fp = scoreFingerprint(m);
      if (scoreSeen[id] && scoreSeen[id] !== fp) {
        updatedAt[id] = now;
      }
      if (!scoreSeen[id]) {
        updatedAt[id] = updatedAt[id] || now;
      }
      scoreSeen[id] = fp;
    });
  }

  function risingEdgeAlerts(matches) {
    var now = Date.now();
    var newly = [];
    matches.forEach(function (m) {
      var id = String(m.id);
      var alerts = m.alerts || [];
      var prev = prevAlertMap[id] || [];
      var isNew = alerts.some(function (a) {
        return prev.indexOf(a) === -1;
      });
      if (isNew && alerts.length) {
        flashUntil[id] = now + FLASH_MS;
        newly.push(m);
      }
      prevAlertMap[id] = alerts.slice();
    });
    if (newly.length) {
      if (soundOn && !reduceMotion) playBallHit();
      showAlertToasts(newly);
    }
    return newly;
  }

  function showAlertToasts(matches) {
    if (!toastsEl) return;
    matches.slice(0, 3).forEach(function (m) {
      var label = m.alert_label || (m.alerts && m.alerts[0]) || "Alert";
      var el = document.createElement("div");
      el.className = "ttb-toast" + (reduceMotion ? "" : " ttb-toast--anim");
      el.innerHTML =
        "<strong>" +
        esc(label) +
        "</strong> · " +
        esc(m.p1) +
        " vs " +
        esc(m.p2);
      toastsEl.appendChild(el);
      setTimeout(function () {
        if (el.parentNode) el.parentNode.removeChild(el);
      }, 4200);
    });
  }

  function clearFilters() {
    tour = "all";
    strategies = [];
    pinned = [];
    surfaces = [];
    singlesOnly = false;
    watchOnly = false;
    searchQ = "";
    if (searchEl) searchEl.value = "";
    sortMode = "alerts";
    savePrefs();
    syncChipUi();
    paint(true);
  }

  function playBallHit() {
    try {
      if (!playBallHit._src) {
        playBallHit._src = "/audio/tennis-hit.wav";
      }
      var a = new Audio(playBallHit._src);
      a.preload = "auto";
      a.volume = 0.75;
      var played = a.play();
      if (played && played.catch) {
        played.catch(function () {
          playBallHitSynth();
        });
      }
    } catch (e) {
      playBallHitSynth();
    }
  }

  function playBallHitSynth() {
    try {
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      var ctx = playBallHit._ctx || new Ctx();
      playBallHit._ctx = ctx;
      if (ctx.state === "suspended" && ctx.resume) ctx.resume();
      var t0 = ctx.currentTime;
      function tone(freq0, freq1, type, gain0, dur, tau) {
        var o = ctx.createOscillator();
        var g = ctx.createGain();
        o.type = type;
        o.frequency.setValueAtTime(freq0, t0);
        o.frequency.exponentialRampToValueAtTime(Math.max(40, freq1), t0 + dur);
        g.gain.setValueAtTime(gain0, t0);
        g.gain.exponentialRampToValueAtTime(0.0001, t0 + tau);
        o.connect(g);
        g.connect(ctx.destination);
        o.start(t0);
        o.stop(t0 + dur);
      }
      tone(340, 250, "sine", 0.2, 0.12, 0.1);
      tone(165, 110, "sine", 0.1, 0.09, 0.07);
      tone(490, 420, "sine", 0.07, 0.1, 0.08);
      tone(1950, 900, "triangle", 0.05, 0.04, 0.03);
    } catch (e) {}
  }

  function agoLabel(id) {
    var ts = updatedAt[String(id)];
    if (!ts) return "";
    var sec = Math.max(0, Math.round((Date.now() - ts) / 1000));
    if (sec < 3) return "just now";
    if (sec < 60) return sec + "s ago";
    return Math.floor(sec / 60) + "m ago";
  }

  function impliedFromDecimal(odds) {
    var n = parseFloat(String(odds).replace(",", "."));
    if (!isFinite(n) || n <= 1) return null;
    return 100 / n;
  }

  function edgeHtml(m) {
    var stored = oddsByMatch[String(m.id)] || "";
    var model = m.win_prob_p1;
    var implied = impliedFromDecimal(stored);
    var edgeBit = '<span class="ttb-edge-out">Paste P1 decimal odds</span>';
    if (implied != null && model != null) {
      var edge = model - implied;
      var cls = edge >= 0 ? "ttb-edge-pos" : "ttb-edge-neg";
      edgeBit =
        '<span class="' +
        cls +
        '">Model ' +
        Number(model).toFixed(1) +
        "% · mkt " +
        implied.toFixed(1) +
        "% · edge " +
        (edge >= 0 ? "+" : "") +
        edge.toFixed(1) +
        "pp</span>";
    } else if (stored) {
      edgeBit = '<span class="ttb-edge-out">Need model % + odds &gt; 1</span>';
    }
    return (
      '<div class="ttb-edge">' +
      '<label class="ttb-edge-label">P1 odds <input class="ttb-odds" data-odds-id="' +
      esc(m.id) +
      '" type="text" inputmode="decimal" placeholder="e.g. 1.85" value="' +
      esc(stored) +
      '" /></label>' +
      edgeBit +
      "</div>"
    );
  }

  var ALERT_LABELS = {
    "0-40": "0–40",
    "15-40": "15–40",
    "30-40": "30–40",
    "break-point": "BP",
    "ad-break": "AD BP",
    deuce: "Deuce",
    tiebreak: "TB",
  };

  function alertPills(m) {
    var alerts = m.alerts || [];
    var show = alerts.filter(function (code) {
      return code !== "break-point" || alerts.length === 1;
    });
    if (!show.length && alerts.length) show = alerts;
    return show
      .map(function (code) {
        var label = ALERT_LABELS[code] || code;
        var cls =
          code === "0-40" || code === "ad-break"
            ? "ttb-alert-pill ttb-alert-pill--hot"
            : "ttb-alert-pill";
        return '<span class="' + cls + '">' + esc(label) + "</span>";
      })
      .join("");
  }

  function serveCell(server, n) {
    return server === n ? '<span class="ttb-serve-dot" title="Serving"></span>' : "";
  }

  function badge(server, n) {
    return server === n ? '<span class="ttb-badge">serving</span>' : "";
  }

  function winProb(m) {
    if (m.win_prob_p1 == null) return { p1: "—", p2: "—" };
    var p1 = Number(m.win_prob_p1);
    if (isNaN(p1)) return { p1: "—", p2: "—" };
    return { p1: p1.toFixed(1) + "%", p2: (100 - p1).toFixed(1) + "%" };
  }

  function isWatched(id) {
    return watchlist.indexOf(String(id)) !== -1;
  }

  function toggleWatch(id) {
    id = String(id);
    var idx = watchlist.indexOf(id);
    if (idx === -1) watchlist.push(id);
    else watchlist.splice(idx, 1);
    savePrefs();
    paint(true);
  }

  function passesStrategy(m) {
    var alerts = m.alerts || [];
    if (!strategies.length) return true;
    var hit = strategies.some(function (s) {
      return alerts.indexOf(s) !== -1;
    });
    if (hit) return true;
    if (!pinned.length) return false;
    return pinned.some(function (s) {
      return alerts.indexOf(s) !== -1;
    });
  }

  function filterMatches(matches) {
    var q = searchQ.trim().toLowerCase();
    return matches.filter(function (m) {
      var mt = matchTour(m);
      if (tour === "atp" && mt !== "atp") return false;
      if (tour === "wta" && mt !== "wta") return false;
      if (singlesOnly && m.is_doubles) return false;
      if (watchOnly && !isWatched(m.id)) return false;
      if (surfaces.length) {
        var s = (m.surface || "").toLowerCase();
        if (surfaces.indexOf(s) === -1) return false;
      }
      if (!passesStrategy(m)) return false;
      if (q) {
        var blob = [m.tournament, m.p1, m.p2, m.surface, mt, m.format]
          .join(" ")
          .toLowerCase();
        if (blob.indexOf(q) === -1) return false;
      }
      return true;
    });
  }

  function sortMatches(matches) {
    var list = matches.slice();
    if (sortMode === "alpha") {
      list.sort(function (a, b) {
        return String(a.p1).localeCompare(String(b.p1));
      });
    } else if (sortMode === "model") {
      list.sort(function (a, b) {
        var ae = modelGap(a);
        var be = modelGap(b);
        return be - ae;
      });
    } else if (sortMode === "updated") {
      list.sort(function (a, b) {
        return (updatedAt[String(b.id)] || 0) - (updatedAt[String(a.id)] || 0);
      });
    } else {
      list.sort(function (a, b) {
        var wa = isWatched(a.id) ? 1 : 0;
        var wb = isWatched(b.id) ? 1 : 0;
        if (wb !== wa) return wb - wa;
        return (b.alert_priority || 0) - (a.alert_priority || 0);
      });
    }
    return list;
  }

  function modelGap(m) {
    var implied = impliedFromDecimal(oddsByMatch[String(m.id)]);
    if (implied == null || m.win_prob_p1 == null) return -999;
    return Math.abs(Number(m.win_prob_p1) - implied);
  }

  function renderMatch(m) {
    var wp = winProb(m);
    var hot = (m.alert_priority || 0) > 0;
    var id = String(m.id);
    var flashing = !reduceMotion && (flashUntil[id] || 0) > Date.now();
    var watched = isWatched(id);
    var tourBits = [];
    if (m.tournament) tourBits.push(esc(m.tournament));
    var mt = matchTour(m);
    if (mt === "atp" || mt === "wta") tourBits.push(esc(mt.toUpperCase()));
    if (m.surface) tourBits.push(esc(m.surface));
    if (m.is_doubles) tourBits.push("doubles");
    if (m.format) tourBits.push(esc(m.format));
    var ago = agoLabel(id);
    var head =
      '<div class="ttb-card-top">' +
      '<div class="ttb-tour">' +
      (tourBits.length ? tourBits.join(" · ") : "Live match") +
      alertPills(m) +
      (ago ? '<span class="ttb-ago" data-ago-id="' + esc(id) + '">· ' + esc(ago) + "</span>" : "") +
      "</div>" +
      '<button type="button" class="ttb-star' +
      (watched ? " is-on" : "") +
      '" data-star-id="' +
      esc(id) +
      '" title="' +
      (watched ? "Remove from My matches" : "Add to My matches") +
      '" aria-label="Watch">' +
      (watched ? "★" : "☆") +
      "</button></div>";

    var cue = "";
    if (m.alert_label) {
      cue =
        '<div class="ttb-alert-cue">Score watch · <strong>' +
        esc(m.alert_label) +
        "</strong> — not a tip</div>";
    }

    return (
      '<article class="ttb-match' +
      (hot ? " ttb-match--alert" : "") +
      (m.alert_priority >= 4 ? " ttb-match--alert-hot" : "") +
      (flashing ? " ttb-match--flash" : "") +
      (watched ? " ttb-match--watched" : "") +
      '" data-match-id="' +
      esc(id) +
      '">' +
      head +
      '<div class="ttb-cols"><div>Players</div><div>Sets</div><div>Games</div><div>Points</div><div>Model</div><div>Serve</div></div>' +
      '<div class="ttb-row"><div class="ttb-name">' +
      esc(m.p1) +
      badge(m.server, 1) +
      '</div><div class="ttb-score">' +
      esc(m.sets_p1) +
      '</div><div class="ttb-score">' +
      esc(m.games_p1) +
      '</div><div class="ttb-score">' +
      esc(m.points_p1) +
      '</div><div class="ttb-score">' +
      esc(wp.p1) +
      '</div><div class="ttb-serve-empty">' +
      serveCell(m.server, 1) +
      "</div></div>" +
      '<div class="ttb-row"><div class="ttb-name">' +
      esc(m.p2) +
      badge(m.server, 2) +
      '</div><div class="ttb-score">' +
      esc(m.sets_p2) +
      '</div><div class="ttb-score">' +
      esc(m.games_p2) +
      '</div><div class="ttb-score">' +
      esc(m.points_p2) +
      '</div><div class="ttb-score">' +
      esc(wp.p2) +
      '</div><div class="ttb-serve-empty">' +
      serveCell(m.server, 2) +
      "</div></div>" +
      (m.set_history
        ? '<div class="ttb-history">Sets: ' +
          esc(m.set_history) +
          (m.is_tiebreak ? " · tiebreak" : "") +
          "</div>"
        : "") +
      cue +
      edgeHtml(m) +
      "</article>"
    );
  }

  function setStatus(text) {
    if (statusEl) statusEl.textContent = text;
  }

  function listFingerprint(matches) {
    return (
      matches
        .map(function (m) {
          return (
            m.id +
            ":" +
            scoreFingerprint(m) +
            ":" +
            (isWatched(m.id) ? 1 : 0) +
            ":" +
            (oddsByMatch[String(m.id)] || "") +
            ":" +
            ((flashUntil[String(m.id)] || 0) > Date.now() ? 1 : 0)
          );
        })
        .join(";") +
      "|" +
      tour +
      "|" +
      strategies.join(",") +
      "|" +
      pinned.join(",") +
      "|" +
      surfaces.join(",") +
      "|" +
      singlesOnly +
      "|" +
      watchOnly +
      "|" +
      compact +
      "|" +
      sortMode +
      "|" +
      searchQ
    );
  }

  function updateAgoLabels() {
    if (!board) return;
    board.querySelectorAll("[data-ago-id]").forEach(function (el) {
      var id = el.getAttribute("data-ago-id");
      var label = agoLabel(id);
      el.textContent = label ? "· " + label : "";
    });
  }

  function paint(force) {
    if (!board) return;
    var matches = sortMatches(filterMatches(lastMatches));
    var fp = listFingerprint(matches);
    var active = document.activeElement;
    var activeOddsId =
      active && active.classList && active.classList.contains("ttb-odds")
        ? active.getAttribute("data-odds-id")
        : null;
    var activeOddsVal = activeOddsId != null ? active.value : null;
    var activeOddsPos =
      activeOddsId != null && typeof active.selectionStart === "number"
        ? active.selectionStart
        : null;

    if (!force && fp === lastPaintFp) {
      updateAgoLabels();
      return;
    }
    lastPaintFp = fp;

    if (!lastMatches.length) {
      board.innerHTML =
        '<div class="ttb-empty">No live matches right now. Check back when tennis is on.</div>';
    } else if (!matches.length) {
      board.innerHTML =
        '<div class="ttb-empty">No matches match your filters. Try All tour, clear alert chips, or turn off My matches.</div>';
    } else {
      board.innerHTML = matches.map(renderMatch).join("");
    }
    board.setAttribute("aria-busy", "false");

    if (activeOddsId != null) {
      var input = board.querySelector('.ttb-odds[data-odds-id="' + activeOddsId + '"]');
      if (input) {
        input.focus();
        if (activeOddsVal != null) input.value = activeOddsVal;
        if (activeOddsPos != null) {
          try {
            input.setSelectionRange(activeOddsPos, activeOddsPos);
          } catch (e) {}
        }
      }
    }

    var when = lastMeta.updated_at
      ? new Date(lastMeta.updated_at).toLocaleTimeString()
      : "now";
    var filterOn =
      tour !== "all" ||
      strategies.length ||
      surfaces.length ||
      singlesOnly ||
      watchOnly ||
      searchQ.trim();
    setStatus(
      lastMatches.length +
        " live in feed" +
        (filterOn ? " · showing " + matches.length + "/" + lastMatches.length : "") +
        (lastMeta.alert_count
          ? " · " + lastMeta.alert_count + " score alert" + (lastMeta.alert_count === 1 ? "" : "s")
          : "") +
        " · updated " +
        when +
        (lastMeta.cached ? " (cached)" : "") +
        " · 8s check"
    );
  }

  function load(opts) {
    opts = opts || {};
    var forceUi = !!opts.force;
    var bust = !!opts.bust;
    if (inFlight) {
      if (forceUi) pendingForce = true;
      return;
    }
    inFlight = true;
    if (forceUi && refreshBtn) {
      refreshBtn.disabled = true;
      setStatus("Refreshing…");
    }
    var url = API;
    if (bust) url += (url.indexOf("?") === -1 ? "?" : "&") + "force=1&_=" + Date.now();
    fetch(url, { credentials: "same-origin", cache: "no-store" })
      .then(function (r) {
        if (!r.ok) {
          var err = new Error("HTTP " + r.status);
          err.status = r.status;
          return r.text().then(function (body) {
            err.body = (body || "").slice(0, 200);
            throw err;
          });
        }
        return r.json();
      })
      .then(function (data) {
        lastMatches = data.matches || [];
        lastMeta = {
          updated_at: data.updated_at,
          cached: !!data.cached,
          alert_count: data.alert_count || 0,
        };
        trackScoreChanges(lastMatches);
        risingEdgeAlerts(lastMatches);
        paint(forceUi);
      })
      .catch(function (err) {
        var hint = err.message || "error";
        if (err.status === 429) {
          hint = "HTTP 429 — BotBlog board limit (not Live Tennis API)";
        }
        board.innerHTML =
          '<div class="ttb-error">Could not load the live board (' +
          esc(hint) +
          "). Retrying…</div>";
        setStatus("Connection issue — will retry");
      })
      .finally(function () {
        inFlight = false;
        if (refreshBtn) refreshBtn.disabled = false;
        if (pendingForce) {
          pendingForce = false;
          load({ force: true, bust: true });
        }
      });
  }

  function toggleInList(list, code) {
    var idx = list.indexOf(code);
    if (idx === -1) list.push(code);
    else list.splice(idx, 1);
  }

  function onFiltersClick(ev) {
    var star = ev.target.closest ? ev.target.closest("[data-star-id]") : null;
    if (star) {
      toggleWatch(star.getAttribute("data-star-id"));
      return;
    }

    var btn = ev.target.closest ? ev.target.closest("button.ttb-chip") : null;
    if (!btn || !filtersEl.contains(btn)) return;

    var tourVal = btn.getAttribute("data-tour");
    if (tourVal) {
      tour = tourVal;
      savePrefs();
      syncChipUi();
      paint(true);
      return;
    }

    var strategy = btn.getAttribute("data-strategy");
    if (strategy) {
      toggleInList(strategies, strategy);
      savePrefs();
      syncChipUi();
      paint(true);
      return;
    }

    var pin = btn.getAttribute("data-pin");
    if (pin) {
      toggleInList(pinned, pin);
      savePrefs();
      syncChipUi();
      paint(true);
      return;
    }

    var surface = btn.getAttribute("data-surface");
    if (surface) {
      toggleInList(surfaces, surface);
      savePrefs();
      syncChipUi();
      paint(true);
      return;
    }

    var toggle = btn.getAttribute("data-toggle");
    if (toggle === "more") {
      moreOpen = !moreOpen;
      savePrefs();
      syncChipUi();
      return;
    }
    if (toggle === "clear") {
      clearFilters();
      return;
    }
    if (toggle === "singles") singlesOnly = !singlesOnly;
    if (toggle === "watchlist") watchOnly = !watchOnly;
    if (toggle === "compact") compact = !compact;
    if (toggle === "sound") {
      soundOn = !soundOn;
      if (soundOn && !reduceMotion) playBallHit();
    }
    if (toggle) {
      savePrefs();
      syncChipUi();
      paint(true);
    }
  }

  function onBoardInput(ev) {
    var input = ev.target;
    if (!input.classList || !input.classList.contains("ttb-odds")) return;
    var id = input.getAttribute("data-odds-id");
    if (!id) return;
    oddsByMatch[String(id)] = input.value.trim();
    savePrefs();
    // Update edge text without full repaint when possible
    var card = input.closest(".ttb-match");
    if (!card) return;
    var m = null;
    for (var i = 0; i < lastMatches.length; i++) {
      if (String(lastMatches[i].id) === String(id)) {
        m = lastMatches[i];
        break;
      }
    }
    if (!m) return;
    var wrap = card.querySelector(".ttb-edge");
    if (wrap) {
      var tmp = document.createElement("div");
      tmp.innerHTML = edgeHtml(m);
      wrap.replaceWith(tmp.firstChild);
      var again = card.querySelector(".ttb-odds");
      if (again) {
        again.focus();
        try {
          again.setSelectionRange(again.value.length, again.value.length);
        } catch (e) {}
      }
    }
  }

  function start() {
    try {
      playBallHit._preload = new Audio("/audio/tennis-hit.wav");
      playBallHit._preload.preload = "auto";
    } catch (e) {}
    syncChipUi();
    if (filtersEl) filtersEl.addEventListener("click", onFiltersClick);
    if (board) {
      board.addEventListener("click", onFiltersClick);
      board.addEventListener("input", onBoardInput);
    }
    if (searchEl) {
      searchEl.addEventListener("input", function () {
        searchQ = searchEl.value || "";
        paint(true);
      });
    }
    if (sortEl) {
      sortEl.addEventListener("change", function () {
        sortMode = sortEl.value || "alerts";
        savePrefs();
        paint(true);
      });
    }
    load();
    if (timer) clearInterval(timer);
    timer = setInterval(load, REFRESH_MS);
    if (clockTimer) clearInterval(clockTimer);
    clockTimer = setInterval(function () {
      updateAgoLabels();
      // Clear expired flashes with a light paint
      var now = Date.now();
      var need = false;
      Object.keys(flashUntil).forEach(function (id) {
        if (flashUntil[id] && flashUntil[id] <= now) {
          delete flashUntil[id];
          need = true;
        }
      });
      if (need) paint(true);
    }, 1000);
  }

  if (refreshBtn) {
    refreshBtn.addEventListener("click", function () {
      if (soundOn && !reduceMotion) playBallHit();
      load({ force: true, bust: true });
    });
  }

  function popOutBoard() {
    var url = new URL(window.location.href);
    url.searchParams.set("embed", "1");
    var features = [
      "popup=yes",
      "noopener=yes",
      "noreferrer=yes",
      "width=1100",
      "height=900",
      "left=80",
      "top=60",
      "menubar=no",
      "toolbar=no",
      "location=yes",
      "status=no",
      "resizable=yes",
      "scrollbars=yes",
    ].join(",");
    var win = window.open(url.toString(), "ttb-board-popout", features);
    if (!win) {
      if (statusEl) {
        setStatus("Pop-out blocked — allow popups, or open this page in a new window");
      }
      return;
    }
    try {
      win.focus();
    } catch (e) {}
  }

  if (popoutBtn) {
    if (isEmbed) {
      popoutBtn.hidden = true;
    } else {
      popoutBtn.addEventListener("click", popOutBoard);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      if (isEmbed && document.body) document.body.classList.add("ttb-embed");
      start();
    });
  } else {
    if (isEmbed && document.body) document.body.classList.add("ttb-embed");
    start();
  }
})();
