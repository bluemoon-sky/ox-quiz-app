import re
import random
import time
import pandas as pd
import streamlit as st

st.set_page_config(page_title="OX 퀴즈", page_icon="✅", layout="centered")

# =========================
# 텍스트 파서
# =========================
# 한 줄 형식 예시:
#   질문문장 (O) [설명: 간단 해설] [오답: 틀리기 쉬운 포인트]
# 괄호 안의 O/X 는 필수, [설명:], [오답:]은 선택
ROW_RE = re.compile(
    r"""^\s*
        (?:\d+\.\s*|\*\s*)?                # (선택) 번호/불릿
        (?P<q>.+?)                         # 질문
        \s*\(\s*(?P<a>[OX])\s*\)\s*        # (O) 또는 (X)
        (?P<meta>(?:\[[^\]]+\]\s*)*)$      # (선택) [설명:...][오답:...]
    """,
    re.M | re.VERBOSE
)

META_RE = re.compile(r"\[\s*(설명|해설|오답|오답설명)\s*:\s*([^\]]+)\]")

def parse_questions(text: str):
    items = []
    for line in text.replace("\r\n", "\n").split("\n"):
        line = line.strip()
        if not line:
            continue
        m = ROW_RE.match(line)
        if not m:
            continue
        q = m.group("q").strip()
        a = m.group("a").strip().upper()
        meta = m.group("meta") or ""
        exp, exp_wrong = "", ""
        for k, v in META_RE.findall(meta):
            if k in ("설명", "해설"):
                exp = v.strip()
            elif k in ("오답", "오답설명"):
                exp_wrong = v.strip()
        items.append({"q": q, "a": a, "exp": exp, "exp_wrong": exp_wrong})
    return items

@st.cache_data(show_spinner=False)
def load_default_questions():
    # utf-8 / utf-8-sig 모두 시도
    for enc in ("utf-8", "utf-8-sig"):
        try:
            with open("ox문제.txt", "r", encoding=enc) as f:
                return parse_questions(f.read())
        except Exception:
            pass
    return []

# =========================
# 금액(원) 표기 보강
# =========================
UNIT_FACTORS = {
    "천원": 1_000,
    "만원": 10_000,
    "십만원": 100_000,
    "백만원": 1_000_000,
    "천만원": 10_000_000,
    "억원": 100_000_000,
}
# 3.5만원, 2억원, 12만 원 등 포착
MONEY_WITH_UNIT = re.compile(r"(\d+(?:\.\d+)?)\s*(천원|만원|십만원|백만원|천만원|억원)")
MONEY_WON = re.compile(r"(\d{1,3}(?:,\d{3})+|\d+)\s*원")

def enrich_money(text: str) -> str:
    """만원/억원 등 → 원 단위 환산값을 ( …원 )으로 덧붙여 정확히 보여줌."""
    def repl_unit(m):
        num = float(m.group(1))
        unit = m.group(2)
        factor = UNIT_FACTORS[unit]
        val = int(round(num * factor))
        return f"{m.group(0)}(={val:,}원)"
    text = MONEY_WITH_UNIT.sub(repl_unit, text)
    # 이미 '원'으로 끝나는 숫자는 콤마가 없다면 콤마 추가
    def repl_won(m):
        raw = m.group(1).replace(",", "")
        try:
            val = int(float(raw))
            return f"{val:,}원"
        except:
            return m.group(0)
    text = MONEY_WON.sub(repl_won, text)
    return text

# =========================
# 세션 상태 초기화
# =========================
def init_state():
    ss = st.session_state
    ss.setdefault("started", False)
    ss.setdefault("order", [])
    ss.setdefault("current", 0)
    ss.setdefault("answers", {})
    ss.setdefault("submitted", False)
    ss.setdefault("retry_mode", False)
    ss.setdefault("feedback", None)      # 정답/오답 메시지
    ss.setdefault("explain", None)       # 해설 문자열

init_state()

# =========================
# 스타일
# =========================
st.markdown("""
<style>
.quiz-card {
  background:#fff; padding:2rem; border-radius:1.5rem;
  box-shadow:0 4px 12px rgba(0,0,0,.12); text-align:center; margin-bottom:1.5rem;
}
.quiz-title { font-weight:800; font-size:1.3rem; margin-bottom:.6rem; }
.explain { background:#f7f9ff; border-left:6px solid #5b8def; padding:1rem 1.2rem; border-radius:.6rem; }
.explain h4 { margin:0 0 .3rem 0; font-size:1rem; }
.stButton button { height:3rem; font-size:1.05rem; font-weight:700; border-radius:.7rem; }
</style>
""", unsafe_allow_html=True)

# =========================
# 사이드바
# =========================
st.sidebar.title("⚙️ 설정")
uploaded = st.sidebar.file_uploader("퀴즈 텍스트 업로드 (.txt)", type=["txt"])

pool = parse_questions(uploaded.read().decode("utf-8", "ignore")) if uploaded else load_default_questions()
total = len(pool)
if total == 0:
    st.error("문제를 불러오지 못했습니다. `ox문제.txt` 형식을 확인하세요.")
    st.stop()

num_q = st.sidebar.slider("퀴즈 문제 수", 5, total, min(10, total))
shuffle = st.sidebar.checkbox("문항 섞기", True)
auto_next = st.sidebar.checkbox("정답 후 자동 넘김", True)
delay = st.sidebar.slider("자동 넘김 지연(초)", 1.0, 4.0, 2.0, .5)

def start_quiz():
    indices = list(range(total))
    if shuffle: random.shuffle(indices)
    st.session_state.order = indices[:num_q]
    st.session_state.current = 0
    st.session_state.answers = {}
    st.session_state.submitted = False
    st.session_state.retry_mode = False
    st.session_state.feedback = None
    st.session_state.explain = None
    st.session_state.started = True

if st.sidebar.button("🚀 시작"):
    start_quiz()

# =========================
# 메인
# =========================
st.title("🎯 OX 퀴즈")

if not st.session_state.started:
    st.info("좌측에서 문제 수를 정하고 **시작**을 눌러주세요.")
    st.stop()

order = st.session_state.order
n_total = len(order)

# 결과/종료 가드
if st.session_state.submitted or st.session_state.current >= n_total:
    st.session_state.submitted = True
    # 성적표
    rows, correct = [], 0
    for i, qidx in enumerate(order, 1):
        q = pool[qidx]["q"]; a = pool[qidx]["a"]
        u = st.session_state.answers.get(qidx, "")
        ok = (u == a); correct += int(ok)
        rows.append({"No.": i, "문제": q, "정답": a, "내 답": u or "무응답", "판정": "✅" if ok else "❌"})
    st.success(f"완료! 점수: **{correct}/{n_total}** ({round(correct/n_total*100,1)}%)")
    st.progress(correct / max(1, n_total))
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("📥 결과 CSV 다운로드", df.to_csv(index=False).encode("utf-8-sig"),
                           "ox_quiz_results.csv", "text/csv")

    # 오답 다시 풀기
    if not st.session_state.retry_mode:
        wrong = [i for i in order if st.session_state.answers.get(i, "") != pool[i]["a"]]
        if wrong and st.button("❗ 오답만 다시 풀기"):
            st.session_state.order = wrong
            st.session_state.current = 0
            st.session_state.answers = {}
            st.session_state.retry_mode = True
            st.session_state.submitted = False
            st.rerun()
        elif not wrong:
            st.info("완벽해요! 오답이 없습니다.")
    if st.button("🔄 처음부터 다시"):
        start_quiz(); st.rerun()
    st.stop()

# 현재 문제
qidx = order[st.session_state.current]
q = pool[qidx]["q"]; a = pool[qidx]["a"]
exp = pool[qidx]["exp"]; exp_wrong = pool[qidx]["exp_wrong"]

st.progress((st.session_state.current + 1) / n_total)
st.markdown(
    f"<div class='quiz-card'>"
    f"<div class='quiz-title'>문제 {st.session_state.current + 1} / {n_total}</div>"
    f"<div style='font-size:1.12rem;'>{q}</div></div>",
    unsafe_allow_html=True
)

# O / X 선택
c1, c2 = st.columns(2, gap="large")
def handle(choice):
    st.session_state.answers[qidx] = choice
    is_correct = (choice == a)
    # 메시지
    st.session_state.feedback = "✅ 정답입니다!" if is_correct else f"❌ 오답! 정답은 {a}"
    # 해설 선택(오답이면 오답 해설 우선)
    what = (exp if is_correct else (exp_wrong or exp)).strip()
    if what:
        st.session_state.explain = enrich_money(what)  # 금액 표기 보강
    else:
        st.session_state.explain = None
    st.rerun()

with c1:
    if st.button("⭕ O", use_container_width=True):
        handle("O")
with c2:
    if st.button("❌ X", use_container_width=True):
        handle("X")

# 피드백 + 해설 + 자동 넘김
if st.session_state.feedback:
    st.info(st.session_state.feedback)
    if st.session_state.explain:
        st.markdown(f"<div class='explain'><h4>해설</h4>{st.session_state.explain}</div>", unsafe_allow_html=True)

    coln1, coln2, coln3 = st.columns([1,1,1])
    with coln2:
        if st.button("➡️ 다음 문제", use_container_width=True):
            st.session_state.feedback = None
            st.session_state.explain = None
            st.session_state.current += 1
            if st.session_state.current >= n_total:
                st.session_state.submitted = True
            st.rerun()

    if auto_next:
        # 잠깐 읽을 수 있도록 지연 후 자동 이동
        time.sleep(float(delay))
        st.session_state.feedback = None
        st.session_state.explain = None
        st.session_state.current += 1
        if st.session_state.current >= n_total:
            st.session_state.submitted = True
        st.rerun()
