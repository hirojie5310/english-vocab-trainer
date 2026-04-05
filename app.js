import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v0.27.3/full/pyodide.mjs";

const state = {
  pyodide: null,
  vocabPayload: null,
  quiz: null,
  selectedMode: null,
  selectedCsvMeta: null,
  csvOptions: [],
  questionIndex: 0,
  correctCount: 0,
  answered: false,
};

const els = {
  runtimeStatus: document.getElementById("runtime-status"),
  stepStatus: document.getElementById("step-status"),
  csvList: document.getElementById("csv-list"),
  selectedFileName: document.getElementById("selected-file-name"),
  toModeBtn: document.getElementById("to-mode-btn"),
  backToFileBtn: document.getElementById("back-to-file-btn"),
  modeButtons: Array.from(document.querySelectorAll(".mode-btn")),
  questionProgress: document.getElementById("question-progress"),
  quizModeLabel: document.getElementById("quiz-mode-label"),
  questionPrompt: document.getElementById("question-prompt"),
  questionPos: document.getElementById("question-pos"),
  choices: document.getElementById("choices"),
  answerFeedback: document.getElementById("answer-feedback"),
  answerReview: document.getElementById("answer-review"),
  answerExample: document.getElementById("answer-example"),
  nextBtn: document.getElementById("next-btn"),
  resultScore: document.getElementById("result-score"),
  resultAccuracy: document.getElementById("result-accuracy"),
  resultMastery: document.getElementById("result-mastery"),
  toResetBtn: document.getElementById("to-reset-btn"),
  resetCopy: document.getElementById("reset-copy"),
  resetKeepBtn: document.getElementById("reset-keep-btn"),
  resetClearBtn: document.getElementById("reset-clear-btn"),
  screens: {
    file: document.getElementById("screen-file"),
    mode: document.getElementById("screen-mode"),
    quiz: document.getElementById("screen-quiz"),
    result: document.getElementById("screen-result"),
    reset: document.getElementById("screen-reset"),
  },
};

const STEP_LABELS = {
  file: "1. CSV選択",
  mode: "2. モード選択",
  quiz: "3. クイズ",
  result: "4. 結果表示",
  reset: "5. 正解ログ確認",
};

function showScreen(name) {
  Object.entries(els.screens).forEach(([key, screen]) => {
    screen.classList.toggle("is-active", key === name);
  });
  els.stepStatus.textContent = STEP_LABELS[name];
}

function safeJsonParse(text, fallback = []) {
  try {
    return JSON.parse(text ?? "");
  } catch {
    return fallback;
  }
}

function getStorageKeys() {
  const datasetId = state.vocabPayload?.dataset_id;
  return {
    correct: `evt.correct.${datasetId}`,
    wrong: `evt.wrong.${datasetId}`,
  };
}

function loadCorrectLog() {
  const keys = getStorageKeys();
  if (!keys.correct) {
    return [];
  }
  return safeJsonParse(localStorage.getItem(keys.correct), []);
}

function saveCorrectLog(entries) {
  const keys = getStorageKeys();
  if (keys.correct) {
    localStorage.setItem(keys.correct, JSON.stringify(entries));
  }
}

function loadWrongLog() {
  const keys = getStorageKeys();
  if (!keys.wrong) {
    return [];
  }
  return safeJsonParse(localStorage.getItem(keys.wrong), []);
}

function saveWrongLog(entries) {
  const keys = getStorageKeys();
  if (keys.wrong) {
    localStorage.setItem(keys.wrong, JSON.stringify(entries));
  }
}

function resetSessionOnly() {
  state.quiz = null;
  state.selectedMode = null;
  state.questionIndex = 0;
  state.correctCount = 0;
  state.answered = false;
  els.choices.innerHTML = "";
  els.answerFeedback.hidden = true;
  els.answerReview.hidden = true;
  els.answerExample.hidden = true;
  els.nextBtn.hidden = true;
}

function resetAllToStep1() {
  resetSessionOnly();
  state.vocabPayload = null;
  state.selectedCsvMeta = null;
  els.selectedFileName.textContent = "まだファイルが選択されていません。";
  els.toModeBtn.disabled = true;
  renderCsvOptions();
  showScreen("file");
}

function renderCsvOptions() {
  els.csvList.innerHTML = "";

  if (state.csvOptions.length === 0) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "CSV候補を読み込めませんでした。";
    els.csvList.appendChild(empty);
    return;
  }

  state.csvOptions.forEach((file) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "choice-btn csv-btn";
    if (state.selectedCsvMeta?.path === file.path) {
      button.classList.add("is-selected");
    }
    button.innerHTML = `<strong>${file.label}</strong><span>${file.description ?? ""}</span>`;
    button.addEventListener("click", async () => {
      try {
        await selectCsvOption(file);
      } catch (error) {
        els.selectedFileName.textContent = "CSVを読み込めませんでした。";
        els.toModeBtn.disabled = true;
        window.alert(error.message || "CSVの取得に失敗しました。");
      }
    });
    els.csvList.appendChild(button);
  });
}

async function initPyodideRuntime() {
  els.runtimeStatus.textContent = "Wasmランタイムを読み込んでいます...";
  state.pyodide = await loadPyodide();
  const pythonSource = await fetch("./web_app.py").then((response) => response.text());
  await state.pyodide.runPythonAsync(pythonSource);
  const manifest = await fetch("./csv-manifest.json").then((response) => {
    if (!response.ok) {
      throw new Error("csv-manifest.json を取得できませんでした。");
    }
    return response.json();
  });
  state.csvOptions = manifest.files ?? [];
  renderCsvOptions();
  els.runtimeStatus.textContent = "Wasmランタイムの準備ができました。";
}

async function parseCsvText(filename, csvText) {
  const result = state.pyodide.globals
    .get("parse_csv_text")(filename, csvText)
    .toString();
  state.vocabPayload = JSON.parse(result);
}

async function selectCsvOption(file) {
  const response = await fetch(`./${file.path}`);
  if (!response.ok) {
    throw new Error(`${file.label} を取得できませんでした。`);
  }
  const csvText = await response.text();
  await parseCsvText(file.label, csvText);
  state.selectedCsvMeta = file;
  els.selectedFileName.textContent = `${file.label} を選択しました。`;
  els.toModeBtn.disabled = false;
  renderCsvOptions();
}

async function buildQuiz() {
  const correctLog = JSON.stringify(loadCorrectLog());
  const wrongLog = JSON.stringify(loadWrongLog());

  const quizJson = state.pyodide.globals
    .get("build_quiz")(
      JSON.stringify(state.vocabPayload),
      state.selectedMode,
      correctLog,
      wrongLog,
      10,
      5,
      2,
    )
    .toString();

  state.quiz = JSON.parse(quizJson);
  state.questionIndex = 0;
  state.correctCount = 0;
  state.answered = false;
}

function currentQuestion() {
  return state.quiz.questions[state.questionIndex];
}

function renderQuestion() {
  const question = currentQuestion();
  const modeLabel =
    state.selectedMode === 1 ? "英単語 → 和訳（4択）" : "和訳 → 英単語（4択）";

  els.questionProgress.textContent = `第${state.questionIndex + 1}問 / 第${state.quiz.num_questions}問`;
  els.quizModeLabel.textContent = modeLabel;
  els.questionPrompt.textContent = question.prompt;
  els.questionPos.textContent =
    question.pos && !state.quiz.is_idiom_dataset ? `品詞: ${question.pos}` : "";
  els.choices.innerHTML = "";

  question.choices.forEach((choice, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "choice-btn";
    button.textContent = `${index + 1}. ${choice}`;
    button.addEventListener("click", () => handleAnswer(index));
    els.choices.appendChild(button);
  });

  els.answerFeedback.hidden = true;
  els.answerFeedback.className = "feedback";
  els.answerReview.hidden = true;
  els.answerExample.hidden = true;
  els.nextBtn.hidden = true;
  state.answered = false;
}

function handleAnswer(selectedIndex) {
  if (state.answered) {
    return;
  }

  state.answered = true;
  const question = currentQuestion();
  const choiceButtons = Array.from(els.choices.querySelectorAll(".choice-btn"));
  const isCorrect = selectedIndex === question.correct_index;

  choiceButtons.forEach((button, index) => {
    button.disabled = true;
    if (index === question.correct_index) {
      button.classList.add("is-correct");
    } else if (index === selectedIndex) {
      button.classList.add("is-wrong");
    }
  });

  if (isCorrect) {
    state.correctCount += 1;
    els.answerFeedback.textContent = "正解です。";
    els.answerFeedback.classList.add("is-correct");
    const correctLog = loadCorrectLog();
    const exists = correctLog.some(
      (item) => item.en === question.en && item.ja === question.ja,
    );
    if (!exists) {
      correctLog.push({
        timestamp: new Date().toISOString(),
        en: question.en,
        ja: question.ja,
      });
      saveCorrectLog(correctLog);
    }
  } else {
    els.answerFeedback.textContent = `不正解です。正解は ${question.correct_index + 1} 番です。`;
    els.answerFeedback.classList.add("is-wrong");
    const wrongLog = loadWrongLog();
    wrongLog.push({
      timestamp: new Date().toISOString(),
      mode: state.selectedMode,
      en: question.en,
      ja: question.ja,
    });
    saveWrongLog(wrongLog);
  }

  els.answerFeedback.hidden = false;
  els.answerReview.textContent = question.review_line;
  els.answerReview.hidden = false;

  const exampleParts = [];
  if (question.example_en) {
    exampleParts.push(`例文: ${question.example_en}`);
  }
  if (question.example_ja) {
    exampleParts.push(`和訳: ${question.example_ja}`);
  }
  if (exampleParts.length > 0) {
    els.answerExample.textContent = exampleParts.join("\n");
    els.answerExample.hidden = false;
  }

  els.nextBtn.textContent =
    state.questionIndex === state.quiz.num_questions - 1 ? "結果を見る" : "次へ";
  els.nextBtn.hidden = false;
}

function showResults() {
  const accuracy = (state.correctCount / state.quiz.num_questions) * 100;
  const correctLog = loadCorrectLog();
  const masteryCount = new Set(correctLog.map((item) => `${item.en}\t${item.ja}`)).size;

  els.resultScore.textContent = `${state.correctCount} / ${state.quiz.num_questions}`;
  els.resultAccuracy.textContent = `正答率 ${accuracy.toFixed(1)}%`;
  els.resultMastery.textContent = `このCSVの正解済み単語数: ${masteryCount} / ${state.quiz.total_count}`;
  showScreen("result");
}

function showResetConfirm() {
  const correctLog = loadCorrectLog();
  const masteryCount = new Set(correctLog.map((item) => `${item.en}\t${item.ja}`)).size;
  els.resetCopy.textContent = `現在、このCSVでは ${masteryCount} 件の正解ログが保存されています。選択後は 1. のCSV選択に戻ります。`;
  showScreen("reset");
}

async function startQuizForMode(mode) {
  state.selectedMode = mode;
  try {
    await buildQuiz();
  } catch (error) {
    const message = error.message || "クイズの作成に失敗しました。";
    if (message.includes("正解ログを消去")) {
      const shouldReset = window.confirm(`${message}\n\nこのCSVの正解ログを今すぐ消去しますか？`);
      if (shouldReset) {
        localStorage.removeItem(getStorageKeys().correct);
        try {
          await buildQuiz();
        } catch (retryError) {
          window.alert(retryError.message || "クイズの再作成に失敗しました。");
          return;
        }
      } else {
        window.alert(message);
        return;
      }
    } else {
      window.alert(message);
      return;
    }
  }
  showScreen("quiz");
  renderQuestion();
}

els.toModeBtn.addEventListener("click", () => {
  if (!state.vocabPayload) {
    return;
  }
  resetSessionOnly();
  showScreen("mode");
});

els.backToFileBtn.addEventListener("click", () => {
  showScreen("file");
});

els.modeButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    await startQuizForMode(Number(button.dataset.mode));
  });
});

els.nextBtn.addEventListener("click", () => {
  if (state.questionIndex === state.quiz.num_questions - 1) {
    showResults();
    return;
  }
  state.questionIndex += 1;
  renderQuestion();
});

els.toResetBtn.addEventListener("click", () => {
  showResetConfirm();
});

els.resetKeepBtn.addEventListener("click", () => {
  resetAllToStep1();
});

els.resetClearBtn.addEventListener("click", () => {
  localStorage.removeItem(getStorageKeys().correct);
  resetAllToStep1();
});

initPyodideRuntime().catch((error) => {
  els.runtimeStatus.textContent = "Wasmランタイムの読み込みに失敗しました。";
  state.csvOptions = [];
  renderCsvOptions();
  window.alert(error.message || "Wasmランタイムを起動できませんでした。");
});
