import streamlit as st
import requests
import json
import base64
import re
from bs4 import BeautifulSoup

# --- 1. 기본 설정 (절대 건드리지 않음) ---
st.set_page_config(page_title="Bar Raiser Copilot", page_icon="✈️", layout="wide")

# 스타일 CSS
st.markdown("""
    <style>
    [data-testid="column"] { min-width: 320px !important; }
    .stMarkdown p, .stSubheader { word-break: keep-all !important; }
    .v-center { display: flex !important; align-items: center !important; justify-content: center !important; height: 100% !important; padding-top: 10px !important; }
    .v-center button { height: 32px !important; width: 32px !important; padding: 0px !important; }
    .q-block { margin-bottom: 15px !important; padding-bottom: 5px !important; }
    .q-text { font-size: 16px !important; font-weight: 600 !important; line-height: 1.6 !important; margin-bottom: 8px !important; }
    [data-testid="stSidebar"] .stButton button { width: 100% !important; height: auto !important; }
    .reset-btn button { background-color: #ff4b4b !important; color: white !important; border: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 초기화 ---
if "ai_questions" not in st.session_state: st.session_state.ai_questions = {"Transform": [], "Tomorrow": [], "Together": []}
if "selected_questions" not in st.session_state: st.session_state.selected_questions = []
if "view_mode" not in st.session_state: st.session_state.view_mode = "Standard"
if "temp_setting" not in st.session_state: st.session_state.temp_setting = 0.7
if "last_error" not in st.session_state: st.session_state.last_error = ""

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
    # [수정] 크롬 브라우저인 척 위장하여 차단 회피
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for s in soup(['script', 'style']): s.decompose() # 잡다한 코드 제거
            text = soup.get_text(separator=' ', strip=True)
            return text if len(text) > 50 else None
    except Exception as e:
        return None

def generate_questions_by_category(category, level, resume_file, jd_text):
    api_key = st.secrets.get("GEMINI_API_KEY")
    prompt = f"""당신은 Bar Raiser 면접관입니다. 
    가치: {BAR_RAISER_CRITERIA[category]}. 레벨: {level}. 
    이력서와 JD를 바탕으로 한국어 심층 면접 질문 10개를 작성하세요.
    오직 JSON 배열만 출력하세요: [{{"q": "질문", "i": "의도"}}]"""
    
    file_ext = resume_file.name.split('.')[-1].lower()
    mime_type = "application/pdf" if file_ext == "pdf" else f"image/{file_ext.replace('jpg', 'jpeg')}"
    file_content = base64.b64encode(resume_file.getvalue()).decode('utf-8')
    
    # [핵심] 3중 엔진 폴백 시스템 (순차 시도)
    models = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-pro"]
    
    for model in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            data = {
                "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": mime_type, "data": file_content}}]}],
                "generationConfig": {"temperature": st.session_state.temp_setting},
                "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
            }
            res = requests.post(url, json=data, timeout=60)
            res_json = res.json()
            
            if 'candidates' in res_json:
                raw_text = res_json['candidates'][0]['content']['parts'][0]['text']
                json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_text, re.DOTALL)
                if json_match: return json.loads(json_match.group())
            
            st.session_state.last_error = f"{model} 응답 없음: {str(res_json)[:100]}"
        except Exception as e:
            st.session_state.last_error = str(e)
            continue
            
    return []

# --- 4. 화면 구성 ---

# [사이드바]
with st.sidebar:
    st.title("✈️ Copilot Menu")
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
            else: st.warning("⚠️ URL 접속 실패. 텍스트를 직접 붙여넣으세요.")
    with tab2:
        jd_text_area = st.text_area("내용 붙여넣기", height=150)
    jd_final = jd_text_area if jd_text_area else jd_fetched

    st.subheader("3. 이력서")
    resume_file = st.file_uploader("파일 업로드", type=["pdf", "png", "jpg", "jpeg"])
    
    st.divider()
    if st.button("질문 생성 시작 🚀", type="primary", use_container_width=True):
        if resume_file and jd_final:
            with st.spinner("질문 생성 중..."):
                for cat in ["Transform", "Tomorrow", "Together"]:
                    st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final)
            st.rerun()
        else: st.error("이력서와 JD를 모두 입력해주세요.")

    st.divider()
    st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
    if st.button("🗑️ 초기화", use_container_width=True):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    with st.expander("⚙️"):
        st.session_state.temp_setting = st.slider("Temp", 0.0, 1.0, st.session_state.temp_setting)
        if st.session_state.last_error: st.error(st.session_state.last_error)

# [메인 타이틀]
st.title("✈️ Bar Raiser Copilot")

# [뷰 모드 버튼]
c1, c2, c3 = st.columns(3)
if c1.button("↔️ 질문 리스트만 보기", use_container_width=True): st.session_state.view_mode = "QuestionWide"; st.rerun()
if c2.button("⬅️ 기본 보기 (반반)", use_container_width=True): st.session_state.view_mode = "Standard"; st.rerun()
if c3.button("↔️ 면접관 노트만 보기", use_container_width=True): st.session_state.view_mode = "NoteWide"; st.rerun()

st.divider()

# --- 5. 렌더링 함수 (정의 먼저, 호출 나중) ---
def render_questions():
    st.subheader("🎯 제안 질문 리스트")
    if not any(st.session_state.ai_questions.values()):
        st.info("👈 사이드바에서 [질문 생성 시작] 버튼을 눌러주세요.")
        return

    for cat in ["Transform", "Tomorrow", "Together"]:
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
            if not questions: st.warning("질문 생성에 실패했습니다. (사이드바 ⚙️ 로그 확인)")
            
            for i, q in enumerate(questions):
                q_val = q.get('q', '')
                i_val = q.get('i', '')
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

# --- 6. 실행 로직 (안전장치 포함) ---
try:
    if st.session_state.view_mode == "QuestionWide":
        render_questions()
    elif st.session_state.view_mode == "NoteWide":
        render_notes()
    else:
        col_l, col_r = st.columns([1.1, 1])
        with col_l: render_questions()
        with col_r: render_notes()
except Exception as e:
    st.error(f"화면 렌더링 중 오류가 발생했습니다: {e}")
