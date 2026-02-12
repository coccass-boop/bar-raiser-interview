import streamlit as st
import requests
import json
import base64
import datetime
from bs4 import BeautifulSoup

# --- 1. 페이지 설정 및 CSS 주입 ---
st.set_page_config(page_title="Bar Raiser Copilot", page_icon="✈️", layout="wide")

# 가독성을 위한 커스텀 폰트 스타일링
st.markdown("""
    <style>
    .main-header {
        font-size: 22px !important;
        font-weight: 800 !important;
        color: #1E1E1E;
        margin-bottom: 10px;
    }
    .stTextArea textarea {
        font-size: 16px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API 키 설정 ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("🚨 API 키를 설정해주세요.")
    st.stop()

# --- 3. 세션 상태 초기화 ---
if "ai_questions" not in st.session_state:
    st.session_state.ai_questions = {"Transform": [], "Tomorrow": [], "Together": []}
if "selected_questions" not in st.session_state:
    st.session_state.selected_questions = []
if "focus_mode" not in st.session_state:
    st.session_state.focus_mode = False # 질문 리스트 넓게 보기 모드

LEVEL_GUIDELINES = {
    "IC-L3": "[기본기 실무자] 가이드 하 업무 수행, 기초 지식 학습.",
    "IC-L4": "[자기완결 실무자] 목표 내 업무 독립적 계획/실행.",
    "IC-L5": "[핵심 전문가] 최적 대안 제시 및 전파, 복잡 문제 해결.",
    "IC-L6": "[선도적 전문가] 파트 리드, 성과 선순환 구조 구축.",
    "IC-L7": "[전사 혁신 주도] 업계 표준 정의 최고 수준 전문성.",
    "M-L5": "[유닛 리더] 과제 운영 및 프로젝트 성공 리딩.",
    "M-L6": "[시니어 리더] 유닛 성과 및 육성 관리.",
    "M-L7": "[디렉터] 전략 방향 및 조직 시너시 총괄."
}

# --- 4. 함수 정의 ---
def fetch_jd(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            return soup.get_text(separator='\n', strip=True)
    except: return None

def generate_questions_by_category(category, level, resume_file, jd_text):
    prompt = f"""
    [Role] Bar Raiser Interviewer. Framework: Trinity Values.
    [Target] {level}. [Category] {category}.
    [JD] {jd_text[:3000]}
    [Task] Create 10 unique questions in Korean for '{category}'. 
    [Format] JSON ONLY: [{{"q": "질문", "i": "의도"}}, ...]
    """
    try:
        pdf_base64 = base64.b64encode(resume_file.getvalue()).decode('utf-8')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={API_KEY}"
        data = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "application/pdf", "data": pdf_base64}}]}]}
        res = requests.post(url, json=data, timeout=60)
        cleaned = res.json()['candidates'][0]['content']['parts'][0]['text'].replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except: return []

# --- 5. 사이드바 ---
with st.sidebar:
    st.title("✈️ Copilot Menu")
    selected_level = st.selectbox("레벨 선택", list(LEVEL_GUIDELINES.keys()))
    st.info(f"💡 {LEVEL_GUIDELINES[selected_level]}")
    
    tab1, tab2 = st.tabs(["🔗 URL", "📝 텍스트"])
    with tab1:
        url_input = st.text_input("URL 입력")
        jd_from_url = fetch_jd(url_input) if url_input else ""
    with tab2:
        jd_from_text = st.text_area("내용 붙여넣기", height=150)
    jd_final_content = jd_from_text if jd_from_text else jd_from_url

    resume_file = st.file_uploader("이력서 PDF", type="pdf")
    
    st.divider()
    if st.button("질문 생성 시작 🚀", type="primary", use_container_width=True):
        if resume_file and jd_final_content:
            with st.spinner("질문 분석 중..."):
                for cat in ["Transform", "Tomorrow", "Together"]:
                    st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final_content)
        else: st.error("이력서와 JD를 확인해주세요.")

# --- 6. 메인 화면 ---
st.title("✈️ Bar Raiser Copilot")

with st.expander("💎 Trinity Values (클릭하여 기준 확인)", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### **Transform**")
        st.caption("💡 Customer Innovation / 📈 Value Creation / 🎯 Excellence")
    with c2:
        st.markdown("#### **Tomorrow**")
        st.caption("🌱 Active Learning / 🚀 Forward Thinking / ⚡ Speed Impact")
    with c3:
        st.markdown("#### **Together**")
        st.caption("🤝 Power of Three / 💗 Trust & Growth / 🌐 Global Perspective")

st.divider()

# 레이아웃 모드 설정 (노트를 접으면 질문 리스트를 넓게)
if st.session_state.focus_mode:
    col_q_width, col_n_width = 10, 0.1
    focus_label = "🔙 원래대로 보기 (노트 열기)"
else:
    col_q_width, col_n_width = 1.1, 1
    focus_label = "↔️ 질문 리스트 넓게 보기"

col_q, col_n = st.columns([col_q_width, col_n_width])

# [왼쪽] 질문 리스트
with col_q:
    st.markdown(f'<p class="main-header">🤖 제안 질문 리스트</p>', unsafe_allow_html=True)
    if st.button(focus_label):
        st.session_state.focus_mode = not st.session_state.focus_mode
        st.rerun()

    for cat in ["Transform", "Tomorrow", "Together"]:
        # 굵은 글씨체 적용
        st.markdown(f'<p style="font-size: 18px; font-weight: 700; margin-top:20px;">📌 {cat} 리스트</p>', unsafe_allow_html=True)
        with st.container(border=True):
            h_col, b_col = st.columns([0.9, 0.1])
            if b_col.button("🔄", key=f"ref_{cat}", help="새로고침"):
                if resume_file and jd_final_content:
                    st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final_content)
                    st.rerun()
            
            if not st.session_state.ai_questions[cat]:
                st.write("질문이 없습니다. 사이드바에서 생성을 시작하세요.")
            
            for i, q in enumerate(st.session_state.ai_questions[cat]):
                qc, ac = st.columns([0.92, 0.08])
                qc.write(f"**Q. {q['q']}**")
                if ac.button("➕", key=f"add_{cat}_{i}"):
                    if q['q'] not in [sq['q'] for sq in st.session_state.selected_questions]:
                        st.session_state.selected_questions.append({"q": q['q'], "cat": cat, "memo": ""})
                st.caption(f"🎯 의도: {q['i']}")
                if i < len(st.session_state.ai_questions[cat]) - 1: st.divider()

# [오른쪽] 면접관 실시간 노트
if not st.session_state.focus_mode:
    with col_n:
        st.markdown(f'<p class="main-header">📝 면접관 실시간 노트</p>', unsafe_allow_html=True)
        with st.container(border=True):
            if st.button("➕ 개별 질문 추가", use_container_width=True):
                st.session_state.selected_questions.append({"q": "", "cat": "Custom", "memo": ""})
            
            st.divider()
            
            for idx, item in enumerate(st.session_state.selected_questions):
                # 헤더
                tag_col, del_col = st.columns([0.9, 0.1])
                category_label = item.get('cat', 'Custom')
                tag_col.markdown(f"<span style='font-size:0.85rem; color:gray;'>Q{idx+1}</span> <span style='background-color:#f0f2f6; padding:2px 6px; border-radius:4px; font-size:0.75rem; font-weight:bold;'>{category_label}</span>", unsafe_allow_html=True)
                
                if del_col.button("✕", key=f"del_{idx}"):
                    st.session_state.selected_questions.pop(idx)
                    st.rerun()
                
                # 질문 (전체가 보이도록 높이 조절)
                st.session_state.selected_questions[idx]['q'] = st.text_area(
                    f"q_input_{idx}", value=item['q'], 
                    placeholder="질문을 직접 입력하세요.",
                    label_visibility="collapsed", height=100, key=f"area_q_{idx}"
                )
                
                # 메모 (전체가 보이도록 높이 조절)
                st.session_state.selected_questions[idx]['memo'] = st.text_area(
                    f"m_input_{idx}", value=item.get('memo', ''),
                    placeholder="답변 메모 및 평가...", 
                    label_visibility="collapsed", height=150, key=f"area_m_{idx}"
                )
                st.markdown("<div style='margin-bottom:30px; border-bottom:1px solid #eee;'></div>", unsafe_allow_html=True)

            if st.session_state.selected_questions:
                out_data = f"Target: {selected_level}\n"
                for s in st.session_state.selected_questions:
                    out_data += f"\n[{s.get('cat', 'Custom')}] Q: {s['q']}\nA: {s.get('memo','')}\n"
                st.download_button("💾 결과 저장 (.txt)", out_data, f"Interview_Note.txt", type="primary", use_container_width=True)
