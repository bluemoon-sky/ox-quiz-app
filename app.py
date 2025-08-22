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
    # utf-8 또는 utf-8-sig 모두 시도
    for enc in ("utf-8", "utf-8-sig"):
        try:
            with open("ox문제.txt", "r", encoding=enc) as f:
                text = f.read()
            return parse_questions(text)
        except Exception:
            continue
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
st.markdown(
    """
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
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .stButton button {
        height: 3rem;
        font-size: 1.1rem;
        font-weight: 700;
        border-radius: 0.7rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# 사이드바
# -----------------------------
st.sidebar.title("⚙️ 설정")
uploaded = st.sidebar.file_uploader("퀴즈 텍스트 업로드", type=["txt"])

if uploaded is not None:
    try:
        text = uploaded.read().decode("utf-8")
    except UnicodeDecodeError:
        text = uploaded.read().decode("utf-8-sig", errors="ignore")
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

def reset_all():
    st.session_state.started = False
    st.session_state.order = []
    st.session_state.current = 0
    st.session_state.answers = {}
    st.session_state.wrong = []
    st.session_state.submitted = False
    st.session_state.retry_mode = False
    st.session_state.feedback = None

if st.sidebar.button("🚀 시작"):
    start_quiz()
if st.sidebar.button("🔁 초기화"):
    reset_all()
    st.rerun()

# -----------------------------
# 메인 화면
# -----------------------------
st.title("🎯 OX 퀴즈")

if not st.session_state.started:
    st.info("좌측에서 문제 수를 선택한 뒤 **시작** 버튼을 눌러주세요.")
    st.stop()

order = st.session_state.order
total_in_quiz = len(order)

# ✅ 결과/종료 가드 (마지막 문항을 풀고 난 후 인덱스 에러 방지)
if st.session_state.submitted or st.session_state.current >= total_in_quiz:
    st.session_state.submitted = True  # 보수적 설정

    # 결과 요약
    rows, correct_cnt = [], 0
    for i, qidx in enumerate(order, start=1):
        qtext = pool[qidx]["q"]
        correct = pool[qidx]["a"]
        user = st.session_state.answers.get(qidx, "")
        ok = (user == correct)
        correct_cnt += int(ok)
        rows.append(
            {
                "No.": i,
                "문제": qtext,
                "정답": correct,
                "내 답": user if user else "무응답",
                "판정": "✅ 정답" if ok else "❌ 오답",
            }
        )

    score_pct = round((correct_cnt / max(1, total_in_quiz)) * 100, 1)
    st.success(f"🎉 퀴즈 완료! 점수: **{correct_cnt} / {total_in_quiz}** ({score_pct}%)")
    st.progress(correct_cnt / max(1, total_in_quiz))

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 결과 CSV 다운로드", csv, file_name="ox_quiz_results.csv", mime="text/csv")

    # 오답 다시 풀기 / 처음부터
    if not st.session_state.retry_mode:
        wrong_list = [idx for idx in order if st.session_state.answers.get(idx, "") != pool[idx]["a"]]
        if wrong_list:
            if st.button("❗ 오답만 다시 풀기"):
                st.session_state.order = wrong_list
                st.session_state.current = 0
                st.session_state.answers = {}
                st.session_state.wrong = []
                st.session_state.retry_mode = True
                st.session_state.submitted = False
                st.rerun()
        else:
            st.info("완벽해요! 오답이 없습니다.")

    if st.button("🔄 처음부터 다시"):
        start_quiz()
        st.rerun()

    st.stop()  # ✅ 결과 화면에서 종료

# ---- 여기서부터는 실제 문제 화면 ----
idx = order[st.session_state.current]
q = pool[idx]["q"]
a = pool[idx]["a"]

st.progress((st.session_state.current + 1) / total_in_quiz)
st.markdown(
    f"<div class='quiz-card'><div class='quiz-question'>문제 {st.session_state.current+1} / {total_in_quiz}</div>"
    f"<div style='font-size:1.15rem; margin-top:0.8rem;'>{q}</div></div>",
    unsafe_allow_html=True,
)

# 선택 버튼 (O / X)
c1, c2 = st.columns(2)
with c1:
    if st.button("⭕", key=f"O_{idx}", use_container_width=True):
        st.session_state.answers[idx] = "O"
        st.session_state.feedback = "✅ 정답입니다!" if a == "O" else f"❌ 오답! 정답은 {a}"
        if a != "O" and idx not in st.session_state.wrong:
            st.session_state.wrong.append(idx)
        st.rerun()

with c2:
    if st.button("❌", key=f"X_{idx}", use_container_width=True):
        st.session_state.answers[idx] = "X"
        st.session_state.feedback = "✅ 정답입니다!" if a == "X" else f"❌ 오답! 정답은 {a}"
        if a != "X" and idx not in st.session_state.wrong:
            st.session_state.wrong.append(idx)
        st.rerun()

# 피드백 → 자동 다음 문제
if st.session_state.feedback:
    st.info(st.session_state.feedback)
    time.sleep(1)  # 짧은 대기 후
    st.session_state.feedback = None
    st.session_state.current += 1
    if st.session_state.current >= total_in_quiz:
        st.session_state.submitted = True
    st.rerun()
