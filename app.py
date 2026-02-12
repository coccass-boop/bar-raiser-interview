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

# (프롬프트용 데이터 - 기존 유지)
VALUE_SYSTEM_PROMPT = {
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
    
    with tab1:
        url_input = st.text_input("URL 입력")
        jd_from_url = fetch_jd(url_input) if url_input else ""
    with tab2:
        jd_from_text = st.text_area("내용 붙여넣기", height=150)

    jd_final_content = jd_from_text if jd_from_text else jd_from_url

    st.subheader("3. 이력서")
    resume_file = st.file_uploader("PDF 업로드", type="pdf")
    
    st.divider()
    main_btn = st.button("전체 질문 생성 시작 🚀", type="primary", use_container_width=True)

# --- 6. 메인 화면 UI ---
st.title("✈️ Bar Raiser Copilot")

# [디자인 적용] Trinity Values 카드형 레이아웃
st.markdown("<h2 style='text-align: center; margin-bottom: 30px;'>Trinity Values</h2>", unsafe_allow_html=True)

# Card 1: Transform
with st.container(border=True):
    st.markdown("### **We TRANSFORM through :**")
    st.markdown("""
    - 💡 **Customer-First Innovation** | 모든 결정은 고객에게 미치는 영향을 가장 먼저 고려해 이뤄집니다.
    - 📈 **Enduring Value Creation** | 시간이 지날수록 더 큰 가치를 만들어내는 솔루션을 구축합니다.
    - 🎯 **Excellence in Execution** | 디지털 전환의 새로운 기준을 세웁니다.
    """, unsafe_allow_html=True)

# Card 2: Tomorrow
with st.container(border=True):
    st.markdown("### **We shape TOMORROW by :**")
    st.markdown("""
    - 🌱 **Active Learning** | 고객 접점에서 발생하는 모든 경험을 공동의 지식으로 전환합니다.
    - 🚀 **Forward Thinking** | 미래를 고려해 확장성과 지속성을 갖춘 솔루션을 구축합니다.
    - ⚡ **Speed with Impact** | 성과는 빠르게 달성하면서도 장기적인 가치를 쌓아갑니다.
    """, unsafe_allow_html=True)

# Card 3: Together
with st.container(border=True):
    st.markdown("### **We succeed TOGETHER through :**")
    st.markdown("""
    - 🤝 **Power of Three** | 고객, 파트너, 그리고 우리 팀이 하나로 연결됩니다.
    - 💗 **Trust & Growth** | 서로의 발전을 지원하며 함께 성장합니다.
    - 🌐 **Global Perspective** | 문화와 시장을 연결하는 가교 역할을 합니다.
    """, unsafe_allow_html=True)

st.divider()

if main_btn:
    if resume_file and jd_final_content:
        with st.spinner("이력서와 JD를 정밀 분석 중입니다..."):
            for cat in ["Transform", "Tomorrow", "Together"]:
                st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final_content)
    else:
        if not resume_file: st.error("이력서 PDF를 업로드해주세요.")
        if not jd_final_content: st.error("JD URL을 입력하거나 내용을 붙여넣어주세요.")

col_q, col_n = st.columns([1.2, 1])

# [왼쪽] 질문 리스트
with col_q:
    st.subheader("🤖 제안 질문 리스트")
    for cat in ["Transform", "Tomorrow", "Together"]:
        with st.expander(f"📌 {cat} 리스트", expanded=True):
            head_col, btn_col = st.columns([0.8, 0.2])
            head_col.markdown(f"**{cat} Candidates**")
            if btn_col.button("🔄", key=f"ref_{cat}"):
                if resume_file and jd_final_content:
                    with st.spinner(f"{cat} 갱신 중..."):
                        st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final_content)
                    st.rerun()
            
            st.divider()
            for i, q in enumerate(st.session_state.ai_questions[cat]):
                q_col, add_col = st.columns([0.88, 0.12])
                q_col.write(f"**Q. {q['q']}**")
                if add_col.button("➕", key=f"add_{cat}_{i}"):
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
        for idx, item in enumerate(st.session_state.selected_questions):
            h_col, d_col = st.columns([0.9, 0.1])
            h_col.markdown(f"**Question {idx+1}**")
            if d_col.button("❌", key=f"del_{idx}"):
                st.session_state.selected_questions.pop(idx)
                st.rerun()
            
            st.session_state.selected_questions[idx]['q'] = st.text_input(f"질문_{idx}", value=item['q'], label_visibility="collapsed", key=f"input_q_{idx}")
            st.session_state.selected_questions[idx]['memo'] = st.text_area(f"메모_{idx}", value=item['memo'], placeholder="메모...", height=100, label_visibility="collapsed", key=f"input_m_{idx}")
            st.divider()
        
        if st.session_state.selected_questions:
            output_content = f"Target Level: {selected_level}\n" + "="*30 + "\n"
            for sq in st.session_state.selected_questions:
                output_content += f"\n[Q] {sq['q']}\n[A] {sq['memo']}\n"
            st.download_button("💾 결과 다운로드 (.txt)", output_content, f"Interview_{selected_level}.txt", type="primary", use_container_width=True)
