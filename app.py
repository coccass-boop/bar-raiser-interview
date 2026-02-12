import streamlit as st
import requests
import json
import base64
import datetime
from bs4 import BeautifulSoup

# --- 1. 페이지 설정 및 붕괴 방지용 강격 CSS ---
st.set_page_config(page_title="Bar Raiser Copilot", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    /* 1. 글자 깨짐(세로 쏟아짐) 원천 차단 */
    [data-testid="column"] {
        min-width: 300px !important; /* 열의 최소 너비를 보장하여 글자 쏟아짐 방지 */
    }
    .stMarkdown p, .stSubheader {
        word-break: keep-all !important;
        white-space: normal !important;
    }

    /* 2. 아이콘 버튼(🔄, ➕, ✕) 수직 중앙 정렬 */
    .v-center {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        height: 100% !important;
        padding-top: 10px !important;
    }
    .v-center button {
        height: 32px !important;
        width: 32px !important;
        padding: 0px !important;
    }

    /* 3. 텍스트 겹침 방지 여백 */
    .q-block {
        margin-bottom: 15px !important;
        padding-bottom: 5px !important;
    }
    .q-text {
        font-size: 16px !important;
        font-weight: 600 !important;
        line-height: 1.6 !important;
        margin-bottom: 8px !important;
    }

    /* 4. 사이드바 버튼 정렬 */
    [data-testid="stSidebar"] .stButton button {
        width: 100% !important;
        height: auto !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API 키 및 데이터 초기화 ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("🚨 API 키를 설정해주세요.")
    st.stop()

if "ai_questions" not in st.session_state:
    st.session_state.ai_questions = {"Transform": [], "Tomorrow": [], "Together": []}
if "selected_questions" not in st.session_state:
    st.session_state.selected_questions = []
if "wide_mode" not in st.session_state:
    st.session_state.wide_mode = False

BAR_RAISER_CRITERIA = {
    "Transform": "Create Enduring Value",
    "Tomorrow": "Forward Thinking",
    "Together": "Trust & Growth"
}

LEVEL_GUIDELINES = {
    "IC-L3": "[기본기 실무자] 가이드 하 업무 수행, 기초 지식 학습.",
    "IC-L4": "[자기완결 실무자] 목표 내 업무 독립적 계획/실행.",
    "IC-L5": "[핵심 전문가] 최적 대안 제시 및 전파, 복잡 문제 해결.",
    "IC-L6": "[선도적 전문가] 파트 리드, 성과 선순환 구조 구축.",
    "IC-L7": "[최고 권위자] 전사 혁신 주도, 업계 표준 정의.",
    "M-L5": "[유닛 리더] 과제 운영 및 프로젝트 성공 리딩.",
    "M-L6": "[시니어 리더] 유닛 성과 및 육성 관리.",
    "M-L7": "[디렉터] 전략 방향 및 조직 시너시 총괄."
}

# --- 3. 핵심 함수 ---
def fetch_jd(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            return soup.get_text(separator='\n', strip=True)
    except: return None

def generate_questions_by_category(category, level, resume_file, jd_text):
    prompt = f"[Role] Bar Raiser. [Value] {BAR_RAISER_CRITERIA[category]}. [Task] 10 Questions JSON List: [{{'q': '질문', 'i': '의도'}}, ...]"
    try:
        pdf_base64 = base64.b64encode(resume_file.getvalue()).decode('utf-8')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={API_KEY}"
        data = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "application/pdf", "data": pdf_base64}}]}]}
        res = requests.post(url, json=data, timeout=60)
        cleaned = res.json()['candidates'][0]['content']['parts'][0]['text'].replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except: return []

# --- 4. 사이드바 (레벨 설명 상시 노출) ---
with st.sidebar:
    st.title("✈️ Copilot Menu")
    selected_level = st.selectbox("1. 레벨 선택", list(LEVEL_GUIDELINES.keys()))
    st.info(f"💡 {LEVEL_GUIDELINES[selected_level]}")
    
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
        else: st.error("이력서와 JD를 확인해주세요.")

# --- 5. 메인 화면 ---
st.title("✈️ Bar Raiser Copilot")
st.divider()

# [레이아웃 핵심] 버튼으로 모드 전환
btn_label = "🔙 면접관 노트 다시 열기" if st.session_state.wide_mode else "↔️ 질문 리스트 넓게 보기 (노트 접기)"
if st.button(btn_label):
    st.session_state.wide_mode = not st.session_state.wide_mode
    st.rerun()

# [질문 리스트 출력 함수]
def render_questions():
    st.subheader("🎯 제안 질문 리스트")
    for cat in ["Transform", "Tomorrow", "Together"]:
        with st.expander(f"📌 {cat}({BAR_RAISER_CRITERIA[cat]}) 리스트", expanded=True):
            # 새로고침 버튼 수직 중앙 정렬
            c1, c2 = st.columns([0.9, 0.1])
            with c2:
                st.markdown('<div class="v-center">', unsafe_allow_html=True)
                if st.button("🔄", key=f"ref_{cat}"):
                    if resume_file and jd_final:
                        st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final)
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.divider()
            for i, q in enumerate(st.session_state.ai_questions[cat]):
                q_text = q.get('q', '질문 데이터 오류')
                i_text = q.get('i', '의도 데이터 오류')
                
                # + 버튼 수직 중앙 정렬
                qc, ac = st.columns([0.9, 0.1])
                with qc:
                    st.markdown(f"<div class='q-block'><div class='q-text'>Q. {q_text}</div>", unsafe_allow_html=True)
                    st.caption(f"🎯 의도: {i_text}")
                    st.markdown("</div>", unsafe_allow_html=True)
                with ac:
                    st.markdown('<div class="v-center">', unsafe_allow_html=True)
                    if st.button("➕", key=f"add_{cat}_{i}"):
                        if q_text not in [sq['q'] for sq in st.session_state.selected_questions]:
                            st.session_state.selected_questions.append({"q": q_text, "cat": cat, "memo": ""})
                    st.markdown('</div>', unsafe_allow_html=True)
                st.divider()

# [모드에 따른 레이아웃 렌더링]
if st.session_state.wide_mode:
    # 와이드 모드: 단일 컨테이너로 전체 화면 사용 (절대 안 깨짐)
    render_questions()
else:
    # 일반 모드: 질문(1.2) : 노트(1) 비율 유지
    col_left, col_right = st.columns([1.2, 1])
    with col_left:
        render_questions()
    with col_right:
        st.subheader("📝 면접관 노트")
        if st.button("➕ 질문을 직접 입력하세요.", use_container_width=True):
            st.session_state.selected_questions.append({"q": "", "cat": "Custom", "memo": ""})
        
        st.divider()
        for idx, item in enumerate(st.session_state.selected_questions):
            # ✕ 버튼 수직 중앙 정렬
            t_col, d_col = st.columns([0.9, 0.1])
            with t_col:
                st.markdown(f"<span style='font-size:0.8rem; color:gray;'>Q{idx+1}</span> <span style='background-color:#f0f2f6; padding:2px 6px; border-radius:4px; font-size:0.7rem; font-weight:bold;'>{item.get('cat','Custom')}</span>", unsafe_allow_html=True)
            with d_col:
                st.markdown('<div class="v-center">', unsafe_allow_html=True)
                if st.button("✕", key=f"del_{idx}"):
                    st.session_state.selected_questions.pop(idx)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            # 질문 및 메모창
            q_val = item.get('q','')
            q_h = max(80, (len(q_val) // 35) * 25 + 35)
            st.session_state.selected_questions[idx]['q'] = st.text_area(f"q_note_{idx}", value=q_val, label_visibility="collapsed", height=q_h, key=f"area_q_{idx}")
            st.session_state.selected_questions[idx]['memo'] = st.text_area(f"m_note_{idx}", value=item.get('memo',''), placeholder="답변 메모...", label_visibility="collapsed", height=150, key=f"area_m_{idx}")
            st.markdown("<div style='margin-bottom:15px; border-bottom:1px solid #eee;'></div>", unsafe_allow_html=True)

        if st.session_state.selected_questions:
            output = f"Target: {selected_level}\n" + "\n".join([f"[{s.get('cat','Custom')}] Q: {s.get('q','')}\nA: {s.get('memo','')}" for s in st.session_state.selected_questions])
            st.download_button("💾 결과 저장 (.txt)", output, f"Interview.txt", type="primary", use_container_width=True)
