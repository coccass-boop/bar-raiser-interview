import streamlit as st
import requests
import json
import base64
import re
import time
import pandas as pd
from bs4 import BeautifulSoup

# --- 1. 디자인 CSS ---
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

# --- 2. 구글 시트 연동 (면접관 인증용) ---
SHEET_ID = "1c1lZRL0oOC95-YTrqMDpUaCGfbUk368yfYI-XlcJxYo"
AUTH_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=%EB%A9%B4%EC%A0%91%EA%B4%80%20%EC%BD%94%EB%93%9C"

# 실시간 반영을 위해 캐시를 끄고 구글 서버 우회 로직을 적용했습니다.
def load_auth_data():
    try:
        # URL 끝에 난수(현재 시간)를 붙여 구글 시트의 캐시를 강제로 무효화!
        fresh_url = f"{AUTH_URL}&_={int(time.time())}"
        df = pd.read_csv(fresh_url)
        
        # 소수점(.0), 쉼표(,) 제거 및 양옆 띄어쓰기 완벽 제거
        codes = df['면접관 코드(그룹입사일)'].astype(str).str.replace(r'\.0$', '', regex=True).str.replace(',', '', regex=False).str.strip()
        names = df['면접관 성명'].astype(str).str.strip()
        
        return pd.Series(names.values, index=codes.values).to_dict()
    except Exception as e:
        if "HTTP Error 401" in str(e):
            st.error("🚨 구글 시트 접근 권한이 없습니다. 시트의 공유 설정을 '링크가 있는 모든 사용자 (뷰어)'로 변경해주세요.")
        else:
            st.error(f"시트 데이터를 불러오는 데 실패했습니다: {e}")
        return {}

# --- 3. 데이터 초기화 ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "user_code" not in st.session_state: st.session_state.user_code = ""
if "user_nickname" not in st.session_state: st.session_state.user_nickname = ""
if "user_key" not in st.session_state: st.session_state.user_key = ""

for key in ["ai_questions", "selected_questions", "view_mode", "temp_setting"]:
    if key not in st.session_state:
        if key == "ai_questions": st.session_state[key] = {"Transform": [], "Tomorrow": [], "Together": []}
        elif key == "selected_questions": st.session_state[key] = []
        elif key == "view_mode": st.session_state[key] = "Standard"
        elif key == "temp_setting": st.session_state[key] = 0.7

BAR_RAISER_CRITERIA = {"Transform": "Create Enduring Value", "Tomorrow": "Forward Thinking", "Together": "Trust & Growth"}
LEVEL_GUIDELINES = {
    "IC-L3": "[기본기 실무자] 가이드 하 업무 수행.", "IC-L4": "[자기완결 실무자] 독립적 계획/실행.",
    "IC-L5": "[핵심 전문가] 최적 대안 제시, 복잡 문제 해결.", "IC-L6": "[선도적 전문가] 성과 선순환 구조 구축.",
    "IC-L7": "[최고 권위자] 전사 혁신 주도.", "M-L5": "[유닛 리더] 과제 운영 리딩.",
    "M-L6": "[시니어 리더] 유닛 성과/육성 관리.", "M-L7": "[디렉터] 전략 방향 총괄."
}

# --- 4. 로그인(인증) 화면 ---
if not st.session_state.authenticated:
    st.title("🔒 Bar Raiser Copilot")
    st.info("부여받으신 면접관 코드를 입력해주세요.")
    
    valid_users = load_auth_data()
    
    col1, col2 = st.columns(2)
    with col1:
        # 입력된 값의 띄어쓰기를 자동으로 잘라냅니다 (.strip())
        code_input = st.text_input("인증 코드 입력", type="password").strip()
    with col2:
        api_key_input = st.text_input("개인 API 키", type="password", value=st.session_state.user_key).strip()
        st.markdown("""
        <div style='font-size: 0.85rem; color: #555;'>
        💡 <b>API 키 무료 발급 방법 (1분 소요)</b><br>
        1. <a href='https://aistudio.google.com/app/apikey' target='_blank'>Google AI Studio</a> 접속 (구글 로그인)<br>
        2. 화면의 <b>'Create API key'</b> 클릭 후 복사 아이콘(📋) 클릭<br>
        3. 위 칸에 붙여넣기 (브라우저를 닫기 전까지 유지됩니다)
        </div>
        """, unsafe_allow_html=True)
    
    st.write("")
    if st.button("인증 및 입장", type="primary"):
        if code_input in valid_users:
            st.session_state.authenticated = True
            st.session_state.user_code = code_input
            st.session_state.user_nickname = valid_users[code_input]
            st.session_state.user_key = api_key_input
            st.rerun()
        elif not valid_users:
            st.error("시트가 연결되지 않아 인증할 수 없습니다. 시트 공유 권한을 확인해주세요.")
        else:
            st.error("등록되지 않은 코드입니다. 시트에 코드가 정확히 추가되었는지 확인해주세요.")
    st.stop()

# --- 5. 핵심 기능 함수 ---
def fetch_jd(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for s in soup(['script', 'style']): s.decompose()
            return soup.get_text(separator=' ', strip=True) if len(soup.get_text()) > 50 else None
    except: return None

def generate_questions_by_category(category, level, resume_file, jd_text, user_api_key):
    final_api_key = user_api_key if user_api_key else st.secrets.get("GEMINI_API_KEY")
    if not final_api_key:
        return [{"q": "API 키를 입력해주세요.", "i": "사이드바 상단 확인"}]

    prompt = f"[Role] Bar Raiser Interviewer. [Target] {level}. [Value] {BAR_RAISER_CRITERIA[category]}. Analyze Resume/JD. Create 10 Questions JSON: [{{'q': '질문', 'i': '의도'}}]"
    
    try:
        file_bytes = resume_file.getvalue()
        pdf_base64 = base64.b64encode(file_bytes).decode('utf-8')
        mime_type = "application/pdf" if resume_file.name.lower().endswith('pdf') else "image/jpeg"
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={final_api_key}"
        data = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": mime_type, "data": pdf_base64}}]}]}
        
        for attempt in range(3):
            res = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(data), timeout=60)
            if res.status_code == 200:
                raw = res.json()['candidates'][0]['content']['parts'][0]['text']
                match = re.search(r'\[\s*\{.*\}\s*\]', raw, re.DOTALL)
                return json.loads(match.group()) if match else [{"q": "JSON 추출 실패", "i": "재시도 해주세요."}]
            elif res.status_code in [429, 500, 503]:
                time.sleep(5)
                continue
            else: 
                return [{"q": f"API 에러 ({res.status_code})", "i": "키 또는 네트워크 상태 확인"}]
    except Exception as e: 
        return [{"q": "시스템 오류 발생", "i": str(e)}]
    return []

# --- 6. 화면 구성 ---
with st.sidebar:
    st.title("✈️ Copilot Menu")
    st.success(f"👤 접속 완료: **{st.session_state.user_nickname}** 님")
    
    with st.expander("💡 개인 API 키 확인 및 변경"):
        st.session_state.user_key = st.text_input("API 키 입력", value=st.session_state.user_key, type="password")
        
    st.markdown('<div class="security-alert">🚨 <b>보안 주의사항</b><br>민감 정보는 마스킹 후 업로드하세요.</div>', unsafe_allow_html=True)
    candidate_name = st.text_input("👤 후보자 이름", placeholder="이름 입력")
    selected_level = st.selectbox("1. 레벨 선택", list(LEVEL_GUIDELINES.keys()))
    
    st.subheader("2. JD (채용공고)")
    tab1, tab2 = st.tabs(["🔗 URL", "📝 텍스트"])
    with tab1:
        url_in = st.text_input("URL 입력")
        jd_fetched = fetch_jd(url_in) if url_in else None
    with tab2: jd_txt_area = st.text_area("내용 붙여넣기", height=100)
    jd_final = jd_txt_area if jd_txt_area else jd_fetched

    resume_file = st.file_uploader("3. 이력서 업로드", type=["pdf", "png", "jpg", "jpeg"])
    st.divider()
    agree = st.checkbox("✅ 민감 정보 없음을 확인했습니다.")
    
    if st.button("질문 생성 시작 🚀", type="primary", use_container_width=True, disabled=not agree):
        if resume_file and jd_final:
            with st.spinner("생성 중..."):
                for cat in ["Transform", "Tomorrow", "Together"]:
                    st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final, st.session_state.user_key)
                    time.sleep(2)
            st.rerun()
        else:
            st.error("이력서와 JD를 모두 입력해주세요.")

    st.divider()
    if st.button("🗑️ 초기화", use_container_width=True):
        for k in ["ai_questions", "selected_questions"]: st.session_state[k] = {"Transform": [], "Tomorrow": [], "Together": []} if k=="ai_questions" else []
        st.rerun()

# --- 7. 메인 화면 ---
st.title("✈️ Bar Raiser Copilot")
c1, c2, c3 = st.columns(3)
if c1.button("↔️ 질문 리스트만 보기", use_container_width=True): st.session_state.view_mode = "QuestionWide"; st.rerun()
if c2.button("⬅️ 기본 보기 (반반)", use_container_width=True): st.session_state.view_mode = "Standard"; st.rerun()
if c3.button("↔️ 면접관 노트만 보기", use_container_width=True): st.session_state.view_mode = "NoteWide"; st.rerun()
st.divider()

def render_questions():
    st.subheader("🎯 제안 질문 리스트")
    if not any(st.session_state.ai_questions.values()):
        st.info("👈 사이드바 정보를 채운 후 버튼을 눌러주세요.")
        return
    for cat in ["Transform", "Tomorrow", "Together"]:
        with st.expander(f"📌 {cat}({BAR_RAISER_CRITERIA[cat]}) 리스트", expanded=True):
            col_h, col_b = st.columns([0.94, 0.06])
            with col_b:
                st.markdown('<div class="v-center">', unsafe_allow_html=True)
                if st.button("🔄", key=f"ref_{cat}"):
                    st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final, st.session_state.user_key)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            st.divider()
            for i, q in enumerate(st.session_state.ai_questions.get(cat, [])):
                q_v, i_v = q.get('q', ''), q.get('i', '')
                qc, ac = st.columns([0.94, 0.06])
                with qc: st.markdown(f"<div class='q-block'><div class='q-text'>Q. {q_v}</div><div style='color:gray; font-size:0.85rem;'>🎯 의도: {i_v}</div></div>", unsafe_allow_html=True)
                with ac:
                    st.markdown('<div class="v-center">', unsafe_allow_html=True)
                    if st.button("➕", key=f"add_{cat}_{i}"):
                        if q_v and q_v not in [sq['q'] for sq in st.session_state.selected_questions]:
                            st.session_state.selected_questions.append({"q": q_v, "cat": cat, "memo": ""})
                    st.markdown('</div>', unsafe_allow_html=True)
                st.divider()

def render_notes():
    st.subheader("📝 면접관 노트")
    if st.button("➕ 직접 입력", use_container_width=True): st.session_state.selected_questions.append({"q": "", "cat": "Custom", "memo": ""})
    st.divider()
    for idx, item in enumerate(st.session_state.selected_questions):
        t_c, d_c = st.columns([0.94, 0.06])
        with t_c: st.markdown(f"<span style='font-size:0.8rem; color:gray;'>Q{idx+1}</span> <span style='background-color:#f0f2f6; padding:2px 6px; border-radius:4px; font-size:0.7rem; font-weight:bold;'>{item.get('cat','Custom')}</span>", unsafe_allow_html=True)
        with d_c:
            st.markdown('<div class="v-center">', unsafe_allow_html=True)
            if st.button("✕", key=f"del_{idx}"): st.session_state.selected_questions.pop(idx); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        st.session_state.selected_questions[idx]['q'] = st.text_area(f"qn_{idx}", value=item.get('q',''), label_visibility="collapsed", height=80, key=f"aq_{idx}")
        st.session_state.selected_questions[idx]['memo'] = st.text_area(f"mn_{idx}", value=item.get('memo',''), placeholder="메모...", label_visibility="collapsed", height=150, key=f"am_{idx}")

    if st.session_state.selected_questions:
        txt = f"후보자: {candidate_name}\n" + "\n".join([f"[{s['cat']}] Q: {s['q']}\nA: {s['memo']}" for s in st.session_state.selected_questions])
        st.download_button("💾 결과 저장 (.txt)", txt, f"Result_{candidate_name}.txt", type="primary", use_container_width=True)

if st.session_state.view_mode == "QuestionWide": render_questions()
elif st.session_state.view_mode == "NoteWide": render_notes()
else:
    cl, cr = st.columns([1.1, 1])
    with cl: render_questions()
    with cr: render_notes()
