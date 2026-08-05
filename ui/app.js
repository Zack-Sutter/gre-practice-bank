const WEIGHTS = [90, 5, 2, 1, 1, 1];

let mode = "quant";

const quant = {
  items: [],
  ratings: {},
  times: {},
  comments: {},
  stats: null,
  history: [],
  historyIndex: -1,
  loaded: false,
};

const vocab = {
  items: [],
  ratings: {},
  times: {},
  comments: {},
  stats: null,
  history: [],
  historyIndex: -1,
  loaded: false,
  answered: false,
  currentQuestion: null,
};

const timer = {
  elapsedMs: 0,
  startMs: null,
  running: false,
  stopped: false,
  interval: null,
  frozenSeconds: 0,
};

const $ = (id) => document.getElementById(id);

function active() {
  return mode === "quant" ? quant : vocab;
}

function itemId(item) {
  return mode === "quant" ? item.post_id : item.word;
}

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

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escapeRegex(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function etymonlineUrl(word) {
  return `https://www.etymonline.com/search?q=${encodeURIComponent(word)}`;
}

function shuffle(items) {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function currentTimerSeconds() {
  if (timer.running && timer.startMs !== null) {
    return Math.floor((timer.elapsedMs + (Date.now() - timer.startMs)) / 1000);
  }
  return Math.floor(timer.elapsedMs / 1000);
}

function updateTimerDisplay() {
  $("timer-display").textContent = formatTime(currentTimerSeconds());
}

function setTimerToggleIcon(iconMode) {
  const btn = $("timer-toggle");
  const pauseIcon = btn.querySelector(".timer-glyph-pause");
  const playIcon = btn.querySelector(".timer-glyph-play");
  if (iconMode === "pause") {
    pauseIcon.classList.remove("hidden");
    playIcon.classList.add("hidden");
    btn.setAttribute("aria-label", "Pause");
  } else if (iconMode === "play") {
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
  if (timer.stopped || timer.running) return;
  timer.running = true;
  timer.startMs = Date.now();
  setTimerToggleIcon("pause");
  if (!timer.interval) {
    timer.interval = setInterval(updateTimerDisplay, 200);
  }
}

function pauseTimer() {
  if (!timer.running) return;
  timer.elapsedMs += Date.now() - timer.startMs;
  timer.running = false;
  timer.startMs = null;
  setTimerToggleIcon("play");
  updateTimerDisplay();
}

function stopTimer() {
  if (timer.running) {
    timer.elapsedMs += Date.now() - timer.startMs;
    timer.running = false;
    timer.startMs = null;
  }
  timer.stopped = true;
  timer.frozenSeconds = Math.floor(timer.elapsedMs / 1000);
  clearInterval(timer.interval);
  timer.interval = null;
  $("timer-toggle").disabled = true;
  setTimerToggleIcon("stopped");
  updateTimerDisplay();
}

function resetTimer() {
  clearInterval(timer.interval);
  timer.elapsedMs = 0;
  timer.startMs = null;
  timer.running = false;
  timer.stopped = false;
  timer.interval = null;
  timer.frozenSeconds = 0;
  $("timer-toggle").disabled = false;
  setTimerToggleIcon("pause");
  updateTimerDisplay();
  startTimer();
}

function toggleTimer() {
  if (timer.stopped) return;
  if (timer.running) pauseTimer();
  else startTimer();
}

function itemById(id) {
  const bucket = active();
  if (mode === "quant") {
    return bucket.items.find((q) => q.post_id === id);
  }
  return bucket.items.find((w) => w.word === id);
}

function bucketItems(excludeId) {
  const bucket = active();
  const buckets = Array.from({ length: 6 }, () => []);
  for (const item of bucket.items) {
    const id = itemId(item);
    if (id === excludeId) continue;
    const rating = bucket.ratings[id] ?? 0;
    buckets[Math.max(0, Math.min(5, rating))].push(item);
  }
  return buckets;
}

function pickWeighted(excludeId) {
  const buckets = bucketItems(excludeId);
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
  const times = stats.times || {};
  const nonzero = Object.keys(times).filter((id) => (times[id] ?? 0) > 0);
  if (!nonzero.length) return 0;
  const sum = nonzero.reduce((acc, id) => acc + times[id], 0);
  return sum / nonzero.length;
}

function renderStats(stats, bucket) {
  bucket.stats = stats;
  bucket.ratings = stats.ratings;
  bucket.times = stats.times || {};
  bucket.comments = stats.comments || {};

  if (active() !== bucket) return;

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

function refreshStatsDisplay() {
  const bucket = active();
  if (bucket.stats) renderStats(bucket.stats, bucket);
}

function renderPriorStats(id) {
  const bucket = active();
  const rating = bucket.ratings[id] ?? 0;
  const seconds = bucket.times[id];
  const el = $("prior-stats");

  if (rating > 0 && seconds !== undefined) {
    el.innerHTML = `Last: <span class="prior-rating">${formatStars(rating)}</span> · ${formatTime(seconds)}`;
    el.classList.remove("hidden");
  } else {
    el.textContent = "";
    el.classList.add("hidden");
  }
}

function buildVocabQuestion(entry, allWords) {
  const word = entry.word;
  let promptHtml = null;

  if (entry.example) {
    const re = new RegExp(`\\b${escapeRegex(word)}\\w*\\b`, "i");
    const match = entry.example.match(re);
    if (match) {
      const blanked = entry.example.replace(match[0], "_____");
      const escaped = escapeHtml(blanked).replace(
        "_____",
        '<span class="question-blank">_____</span>',
      );
      promptHtml = `<p>${escaped}</p>`;
    }
  }

  if (!promptHtml) {
    promptHtml = `<p>${escapeHtml(entry.definition)}</p>`;
  }

  const pool = allWords.map((w) => w.word).filter((w) => w !== word);
  const distractorCount = Math.min(4, pool.length);
  const distractors = shuffle(pool).slice(0, distractorCount);
  const choices = shuffle([word, ...distractors]);
  const definitions = new Map(allWords.map((w) => [w.word, w.definition]));
  const choiceEntries = choices.map((choiceWord) => ({
    word: choiceWord,
    definition: definitions.get(choiceWord) || "",
  }));

  return {
    word,
    definition: entry.definition,
    promptHtml,
    choices,
    choiceEntries,
    answer: word,
  };
}

async function loadQuantData() {
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

  quant.items = qData.questions;
  quant.loaded = true;
  renderStats(rData, quant);

  if (quant.items.length === 0) {
    throw new Error("no questions available");
  }
}

async function loadVocabData() {
  const [wRes, rRes] = await Promise.all([
    fetch("/api/words"),
    fetch("/api/word-ratings"),
  ]);

  if (!wRes.ok) throw new Error("failed to load words");
  if (!rRes.ok) {
    const err = await rRes.json().catch(() => ({}));
    throw new Error(err.error || "failed to load word ratings");
  }

  const wData = await wRes.json();
  const rData = await rRes.json();

  vocab.items = wData.words;
  vocab.loaded = true;
  renderStats(rData, vocab);

  if (vocab.items.length === 0) {
    throw new Error("no words available");
  }
}

function updateModeUI() {
  const isQuant = mode === "quant";
  document.body.classList.toggle("mode-quant", isQuant);
  document.body.classList.toggle("mode-vocab", !isQuant);
  $("mode-accent").textContent = isQuant ? "quant" : "vocab";
  $("mode-title").setAttribute(
    "aria-label",
    isQuant ? "Switch to vocab practice" : "Switch to quant practice",
  );
  $("reveal-btn").classList.toggle("hidden", !isQuant);
  $("source-link").classList.toggle("hidden", !isQuant);
  document.querySelector(".reveal-bar").classList.toggle("hidden", !isQuant);
  if (!isQuant) $("answer").classList.add("hidden");
}

function resetRevealState() {
  $("answer").classList.add("hidden");
  $("stars").classList.add("hidden");
  hideCommentAside();

  if (mode === "quant") {
    $("reveal-btn").classList.remove("hidden");
    $("choices").classList.add("hidden");
    $("choices").innerHTML = "";
  } else {
    vocab.answered = false;
    vocab.currentQuestion = null;
    $("reveal-btn").classList.add("hidden");
    $("choices").classList.remove("hidden");
    $("choices").innerHTML = "";
  }
}

function renderChoices(question) {
  const container = $("choices");
  container.innerHTML = "";

  for (const { word, definition } of question.choiceEntries) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "choice-btn";
    btn.dataset.word = word;
    btn.innerHTML =
      `<span class="choice-word">${escapeHtml(word)}</span>` +
      `<span class="choice-def">${escapeHtml(definition)}</span>`;
    btn.addEventListener("click", (e) => {
      if (vocab.answered) {
        if (e.target.closest(".choice-word")) {
          window.open(etymonlineUrl(word), "_blank", "noopener,noreferrer");
        }
        return;
      }
      selectChoice(word, question);
    });
    container.appendChild(btn);
  }
}

function selectChoice(selected, question) {
  if (vocab.answered) return;
  vocab.answered = true;
  stopTimer();

  $("choices").querySelectorAll(".choice-btn").forEach((btn) => {
    btn.classList.add("revealed");
    const word = btn.dataset.word;
    if (word === question.answer) {
      btn.classList.add("correct");
    } else if (word === selected) {
      btn.classList.add("incorrect");
    }
  });

  $("stars").classList.remove("hidden");
  showCommentAside(vocab.history[vocab.historyIndex]);
}

function hideCommentAside() {
  $("comment-empty").classList.add("hidden");
  $("comment-view").classList.add("hidden");
  $("comment-edit").classList.add("hidden");
}

const COMMENT_TEXT_BASE_REM = 0.9;
const COMMENT_TEXT_MIN_REM = 0.65;
const COMMENT_TEXT_STEP_REM = 0.05;

function fitCommentText() {
  const el = $("comment-text");
  const view = $("comment-view");
  if (view.classList.contains("hidden")) return;

  const box = view.querySelector(".comment-box");
  const maxHeight = box ? box.clientHeight - 4 : $("stars").clientHeight;
  let size = COMMENT_TEXT_BASE_REM;
  el.style.fontSize = `${size}rem`;

  while (size > COMMENT_TEXT_MIN_REM) {
    if (el.scrollHeight <= maxHeight && el.scrollWidth <= el.clientWidth) {
      break;
    }
    size -= COMMENT_TEXT_STEP_REM;
    el.style.fontSize = `${size}rem`;
  }
}

function renderCommentAside(id) {
  const bucket = active();
  const text = bucket.comments[id] || "";

  $("comment-empty").classList.toggle("hidden", text.length > 0);
  $("comment-view").classList.toggle("hidden", text.length === 0);
  $("comment-edit").classList.add("hidden");

  if (text.length > 0) {
    $("comment-text").textContent = text;
    $("comment-text").style.fontSize = "";
    requestAnimationFrame(() => fitCommentText());
  }
}

function showCommentAside(id) {
  renderCommentAside(id);
}

function enterCommentEdit() {
  const bucket = active();
  const id = bucket.history[bucket.historyIndex];
  const text = bucket.comments[id] || "";

  $("comment-empty").classList.add("hidden");
  $("comment-view").classList.add("hidden");
  $("comment-edit").classList.remove("hidden");
  $("comment-input").value = text;
  $("comment-input").focus();
}

function cancelCommentEdit() {
  const bucket = active();
  renderCommentAside(bucket.history[bucket.historyIndex]);
}

async function saveComment() {
  const bucket = active();
  const id = bucket.history[bucket.historyIndex];
  const text = $("comment-input").value;
  const url = mode === "quant" ? "/api/comments" : "/api/word-comments";
  const body =
    mode === "quant" ? { post_id: id, comment: text } : { word: id, comment: text };

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    showError(err.error || "failed to save note");
    return;
  }

  renderStats(await res.json(), bucket);
  renderCommentAside(id);
}

async function renderQuantQuestion(postId) {
  const q = itemById(postId);
  if (!q) return;

  resetRevealState();
  renderPriorStats(postId);
  resetTimer();

  $("question-body").innerHTML = q.body_html;
  $("source-link").href = q.source_url;
  $("answer").textContent = q.official_answer;
  $("prev-btn").disabled = quant.historyIndex <= 0;

  if (window.MathJax?.typesetClear) {
    MathJax.typesetClear([$("question-body")]);
  }
  if (window.MathJax?.typesetPromise) {
    await MathJax.typesetPromise([$("question-body")]);
  }
}

function renderVocabQuestion(word) {
  const entry = itemById(word);
  if (!entry) return;

  resetRevealState();
  renderPriorStats(word);
  resetTimer();

  const question = buildVocabQuestion(entry, vocab.items);
  vocab.currentQuestion = question;

  $("question-body").innerHTML = question.promptHtml;
  renderChoices(question);
  $("prev-btn").disabled = vocab.historyIndex <= 0;
}

async function renderCurrent(id) {
  if (mode === "quant") {
    await renderQuantQuestion(id);
  } else {
    renderVocabQuestion(id);
  }
}

function goToItem(id, { pushHistory = true } = {}) {
  const bucket = active();
  if (pushHistory) {
    if (bucket.historyIndex < bucket.history.length - 1) {
      bucket.history = bucket.history.slice(0, bucket.historyIndex + 1);
    }
    bucket.history.push(id);
    bucket.historyIndex = bucket.history.length - 1;
  }
  renderCurrent(id);
}

function goNext() {
  const bucket = active();
  const current = bucket.history[bucket.historyIndex];
  const next = pickWeighted(current);
  if (!next) return;
  goToItem(itemId(next));
}

function goPrev() {
  const bucket = active();
  if (bucket.historyIndex <= 0) return;
  bucket.historyIndex -= 1;
  renderCurrent(bucket.history[bucket.historyIndex]);
}

async function rate(rating) {
  const bucket = active();
  const id = bucket.history[bucket.historyIndex];
  const seconds = timer.frozenSeconds || Math.floor(timer.elapsedMs / 1000);
  const url = mode === "quant" ? "/api/ratings" : "/api/word-ratings";
  const body =
    mode === "quant"
      ? { post_id: id, rating, seconds }
      : { word: id, rating, seconds };

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    showError(err.error || "failed to save rating");
    return;
  }

  renderStats(await res.json(), bucket);
  goNext();
}

let starBurstLayer = null;

function getStarBurstLayer() {
  if (!starBurstLayer) {
    starBurstLayer = document.createElement("div");
    starBurstLayer.className = "star-burst-layer";
    document.body.appendChild(starBurstLayer);
  }
  return starBurstLayer;
}

function shootStarBurst(count, x, y) {
  const layer = getStarBurstLayer();
  const base = Math.random() * 360;
  const dist = 85;

  for (let i = 0; i < count; i += 1) {
    const angleDeg = base + i * (360 / count) + (Math.random() * 20 - 10);
    const angleRad = (angleDeg * Math.PI) / 180;
    const tx = Math.cos(angleRad) * dist;
    const ty = Math.sin(angleRad) * dist;

    const burst = document.createElement("div");
    burst.className = "star-burst";
    burst.style.left = `${x}px`;
    burst.style.top = `${y}px`;
    burst.style.setProperty("--tx", `${tx}px`);
    burst.style.setProperty("--ty", `${ty}px`);
    burst.style.setProperty("--angle", `${angleDeg}deg`);
    burst.innerHTML =
      '<span class="star-burst-inner">' +
      '<span class="star-burst-trail"></span>' +
      '<span class="star-burst-icon">★</span>' +
      "</span>";
    burst.addEventListener("animationend", () => burst.remove());
    layer.appendChild(burst);
  }
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

    btn.addEventListener("click", (e) => {
      shootStarBurst(rating, e.clientX, e.clientY);
      rate(rating);
    });
  });

  stars.addEventListener("mouseleave", () => {
    buttons.forEach((b) => b.classList.remove("hover"));
  });
}

function startModeSession() {
  const bucket = active();
  refreshStatsDisplay();
  updateModeUI();

  if (bucket.history.length === 0) {
    const first = pickWeighted(null) || bucket.items[0];
    goToItem(itemId(first));
    return;
  }

  renderCurrent(bucket.history[bucket.historyIndex]);
}

async function toggleMode() {
  mode = mode === "quant" ? "vocab" : "quant";

  try {
    if (mode === "vocab" && !vocab.loaded) {
      await loadVocabData();
    }
    startModeSession();
  } catch (err) {
    mode = mode === "quant" ? "vocab" : "quant";
    showError(err.message);
  }
}

async function init() {
  try {
    await loadQuantData();
    setupStars();
    updateModeUI();
    startModeSession();

    $("mode-title").addEventListener("click", toggleMode);

    $("reveal-btn").addEventListener("click", () => {
      stopTimer();
      $("answer").classList.remove("hidden");
      $("reveal-btn").classList.add("hidden");
      $("stars").classList.remove("hidden");
      showCommentAside(quant.history[quant.historyIndex]);
    });

    $("comment-add-btn").addEventListener("click", enterCommentEdit);
    $("comment-edit-btn").addEventListener("click", enterCommentEdit);
    $("comment-save-btn").addEventListener("click", saveComment);
    $("comment-cancel-btn").addEventListener("click", cancelCommentEdit);

    $("timer-toggle").addEventListener("click", toggleTimer);
    $("next-btn").addEventListener("click", goNext);
    $("prev-btn").addEventListener("click", goPrev);
  } catch (err) {
    showError(err.message);
  }
}

init();
