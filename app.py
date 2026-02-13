import streamlit as st
import requests
import json
import base64
import re
import time
import gc
from bs4 import BeautifulSoup

# --- 1. 디자인 CSS (선생님 확정안 100% 유지) ---
st.set_page_config(page_title="Bar Raiser Copilot", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    /* 화면 깨짐 방지 */
    [data-testid="column"] { min-width: 320px !important; }
    .stMarkdown p, .stSubheader { word-break: keep-all !important; }

    /* 아이콘 버튼 테두리 제거 (투명 버튼) */
    .v-center {
        display: flex !important; align-items: center !important; justify-content: center !important;
        height: 100% !important; padding-top: 10px !important;
    }
    .v-center button {
        border: none !important; background: transparent !important; box-shadow: none !important;
        padding: 0px !important; height: 32px !important; width: 32px !important; color: #555 !important;
    }
    .v-center button:hover { color: #ff4b4b !important; }

    /* 텍스트 가독성 */
    .q-block { margin-bottom: 15px !important; padding-bottom: 5px !important; }
    .q-text { font-size: 16px !important; font-weight: 600 !important; line-height: 1.6 !important; margin-bottom: 8px !important; }

    /* 버튼 스타일 */
    [data-testid="stSidebar"] .stButton button { width: 100% !important; height: auto !important; }
    .reset-btn button { background-color: #ff4b4b !important; color: white !important; border: none !important; }
    
    /* 보안 경고 박스 */
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
        return []

    prompt = f"""
    [System Rule]
    You are a Bar Raiser Interviewer. Do NOT include PII (Name, Phone, etc).
    
    [Context]
    Level: {level} ({LEVEL_GUIDELINES[level]}).
    Core Value: {BAR_RAISER_CRITERIA[category]}.
    
    [JD Summary]
    {jd_text[:2000]}
    
    [Task]
    Analyze Resume.
    1. Check if Fresh or Junior.
    2. Create 10 Deep-dive Interview Questions in Korean.
    [Format] Return ONLY a JSON array: [{{"q": "질문 내용", "i": "질문 의도"}}]
    """

    file_bytes = resume_file.getvalue()
    pdf_base64 = base64.b64encode(file_bytes).decode('utf-8')
    file_ext = resume_file.name.split('.')[-1].lower()
    mime_type = "application/pdf" if file_ext == "pdf" else f"image/{file_ext.replace('jpg', 'jpeg')}"

    # [핵심 수정] 끈질긴 재시도 로직 (Exponential Backoff)
    # 실패하면 5초 -> 8초 -> 10초 대기 후 다시 시도
    wait_times = [5, 8, 10] 
    
    for wait in wait_times:
        try:
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
            
            response = requests.post(url, headers=headers, data=json.dumps(data), timeout=60)
            
            if response.status_code == 200:
                raw_text = response.json()['candidates'][0]['content']['parts'][0]['text']
                json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            
            # 429 에러(Too Many Requests) 또는 기타 에러 시 대기 후 재시도
            time.sleep(wait)
            continue
            
        except Exception:
            time.sleep(wait)
            continue
    
    # 모든 시도 실패 시 빈 리스트 반환
    return []

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
            with st.spinner("AI 서버 과부하를 피해 천천히 생성 중입니다... (약 15초 소요)"):
                # [수정] 대기 시간 대폭 증가 (안전 제일)
                st.session_state.ai_questions["Transform"] = generate_questions_by_category("Transform", selected_level, resume_file, jd_final)
                time.sleep(4) # 4초 대기
                
                st.session_state.ai_questions["Tomorrow"] = generate_questions_by_category("Tomorrow", selected_level, resume_file, jd_final)
                time.sleep(4) # 4초 대기
                
                st.session_state.ai_questions["Together"] = generate_questions_by_category("Together", selected_level, resume_file, jd_final)
            
            gc.collect() 
            st.rerun()
        else: st.error("정보를 모두 입력해주세요.")
    
    st.divider()
    st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
    if st.button("🗑️ 초기화", use_container_width=True):
