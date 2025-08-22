import re
import random
import time
import pandas as pd
import streamlit as st

st.set_page_config(page_title="OX 퀴즈", page_icon="✅", layout="centered")

# -----------------------------
# 문제 파싱 함수
# -----------------------------
PATTERN = re.compile(r'^\s*(?:\d+\.\s*|\*\s*)?(?P<q>.+?)\s*\(\s*(?P<a>[OX])\s*\)?\s*$', re.M)

def parse_questions(text: str):
    items = []
    for m in PATTERN.finditer(text.replace('\r\n', '\n')):
        q = m.group('q').strip()
        a = m.group('a').strip().upper()
        if a not in ('O', 'X'):
            continue
        items.append({'q': q, 'a': a})
    return items

@st.cache_data(show_spinner=False)
def load_default_questions():
    try:
        with open("ox문제.txt", "r", encoding="utf-8") as f:
            text = f.read()
        return parse_questions(text)
    except Exception:
        return []

# -----------------------------
# 세션 상태 초기화
# -----------------------------
def init_state():
    if "started" not in st.session_state:
        st.session_state.started = False
    if "order" not in st.session_state:
        st.session_state.order = []
    if "current" not in st.session_state:
        st.session_state.current = 0
    if "answers" not in st.session_state:
        st.session_state.answers = {}
    if "wrong" not in st.session_state:
        st.session_state.wrong = []
    if "submitted" not in st.session_state:
        st.session_state.submitted = False
    if "retry_mode" not in st.session_state:
        st.session_state.retry_mode = False
    if "feedback" not in st.session_state:
        st.session_state.feedback = None

init_state()

# -----------------------------
# 스타일 (CSS)
# -----------------------------
st.markdown("""
    <style>
    .quiz-card {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        text-align: center;
        margin-bottom: 2rem;
    }
    .quiz-question {
        font-size: 1.3rem;
        font-weight: bold;
        margin-bottom: 1.5rem;
    }
    .stButton button {
        height: 3rem;
        font-size: 1.2rem;
        font-weight: bold;
        border-radius: 0.7rem;
    }
    .btn-o button {
        background-color: #2ecc71 !important;
        color: white !important;
    }
    .btn-x button {
        background-color: #e74c3c !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------
# 사이드바
# -----------------------------
st.sidebar.title("⚙️ 설정")
uploaded = st.sidebar.file_uploader("퀴즈 텍스트 업로드", type=["txt"])

if uploaded is not None:
    text = uploaded.read().decode("utf-8")
    pool = parse_questions(text)
else:
    pool = load_default_questions()

total = len(pool)
if total == 0:
    st.error("문제를 불러오지 못했습니다. `ox문제.txt`를 확인하세요.")
    st.stop()

num_q = st.sidebar.slider("퀴즈 문제 수", min_value=5, max_value=total, value=min(10, total))
shuffle = st.sidebar.checkbox("문항 섞기", value=True)

def start_quiz():
    indices = list(range(total))
    if shuffle:
        random.shuffle(indices)
    st.session_state.order = indices[:num_q]
    st.session_state.current = 0
    st.session_state.answers = {}
    st.session_state.wrong = []
    st.session_state.submitted = False
    st.session_state.retry_mode = False
    st.session_state.feedback = None
    st.session_state.started = True

if st.sidebar.button("🚀 시작"):
    start_quiz()

# -----------------------------
# 메인 화면
# -----------------------------
st.title("🎯 OX 퀴즈")

if not st.session_state.started:
    st.info("좌측에서 문제 수를 선택한 뒤 **시작** 버튼을 눌러주세요.")
    st.stop()

order = st.session_state.order
idx = st.session_state.order[st.session_state.current]
q = pool[idx]["q"]
a = pool[idx]["a"]

st.progress((st.session_state.current + 1) / len(order))
st.markdown(f"<div class='quiz-card'><div class='quiz-question'>문제 {st.session_state.current+1} / {len(order)}<br><br>{q}</div></div>", unsafe_allow_html=True)

# -----------------------------
# 선택 버튼 (O, X)
# -----------------------------
col1, col2 = st.columns(2)
with col1:
    if st.button("⭕ O", key=f"O_{idx}"):
        st.session_state.answers[idx] = "O"
        if "O" == a:
            st.session_state.feedback = "✅ 정답입니다!"
        else:
            st.session_state.feedback = f"❌ 오답! 정답은 {a}"
            if idx not in st.session_state.wrong:
                st.session_state.wrong.append(idx)
        st.rerun()

with col2:
    if st.button("❌ X", key=f"X_{idx}"):
        st.session_state.answers[idx] = "X"
        if "X" == a:
            st.session_state.feedback = "✅ 정답입니다!"
        else:
            st.session_state.feedback = f"❌ 오답! 정답은 {a}"
            if idx not in st.session_state.wrong:
                st.session_state.wrong.append(idx)
        st.rerun()

# -----------------------------
# 정답 피드백 표시 후 자동 다음 문제
# -----------------------------
if st.session_state.feedback:
    st.info(st.session_state.feedback)
    # 1초 후 다음 문제로
    time.sleep(1)
    st.session_state.feedback = None
    st.session_state.current += 1
    if st.session_state.current >= len(order):
        st.session_state.submitted = True
    st.rerun()

# -----------------------------
# 결과 화면
# -----------------------------
if st.session_state.submitted:
    if st.session_state.wrong and not st.session_state.retry_mode:
        st.warning(f"오답이 {len(st.session_state.wrong)}개 있습니다. 다시 풀어보세요!")
        if st.button("❗ 오답만 다시 풀기"):
            st.session_state.order = st.session_state.wrong
            st.session_state.current = 0
            st.session_state.wrong = []
            st.session_state.retry_mode = True
            st.session_state.submitted = False
            st.rerun()
    else:
        score = sum(1 for i in st.session_state.answers if pool[i]["a"] == st.session_state.answers[i])
        st.success("🎉 퀴즈 완료!")
        st.write(f"최종 점수: **{score} / {len(order)}**")
        st.progress(score/len(order))
