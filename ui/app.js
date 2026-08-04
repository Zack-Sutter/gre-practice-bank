const WEIGHTS = [80, 10, 5, 3, 1, 1];

const state = {
  questions: [],
  ratings: {},
  times: {},
  stats: null,
  history: [],
  historyIndex: -1,
  revealed: false,
  timerElapsedMs: 0,
  timerStartMs: null,
  timerRunning: false,
  timerStopped: false,
  timerInterval: null,
  frozenSeconds: 0,
};

const $ = (id) => document.getElementById(id);

function showError(msg) {
  const el = $("error");
  el.textContent = msg;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 5000);
}

function formatTime(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds));
  const mins = Math.floor(s / 60);
  const secs = s % 60;
  return `${mins}:${String(secs).padStart(2, "0")}`;
}

function formatStars(rating) {
  return "★".repeat(rating) + "☆".repeat(5 - rating);
}

function currentTimerSeconds() {
  if (state.timerRunning && state.timerStartMs !== null) {
    return Math.floor((state.timerElapsedMs + (Date.now() - state.timerStartMs)) / 1000);
  }
  return Math.floor(state.timerElapsedMs / 1000);
}

function updateTimerDisplay() {
  $("timer-display").textContent = formatTime(currentTimerSeconds());
}

function setTimerToggleIcon(mode) {
  const btn = $("timer-toggle");
  const pauseIcon = btn.querySelector(".timer-glyph-pause");
  const playIcon = btn.querySelector(".timer-glyph-play");
  if (mode === "pause") {
    pauseIcon.classList.remove("hidden");
    playIcon.classList.add("hidden");
    btn.setAttribute("aria-label", "Pause");
  } else if (mode === "play") {
    pauseIcon.classList.add("hidden");
    playIcon.classList.remove("hidden");
    btn.setAttribute("aria-label", "Start");
  } else {
    pauseIcon.classList.remove("hidden");
    playIcon.classList.add("hidden");
    btn.setAttribute("aria-label", "Stopped");
  }
}

function startTimer() {
  if (state.timerStopped) return;
  if (state.timerRunning) return;
  state.timerRunning = true;
  state.timerStartMs = Date.now();
  setTimerToggleIcon("pause");
  if (!state.timerInterval) {
    state.timerInterval = setInterval(updateTimerDisplay, 200);
  }
}

function pauseTimer() {
  if (!state.timerRunning) return;
  state.timerElapsedMs += Date.now() - state.timerStartMs;
  state.timerRunning = false;
  state.timerStartMs = null;
  setTimerToggleIcon("play");
  updateTimerDisplay();
}

function stopTimer() {
  if (state.timerRunning) {
    state.timerElapsedMs += Date.now() - state.timerStartMs;
    state.timerRunning = false;
    state.timerStartMs = null;
  }
  state.timerStopped = true;
  state.frozenSeconds = Math.floor(state.timerElapsedMs / 1000);
  clearInterval(state.timerInterval);
  state.timerInterval = null;
  $("timer-toggle").disabled = true;
  setTimerToggleIcon("stopped");
  updateTimerDisplay();
}

function resetTimer() {
  clearInterval(state.timerInterval);
  state.timerElapsedMs = 0;
  state.timerStartMs = null;
  state.timerRunning = false;
  state.timerStopped = false;
  state.timerInterval = null;
  state.frozenSeconds = 0;
  $("timer-toggle").disabled = false;
  setTimerToggleIcon("pause");
  updateTimerDisplay();
  startTimer();
}

function toggleTimer() {
  if (state.timerStopped) return;
  if (state.timerRunning) {
    pauseTimer();
  } else {
    startTimer();
  }
}

function questionById(postId) {
  return state.questions.find((q) => q.post_id === postId);
}

function bucketQuestions(excludeId) {
  const buckets = Array.from({ length: 6 }, () => []);
  for (const q of state.questions) {
    if (q.post_id === excludeId) continue;
    const rating = state.ratings[q.post_id] ?? 0;
    buckets[Math.max(0, Math.min(5, rating))].push(q);
  }
  return buckets;
}

function pickWeighted(excludeId) {
  const buckets = bucketQuestions(excludeId);
  const available = buckets.flat();
  if (available.length === 0) return null;

  let roll = Math.floor(Math.random() * 100);
  for (let tier = 0; tier < 6; tier++) {
    roll -= WEIGHTS[tier];
    if (roll < 0) {
      for (let t = tier; t < 6; t++) {
        if (buckets[t].length > 0) {
          return buckets[t][Math.floor(Math.random() * buckets[t].length)];
        }
      }
      break;
    }
  }
  return available[Math.floor(Math.random() * available.length)];
}

function computeAverageTime(stats) {
  if (stats.average_time != null && !Number.isNaN(stats.average_time)) {
    return stats.average_time;
  }
  const ratings = stats.ratings || {};
  const times = stats.times || {};
  const ids = Object.keys(ratings);
  if (!ids.length) return 0;
  const sum = ids.reduce((acc, id) => acc + (times[id] ?? 0), 0);
  return sum / ids.length;
}

function renderStats(stats) {
  state.stats = stats;
  state.ratings = stats.ratings;
  state.times = stats.times || {};

  const counts = Array.from({ length: 6 }, (_, tier) => stats.counts[String(tier)] || 0);
  const total = counts.reduce((a, b) => a + b, 0);
  const maxCount = Math.max(...counts, 1);
  const bar = $("dist-bar");
  bar.innerHTML = "";

  for (let tier = 0; tier < 6; tier++) {
    const count = counts[tier];
    const pct = total ? (count / maxCount) * 100 : 0;

    const col = document.createElement("div");
    col.className = "dist-col";

    const track = document.createElement("div");
    track.className = "dist-col-track";

    const fill = document.createElement("div");
    fill.className = `dist-col-bar tier-${tier}`;
    fill.style.height = `${pct}%`;

    const label = document.createElement("span");
    label.className = "dist-col-label";
    label.textContent = String(tier);

    track.appendChild(fill);
    col.appendChild(track);
    col.appendChild(label);
    bar.appendChild(col);
  }

  $("avg-value").textContent = stats.average.toFixed(1);
  $("avg-time-value").textContent = formatTime(computeAverageTime(stats));
}

function renderPriorStats(postId) {
  const rating = state.ratings[postId] ?? 0;
  const seconds = state.times[postId];
  const el = $("prior-stats");

  if (rating > 0 && seconds !== undefined) {
    el.innerHTML = `Last: <span class="prior-rating">${formatStars(rating)}</span> · ${formatTime(seconds)}`;
    el.classList.remove("hidden");
  } else {
    el.textContent = "";
    el.classList.add("hidden");
  }
}

async function loadData() {
  const [qRes, rRes] = await Promise.all([
    fetch("/api/questions"),
    fetch("/api/ratings"),
  ]);

  if (!qRes.ok) throw new Error("failed to load questions");
  if (!rRes.ok) {
    const err = await rRes.json().catch(() => ({}));
    throw new Error(err.error || "failed to load ratings");
  }

  const qData = await qRes.json();
  const rData = await rRes.json();

  state.questions = qData.questions;
  renderStats(rData);

  if (state.questions.length === 0) {
    throw new Error("no questions available");
  }
}

function resetRevealState() {
  state.revealed = false;
  $("answer").classList.add("hidden");
  $("reveal-btn").classList.remove("hidden");
  $("stars").classList.add("hidden");
}

async function renderQuestion(postId) {
  const q = questionById(postId);
  if (!q) return;

  resetRevealState();
  renderPriorStats(postId);
  resetTimer();

  $("question-body").innerHTML = q.body_html;
  $("source-link").href = q.source_url;
  $("answer").textContent = q.official_answer;

  $("prev-btn").disabled = state.historyIndex <= 0;

  if (window.MathJax?.typesetClear) {
    MathJax.typesetClear([$("question-body")]);
  }
  if (window.MathJax?.typesetPromise) {
    await MathJax.typesetPromise([$("question-body")]);
  }
}

function goToQuestion(postId, { pushHistory = true } = {}) {
  if (pushHistory) {
    if (state.historyIndex < state.history.length - 1) {
      state.history = state.history.slice(0, state.historyIndex + 1);
    }
    state.history.push(postId);
    state.historyIndex = state.history.length - 1;
  }
  renderQuestion(postId);
}

function goNext() {
  const current = state.history[state.historyIndex];
  const next = pickWeighted(current);
  if (!next) return;
  goToQuestion(next.post_id);
}

function goPrev() {
  if (state.historyIndex <= 0) return;
  state.historyIndex -= 1;
  renderQuestion(state.history[state.historyIndex]);
}

async function rate(rating) {
  const postId = state.history[state.historyIndex];
  const seconds = state.frozenSeconds || Math.floor(state.timerElapsedMs / 1000);

  const res = await fetch("/api/ratings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ post_id: postId, rating, seconds }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    showError(err.error || "failed to save rating");
    return;
  }

  renderStats(await res.json());
  goNext();
}

function setupStars() {
  const stars = $("stars");
  const buttons = stars.querySelectorAll(".star");

  buttons.forEach((btn) => {
    const rating = Number(btn.dataset.rating);

    btn.addEventListener("mouseenter", () => {
      buttons.forEach((b) => {
        b.classList.toggle("hover", Number(b.dataset.rating) <= rating);
      });
    });

    btn.addEventListener("click", () => rate(rating));
  });

  stars.addEventListener("mouseleave", () => {
    buttons.forEach((b) => b.classList.remove("hover"));
  });
}

async function init() {
  try {
    await loadData();
    setupStars();

    const first = pickWeighted(null) || state.questions[0];
    goToQuestion(first.post_id);

    $("reveal-btn").addEventListener("click", () => {
      state.revealed = true;
      stopTimer();
      $("answer").classList.remove("hidden");
      $("reveal-btn").classList.add("hidden");
      $("stars").classList.remove("hidden");
    });

    $("timer-toggle").addEventListener("click", toggleTimer);
    $("next-btn").addEventListener("click", goNext);
    $("prev-btn").addEventListener("click", goPrev);
  } catch (err) {
    showError(err.message);
  }
}

init();
