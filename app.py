import streamlit as st
import requests
import json
import base64
import datetime
from bs4 import BeautifulSoup

# --- 1. 디자인 CSS (선생님 확정안 100% 유지) ---
st.set_page_config(page_title="Bar Raiser Copilot", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    [data-testid="column"] { min-width: 320px !important; }
    .v-center {
        display: flex !important; align-items: center !important; justify-content: center !important;
        height: 100% !important; padding-top: 10px !important;
    }
    .v-center button { height: 32px !important; width: 32px !important; padding: 0px !important; }
    .q-block { margin-bottom: 15px !important; padding-bottom: 5px !important; }
    .q-text { font-size: 16px !important; font-weight: 600 !important; line-height: 1.6 !important; margin-bottom: 8px !important; }
    [data-testid="stSidebar"] .stButton button { width: 100% !important; height: auto !important; }
    .reset-btn button { background-color: #ff4b4b !important; color: white !important; border: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 초기화 ---
if "ai_questions" not in st.session_state:
    st.session_state.ai_questions = {"Transform": [], "Tomorrow": [], "Together": []}
if "selected_questions" not in st.session_state:
    st.session_state.selected_questions = []
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Standard" 
if "temp_setting" not in st.session_state:
    st.session_state.temp_setting = 0.7

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

# --- 3. 함수 정의 (로직 강화) ---
def fetch_jd(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            text = soup.get_text(separator='\n', strip=True)
            return text if len(text) > 50 else None
    except: return None

def generate_questions_by_category(category, level, resume_file, jd_text):
    temp = st.session_state.temp_setting
    # 프롬프트에 JSON 형식을 더 엄격하게 요구
    prompt = f"""[Role] Bar Raiser Interviewer. [Level] {level}. [Focus] {BAR_RAISER_CRITERIA[category]}.
    Create 10 interview questions in Korean based on the resume and JD.
    Return ONLY a valid JSON array of objects with keys "q" (question) and "i" (intent).
    Example: [{{"q": "...", "i": "..."}}]"""
    
    try:
        pdf_base64 = base64.b64encode(resume_file.getvalue()).decode('utf-8')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={st.secrets['GEMINI_API_KEY']}"
        data = {
            "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "application/pdf", "data": pdf_base64}}]}],
            "generationConfig": {"temperature": temp}
        }
        res = requests.post(url, json=data, timeout=60)
        res_json = res.json()
        
        # API 응답 구조 확인 및 정제
        if 'candidates' in res_json and len(res_json['candidates']) > 0:
            raw_text = res_json['candidates'][0]['content']['parts'][0]['text']
            # 마크다운 태그 제거
            cleaned = raw_text.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, list) else []
        return []
    except Exception as e:
        st.sidebar.error(f"API 오류: {str(e)}") # 사이드바에 에러 노출
        return []

# --- 4. 사이드바 (상태 체크 강화) ---
with st.sidebar:
    st.title("✈️ Copilot Menu")
    candidate_name = st.text_input("👤 후보자 이름", placeholder="이름을 입력하세요")
    selected_level = st.selectbox("1. 레벨 선택", list(LEVEL_GUIDELINES.keys()))
    st.info(f"💡 {LEVEL_GUIDELINES[selected_level]}")
    
    st.subheader("2. JD (채용공고)")
    tab1, tab2 = st.tabs(["🔗 URL", "📝 텍스트"])
    with tab1:
        url_input = st.text_input("URL 입력")
        jd_fetched = fetch_jd(url_input) if url_input else None
        if url_input:
            if jd_fetched: st.success("✅ JD 분석 완료")
            else: st.warning("⚠️ URL 분석 실패. 텍스트를 직접 입력하세요.")
    with tab2:
        jd_text_area = st.text_area("내용 붙여넣기", height=150)
    jd_final = jd_text_area if jd_text_area else jd_fetched

    st.subheader("3. 이력서")
    resume_file = st.file_uploader("PDF 업로드", type="pdf")
    
    st.divider()
    if st.button("질문 생성 시작 🚀", type="primary", use_container_width=True):
        if resume_file and jd_final:
            with st.spinner("AI가 질문을 생성하고 있습니다..."):
                for cat in ["Transform", "Tomorrow", "Together"]:
                    result = generate_questions_by_category(cat, selected_level, resume_file, jd_final)
                    st.session_state.ai_questions[cat] = result
            # 데이터 생성 후 강제 화면 갱신
            st.rerun()
        else:
            st.error("이력서와 JD가 모두 필요합니다.")

    st.divider()
    st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
    if st.button("🗑️ 초기화", use_container_width=True):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    with st.expander("⚙️"):
        st.session_state.temp_setting = st.slider("Temp", 0.0, 1.0, st.session_state.temp_setting)

# --- 5. 메인 화면 ---
st.title("✈️ Bar Raiser Copilot")

c_v1, c_v2, c_v3 = st.columns(3)
if c_v1.button("↔️ 질문 리스트만 보기", use_container_width=True): st.session_state.view_mode = "QuestionWide"; st.rerun()
if c_v2.button("⬅️ 기본 보기 (반반)", use_container_width=True): st.session_state.view_mode = "Standard"; st.rerun()
if c_v3.button("↔️ 면접관 노트만 보기", use_container_width=True): st.session_state.view_mode = "NoteWide"; st.rerun()

st.divider()

def render_questions():
    st.subheader("🎯 제안 질문 리스트")
    # 질문이 아예 없는 경우에 대한 안내
    has_questions = any(st.session_state.ai_questions.values())
    if not has_questions:
        st.warning("왼쪽 사이드바에서 [질문 생성 시작 🚀] 버튼을 눌러주세요.")
        return

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
            
            questions = st.session_state.ai_questions.get(cat, [])
            if not questions:
                st.info(f"{cat}에 대한 질문을 생성할 수 없습니다. 다시 시도해 보세요.")
            
            for i, q in enumerate(questions):
                q_val, i_val = q.get('q',''), q.get('i','')
                qc, ac = st.columns([0.94, 0.06])
                with qc:
                    st.markdown(f"<div class='q-block'><div class='q-text'>Q. {q_val}</div><div style='color:gray; font-size:0.85rem;'>🎯 의도: {i_val}</div></div>", unsafe_allow_html=True)
                with ac:
                    st.markdown('<div class="v-center">', unsafe_allow_html=True)
                    if st.button("➕", key=f"add_{cat}_{i}"):
                        if q_val not in [sq['q'] for sq in st.session_state.selected_questions]:
                            st.session_state.selected_questions.append({"q": q_val, "cat": cat, "memo": ""})
                    st.markdown('</div>', unsafe_allow_html=True)
                st.divider()

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
                st.session_state.selected_questions.pop(idx); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        q_v = item.get('q','')
        q_h = max(80, (len(q_v) // 35) * 25 + 35)
        st.session_state.selected_questions[idx]['q'] = st.text_area(f"qn_{idx}", value=q_v, label_visibility="collapsed", height=q_h, key=f"aq_{idx}")
        st.session_state.selected_questions[idx]['memo'] = st.text_area(f"mn_{idx}", value=item.get('memo',''), placeholder="답변 메모...", label_visibility="collapsed", height=150, key=f"am_{idx}")
        st.markdown("<div style='margin-bottom:15px; border-bottom:1px solid #eee;'></div>", unsafe_allow_html=True)

    if st.session_state.selected_questions:
        txt_out = f"후보자: {candidate_name if candidate_name else '미입력'}\n"
        for s in st.session_state.selected_questions:
            txt_out += f"\n[{s.get('cat','Custom')}] Q: {s.get('q','')}\nA: {s.get('memo','')}\n"
        st.download_button("💾 면접 결과 저장 (.txt)", txt_out, f"Result_{candidate_name}.txt", type="primary", use_container_width=True)

# 레이아웃 실행
if st.session_state.view_mode == "QuestionWide": render_questions()
elif st.session_state.view_mode == "NoteWide": render_notes()
else:
    col_l, col_r = st.columns([1.1, 1])
    with col_l: render_questions()
    with col_r: render_notes()
