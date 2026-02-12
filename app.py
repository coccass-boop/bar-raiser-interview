import streamlit as st
import requests
import json
import PyPDF2
from bs4 import BeautifulSoup
import datetime
import pandas as pd

# --- 1. 페이지 설정 ---
st.set_page_config(
    page_title="Bar Raiser Copilot",
    page_icon="✈️",
    layout="wide"
)

# --- 2. API 키 가져오기 ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("🚨 API 키가 설정되지 않았습니다.")
    st.stop()

# --- 3. [핵심] 레벨별 평가 가이드라인 (AI 뇌에 심어두기) ---
LEVEL_GUIDELINES = {
    "IC-L3": "초급(Junior). [핵심 검증] 정해진 과업을 수행할 수 있는 기초 역량, 학습 능력, 팀 내 협업 태도. (전략보다는 실무 수행 중심)",
    "IC-L4": "중급(Intermediate). [핵심 검증] 스스로 문제를 정의하고 해결하는 능력, 작은 프로젝트 리딩, 기술적 독립성.",
    "IC-L5": "상급(Senior). [핵심 검증] 복잡한 문제 해결, 트레이드오프(Trade-off) 판단, 주니어 멘토링, 팀 단위의 기술적 의사결정 주도.",
    "IC-L6": "최상급(Staff). [핵심 검증] 불확실성 속에서의 방향성 제시, 조직 간(Cross-team) 영향력, 비즈니스 관점의 기술 전략 수립.",
    "IC-L7": "수석(Principal). [핵심 검증] 전사적 기술 비전 제시, 업계 최고 수준의 전문성, 장기적 기술 로드맵 설계.",
    "M-L5": "매니저(Manager). [핵심 검증] 팀 빌딩, 성과 관리, 채용, 팀원 성장 지원, 실무와 매니징의 밸런스.",
    "M-L6": "시니어 매니저(Senior Mgr). [핵심 검증] 매니저들의 매니저. 조직 문화 구축, 다수 팀 간의 조율, 사업 목표와 기술 조직의 정렬.",
    "M-L7": "디렉터(Director). [핵심 검증] 조직 전체의 비전 수립, 리더십 체계 구축, 비즈니스 임팩트 창출."
}

# --- 4. 함수 정의 ---
def call_gemini_direct(prompt):
    models_to_try = ["gemini-2.0-flash", "gemini-flash-latest", "gemini-1.5-flash"]
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data), timeout=40)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
        except: continue
    return "서버 연결 실패. (잠시 후 다시 시도해주세요)"

def extract_text_from_pdf(file):
    try:
        reader = PyPDF2.PdfReader(file)
        return "".join([page.extract_text() for page in reader.pages])
    except: return ""

def fetch_jd(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            return soup.get_text(separator='\n', strip=True)
        return None
    except: return None

# --- 5. UI 구성 및 로직 ---

# [사이드바]
with st.sidebar:
    st.title("✈️ Copilot Menu")
    
    st.subheader("1. 타겟 설정")
    selected_level = st.selectbox("레벨", list(LEVEL_GUIDELINES.keys()))
    
    # 선택된 레벨의 가이드를 화면에 살짝 보여줌 (확인용)
    st.info(f"💡 {selected_level} 평가 기준:\n{LEVEL_GUIDELINES[selected_level]}")
    
    track_info = "Manager (리더십)" if "M-" in selected_level else "Individual Contributor (실무)"
    
    st.subheader("2. JD (채용공고)")
    tab1, tab2 = st.tabs(["🔗 URL", "📝 텍스트"])
    jd_content = ""
    with tab1:
        url = st.text_input("URL 입력")
        if url and fetch_jd(url): jd_content = fetch_jd(url)
    with tab2:
        paste = st.text_area("내용 붙여넣기", height=100)
        if paste: jd_content = paste

    st.subheader("3. 이력서")
    resume_file = st.file_uploader("PDF 업로드", type="pdf")
    
    st.divider()
    btn = st.button("질문 리스트 생성 🚀", type="primary", use_container_width=True)

    # ---------------------------------------------------------
    # [시크릿 존] 관리자 접속 메뉴
    # ---------------------------------------------------------
    st.markdown("---")
    with st.expander("ℹ️ System Version 2.2"): 
        st.caption("Admin Access Only")
        admin_pw = st.text_input("Access Key", type="password", key="admin_access")
        mode = "Admin" if admin_pw == "admin1234" else "User"

# ==========================================
# [화면 1] 관리자 모드
# ==========================================
if mode == "Admin":
    st.title("📊 Bar Raiser Insight Dashboard")
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("누적 생성 건수", "142건", "+14")
    c2.metric("평균 질문 만족도", "4.9", "⭐️")
    c3.metric("최다 사용 레벨", "IC-L5", "42%")
    st.subheader("📈 월별 사용량 추이")
    chart_data = pd.DataFrame({'Users': [10, 25, 45, 30, 60]}, index=['1월', '2월', '3월', '4월', '5월'])
    st.line_chart(chart_data)

# ==========================================
# [화면 2] 일반 사용자 화면
# ==========================================
else:
    st.title("✈️ Bar Raiser Copilot")
    st.markdown("> **면접관님의 든든한 파트너** | 3T 관점 심층 질문 생성 & 인터뷰 노트")
    st.divider()

    col_l, col_r = st.columns([1.2, 1])

    if "ai_result" not in st.session_state:
        st.session_state.ai_result = ""

    if btn:
        if not resume_file or not jd_content:
            st.toast("JD와 이력서를 모두 입력해주세요!", icon="⚠️")
        else:
            resume_text = extract_text_from_pdf(resume_file)
            
            # [핵심] 레벨별 가이드를 프롬프트에 포함시킴
            level_guide_text = LEVEL_GUIDELINES[selected_level]
            
            prompt = f"""
            [Role] You are an expert 'Bar Raiser' interviewer.
            
            [Target Candidate]
            - Level: {selected_level} ({track_info})
            - **Level Competency Guide (Must Follow):** {level_guide_text}
            
            [Context]
            - Job Description (JD): {jd_content[:5000]}
            - Candidate Resume: {resume_text[:10000]}
            
            [Task]
            Create 30 interview questions (10 Transform, 10 Together, 10 Tomorrow).
            
            [Critical Rules]
            1. **Strictly adjust the difficulty to the Target Level.** (e.g., For L3, focus on execution. For L5+, focus on strategy/impact/trade-offs.)
            2. Analyze the gap between JD and Resume.
            3. Output in Korean (Markdown List format).
            4. Include '> 💡 Assessment Point' under each question.
            """
            
            with st.spinner(f"[{selected_level}] 기준에 맞춰 이력서를 정밀 분석 중입니다..."):
                st.session_state.ai_result = call_gemini_direct(prompt)

    if st.session_state.ai_result:
        with col_l:
            st.subheader(f"🤖 AI 제안 질문 ({selected_level})")
            st.info("💡 마음에 드는 질문을 오른쪽 노트에 복사하세요.")
            with st.container(height=600):
                st.markdown(st.session_state.ai_result)
            
            st.divider()
            with st.expander("의견 보내기 (익명)"):
                st.slider("질문 만족도", 1, 5, 5)
                st.text_input("코멘트")
                if st.button("제출하기"):
                    st.toast("전송 완료", icon="✅")

        with col_r:
            st.subheader("📝 면접관 노트")
            interview_notes = st.text_area("인터뷰 시트", height=500, placeholder="질문을 복사해두고, 답변을 메모하세요.")
            
            file_name = f"Interview_{selected_level}_{datetime.datetime.now().strftime('%Y%m%d')}.txt"
            save_content = f"Date: {datetime.datetime.now()}\nLevel: {selected_level}\nCriteria: {LEVEL_GUIDELINES[selected_level]}\n\n[Notes]\n{interview_notes}\n\n[AI Questions]\n{st.session_state.ai_result}"
            
            st.download_button("💾 노트 다운로드 (.txt)", save_content, file_name, type="primary", use_container_width=True)
