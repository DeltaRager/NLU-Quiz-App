from __future__ import annotations

import json
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from quiz_builder.env_utils import load_dotenv
from quiz_builder.io_utils import load_mcqs, write_json
from quiz_builder.models import MCQ
from quiz_builder.openai_explainer import explain_mcq


ORIGINALS_DATASET_PATHS = [
    Path("quiz_data/originals_reviewed.json"),
    Path("quiz_data/originals_extracted.json"),
]
SESSION_RESULTS_DIR = Path("quiz_data/session_results")
OPTION_LABELS = ["A", "B", "C", "D"]
SESSION_QUESTION_COUNT = 30
SESSION_TIME_LIMIT_SECONDS = 18 * 60


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
        :root {
          --bg-1: #0d1117;
          --bg-2: #111827;
          --bg-3: #161b22;
          --card: rgba(17, 24, 39, 0.88);
          --card-2: rgba(20, 27, 45, 0.92);
          --line: rgba(148, 163, 184, 0.18);
          --text: #e5e7eb;
          --muted: #94a3b8;
          --accent: #f97316;
          --accent-2: #22c55e;
          --accent-3: #38bdf8;
        }
        .stApp {
          background:
            radial-gradient(circle at top right, rgba(249,115,22,0.12), transparent 26%),
            radial-gradient(circle at left 20%, rgba(56,189,248,0.10), transparent 24%),
            linear-gradient(180deg, var(--bg-1), var(--bg-2));
          color: var(--text);
        }
        header[data-testid="stHeader"] {
          display: none;
        }
        [data-testid="stToolbar"] {
          display: none;
        }
        #MainMenu, footer {
          visibility: hidden;
          height: 0;
        }
        .block-container {
          max-width: 980px;
          padding-top: 0.2rem;
          padding-bottom: 0.75rem;
          padding-left: 1rem;
          padding-right: 1rem;
        }
        h1, h2, h3 {
          font-family: "IBM Plex Sans", sans-serif !important;
          color: var(--text);
          letter-spacing: -0.02em;
          font-weight: 700;
        }
        html, body, [class*="css"]  {
          font-family: "IBM Plex Sans", sans-serif;
          color: var(--text);
        }
        .hero-card, .quiz-card, .review-card {
          background: linear-gradient(180deg, var(--card), var(--card-2));
          border: 1px solid var(--line);
          border-radius: 20px;
          padding: 0.9rem 1rem;
          box-shadow: 0 24px 64px rgba(0, 0, 0, 0.35);
          backdrop-filter: blur(10px);
        }
        .hero-card h1, .quiz-card h1, .review-card h1 {
          font-size: 1.7rem;
          margin-bottom: 0.2rem;
        }
        .quiz-question, .review-question {
          margin: 0.4rem 0 0.55rem 0;
          font-size: 1.1rem;
          line-height: 1.35;
          font-weight: 600;
        }
        .meta-chip {
          display: inline-block;
          margin-right: 0.5rem;
          margin-bottom: 0.3rem;
          padding: 0.2rem 0.5rem;
          border-radius: 999px;
          border: 1px solid var(--line);
          background: rgba(30, 41, 59, 0.8);
          color: var(--muted);
          font-size: 0.75rem;
        }
        .timer-strip {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 1rem;
          background: linear-gradient(90deg, rgba(249,115,22,0.14), rgba(56,189,248,0.10));
          border: 1px solid var(--line);
          border-radius: 16px;
          padding: 0.55rem 0.8rem;
          margin-bottom: 0.75rem;
          margin-top: 0.45rem;
        }
        .timer-big {
          font-size: 1.35rem;
          font-weight: 700;
          color: var(--accent);
        }
        .soft-note {
          color: var(--muted);
          font-size: 0.82rem;
        }
        .summary-line {
          color: var(--muted);
          font-size: 0.85rem;
          margin: 0.15rem 0 0.45rem 0;
        }
        .option-list {
          margin-top: 0.35rem;
        }
        .option-row {
          border: 1px solid var(--line);
          border-radius: 12px;
          background: rgba(15, 23, 42, 0.72);
          padding: 0.45rem 0.65rem;
          margin-bottom: 0.3rem;
          line-height: 1.3;
        }
        .option-row.correct {
          border-color: rgba(34, 197, 94, 0.45);
          background: rgba(20, 83, 45, 0.32);
        }
        .option-row.selected {
          border-color: rgba(239, 68, 68, 0.45);
          background: rgba(127, 29, 29, 0.28);
        }
        .review-answer-line {
          color: var(--text);
          font-size: 0.9rem;
          margin: 0.2rem 0;
        }
        .hidden-submit {
          display: none;
        }
        .stButton > button {
          border-radius: 12px;
          border: 1px solid var(--line);
          background: rgba(30, 41, 59, 0.8);
          color: var(--text);
          min-height: 2.4rem;
          padding-top: 0.25rem;
          padding-bottom: 0.25rem;
        }
        .stButton > button[kind="primary"] {
          background: linear-gradient(90deg, var(--accent), #ea580c);
          color: white;
          border: none;
        }
        .stRadio label, .stSelectbox label, .stMarkdown, .stCaption, .stText {
          color: var(--text) !important;
        }
        [data-testid="stMetric"] {
          background: rgba(15, 23, 42, 0.72);
          border: 1px solid var(--line);
          padding: 0.45rem 0.65rem;
          border-radius: 14px;
        }
        [data-testid="stMetricLabel"] {
          font-size: 0.78rem;
        }
        [data-testid="stMetricValue"] {
          font-size: 1.15rem;
        }
        [data-baseweb="select"] > div {
          background: rgba(15, 23, 42, 0.88);
          border-color: var(--line);
        }
        div[role="radiogroup"] label {
          background: rgba(15, 23, 42, 0.72);
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 0.42rem 0.6rem;
          margin-bottom: 0.3rem;
        }
        .stAlert {
          border-radius: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def reset_app_state() -> None:
    st.session_state.app_mode = "home"
    st.session_state.active_session = None
    st.session_state.review_index = 0


def initialize_state() -> None:
    if "app_mode" not in st.session_state:
        reset_app_state()


@st.cache_data(show_spinner=False)
def load_dataset() -> list[MCQ]:
    for path in ORIGINALS_DATASET_PATHS:
        if path.exists():
            return load_mcqs(path)
    st.error(
        "Original quiz dataset not found. Expected one of: "
        + ", ".join(str(path) for path in ORIGINALS_DATASET_PATHS)
    )
    st.stop()


@st.cache_data(show_spinner=False)
def load_saved_session_results() -> list[dict]:
    if not SESSION_RESULTS_DIR.exists():
        return []

    loaded: list[dict] = []
    for path in sorted(SESSION_RESULTS_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        data["_result_path"] = str(path)
        loaded.append(data)
    loaded.sort(key=lambda item: item.get("completed_at_iso") or item.get("started_at_iso") or "", reverse=True)
    return loaded


def sanitize_option_text(text: str) -> str:
    return re.sub(r"^\s*[A-D][\).:\-]\s*", "", text).strip()


def shuffle_question_options(question: MCQ, seed: int) -> MCQ:
    pairs = list(zip(OPTION_LABELS, [sanitize_option_text(option) for option in question.options]))
    rng = random.Random(f"{seed}:{question.id}")
    rng.shuffle(pairs)
    shuffled_options = [option_text for _, option_text in pairs]
    correct_index = next(idx for idx, (label, _text) in enumerate(pairs) if label == question.correct_option)
    return MCQ(
        id=question.id,
        question=question.question,
        options=shuffled_options,
        correct_option=OPTION_LABELS[correct_index],
        source=question.source,
        topic=question.topic,
        needs_review=question.needs_review,
        notes=question.notes,
        source_pdf=question.source_pdf,
        source_snippet=question.source_snippet,
    )


def source_label(question: MCQ) -> str:
    parts = [question.source]
    if question.topic:
        parts.append(question.topic)
    if question.source_pdf:
        parts.append(question.source_pdf)
    return " | ".join(parts)


def option_display(label: str, text: str) -> str:
    return f"{label}. {text}"


def review_option_class(label: str, row: dict) -> str:
    if label == row["correct_option"]:
        return "option-row correct"
    if label == row["selected_option"]:
        return "option-row selected"
    return "option-row"


def build_session_questions(dataset: list[MCQ], seed: int) -> list[MCQ]:
    if len(dataset) < SESSION_QUESTION_COUNT:
        st.error(
            f"At least {SESSION_QUESTION_COUNT} original questions are required, found {len(dataset)}."
        )
        st.stop()
    rng = random.Random(seed)
    sampled = rng.sample(dataset, SESSION_QUESTION_COUNT)
    return [shuffle_question_options(question, seed) for question in sampled]


def new_session_payload(dataset: list[MCQ]) -> dict:
    seed = random.randint(1, 10_000_000)
    started_at = time.time()
    started_iso = datetime.now(timezone.utc).isoformat()
    questions = build_session_questions(dataset, seed)
    return {
        "session_id": f"session-{int(started_at)}-{seed}",
        "started_at": started_at,
        "started_at_iso": started_iso,
        "time_limit_seconds": SESSION_TIME_LIMIT_SECONDS,
        "current_index": 0,
        "questions": [question.to_dict() for question in questions],
        "answers": {},
        "completed": False,
        "score": None,
        "result_path": None,
        "review_result": None,
        "review_explanations": {},
        "review_errors": {},
    }


def review_session_from_result(result_data: dict) -> dict:
    return {
        "session_id": result_data["session_id"],
        "started_at": 0.0,
        "started_at_iso": result_data.get("started_at_iso"),
        "time_limit_seconds": result_data.get("time_limit_seconds", SESSION_TIME_LIMIT_SECONDS),
        "current_index": 0,
        "questions": [],
        "answers": {},
        "completed": True,
        "score": result_data.get("score"),
        "result_path": result_data.get("_result_path"),
        "review_result": result_data,
        "review_explanations": {},
        "review_errors": {},
    }


def get_active_session() -> dict:
    session = st.session_state.active_session
    if not session:
        st.error("No active quiz session. Return to the home page and start a new session.")
        st.stop()
    return session


def session_questions(session: dict) -> list[MCQ]:
    return [MCQ.from_dict(item) for item in session["questions"]]


def compute_remaining_seconds(session: dict) -> int:
    elapsed = int(time.time() - session["started_at"])
    return max(0, session["time_limit_seconds"] - elapsed)


def answer_state(session: dict, question_id: str) -> dict:
    if question_id not in session["answers"]:
        session["answers"][question_id] = {"selected_option": None}
    return session["answers"][question_id]


def selected_answer(session: dict, question_id: str) -> str | None:
    answer = session["answers"].get(question_id)
    if not answer:
        return None
    selected_option = answer.get("selected_option")
    return selected_option if selected_option in OPTION_LABELS else None


def answered_count(session: dict, questions: list[MCQ]) -> int:
    return sum(1 for question in questions if selected_answer(session, question.id))


def format_remaining(seconds: int) -> str:
    minutes = seconds // 60
    remainder = seconds % 60
    return f"{minutes:02d}:{remainder:02d}"


def selected_radio_index(selected_option: str | None) -> int | None:
    if selected_option not in OPTION_LABELS:
        return None
    return OPTION_LABELS.index(selected_option)


def finish_session(session: dict) -> None:
    if session["completed"]:
        return
    questions = session_questions(session)
    score = 0
    answer_rows = []
    for question in questions:
        selected_option = answer_state(session, question.id)["selected_option"]
        is_correct = selected_option == question.correct_option
        if is_correct:
            score += 1
        correct_index = OPTION_LABELS.index(question.correct_option)
        answer_rows.append(
            {
                "id": question.id,
                "question": question.question,
                "selected_option": selected_option,
                "correct_option": question.correct_option,
                "correct_option_text": question.options[correct_index],
                "options": question.options,
                "is_correct": is_correct,
                "source": question.source,
                "topic": question.topic,
                "source_pdf": question.source_pdf,
                "source_snippet": question.source_snippet,
            }
        )

    completed_at = time.time()
    session["completed"] = True
    session["score"] = score

    result_payload = {
        "session_id": session["session_id"],
        "started_at_iso": session["started_at_iso"],
        "completed_at_iso": datetime.now(timezone.utc).isoformat(),
        "time_limit_seconds": session["time_limit_seconds"],
        "duration_seconds": min(int(completed_at - session["started_at"]), session["time_limit_seconds"]),
        "score": score,
        "total_questions": len(questions),
        "answers": answer_rows,
    }
    SESSION_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_path = SESSION_RESULTS_DIR / f"{session['session_id']}.json"
    write_json(result_path, result_payload)
    load_saved_session_results.clear()
    session["result_path"] = str(result_path)
    session["review_result"] = result_payload
    st.session_state.app_mode = "review"
    st.session_state.review_index = 0


def render_home(dataset: list[MCQ]) -> None:
    saved_sessions = load_saved_session_results()
    st.markdown("<div class='hero-card'>", unsafe_allow_html=True)
    st.title("NLU Quiz Sessions")
    st.caption("Timed 30-question runs pulled from the original quiz bank for exam practice.")
    chip_col1, chip_col2 = st.columns(2)
    chip_col1.markdown(f"<span class='meta-chip'>Bank size: {len(dataset)} questions</span>", unsafe_allow_html=True)
    chip_col2.markdown(
        f"<span class='meta-chip'>Session: {SESSION_QUESTION_COUNT} questions / 18 minutes</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p class='soft-note'>Start a fresh timed run, finish automatically or manually, "
        "then review every question with explanations after the session ends.</p>",
        unsafe_allow_html=True,
    )

    if st.button("Start New Session", type="primary"):
        st.session_state.active_session = new_session_payload(dataset)
        st.session_state.app_mode = "quiz"
        st.rerun()

    st.markdown("### Saved Sessions")
    if not saved_sessions:
        st.caption("No saved sessions found yet.")
    else:
        labels = []
        for result in saved_sessions:
            completed = result.get("completed_at_iso", "unknown time")
            labels.append(
                f"{completed}  |  Score {result.get('score', 0)}/{result.get('total_questions', SESSION_QUESTION_COUNT)}  |  {result['session_id']}"
            )
        selected_label = st.selectbox("Open a previous session", labels, key="saved_session_select")
        selected_index = labels.index(selected_label)
        selected_result = saved_sessions[selected_index]
        st.caption(selected_result.get("_result_path", ""))
        if st.button("Review Selected Session"):
            st.session_state.active_session = review_session_from_result(selected_result)
            st.session_state.review_index = 0
            st.session_state.app_mode = "review"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def render_quiz_timer(remaining_seconds: int, current_index: int, question_count: int, answered_total: int) -> None:
    components.html(
        f"""
        <style>
        body {{
          margin: 0;
          font-family: "IBM Plex Sans", sans-serif;
          background: transparent;
          color: #e5e7eb;
        }}
        .timer-strip {{
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 1rem;
          background: linear-gradient(90deg, rgba(249,115,22,0.14), rgba(56,189,248,0.10));
          border: 1px solid rgba(148, 163, 184, 0.18);
          border-radius: 16px;
          padding: 0.55rem 0.8rem;
          margin: 0;
        }}
        .timer-big {{
          font-size: 1.35rem;
          font-weight: 700;
          color: #f97316;
          line-height: 1;
        }}
        .soft-note {{
          color: #94a3b8;
          font-size: 0.82rem;
          line-height: 1.3;
        }}
        </style>
        <div class="timer-strip">
          <div>
            <div class="soft-note">Live session timer</div>
            <div class="timer-big" id="quiz-timer-value">{format_remaining(remaining_seconds)}</div>
          </div>
          <div class="soft-note">
            Question {current_index + 1} of {question_count}<br/>
            Answered: {answered_total} / {question_count}
          </div>
        </div>
        <script>
        const parentWindow = window.parent;
        const timerElement = document.getElementById("quiz-timer-value");
        let remaining = {remaining_seconds};

        function formatRemaining(totalSeconds) {{
          const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
          const seconds = String(totalSeconds % 60).padStart(2, "0");
          return `${{minutes}}:${{seconds}}`;
        }}

        function clickAutoSubmit() {{
          const buttons = [...parentWindow.document.querySelectorAll("button")];
          const button = buttons.find((item) => item.innerText.trim() === "Auto Submit Session" && !item.disabled);
          if (button) {{
            button.click();
          }}
        }}

        timerElement.textContent = formatRemaining(remaining);
        if (window.__quizTimerInterval) {{
          clearInterval(window.__quizTimerInterval);
        }}
        window.__quizTimerInterval = setInterval(() => {{
          remaining -= 1;
          if (remaining <= 0) {{
            timerElement.textContent = "00:00";
            clearInterval(window.__quizTimerInterval);
            clickAutoSubmit();
            return;
          }}
          timerElement.textContent = formatRemaining(remaining);
        }}, 1000);
        </script>
        """,
        height=88,
    )


def render_quiz(session: dict) -> None:
    questions = session_questions(session)
    remaining_seconds = compute_remaining_seconds(session)
    if remaining_seconds <= 0:
        finish_session(session)
        st.rerun()

    question = questions[session["current_index"]]
    answer = answer_state(session, question.id)

    st.markdown("<div class='quiz-card'>", unsafe_allow_html=True)
    st.title("Active Quiz Session")
    st.caption("Explanations are disabled during the timed session.")
    stats_col1, stats_col2 = st.columns(2)
    stats_col1.metric("Question", f"{session['current_index'] + 1} / {len(questions)}")
    stats_col2.metric("Answered", answered_count(session, questions))
    st.markdown(
        f"<div class='quiz-question'>{question.question}</div><div class='soft-note'>{source_label(question)}</div>",
        unsafe_allow_html=True,
    )

    options = {
        option_display(label, question.options[idx]): label
        for idx, label in enumerate(OPTION_LABELS)
    }
    option_keys = list(options.keys())
    radio_index = selected_radio_index(answer["selected_option"])
    selected = st.radio(
        "Choose one option:",
        option_keys,
        index=radio_index,
        key=f"quiz_radio_{question.id}",
    )

    if selected is not None:
        answer["selected_option"] = options[selected]

    render_quiz_timer(
        remaining_seconds=remaining_seconds,
        current_index=session["current_index"],
        question_count=len(questions),
        answered_total=answered_count(session, questions),
    )

    nav_col1, nav_col2, nav_col3 = st.columns(3)
    if nav_col1.button("Previous", disabled=session["current_index"] == 0):
        session["current_index"] = max(0, session["current_index"] - 1)
        st.rerun()

    if nav_col2.button("Next", disabled=session["current_index"] >= len(questions) - 1):
        session["current_index"] = min(len(questions) - 1, session["current_index"] + 1)
        st.rerun()

    if nav_col3.button("Submit Session Now", type="primary"):
        finish_session(session)
        st.rerun()
    st.markdown("<div class='hidden-submit'>", unsafe_allow_html=True)
    if st.button("Auto Submit Session", key="auto_submit_session"):
        finish_session(session)
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def load_review_result(session: dict) -> dict:
    cached = session.get("review_result")
    if cached:
        return cached

    result_path = Path(session["result_path"]) if session.get("result_path") else None
    if not result_path or not result_path.exists():
        st.error("Saved result JSON was not found.")
        st.stop()

    loaded = json.loads(result_path.read_text(encoding="utf-8"))
    session["review_result"] = loaded
    return loaded


def render_review_shortcuts() -> None:
    components.html(
        """
        <script>
        const parentWindow = window.parent;
        if (!parentWindow.__nluReviewKeysBound) {
          parentWindow.__nluReviewKeysBound = true;
          parentWindow.addEventListener("keydown", (event) => {
            const target = event.target;
            const tagName = target && target.tagName ? target.tagName.toUpperCase() : "";
            const isEditable = tagName === "INPUT" || tagName === "TEXTAREA" || target?.isContentEditable;
            if (isEditable) return;

            const buttons = [...parentWindow.document.querySelectorAll("button")];
            if (event.key === "ArrowLeft") {
              const button = buttons.find((item) => item.innerText.trim() === "Previous Review" && !item.disabled);
              if (button) {
                event.preventDefault();
                button.click();
              }
            }
            if (event.key === "ArrowRight") {
              const button = buttons.find((item) => item.innerText.trim() === "Next Review" && !item.disabled);
              if (button) {
                event.preventDefault();
                button.click();
              }
            }
          });
        }
        </script>
        """,
        height=0,
        width=0,
    )


def render_review(session: dict) -> None:
    if not session.get("completed"):
        st.error("No completed session to review.")
        st.stop()

    result_data = load_review_result(session)
    answers = result_data["answers"]
    current_index = min(st.session_state.review_index, len(answers) - 1)
    st.session_state.review_index = current_index

    st.markdown("<div class='review-card'>", unsafe_allow_html=True)
    st.title("Session Review")
    st.markdown(
        f"<div class='summary-line'>Score {result_data['score']} / {result_data['total_questions']}  |  "
        f"Duration {result_data['duration_seconds']}s</div>",
        unsafe_allow_html=True,
    )
    render_review_shortcuts()

    row = answers[current_index]
    question = MCQ(
        id=row["id"],
        question=row["question"],
        options=row["options"],
        correct_option=row["correct_option"],
        source=row["source"],
        topic=row["topic"],
        source_pdf=row["source_pdf"],
        source_snippet=row["source_snippet"],
    )

    st.markdown(
        f"<div class='meta-chip'>Question {current_index + 1} of {len(answers)}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='review-question'>{row['question']}</div>"
        f"<div class='soft-note'>{source_label(question)}</div>",
        unsafe_allow_html=True,
    )
    option_rows = []
    for label, option_text in zip(OPTION_LABELS, row["options"]):
        option_rows.append(f"<div class='{review_option_class(label, row)}'>{label}. {option_text}</div>")
    st.markdown(f"<div class='option-list'>{''.join(option_rows)}</div>", unsafe_allow_html=True)

    selected_text = row["selected_option"] if row["selected_option"] else "unanswered"
    st.markdown(f"<div class='review-answer-line'>Your answer: {selected_text}</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='review-answer-line'>Correct answer: {row['correct_option']}</div>",
        unsafe_allow_html=True,
    )

    nav_col1, nav_col2, nav_col3 = st.columns(3)
    if nav_col1.button("Previous Review", disabled=current_index == 0):
        st.session_state.review_index = max(0, st.session_state.review_index - 1)
        st.rerun()
    if nav_col2.button("Next Review", disabled=current_index >= len(answers) - 1):
        st.session_state.review_index = min(len(answers) - 1, st.session_state.review_index + 1)
        st.rerun()
    if nav_col3.button("Back to Home"):
        st.session_state.app_mode = "home"
        st.rerun()

    explanation_key = row["id"]
    if st.button("Explain This Question", key=f"review_explain_{row['id']}"):
        with st.spinner("Generating explanation..."):
            try:
                session["review_explanations"][explanation_key] = explain_mcq(
                    question,
                    user_choice=row["selected_option"],
                )
                session["review_errors"].pop(explanation_key, None)
            except Exception as exc:  # noqa: BLE001
                session["review_errors"][explanation_key] = str(exc)
        st.rerun()

    if explanation_key in session["review_explanations"]:
        st.markdown("#### Explanation")
        st.write(session["review_explanations"][explanation_key])
    elif explanation_key in session["review_errors"]:
        st.warning(f"Explanation unavailable: {session['review_errors'][explanation_key]}")
    st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(page_title="NLU Quiz Sessions", page_icon=":books:", layout="wide")
    load_dotenv(Path(".env"))
    inject_styles()
    initialize_state()
    dataset = load_dataset()

    if st.session_state.app_mode == "home":
        render_home(dataset)
        return

    session = get_active_session()
    if st.session_state.app_mode == "quiz":
        render_quiz(session)
        return

    if st.session_state.app_mode == "review":
        render_review(session)
        return

    reset_app_state()
    st.rerun()


if __name__ == "__main__":
    main()
