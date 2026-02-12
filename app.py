import streamlit as st
import requests
import json
import base64
import datetime
import re
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
for key in ["ai_questions", "selected_questions", "view_mode", "temp_setting", "debug_log"]:
    if key not in st.session_state:
        if key == "ai_questions": st.session_state[key] = {"Transform": [], "Tomorrow": [], "Together": []}
        elif key == "selected_questions": st.session_state[key] = []
        elif key == "view_mode": st.session_state[key] = "Standard"
        elif key == "temp_setting": st.session_state[key] = 0.7
        else: st.session_state[key] = ""

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

# --- 3. 핵심 함수 (404 에러 방지용 멀티 엔진 시스템) ---
def fetch_jd(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            return text if len(text) > 20 else None
    except: return None

def generate_questions_by_category(category, level, resume_file, jd_text):
    api_key = st.secrets.get("GEMINI_API_KEY")
    prompt = f"[Role] Bar Raiser Interviewer. [Value] {BAR_RAISER_CRITERIA[category]}. Create 10 Questions JSON."
    file_ext = resume_file.name.split('.')[-1].lower()
    mime_type = "application/pdf" if file_ext == "pdf" else f"image/{file_ext.replace('jpg', 'jpeg')}"
    file_content = base64.b64encode(resume_file.getvalue()).decode('utf-8')
    
    # [명확한 해결책] 성공할 때까지 경로를 바꿔가며 찌르는 시퀀스
    endpoints = [
        "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    ]
    
    last_error = ""
    for url in endpoints:
        try:
            full_url = f"{url}?key={api_key}"
            data = {
                "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": mime_type, "data": file_content}}]}],
                "generationConfig": {"temperature": st.session_state.temp_setting},
                "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
            }
            res = requests.post(full_url, json=data, timeout=60)
            res_json = res.json()
            
            if res.status_code == 200 and 'candidates' in res_json:
                raw_text = res_json['candidates'][0]['content']['parts'][0]['text']
                json_match = re.search(r'\[\s*{.*}\s*\]', raw_text, re.DOTALL)
                if json_match: return json.loads(json_match.group())
            
            last_error = str(res_json)
        except Exception as e:
            last_error = str(e)
            continue # 다음 엔드포인트로 시도
            
    st.session_state.debug_log = last_error
    return []

# --- 4. 사이드바 (확정 디자인 유지) ---
with st.sidebar:
    st.title("✈️ Copilot Menu")
    candidate_name = st.text_input("👤 후보자 이름", placeholder="이름을 입력하세요")
    selected_level = st.selectbox("1. 레벨 선택", list(LEVEL_GUIDELINES.keys()))
    st.info(f"💡 {LEVEL_GUIDELINES[selected_level]}")
    
    tab1, tab2 = st.tabs(["🔗 URL", "📝 텍스트"])
    with tab1:
        url_input = st.text_input("URL 입력")
        jd_fetched = fetch_jd(url_input) if url_input else None
        if url_input:
            if jd_fetched: st.success("✅ JD 분석 완료")
            else: st.error("❌ 분석 불가. 직접 입력하세요.")
    with tab2:
        jd_text_area = st.text_area("내용 붙여넣기", height=150)
    jd_final = jd_text_area if jd_text_area else jd_fetched

    resume_file = st.file_uploader("PDF 또는 이미지 업로드", type=["pdf", "png", "jpg", "jpeg"])
    st.divider()
    if st.button("질문 생성 시작 🚀", type="primary", use_container_width=True):
        if resume_file and jd_final:
            with st.spinner("최종 엔진이 질문을 생성하고 있습니다..."):
                for cat in ["Transform", "Tomorrow", "Together"]:
                    st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final)
            st.rerun()
        else: st.warning("이력서와 JD를 확인해주세요.")

    st.divider()
    st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
    if st.button("🗑️ 초기화", use_container_width=True):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    with st.expander("⚙️"):
        st.session_state.temp_setting = st.slider("Temp", 0.0, 1.0, st.session_state.temp_setting)
        if st.session_state.debug_log: st.code(st.session_state.debug_log[:300])

# --- 5. 메인 화면 (3가지 뷰 모드) ---
st.title("✈️ Bar Raiser Copilot")

c_v1, c_v2, c_v3 = st.columns(3)
if c_v1.button("↔️ 질문 리스트만 보기", use_container_width=True): st.session_state.view_mode = "QuestionWide"; st.rerun()
if c_v2.button("⬅️ 기본 보기 (반반)", use_container_width=True): st.session_state.view_mode = "Standard"; st.rerun()
if c_v3.button("↔️ 면접관 노트만 보기", use_container_width=True): st.session_state.view_mode = "NoteWide"; st.rerun()

st.divider()



def render_questions():
    st.subheader("🎯 제안 질문 리스트")
    if not any(st.session_state.ai_questions.values()):
        st.info("사이드바 정보를 채운 후 [질문 생성 시작]을 눌러주세요.")
        return

    for cat in ["Transform", "Tomorrow", "Together"]:
        with st.expander(f"📌 {cat}({BAR_RAISER_CRITERIA[cat]}) 리스트", expanded=True):
            c1, c2 = st.columns([0.94, 0.06])
            with c2:
                st.markdown('<div class="v-center">', unsafe_allow_html=True)
                if st.button("🔄", key=f"ref_{cat}"):
                    st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            st.divider()
            for i, q in enumerate(st.session_state.ai_questions.get(cat, [])):
                q_val, i_val = q.get('q','질문 생성 실패'), q.get('i','오류 발생')
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
        txt_out = f"후보자: {candidate_name}\n"
        for s in st.session_state.selected_questions:
            txt_out += f"\n[{s.get('cat','Custom')}] Q: {s.get('q','')}\nA: {s.get('memo','')}\n"
        st.download_button("💾 면접 결과 저장 (.txt)", txt_out, f"Result_{candidate_name}.txt", type="primary", use_container_width=True)

if st.session_state.view_mode == "QuestionWide": render_questions()
elif st.session_state.view_mode == "NoteWide": render_notes()
else:
    col_l, col_r = st.columns([1.1, 1])
    with col_l: render_questions()
    with col_r: render_notes()
