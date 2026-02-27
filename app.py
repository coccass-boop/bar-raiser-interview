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
    /* 카드형 UI 가독성 개선 */
    .q-card {
        border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; margin-bottom: 15px;
        background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .q-text { font-size: 15px !important; font-weight: 700 !important; color: #1f1f1f; margin-bottom: 8px; line-height: 1.5; }
    .i-text { font-size: 13px !important; color: #666666; background-color: #f8f9fa; padding: 6px 10px; border-radius: 4px; margin-bottom: 10px; }
    [data-testid="stSidebar"] .stButton button { width: 100% !important; height: auto !important; }
    .logout-btn button { 
        width: auto !important; height: auto !important; 
        font-size: 11px !important; padding: 4px 10px !important; 
        color: #999 !important; border: 1px solid #eee !important; 
        background: transparent !important; float: right !important; margin-top: 40px !important;
    }
    .logout-btn button:hover { color: #ff4b4b !important; border-color: #ff4b4b !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 구글 시트 연동 (면접관 인증용) ---
SHEET_ID = "1c1lZRL0oOC95-YTrqMDpUaCGfbUk368yfYI-XlcJxYo"
AUTH_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=%EB%A9%B4%EC%A0%91%EA%B4%80%20%EC%BD%94%EB%93%9C"

def load_auth_data():
    try:
        fresh_url = f"{AUTH_URL}&_={int(time.time())}"
        df = pd.read_csv(fresh_url, dtype=str, keep_default_na=False)
        df.columns = df.columns.astype(str).str.strip()
        code_col = next((c for c in df.columns if '코드' in c or '입사일' in c), None)
        name_col = next((c for c in df.columns if '성명' in c or '이름' in c or '면접관' in c and c != code_col), None)
        
        if not code_col or not name_col: return {}
        codes = df[code_col].str.replace(r'\s+', '', regex=True).str.replace(',', '', regex=False).str.replace(r'\.0*$', '', regex=True)
        names = df[name_col].str.replace(r'\s+', '', regex=True)
        
        valid_dict = {c: n for c, n in zip(codes, names) if c}
        return valid_dict
    except Exception as e:
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
        raw_code = st.text_input("인증 코드 입력", type="password")
        clean_code_input = re.sub(r'\s+', '', raw_code) 
    with col2:
        api_key_input = st.text_input("개인 API 키 (필수)", type="password", value=st.session_state.user_key).strip()
        st.markdown("""
        <div style='font-size: 0.85rem; color: #555;'>
        💡 <b>API 키가 없으신가요? (1분 소요)</b><br>
        1. <a href='https://aistudio.google.com/app/apikey' target='_blank'>Google AI Studio</a> 접속<br>
        2. <b>'Create API key'</b> 클릭 후 복사(📋)하여 위 칸에 붙여넣기
        </div>
        """, unsafe_allow_html=True)
    
    st.write("")
    if st.button("인증 및 입장", type="primary"):
        # [수정 1] API 키 필수 입력 로직
        if not api_key_input:
            st.error("🚨 개인 API 키를 반드시 입력해주세요!")
        elif clean_code_input in valid_users:
            st.session_state.authenticated = True
            st.session_state.user_code = clean_code_input
            st.session_state.user_nickname = valid_users[clean_code_input]
            st.session_state.user_key = api_key_input
            st.rerun()
        elif not valid_users:
            st.error("시트가 연결되지 않아 인증할 수 없습니다.")
        else:
            st.error("관리자에게 문의주세요.")
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

# [수정 2] count=5 파라미터 추가, 프롬프트에 레벨 상세설명 주입
def generate_questions_by_category(category, level, resume_file, jd_text, user_api_key, count=5):
    final_api_key = user_api_key if user_api_key else st.secrets.get("GEMINI_API_KEY")
    if not final_api_key: return []

    level_desc = LEVEL_GUIDELINES.get(level, "")
    prompt = f"[Role] Bar Raiser Interviewer. [Target] {level} ({level_desc}). [Value] {BAR_RAISER_CRITERIA[category]}. Analyze Resume/JD. Create {count} Questions JSON: [{{'q': '질문', 'i': '의도'}}]"
    
    try:
        file_bytes = resume_file.getvalue()
        pdf_base64 = base64.b64encode(file_bytes).decode('utf-8')
        mime_type = "application/pdf" if resume_file.name.lower().endswith('pdf') else "image/jpeg"
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={final_api_key}"
        data = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": mime_type, "data": pdf_base64}}]}]}
        
        for attempt in range(3):
            res = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(data), timeout=60)
            if res.status_code == 200:
                raw = res.json()['candidates'][0]['content']['parts'][0]['text']
                match = re.search(r'\[\s*\{.*\}\s*\]', raw, re.DOTALL)
                return json.loads(match.group()) if match else []
            elif res.status_code in [429, 500, 503]:
                time.sleep(3)
                continue
            else: return []
    except Exception: return []
    return []

# --- 6. 사이드바 구성 ---
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
            with st.spinner("5개의 날카로운 질문을 뽑고 있습니다..."):
                for cat in ["Transform", "Tomorrow", "Together"]:
                    # 기본 5개 생성
                    st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final, st.session_state.user_key, count=5)
                    time.sleep(1.5)
            st.rerun()
        else:
            st.error("이력서와 JD를 모두 입력해주세요.")

    st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
    if st.button("🚪 로그아웃", help="인증 화면으로 돌아갑니다"):
        st.session_state.authenticated = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- 7. 메인 화면 ---
st.title("✈️ Bar Raiser Copilot (v23-1)")
c1, c2, c3 = st.columns(3)
if c1.button("↔️ 질문 리스트만 보기", use_container_width=True): st.session_state.view_mode = "QuestionWide"; st.rerun()
if c2.button("⬅️ 기본 보기 (반반)", use_container_width=True): st.session_state.view_mode = "Standard"; st.rerun()
if c3.button("↔️ 면접관 노트만 보기", use_container_width=True): st.session_state.view_mode = "NoteWide"; st.rerun()
st.divider()

def render_questions():
    st.subheader("🎯 제안 질문 리스트 (가치별 5개)")
    if not any(st.session_state.ai_questions.values()):
        st.info("👈 사이드바 정보를 채운 후 버튼을 눌러주세요.")
        return
    for cat in ["Transform", "Tomorrow", "Together"]:
        with st.expander(f"📌 {cat} ({BAR_RAISER_CRITERIA[cat]})", expanded=True):
            
            # [수정 3] 전체 새로고침 vs 선택 새로고침 버튼
            b1, b2 = st.columns(2)
            with b1:
                if st.button("🔄 전체 새로고침", key=f"ref_all_{cat}", use_container_width=True):
                    with st.spinner("새로 뽑는 중..."):
                        st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final, st.session_state.user_key, count=5)
                    st.rerun()
            with b2:
                if st.button("♻️ 선택한 질문만 다시 뽑기", key=f"ref_sel_{cat}", use_container_width=True):
                    # 체크된 인덱스 찾기
                    sel_indices = [idx for idx in range(len(st.session_state.ai_questions[cat])) if st.session_state.get(f"chk_{cat}_{idx}")]
                    if sel_indices:
                        with st.spinner("선택된 질문 교체 중..."):
                            new_qs = generate_questions_by_category(cat, selected_level, resume_file, jd_final, st.session_state.user_key, count=len(sel_indices))
                            for new_q, target_idx in zip(new_qs, sel_indices):
                                st.session_state.ai_questions[cat][target_idx] = new_q
                        st.rerun()
                    else:
                        st.warning("다시 뽑을 질문을 먼저 체크해주세요!")
            
            st.write("") # 간격
            
            # [수정 4] 가독성 높은 카드 UI 적용
            for i, q in enumerate(st.session_state.ai_questions.get(cat, [])):
                q_v, i_v = q.get('q', ''), q.get('i', '')
                st.markdown(f"""
                <div class="q-card">
                    <div class="q-text">Q{i+1}. {q_v}</div>
                    <div class="i-text">🎯 <b>의도:</b> {i_v}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # 액션 버튼 (체크박스 & 노트 담기)
                ca, cb = st.columns([0.7, 0.3])
                with ca:
                    st.checkbox("이 질문 다시 뽑기", key=f"chk_{cat}_{i}")
                with cb:
                    if st.button("➕ 노트에 담기", key=f"add_{cat}_{i}", use_container_width=True):
                        if q_v and q_v not in [sq['q'] for sq in st.session_state.selected_questions]:
                            st.session_state.selected_questions.append({"q": q_v, "cat": cat, "memo": ""})
                            st.toast("✅ 면접관 노트에 추가되었습니다!")

def render_notes():
    st.subheader("📝 면접관 노트")
    if st.button("➕ 직접 입력 (새 질문)", use_container_width=True): 
        st.session_state.selected_questions.append({"q": "", "cat": "Custom", "memo": ""})
    st.divider()
    
    for idx, item in enumerate(st.session_state.selected_questions):
        st.markdown(f"**[{item.get('cat','Custom')}] 질문 {idx+1}**")
        
        # [수정 5] 실시간 값 바인딩 (입력 즉시 session_state에 저장되도록 key 활용)
        st.session_state.selected_questions[idx]['q'] = st.text_area("질문", value=item.get('q',''), height=70, key=f"aq_{idx}", label_visibility="collapsed")
        st.session_state.selected_questions[idx]['memo'] = st.text_area("메모/답변", value=item.get('memo',''), placeholder="지원자 답변 및 평가 메모...", height=120, key=f"am_{idx}", label_visibility="collapsed")
        
        if st.button("🗑️ 삭제", key=f"del_{idx}"): 
            st.session_state.selected_questions.pop(idx); st.rerun()
        st.markdown("---")

    # [수정 6] 다운로드 파일 텍스트 가독성 대폭 개선
    if st.session_state.selected_questions:
        txt_content = f"=========================================\n"
        txt_content += f" 👤 면접 후보자 : {candidate_name if candidate_name else '이름 미상'}\n"
        txt_content += f" 📊 지원 레벨 : {selected_level}\n"
        txt_content += f"=========================================\n\n"
        
        for idx, s in enumerate(st.session_state.selected_questions):
            # 화면의 최신 값을 바로 가져옵니다.
            cur_q = st.session_state.get(f"aq_{idx}", s['q'])
            cur_a = st.session_state.get(f"am_{idx}", s['memo'])
            
            txt_content += f"▶ [질문 {idx+1}] ({s['cat']} 역량 검증)\n"
            txt_content += f"Q : {cur_q}\n"
            txt_content += f"-----------------------------------------\n"
            txt_content += f"A (답변 및 메모) :\n{cur_a}\n"
            txt_content += f"=========================================\n\n"
            
        st.download_button("💾 예쁘게 결과 저장하기 (.txt)", txt_content, f"면접기록_{candidate_name}.txt", type="primary", use_container_width=True)

if st.session_state.view_mode == "QuestionWide": render_questions()
elif st.session_state.view_mode == "NoteWide": render_notes()
else:
    cl, cr = st.columns([1.1, 1])
    with cl: render_questions()
    with cr: render_notes()
