import streamlit as st
import requests
import json
import base64
import datetime
from bs4 import BeautifulSoup

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="Bar Raiser Copilot", page_icon="✈️", layout="wide")

# --- 2. API 키 설정 ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("🚨 API 키를 설정해주세요.")
    st.stop()

# --- 3. 데이터 및 세션 초기화 ---
if "ai_questions" not in st.session_state:
    st.session_state.ai_questions = {"Transform": [], "Tomorrow": [], "Together": []}
if "selected_questions" not in st.session_state:
    st.session_state.selected_questions = []

VALUE_SYSTEM = {
    "Transform": ["1. Customer-First Innovation", "2. Enduring Value Creation", "3. Excellence in Execution"],
    "Tomorrow": ["4. Active Learning", "5. Forward Thinking", "6. Speed with Impact"],
    "Together": ["7. Power of Three", "8. Trust & Growth", "9. Global Perspective"]
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

# --- 4. 핵심 기능 함수 ---
def fetch_jd(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            return soup.get_text(separator='\n', strip=True)
    except: return None

def generate_questions_by_category(category, level, resume_file, jd_text):
    prompt = f"""
    [Role] Bar Raiser Interviewer. Framework: 3T & 9Value.
    [Target] {level}. [Category] {category}.
    [JD] {jd_text[:3000]}
    [Task] Create 10 unique questions in Korean for '{category}'. 
    Analyze the gap between JD and Resume.
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

# --- 5. 사이드바 디자인 ---
with st.sidebar:
    st.title("✈️ Copilot Menu")
    selected_level = st.selectbox("레벨 선택", list(LEVEL_GUIDELINES.keys()))
    st.info(f"💡 {LEVEL_GUIDELINES[selected_level]}")
    
    st.subheader("2. JD (채용공고)")
    tab1, tab2 = st.tabs(["🔗 URL", "📝 텍스트"])
    jd_content = ""
    with tab1:
        url_input = st.text_input("URL 입력")
        if url_input: jd_content = fetch_jd(url_input)
    with tab2:
        jd_content = st.text_area("내용 붙여넣기", height=150)

    st.subheader("3. 이력서")
    resume_file = st.file_uploader("PDF 업로드", type="pdf")
    
    st.divider()
    main_btn = st.button("전체 질문 생성 시작 🚀", type="primary", use_container_width=True)
    
    with st.expander("ℹ️ System v3.9.2"):
        admin_pw = st.text_input("Access Key", type="password")
        mode = "Admin" if admin_pw == "admin1234" else "User"

# --- 6. 메인 화면 UI ---
st.title("✈️ Bar Raiser Copilot")

# 상단 가이드 (접기 가능)
with st.expander("💡 바레이저 3T & 9VALUE 가이드"):
    c1, c2, c3 = st.columns(3)
    for i, cat in enumerate(VALUE_SYSTEM.keys()):
        with [c1, c2, c3][i]:
            st.markdown(f"**{cat}**")
            for v in VALUE_SYSTEM[cat]: st.caption(v)

if main_btn:
    if resume_file and jd_content:
        with st.spinner("이력서와 JD를 정밀 분석 중입니다..."):
            for cat in ["Transform", "Tomorrow", "Together"]:
                st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_content)
    else: st.warning("이력서와 JD를 모두 입력해주세요.")

col_q, col_n = st.columns([1.2, 1])

# [왼쪽] 질문 리스트
with col_q:
    st.subheader("🤖 제안 질문 리스트")
    for cat in ["Transform", "Tomorrow", "Together"]:
        with st.expander(f"📌 {cat} 리스트", expanded=True):
            # [디자인 수정] 제목줄에 새로고침 버튼 작게 배치
            head_col, btn_col = st.columns([0.8, 0.2])
            head_col.markdown(f"**{cat} Candidates**")
            if btn_col.button("🔄", key=f"ref_{cat}", help=f"{cat} 항목만 다시 생성"):
                if resume_file and jd_content:
                    with st.spinner(f"{cat} 갱신 중..."):
                        st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_content)
                    st.rerun()
            
            st.divider()
            
            for i, q in enumerate(st.session_state.ai_questions[cat]):
                q_col, add_col = st.columns([0.88, 0.12])
                q_col.write(f"**Q. {q['q']}**")
                # 추가 버튼도 조금 더 직관적으로
                if add_col.button("➕", key=f"add_{cat}_{i}", help="노트에 추가"):
                    if q['q'] not in [sq['q'] for sq in st.session_state.selected_questions]:
                        st.session_state.selected_questions.append({"q": q['q'], "memo": ""})
                st.caption(f"🎯 의도: {q['i']}")
                st.divider()

# [오른쪽] 면접관 실시간 노트
with col_n:
    with st.expander("📝 면접관 실시간 노트 (기록창)", expanded=True):
        if st.button("➕ 직접 준비한 질문 추가", use_container_width=True):
            st.session_state.selected_questions.append({"q": "직접 입력한 질문입니다.", "memo": ""})
        
        st.divider()
        
        if not st.session_state.selected_questions:
            st.write("왼쪽 리스트에서 ➕ 버튼을 눌러 질문을 추가하세요.")
        
        for idx, item in enumerate(st.session_state.selected_questions):
            # 질문 헤더 + 삭제 버튼
            h_col, d_col = st.columns([0.9, 0.1])
            h_col.markdown(f"**Question {idx+1}**")
            if d_col.button("❌", key=f"del_{idx}", help="이 문항 삭제"):
                st.session_state.selected_questions.pop(idx)
                st.rerun()
            
            # 질문 내용 (수정 가능)
            st.session_state.selected_questions[idx]['q'] = st.text_input(
                f"질문_{idx}", value=item['q'], label_visibility="collapsed", key=f"input_q_{idx}"
            )
            
            # 답변 칸
            st.session_state.selected_questions[idx]['memo'] = st.text_area(
                f"메모_{idx}", value=item['memo'], placeholder="답변 내용 및 평가 기록...", 
                height=100, label_visibility="collapsed", key=f"input_m_{idx}"
            )
            st.divider()
        
        if st.session_state.selected_questions:
            # 다운로드 데이터 구성
            output_content = f"Target Level: {selected_level}\nDate: {datetime.datetime.now()}\n" + "="*30 + "\n"
            for sq in st.session_state.selected_questions:
                output_content += f"\n[Q] {sq['q']}\n[A] {sq['memo']}\n"
            
            st.download_button("💾 결과 다운로드 (.txt)", output_content, f"Interview_{selected_level}.txt", type="primary", use_container_width=True)
