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

# --- 3. 세션 상태 관리 ---
if "ai_questions" not in st.session_state:
    st.session_state.ai_questions = {"Transform": [], "Tomorrow": [], "Together": []}
if "selected_questions" not in st.session_state:
    st.session_state.selected_questions = []
if "wide_mode" not in st.session_state:
    st.session_state.wide_mode = False

# 바레이저 전용 핵심 3T 기준 정의
BAR_RAISER_CRITERIA = {
    "Transform": "Create Enduring Value (시간이 지날수록 더 큰 가치를 만들어내는 솔루션 구축)",
    "Tomorrow": "Forward Thinking (미래를 고려해 확장성과 지속성을 갖춘 솔루션 구축)",
    "Together": "Trust & Growth (서로의 발전을 지원하며 함께 성장)"
}

LEVEL_GUIDELINES = {
    "IC-L3": "[기본기 실무자] 가이드 하 업무 수행.",
    "IC-L4": "[자기완결 실무자] 목표 내 업무 독립적 계획/실행.",
    "IC-L5": "[핵심 전문가] 최적 대안 제시 및 전파.",
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
    # 바레이저 타겟 가치 설정
    target_value = BAR_RAISER_CRITERIA[category]
    
    prompt = f"""
    [Role] You are an expert 'Bar Raiser' interviewer. 
    [Mission] Generate 10 deep-dive interview questions for the candidate.
    
    [Target Evaluation Criteria]
    - Category: {category}
    - Specific Focus: {target_value}
    
    [Contextual References (Use for background, but do not target specifically)]
    - Other Values: Customer-First Innovation, Excellence in Execution, Active Learning, Speed with Impact, Power of Three, Global Perspective.
    
    [Input Data]
    - Candidate Level: {level}
    - Job Description: {jd_text[:3000]}
    - Candidate Resume: (Attached as PDF)
    
    [Requirements]
    1. Focus strictly on evaluating '{target_value}'.
    2. Analyze the gap between the candidate's experience and the JD requirements.
    3. Return ONLY a valid JSON list of objects: [{{"q": "질문 내용", "i": "질문 의도 및 평가 포인트"}}]
    """
    try:
        pdf_base64 = base64.b64encode(resume_file.getvalue()).decode('utf-8')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={API_KEY}"
        data = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "application/pdf", "data": pdf_base64}}]}]}
        res = requests.post(url, json=data, timeout=60)
        cleaned = res.json()['candidates'][0]['content']['parts'][0]['text'].replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except: return []

# --- 5. 사이드바 (디자인 유지) ---
with st.sidebar:
    st.title("✈️ Copilot Menu")
    selected_level = st.selectbox("레벨 선택", list(LEVEL_GUIDELINES.keys()))
    st.info(f"💡 {LEVEL_GUIDELINES[selected_level]}")
    
    st.subheader("2. JD (채용공고)")
    tab1, tab2 = st.tabs(["🔗 URL", "📝 텍스트"])
    with tab1:
        url_input = st.text_input("URL 입력")
        jd_from_url = fetch_jd(url_input) if url_input else ""
    with tab2:
        jd_from_text = st.text_area("내용 붙여넣기", height=150)
    jd_final_content = jd_from_text if jd_from_text else jd_from_url

    st.subheader("3. 이력서")
    resume_file = st.file_uploader("PDF 업로드", type="pdf")
    
    st.divider()
    if st.button("질문 생성 시작 🚀", type="primary", use_container_width=True):
        if resume_file and jd_final_content:
            with st.spinner("바레이저 기준에 맞춰 질문 설계 중..."):
                for cat in ["Transform", "Tomorrow", "Together"]:
                    st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final_content)
        else: st.error("이력서와 JD를 모두 확인해주세요.")

# --- 6. 메인 화면 ---
st.title("✈️ Bar Raiser Copilot")
st.divider()

# 레이아웃 제어
if st.session_state.wide_mode:
    col_q_ratio, col_n_ratio = 10, 0.01
    toggle_btn_label = "🔙 면접관 노트 다시 열기"
else:
    col_q_ratio, col_n_ratio = 1.1, 1
    toggle_btn_label = "↔️ 질문 리스트 넓게 보기 (노트 접기)"

col_q, col_n = st.columns([col_q_ratio, col_n_ratio])

# [왼쪽] 제안 질문 리스트
with col_q:
    st.subheader("🎯 제안 질문 리스트")
    if st.button(toggle_btn_label):
        st.session_state.wide_mode = not st.session_state.wide_mode
        st.rerun()

    for cat in ["Transform", "Tomorrow", "Together"]:
        # expander 내부에 새로고침 버튼을 우측 상단으로 배치
        with st.expander(f"📌 {cat} 리스트 ({BAR_RAISER_CRITERIA[cat].split('(')[0]})", expanded=True):
            head_col, ref_col = st.columns([0.94, 0.06])
            with ref_col:
                if st.button("🔄", key=f"ref_{cat}", help=f"{cat} 새로고침"):
                    if resume_file and jd_final_content:
                        st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final_content)
                        st.rerun()
            
            if not st.session_state.ai_questions[cat]:
                st.write("질문이 없습니다.")
            
            for i, q in enumerate(st.session_state.ai_questions[cat]):
                # + 버튼 중앙 정렬 및 크기 최적화
                qc, ac = st.columns([0.94, 0.06])
                qc.write(f"**Q. {q['q']}**")
                with ac:
                    st.markdown("<div style='margin-top:-5px;'>", unsafe_allow_html=True)
                    if st.button("➕", key=f"add_{cat}_{i}"):
                        if q['q'] not in [sq['q'] for sq in st.session_state.selected_questions]:
                            st.session_state.selected_questions.append({"q": q['q'], "cat": cat, "memo": ""})
                    st.markdown("</div>", unsafe_allow_html=True)
                st.caption(f"🎯 의도: {q['i']}")
                st.divider()

# [오른쪽] 면접관 노트
if not st.session_state.wide_mode:
    with col_n:
        st.subheader("📝 면접관 노트")
        if st.button("➕ 질문을 직접 입력하세요.", use_container_width=True):
            st.session_state.selected_questions.append({"q": "", "cat": "Custom", "memo": ""})
        
        st.divider()
        for idx, item in enumerate(st.session_state.selected_questions):
            tag_col, del_col = st.columns([0.95, 0.05])
            cat_label = item.get('cat', 'Custom')
            tag_col.markdown(f"<span style='font-size:0.8rem; color:gray;'>Q{idx+1}</span> <span style='background-color:#f0f2f6; padding:2px 6px; border-radius:4px; font-size:0.7rem; font-weight:bold;'>{cat_label}</span>", unsafe_allow_html=True)
            
            if del_col.button("✕", key=f"del_{idx}"):
                st.session_state.selected_questions.pop(idx)
                st.rerun()
            
            # 질문 영역 (동적 높이 조절로 전체 보이게 설정)
            q_text = item['q']
            q_height = max(70, (len(q_text) // 35) * 25 + 30)
            st.session_state.selected_questions[idx]['q'] = st.text_area(
                f"q_{idx}", value=q_text, placeholder="질문을 입력하세요.", 
                label_visibility="collapsed", height=q_height, key=f"area_q_{idx}"
            )
            
            # 메모 영역
            st.session_state.selected_questions[idx]['memo'] = st.text_area(
                f"m_{idx}", value=item.get('memo',''), placeholder="답변 메모...", 
                label_visibility="collapsed", height=150, key=f"area_m_{idx}"
            )
            st.markdown("<div style='margin-bottom:15px; border-bottom:1px solid #eee;'></div>", unsafe_allow_html=True)

        if st.session_state.selected_questions:
            output = f"Target Level: {selected_level}\nDate: {datetime.datetime.now()}\n"
            for s in st.session_state.selected_questions:
                output += f"\n[{s.get('cat','Custom')}] Q: {s['q']}\nA: {s.get('memo','')}\n"
            st.download_button("💾 결과 저장 (.txt)", output, f"Interview_{selected_level}.txt", type="primary", use_container_width=True)
