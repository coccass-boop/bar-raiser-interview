import streamlit as st
import requests
import json
import base64
import datetime
from bs4 import BeautifulSoup

# --- 1. 페이지 설정 및 섬세한 UI 보정 CSS (정렬 고정) ---
st.set_page_config(page_title="Bar Raiser Copilot", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    /* 1. 글자 깨짐 방지 및 최소 너비 확보 */
    [data-testid="column"] { min-width: 320px !important; }
    .stMarkdown p, .stSubheader { word-break: keep-all !important; }

    /* 2. 아이콘 버튼(🔄, ➕, ✕) 수직 중앙 정렬 (선생님 확정안) */
    .v-center {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        height: 100% !important;
        padding-top: 10px !important;
    }
    .v-center button { height: 32px !important; width: 32px !important; padding: 0px !important; }

    /* 3. 텍스트 겹침 방지 여백 */
    .q-block { margin-bottom: 15px !important; padding-bottom: 5px !important; }
    .q-text { font-size: 16px !important; font-weight: 600 !important; line-height: 1.6 !important; margin-bottom: 8px !important; }

    /* 4. 사이드바 버튼 정렬 */
    [data-testid="stSidebar"] .stButton button { width: 100% !important; height: auto !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 및 세션 초기화 ---
if "ai_questions" not in st.session_state:
    st.session_state.ai_questions = {"Transform": [], "Tomorrow": [], "Together": []}
if "selected_questions" not in st.session_state:
    st.session_state.selected_questions = []
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Standard" 

BAR_RAISER_CRITERIA = {
    "Transform": "Create Enduring Value",
    "Tomorrow": "Forward Thinking",
    "Together": "Trust & Growth"
}

LEVEL_GUIDELINES = {
    "IC-L3": "[기본기 실무자] 가이드 하 업무 수행.", "IC-L4": "[자기완결 실무자] 목표 내 실행.",
    "IC-L5": "[핵심 전문가] 문제 해결 주도.", "IC-L6": "[선도적 전문가] 파트 리드.",
    "IC-L7": "[최고 권위자] 전사 혁신.", "M-L5": "[유닛 리더] 과제 운영.",
    "M-L6": "[시니어 리더] 육성 관리.", "M-L7": "[디렉터] 전략 총괄."
}

# --- 3. 함수 정의 ---
def fetch_jd(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            return soup.get_text(separator='\n', strip=True)
    except: return None

def generate_questions_by_category(category, level, resume_file, jd_text):
    prompt = f"[Role] Bar Raiser. [Value] {BAR_RAISER_CRITERIA[category]}. [Task] 10 Questions JSON List. [Format] {{'q': '질문', 'i': '의도'}}"
    try:
        pdf_base64 = base64.b64encode(resume_file.getvalue()).decode('utf-8')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={API_KEY}"
        data = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "application/pdf", "data": pdf_base64}}]}]}
        res = requests.post(url, json=data, timeout=60)
        cleaned = res.json()['candidates'][0]['content']['parts'][0]['text'].replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except: return []

# --- 4. 사이드바 ---
with st.sidebar:
    st.title("✈️ Copilot Menu")
    
    # [추가] 후보자 이름 입력란
    candidate_name = st.text_input("👤 후보자 이름", placeholder="이름을 입력하세요")
    
    selected_level = st.selectbox("1. 레벨 선택", list(LEVEL_GUIDELINES.keys()))
    st.info(f"💡 {LEVEL_GUIDELINES[selected_level]}")
    
    st.subheader("2. JD (채용공고)")
    tab1, tab2 = st.tabs(["🔗 URL", "📝 텍스트"])
    with tab1:
        url_input = st.text_input("URL 입력")
        jd_from_url = fetch_jd(url_input) if url_input else ""
    with tab2:
        jd_from_text = st.text_area("내용 붙여넣기", height=150)
    jd_final = jd_from_text if jd_from_text else jd_from_url

    resume_file = st.file_uploader("PDF 업로드", type="pdf")
    st.divider()
    if st.button("질문 생성 시작 🚀", type="primary", use_container_width=True):
        if resume_file and jd_final:
            with st.spinner("질문 설계 중..."):
                for cat in ["Transform", "Tomorrow", "Together"]:
                    st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final)
        else: st.error("정보를 입력해주세요.")

# --- 5. 메인 화면 ---
st.title("✈️ Bar Raiser Copilot")

# 레이아웃 모드 전환 버튼
c_v1, c_v2, c_v3 = st.columns(3)
if c_v1.button("↔️ 질문 리스트만 보기", use_container_width=True):
    st.session_state.view_mode = "QuestionWide"
    st.rerun()
if c_v2.button("⬅️ 기본 보기 (반반)", use_container_width=True):
    st.session_state.view_mode = "Standard"
    st.rerun()
if c_v3.button("↔️ 면접관 노트만 보기", use_container_width=True):
    st.session_state.view_mode = "NoteWide"
    st.rerun()

st.divider()

# [함수화] 제안 질문 리스트 렌더링
def render_questions():
    st.subheader("🎯 제안 질문 리스트")
    for cat in ["Transform", "Tomorrow", "Together"]:
        with st.expander(f"📌 {cat}({BAR_RAISER_CRITERIA[cat]}) 리스트", expanded=True):
            c1, c2 = st.columns([0.94, 0.06])
            with c2:
                st.markdown('<div class="v-center">', unsafe_allow_html=True)
                if st.button("🔄", key=f"ref_{cat}"):
                    if resume_file and jd_final:
                        st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final)
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            st.divider()
            for i, q in enumerate(st.session_state.ai_questions[cat]):
                q_val = q.get('q', '질문 없음')
                i_val = q.get('i', '의도 없음')
                qc, ac = st.columns([0.94, 0.06])
                with qc:
                    st.markdown(f"<div class='q-block'><div class='q-text'>Q. {q_val}</div>", unsafe_allow_html=True)
                    st.caption(f"🎯 의도: {i_val}")
                    st.markdown("</div>", unsafe_allow_html=True)
                with ac:
                    st.markdown('<div class="v-center">', unsafe_allow_html=True)
                    if st.button("➕", key=f"add_{cat}_{i}"):
                        if q_val not in [sq['q'] for sq in st.session_state.selected_questions]:
                            st.session_state.selected_questions.append({"q": q_val, "cat": cat, "memo": ""})
                    st.markdown('</div>', unsafe_allow_html=True)
                st.divider()

# [함수화] 면접관 노트 렌더링
def render_notes():
    st.subheader("📝 면접관 노트")
    if st.button("➕ 질문을 직접 입력하세요.", use_container_width=True):
        st.session_state.selected_questions.append({"q": "", "cat": "Custom", "memo": ""})
    
    st.divider()
    for idx, item in enumerate(st.session_state.selected_questions):
        t_col, d_col = st.columns([0.94, 0.06])
        with t_col:
            st.markdown(f"<span style='font-size:0.8rem; color:gray;'>Q{idx+1}</span> <span style='background-color:#f0f2f6; padding:2px 6px; border-radius:4px; font-size:0.7rem; font-weight:bold;'>{item.get('cat','Custom')}</span>", unsafe_allow_html=True)
        with d_col:
            st.markdown('<div class="v-center">', unsafe_allow_html=True)
            if st.button("✕", key=f"del_{idx}"):
                st.session_state.selected_questions.pop(idx)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        q_val = item.get('q','')
        q_h = max(80, (len(q_val) // 35) * 25 + 35)
        st.session_state.selected_questions[idx]['q'] = st.text_area(f"qn_{idx}", value=q_val, label_visibility="collapsed", height=q_h, key=f"aq_{idx}")
        st.session_state.selected_questions[idx]['memo'] = st.text_area(f"mn_{idx}", value=item.get('memo',''), placeholder="답변 메모...", label_visibility="collapsed", height=150, key=f"am_{idx}")
        st.markdown("<div style='margin-bottom:15px; border-bottom:1px solid #eee;'></div>", unsafe_allow_html=True)

    if st.session_state.selected_questions:
        # [수정] 저장 파일에 후보자 이름 및 날짜 포함
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        txt_output = f"Bar Raiser Interview Evaluation\n"
        txt_output += f"후보자: {candidate_name if candidate_name else '미입력'}\n"
        txt_output += f"레벨: {selected_level}\n"
        txt_output += f"일시: {timestamp}\n"
        txt_output += "="*40 + "\n"
        for s in st.session_state.selected_questions:
            txt_output += f"\n[{s.get('cat','Custom')}] \nQ: {s.get('q','')}\nA: {s.get('memo','')}\n" + "-"*20
        
        st.download_button("💾 면접 결과 저장 (.txt)", txt_output, f"Result_{candidate_name}_{selected_level}.txt", type="primary", use_container_width=True)

# 레이아웃 실행
if st.session_state.view_mode == "QuestionWide":
    render_questions()
elif st.session_state.view_mode == "NoteWide":
    render_notes()
else:
    col_l, col_r = st.columns([1.1, 1])
    with col_l: render_questions()
    with col_r: render_notes()
