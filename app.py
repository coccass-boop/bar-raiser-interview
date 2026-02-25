import streamlit as st
import requests
import json
import base64
import re
import time
from bs4 import BeautifulSoup

# --- 1. 디자인 CSS (유지) ---
st.set_page_config(page_title="Bar Raiser Copilot", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    [data-testid="column"] { min-width: 320px !important; }
    .stMarkdown p, .stSubheader { word-break: keep-all !important; }
    .v-center {
        display: flex !important; align-items: center !important; justify-content: center !important;
        height: 100% !important; padding-top: 10px !important;
    }
    .v-center button {
        border: none !important; background: transparent !important; box-shadow: none !important;
        padding: 0px !important; height: 32px !important; width: 32px !important; color: #555 !important;
    }
    .v-center button:hover { color: #ff4b4b !important; }
    .q-block { margin-bottom: 15px !important; padding-bottom: 5px !important; }
    .q-text { font-size: 16px !important; font-weight: 600 !important; line-height: 1.6 !important; margin-bottom: 8px !important; }
    [data-testid="stSidebar"] .stButton button { width: 100% !important; height: auto !important; }
    .reset-btn button { background-color: #ff4b4b !important; color: white !important; border: none !important; }
    .security-alert {
        background-color: #fff5f5; border: 1px solid #ff4b4b; border-radius: 5px;
        padding: 15px; font-size: 0.85rem; color: #d8000c; margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 초기화 ---
for key in ["ai_questions", "selected_questions", "view_mode", "temp_setting", "last_error"]:
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
            for s in soup(['script', 'style']): s.decompose()
            text = soup.get_text(separator=' ', strip=True)
            return text if len(text) > 50 else None
    except: return None

def generate_questions_by_category(category, level, resume_file, jd_text):
    try:
        API_KEY = st.secrets["GEMINI_API_KEY"]
    except:
        return [{"q": "API 키 오류", "i": "Secrets 설정을 확인해주세요."}]

    prompt = f"""
    [Role] Bar Raiser Interviewer. [Target] {level}. 
    [Values] {BAR_RAISER_CRITERIA[category]}.
    Analyze the Resume and JD. Create 10 Interview Questions in Korean.
    [Format] Return ONLY a JSON array: [{{"q": "질문", "i": "의도"}}]
    """

    try:
        file_bytes = resume_file.getvalue()
        pdf_base64 = base64.b64encode(file_bytes).decode('utf-8')
        file_ext = resume_file.name.split('.')[-1].lower()
        mime_type = "application/pdf" if file_ext == "pdf" else f"image/{file_ext.replace('jpg', 'jpeg')}"
    except:
        return [{"q": "파일 처리 실패", "i": "파일을 확인해주세요."}]

    max_retries = 3  
    retry_delay = 10 

    target_model = "gemini-flash-latest"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    data = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime_type, "data": pdf_base64}}
            ]
        }],
        "generationConfig": {"temperature": st.session_state.temp_setting}
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data), timeout=60)
            
            if response.status_code == 200:
                raw_text = response.json()['candidates'][0]['content']['parts'][0]['text']
                json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    return [{"q": "파싱 실패", "i": "JSON 형식이 아닙니다."}]
            
            # 🚨 유일하게 수정한 부분: 500, 503(서버 에러)도 10초 대기 후 재시도하도록 추가
            elif response.status_code in [429, 500, 503]:
                time.sleep(retry_delay)
                continue 
            
            else:
                return [{"q": f"API 에러 ({response.status_code})", "i": response.text[:100]}]
                
        except Exception as e:
            return [{"q": "시스템 오류", "i": str(e)}]
    
    return [{"q": "생성 실패 (서버 불안정)", "i": "잠시 후 다시 시도해주세요."}]

# --- 4. 화면 구성 ---

with st.sidebar:
    st.title("✈️ Copilot Menu")
    
    st.markdown("""
    <div class="security-alert">
    🚨 <b>보안 주의사항</b><br>
    업로드 전 주민번호, 전화번호 등 민감 정보는 반드시 마스킹해주세요.<br>
    </div>
    """, unsafe_allow_html=True)

    candidate_name = st.text_input("👤 후보자 이름", placeholder="이름 입력")
    selected_level = st.selectbox("1. 레벨 선택", list(LEVEL_GUIDELINES.keys()))
    st.info(f"💡 {LEVEL_GUIDELINES[selected_level]}")
    
    st.subheader("2. JD (채용공고)")
    tab1, tab2 = st.tabs(["🔗 URL", "📝 텍스트"])
    with tab1:
        url_input = st.text_input("URL 입력")
        jd_fetched = fetch_jd(url_input) if url_input else None
        if url_input:
            if jd_fetched: st.success("✅ JD 분석 완료")
            else: st.warning("⚠️ URL 접속 실패. 텍스트를 붙여넣으세요.")
    with tab2:
        jd_text_area = st.text_area("내용 붙여넣기", height=150)
    jd_final = jd_text_area if jd_text_area else jd_fetched

    st.subheader("3. 이력서")
    resume_file = st.file_uploader("파일 업로드", type=["pdf", "png", "jpg", "jpeg"])
    
    st.divider()
    
    agreement = st.checkbox("✅ 민감 정보가 없음을 확인했습니다.")
    
    if st.button("질문 생성 시작 🚀", type="primary", use_container_width=True, disabled=not agreement):
        if resume_file and jd_final:
            with st.spinner("AI가 질문을 생성 중입니다... (구글 서버 불안정 시 자동 대기합니다)"):
                
                st.session_state.ai_questions["Transform"] = generate_questions_by_category("Transform", selected_level, resume_file, jd_final)
                time.sleep(5) 
                
                st.session_state.ai_questions["Tomorrow"] = generate_questions_by_category("Tomorrow", selected_level, resume_file, jd_final)
                time.sleep(5) 
                
                st.session_state.ai_questions["Together"] = generate_questions_by_category("Together", selected_level, resume_file, jd_final)
            
            st.rerun()
        else: st.error("정보를 모두 입력해주세요.")
    
    st.divider()
    st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
    if st.button("🗑️ 초기화", use_container_width=True):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    with st.expander("⚙️"):
        st.session_state.temp_setting = st.slider("Temp", 0.0, 1.0, st.session_state.temp_setting)

st.title("✈️ Bar Raiser Copilot")

c1, c2, c3 = st.columns(3)
if c1.button("↔️ 질문 리스트만 보기", use_container_width=True): st.session_state.view_mode = "QuestionWide"; st.rerun()
if c2.button("⬅️ 기본 보기 (반반)", use_container_width=True): st.session_state.view_mode = "Standard"; st.rerun()
if c3.button("↔️ 면접관 노트만 보기", use_container_width=True): st.session_state.view_mode = "NoteWide"; st.rerun()

st.divider()

def render_questions():
    st.subheader("🎯 제안 질문 리스트")
    if not any(st.session_state.ai_questions.values()):
        st.info("👈 사이드바에서 [질문 생성 시작] 버튼을 눌러주세요.")
        return

    categories = ["Transform", "Tomorrow", "Together"]
    
    for cat in categories:
        with st.expander(f"📌 {cat}({BAR_RAISER_CRITERIA[cat]}) 리스트", expanded=True):
            col_head, col_btn = st.columns([0.94, 0.06])
            with col_btn:
                st.markdown('<div class="v-center">', unsafe_allow_html=True)
                if st.button("🔄", key=f"ref_{cat}"):
                    if resume_file and jd_final:
                        st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final)
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            st.divider()
            
            questions = st.session_state.ai_questions.get(cat, [])
            
            if not questions:
                st.warning("질문 생성 실패. (API 에러일 수 있습니다)")
            
            for i, q in enumerate(questions):
                q_val = q.get('q', 'Error')
                i_val = q.get('i', 'Error')
                
                if "API 에러" in q_val or "생성 실패" in q_val:
                    st.error(f"{q_val} : {i_val}")
                    continue

                qc, ac = st.columns([0.94, 0.06])
                with qc:
                    st.markdown(f"<div class='q-block'><div class='q-text'>Q. {q_val}</div><div style='color:gray; font-size:0.85rem;'>🎯 의도: {i_val}</div></div>", unsafe_allow_html=True)
                with ac:
                    st.markdown('<div class="v-center">', unsafe_allow_html=True)
                    if st.button("➕", key=f"add_{cat}_{i}"):
                        if q_val and q_val not in [sq['q'] for sq in st.session_state.selected_questions]:
                            st.session_state.selected_questions.append({"q": q_val, "cat": cat, "memo": ""})
                    st.markdown('</div>', unsafe_allow_html=True)
                st.divider()

def render_notes():
    st.subheader("📝 면접관 노트")
    if st.button("➕ 질문 직접 입력", use_container_width=True):
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
        st.session_state.selected_questions[idx]['memo'] = st.text_area(f"mn_{idx}", value=item.get('memo',''), placeholder="메모...", label_visibility="collapsed", height=150, key=f"am_{idx}")
        st.markdown("<div style='margin-bottom:15px; border-bottom:1px solid #eee;'></div>", unsafe_allow_html=True)

    if st.session_state.selected_questions:
        txt_out = f"후보자: {candidate_name}\n"
        for s in st.session_state.selected_questions:
            txt_out += f"\n[{s.get('cat','Custom')}] Q: {s.get('q','')}\nA: {s.get('memo','')}\n"
        st.download_button("💾 결과 저장 (.txt)", txt_out, f"Result_{candidate_name}.txt", type="primary", use_container_width=True)

if st.session_state.view_mode == "QuestionWide": render_questions()
elif st.session_state.view_mode == "NoteWide": render_notes()
else:
    col_l, col_r = st.columns([1.1, 1])
    with col_l: render_questions()
    with col_r: render_notes()
