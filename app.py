
import re
import random
import pandas as pd
import streamlit as st

st.set_page_config(page_title="OX 퀴즈", page_icon="✅", layout="centered")

# -----------------------------
# Utilities
# -----------------------------
PATTERN = re.compile(r'^\s*(?:\d+\.\s*|\*\s*)?(?P<q>.+?)\s*\(\s*(?P<a>[OX])\s*\)?\s*$', re.M)

def parse_questions(text: str):
    """Parse lines like '1. 질문 (O)' or '* 질문 (X)' into [{'q':..., 'a':'O'|'X'}, ...].
       Robust to missing closing parenthesis and extra spaces.
    """
    items = []
    for m in PATTERN.finditer(text.replace('\r\n', '\n')):
        q = m.group('q').strip()
        a = m.group('a').strip().upper()
        if a not in ('O', 'X'):
            continue
        # Remove trailing punctuation like '.' at end of Korean sentences only if duplicated
        items.append({'q': q, 'a': a})
    # Deduplicate keeping order
    seen = set()
    uniq = []
    for it in items:
        key = (it['q'], it['a'])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(it)
    return uniq

@st.cache_data(show_spinner=False)
def load_default_questions():
    # Try local file first
    try_paths = ["ox문제.txt", "./ox문제.txt", "/app/ox문제.txt"]
    text = None
    for p in try_paths:
        try:
            with open(p, "r", encoding="utf-8") as f:
                text = f.read()
                break
        except Exception:
            try:
                with open(p, "r", encoding="utf-8-sig") as f:
                    text = f.read()
                    break
            except Exception:
                continue
    if text is None:
        return []
    return parse_questions(text)

def init_state():
    if "started" not in st.session_state:
        st.session_state.started = False
    if "pool" not in st.session_state:
        st.session_state.pool = []           # full list of questions
    if "order" not in st.session_state:
        st.session_state.order = []          # indices of questions used in this quiz
    if "answers" not in st.session_state:
        st.session_state.answers = {}        # idx -> 'O'/'X'
    if "current" not in st.session_state:
        st.session_state.current = 0
    if "submitted" not in st.session_state:
        st.session_state.submitted = False

init_state()

# -----------------------------
# Sidebar - controls
# -----------------------------
st.sidebar.title("⚙️ 설정")
uploaded = st.sidebar.file_uploader("퀴즈 텍스트 업로드 (예: '질문 (O)')", type=["txt"])

if uploaded is not None:
    try:
        txt = uploaded.read().decode("utf-8")
    except UnicodeDecodeError:
        txt = uploaded.read().decode("utf-8-sig", errors="ignore")
    pool = parse_questions(txt)
else:
    pool = load_default_questions()

st.session_state.pool = pool

total = len(pool)
st.sidebar.markdown(f"총 문제 수: **{total}**")

if total == 0:
    st.error("문제를 불러오지 못했습니다. 좌측에서 `ox문제.txt`를 업로드하거나 앱과 같은 폴더에 파일을 두세요.")
    st.stop()

num_q = st.sidebar.slider("퀴즈 문제 수", min_value=5, max_value=total, value=min(20, total), step=1)
shuffle = st.sidebar.checkbox("문항 섞기", value=True)

col_a, col_b = st.sidebar.columns(2)
def start_quiz():
    st.session_state.started = True
    indices = list(range(len(st.session_state.pool)))
    if shuffle:
        random.shuffle(indices)
    st.session_state.order = indices[:num_q]
    st.session_state.answers = {}
    st.session_state.current = 0
    st.session_state.submitted = False

def reset_quiz():
    st.session_state.started = False
    st.session_state.order = []
    st.session_state.answers = {}
    st.session_state.current = 0
    st.session_state.submitted = False

with col_a:
    if st.button("🚀 시작", use_container_width=True):
        start_quiz()
with col_b:
    if st.button("🔁 초기화", use_container_width=True):
        reset_quiz()

# -----------------------------
# Main UI
# -----------------------------
st.title("✅ OX 퀴즈")
st.caption("텍스트파일에서 불러온 OX 문제로 퀴즈를 풀어보세요. (형식: `질문 (O)` 또는 `질문 (X)`)")

if not st.session_state.started:
    st.subheader("미리보기")
    preview = pd.DataFrame(st.session_state.pool)[: min(10, total)]
    st.dataframe(preview, use_container_width=True, hide_index=True)
    st.info("좌측에서 문제 수를 선택한 뒤 **시작**을 눌러주세요.")
    st.stop()

order = st.session_state.order
idx = order[st.session_state.current]
q = st.session_state.pool[idx]["q"]
a = st.session_state.pool[idx]["a"]

st.progress((st.session_state.current + 1) / len(order))
st.subheader(f"문제 {st.session_state.current + 1} / {len(order)}")
choice = st.radio(q, options=["O", "X"], index=0 if st.session_state.answers.get(idx, None) == "O" else (1 if st.session_state.answers.get(idx, None) == "X" else 0), horizontal=True)

# Save choice when changed
st.session_state.answers[idx] = choice

nav1, nav2, nav3 = st.columns(3)
with nav1:
    if st.button("⬅️ 이전", disabled=st.session_state.current == 0, use_container_width=True):
        st.session_state.current -= 1
        st.rerun()
with nav2:
    if st.button("제출", disabled=st.session_state.submitted, use_container_width=True):
        st.session_state.submitted = True
        st.rerun()
with nav3:
    if st.button("다음 ➡️", disabled=st.session_state.current >= len(order) - 1, use_container_width=True):
        st.session_state.current += 1
        st.rerun()

# -----------------------------
# Results
# -----------------------------
if st.session_state.submitted:
    # Build results
    rows = []
    correct_count = 0
    for i, qidx in enumerate(order, start=1):
        qtext = st.session_state.pool[qidx]["q"]
        correct = st.session_state.pool[qidx]["a"]
        user = st.session_state.answers.get(qidx, "")
        ok = (user == correct)
        correct_count += int(ok)
        rows.append({
            "No.": i,
            "문제": qtext,
            "정답": correct,
            "내 답": user if user else "무응답",
            "판정": "✅ 정답" if ok else "❌ 오답"
        })
    df = pd.DataFrame(rows)
    score_pct = round(correct_count / len(order) * 100, 1)
    st.success(f"점수: **{correct_count} / {len(order)}**  ({score_pct}%)")
    st.dataframe(df, use_container_width=True, hide_index=True)

    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 결과 CSV 다운로드", csv, file_name="ox_quiz_results.csv", mime="text/csv")

    st.info("다시 풀려면 좌측의 **초기화**를 누른 뒤 **시작**하세요.")
