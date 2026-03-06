import streamlit as st
import requests
import json
import base64
import re
import time
import pandas as pd
from bs4 import BeautifulSoup
import concurrent.futures

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
        background: transparent !important; float: right !important; margin-top: 10px !important;
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

if "uploader_key" not in st.session_state: st.session_state.uploader_key = 0

for key in ["ai_questions", "selected_questions", "view_mode", "temp_setting"]:
    if key not in st.session_state:
        if key == "ai_questions": st.session_state[key] = {"Transform": [], "Tomorrow": [], "Together": []}
        elif key == "selected_questions": st.session_state[key] = []
        elif key == "view_mode": st.session_state[key] = "Standard"
        elif key == "temp_setting": st.session_state[key] = 0.7

BAR_RAISER_CRITERIA = {
    "Transform": "Enduring Value Creation (시간이 지날수록 더 큰 가치를 만들어내는 솔루션을 구축합니다.)",
    "Tomorrow": "Forward Thinking (미래를 고려해 확장성과 지속성을 갖춘 솔루션을 구축합니다.)",
    "Together": "Trust & Growth (서로의 발전을 지원하며 함께 성장합니다.)"
}
LEVEL_GUIDELINES = {
    "IC-L3": "[기본기 확립 실무자] 명확한 지시와 가이드 하에 단기적 업무 수행. 피드백을 성장의 기회로 삼음.",
    "IC-L4": "[자기완결성 독립 실무자] 외부 변수에 흔들리지 않고 스스로 계획 수립/해결. 협업 요청에 해결 지향적 대응.",
    "IC-L5": "[핵심 직무 전문가] 복잡/다면적 문제 분석 및 최적 대안 제시. 자신의 전문성으로 팀 성과에 기여 및 후배에게 긍정적 영향.",
    "IC-L6": "[선도적 전문가] 단일 유닛 성과를 넘어 부서 단위 확장(Scale-up) 시킴. 얽힌 복잡한 과제 리딩 및 이해관계자 설득.",
    "IC-L7": "[전사 혁신 주도 최고 권위자] 비즈니스 혁신 창출 및 전사적 목표 달성에 기여. C-Level 및 외부 핵심 파트너와 담판.",
    "M-L5": "[유닛 리더] 단일 기능 유닛 성장 주도. 구성원의 강점과 의견을 존중하고 심리적 안정감 구축.",
    "M-L6": "[시니어 리더] 독립적 유닛 리딩. 단기 성과뿐만 아니라 구성원 장기 성장 지원. 건강한 갈등을 생산적 논의로 이끎.",
    "M-L7": "[디렉터] 전사 전략 연계 중장기 로드맵 총괄. 신뢰 기반 권한 위임 및 전사 협력을 통한 시너지 창출."
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
@st.cache_data(ttl=3600)
def fetch_jd(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for s in soup(['script', 'style']): s.decompose()
            return soup.get_text(separator=' ', strip=True) if len(soup.get_text()) > 50 else None
    except: return None

def generate_questions_by_category(category, level, resume_file, jd_text, user_api_key, tech_feedback="", portfolio_file=None, count=5):
    final_api_key = user_api_key if user_api_key else st.secrets.get("GEMINI_API_KEY")
    if not final_api_key: return [{"q": "🚨 API 키 오류", "i": "API 키를 확인해주세요."}]

    level_desc = LEVEL_GUIDELINES.get(level, "")
    value_desc = BAR_RAISER_CRITERIA[category]
    feedback_instruction = f" [실무면접 전달사항 반영 필수]: {tech_feedback}." if tech_feedback else ""
    portfolio_instruction = " 및 제출된 포트폴리오" if portfolio_file else ""
    
    prompt = f"""
    [Role] 당신은 메가존의 최고 수준 'Bar Raiser' 면접관입니다.
    [Target Level Requirements] 지원 레벨: {level} 
    요구되는 역량 수준: {level_desc}
    [Core Value to Test] {category} : {value_desc}
    [Task] 지원자의 이력서와 JD{portfolio_instruction}를 분석하여, 해당 Core Value에 부합하는 인재인지 검증하는 면접 질문 {count}개를 JSON 포맷으로 생성하세요.
    
    [CRITICAL RULES - MUST OBEY]
    1. 절대 실무 능력이나 기술적 지식(Hard Skill)을 묻지 마세요.
    2. 어려운 HR 전문 용어나 추상적인 단어는 철저히 배제하고, 누구나 이해하기 쉬운 직관적인 단어로만 질문하세요.
    3. 구구절절한 서론을 빼고, 면접관이 대본으로 바로 읽을 수 있는 편안한 구어체(1~2문장)로 간결하게 작성하세요.
    4. **가장 중요**: 지원자의 'Target Level Requirements(요구되는 역량 수준)'에 맞는 난이도와 시야를 검증하세요.
    5. {feedback_instruction}
    
    [Output Format] 
    JSON: [{{'q': '면접관이 바로 읽을 수 있는 쉽고 간결한 질문', 'i': '왜 이 질문을 해야 하는지 면접관이 단번에 이해할 수 있는 명확한 의도 (1줄)'}}]
    """
    
    try:
        parts = [{"text": prompt}]
        
        # 1. 이력서 (필수)
        res_bytes = resume_file.getvalue()
        res_b64 = base64.b64encode(res_bytes).decode('utf-8')
        res_mime = "application/pdf" if resume_file.name.lower().endswith('pdf') else "image/jpeg"
        parts.append({"inline_data": {"mime_type": res_mime, "data": res_b64}})
        
        # 2. 포트폴리오 (선택)
        if portfolio_file:
            port_bytes = portfolio_file.getvalue()
            port_b64 = base64.b64encode(port_bytes).decode('utf-8')
            port_mime = "application/pdf" if portfolio_file.name.lower().endswith('pdf') else "image/jpeg"
            parts.append({"inline_data": {"mime_type": port_mime, "data": port_b64}})
            
        data = {"contents": [{"parts": parts}]}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={final_api_key}"
        
        for attempt in range(3):
            res = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(data), timeout=60)
            if res.status_code == 200:
                try:
                    raw = res.json()['candidates'][0]['content']['parts'][0]['text']
                    match = re.search(r'\[\s*\{.*\}\s*\]', raw, re.DOTALL)
                    if match:
                        return json.loads(match.group())
                    else:
                        return [{"q": "🚨 AI 양식 오류", "i": "AI가 규격에 맞지 않는 답변을 했습니다. 다시 뽑기를 눌러주세요."}]
                except Exception as e:
                    return [{"q": "🚨 분석 중 에러 발생", "i": "다시 뽑기를 눌러주세요."}]
            elif res.status_code == 429:
                # [핵심] 과부하 시 휴식 시간을 대폭 늘려 안정성 확보! (기본 5초 대기)
                time.sleep(5 + attempt * 2)
                continue
            elif res.status_code in [500, 503]:
                time.sleep(3)
                continue
            else:
                return [{"q": f"🚨 구글 서버 접속 오류 ({res.status_code})", "i": "잠시 후 다시 시도해주세요."}]
                
        return [{"q": "🚨 구글 AI 서버 과부하 (연속 발생)", "i": "너무 많은 요청이 몰렸습니다. 10~20초 뒤에 다시 시도해주세요."}]

    except Exception as e:
        return [{"q": "🚨 시스템 오류 발생", "i": "첨부된 파일이 너무 크거나 일시적인 문제일 수 있습니다."}]

def reset_all_inputs():
    st.session_state.ai_questions = {"Transform": [], "Tomorrow": [], "Together": []}
    st.session_state.selected_questions = []
    if "input_candidate" in st.session_state: st.session_state.input_candidate = ""
    if "input_jd_txt" in st.session_state: st.session_state.input_jd_txt = "" 
    if "input_feedback" in st.session_state: st.session_state.input_feedback = ""
    if "input_agree" in st.session_state: st.session_state.input_agree = False
    if "input_level" in st.session_state: st.session_state.input_level = list(LEVEL_GUIDELINES.keys())[0]
    st.session_state.uploader_key += 1

# --- 6. 사이드바 구성 ---
with st.sidebar:
    st.title("✈️ Copilot Menu")
    st.success(f"👤 접속 완료: **{st.session_state.user_nickname}** 님")
    
    st.markdown('<div class="security-alert">🚨 <b>보안 주의사항</b><br>민감 정보는 마스킹 후 업로드하세요.</div>', unsafe_allow_html=True)
    
    candidate_name = st.text_input("👤 후보자 이름", placeholder="이름 입력", key="input_candidate")
    selected_level = st.selectbox("1. 레벨 선택", list(LEVEL_GUIDELINES.keys()), key="input_level")
    
    st.subheader("2. JD (채용공고)")
    jd_input = st.text_area(placeholder="나인하이어 채용공고 링크를 붙여넣으세요.", height=100, key="input_jd_txt")
    
    jd_final = None
    if jd_input:
        if jd_input.strip().startswith("http"): 
            jd_fetched = fetch_jd(jd_input.strip())
            if jd_fetched:
                jd_final = jd_fetched
            else:
                st.warning("⚠️ 해당 채용 사이트 보안으로 링크를 읽지 못했습니다! 텍스트를 직접 복사해서 넣어주세요.")
        else:
            jd_final = jd_input 

    st.subheader("3. 이력서 업로드 (필수)")
    resume_file = st.file_uploader("이력서 파일 선택", type=["pdf", "png", "jpg", "jpeg"], label_visibility="collapsed", key=f"uploader_{st.session_state.uploader_key}")
    
    st.subheader("3-1. 포트폴리오 업로드 (선택)")
    portfolio_file = st.file_uploader("포트폴리오 파일 선택", type=["pdf", "png", "jpg", "jpeg"], label_visibility="collapsed", key=f"port_uploader_{st.session_state.uploader_key}")
    
    st.subheader("4. 이전 면접(실무) 전달사항 (선택)")
    tech_feedback = st.text_area("확인 요망 사항", placeholder="예: 협업 시 갈등을 어떻게 해결했는지 더 깊게 검증해 주세요.", height=80, label_visibility="collapsed", key="input_feedback")

    st.divider()
    agree = st.checkbox("✅ 민감 정보 없음을 확인했습니다.", key="input_agree")
    
    if st.button("질문 생성 시작 🚀", type="primary", use_container_width=True, disabled=not agree):
        if resume_file and jd_final:
            with st.spinner("⚡ 3T 핵심 가치 기반 질문을 생성 중입니다... (약 10~15초 소요)"):
                current_api_key = st.session_state.user_key

                def fetch_cat_safe(cat, api_key, delay):
                    # [핵심] 일꾼들이 구글 문을 동시에 두드리지 않도록 2초 간격으로 시차를 줍니다!
                    time.sleep(delay)
                    return cat, generate_questions_by_category(cat, selected_level, resume_file, jd_final, api_key, tech_feedback=tech_feedback, portfolio_file=portfolio_file, count=5)

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = []
                    # 0초, 2초, 4초 뒤에 각각 출발시킵니다.
                    for idx, cat in enumerate(["Transform", "Tomorrow", "Together"]):
                        futures.append(executor.submit(fetch_cat_safe, cat, current_api_key, idx * 2.0))
                        
                    for future in concurrent.futures.as_completed(futures):
                        cat, result = future.result()
                        st.session_state.ai_questions[cat] = result
            st.rerun()
        elif not jd_final and jd_input:
            st.error("JD 내용을 인식하지 못했습니다. URL 대신 텍스트를 붙여넣어 주세요!")
        else:
            st.error("이력서와 JD를 모두 입력해주세요.")

    st.divider()
    
    st.button("🗑️ 초기화", use_container_width=True, on_click=reset_all_inputs)

    st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
    if st.button("🚪 로그아웃", help="인증 화면으로 돌아갑니다"):
        st.session_state.authenticated = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

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
        desc = BAR_RAISER_CRITERIA[cat].split('(')[0].strip()
        with st.expander(f"📌 {cat} ({desc})", expanded=False):
            
            b1, b2 = st.columns(2)
            with b1:
                if st.button("🔄 전체 새로고침", key=f"ref_all_{cat}", use_container_width=True):
                    with st.spinner("새로 뽑는 중..."):
                        st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final, st.session_state.user_key, tech_feedback=tech_feedback, portfolio_file=portfolio_file, count=5)
                        for idx in range(5):
                            if f"chk_{cat}_{idx}" in st.session_state:
                                st.session_state[f"chk_{cat}_{idx}"] = False
                    st.rerun()
            with b2:
                if st.button("♻️ 선택한 질문만 다시 뽑기", key=f"ref_sel_{cat}", use_container_width=True):
                    sel_indices = [idx for idx in range(len(st.session_state.ai_questions[cat])) if st.session_state.get(f"chk_{cat}_{idx}")]
                    if sel_indices:
                        with st.spinner("선택된 질문 교체 중..."):
                            new_qs = generate_questions_by_category(cat, selected_level, resume_file, jd_final, st.session_state.user_key, tech_feedback=tech_feedback, portfolio_file=portfolio_file, count=len(sel_indices))
                            for new_q, target_idx in zip(new_qs, sel_indices):
                                st.session_state.ai_questions[cat][target_idx] = new_q
                                st.session_state[f"chk_{cat}_{target_idx}"] = False
                        st.rerun()
                    else:
                        st.warning("다시 뽑을 질문을 먼저 체크해주세요!")
            
            st.write("") 
            
            for i, q in enumerate(st.session_state.ai_questions.get(cat, [])):
                q_v, i_v = q.get('q', ''), q.get('i', '')
                st.markdown(f"""
                <div class="q-card">
                    <div class="q-text">Q{i+1}. {q_v}</div>
                    <div class="i-text">🎯 <b>의도:</b> {i_v}</div>
                </div>
                """, unsafe_allow_html=True)
                
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
        
        st.session_state.selected_questions[idx]['q'] = st.text_area("질문", value=item.get('q',''), height=100, key=f"aq_{idx}", label_visibility="collapsed")
        st.session_state.selected_questions[idx]['memo'] = st.text_area("메모/답변", value=item.get('memo',''), placeholder="지원자 답변 및 평가 메모...", height=200, key=f"am_{idx}", label_visibility="collapsed")
        
        if st.button("🗑️ 삭제", key=f"del_{idx}"): 
            st.session_state.selected_questions.pop(idx); st.rerun()
        st.markdown("---")

    if st.session_state.selected_questions:
        txt_content = f"=========================================\n"
        txt_content += f" 👤 면접 후보자 : {candidate_name if candidate_name else '이름 미상'}\n"
        txt_content += f" 📊 지원 레벨 : {selected_level}\n"
        txt_content += f"=========================================\n\n"
        
        for idx, s in enumerate(st.session_state.selected_questions):
            cur_q = st.session_state.get(f"aq_{idx}", s['q'])
            cur_a = st.session_state.get(f"am_{idx}", s['memo'])
            
            txt_content += f"▶ [질문 {idx+1}] ({s['cat']} 역량 검증)\n"
            txt_content += f"Q : {cur_q}\n"
            txt_content += f"-----------------------------------------\n"
            txt_content += f"A (답변 및 메모) :\n{cur_a}\n"
            txt_content += f"=========================================\n\n"
            
        st.download_button("💾 결과 텍스트로 저장하기 (.txt)", txt_content, f"면접기록_{candidate_name}.txt", type="primary", use_container_width=True)

if st.session_state.view_mode == "QuestionWide": 
    _, col_center, _ = st.columns([1, 3, 1])
    with col_center:
        render_questions()
elif st.session_state.view_mode == "NoteWide": 
    _, col_center, _ = st.columns([1, 3, 1])
    with col_center:
        render_notes()
else:
    cl, cr = st.columns([1.1, 1])
    with cl: render_questions()
    with cr: render_notes()
