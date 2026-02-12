import streamlit as st
import requests
import json
import PyPDF2
from bs4 import BeautifulSoup
import datetime
import pandas as pd
import random # (통계 예시 보여주기용, 나중에 삭제)

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

# --- 3. 함수 정의 ---
def call_gemini_direct(prompt):
    models_to_try = ["gemini-2.0-flash", "gemini-flash-latest"]
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data), timeout=40)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
        except: continue
    return "서버 연결 실패. 다시 시도해주세요."

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

# --- 4. UI 구성 ---

# 사이드바 (공통 메뉴 + 관리자 로그인)
with st.sidebar:
    st.title("✈️ Copilot Menu")
    
    # 모드 전환 (일반 사용자 vs 관리자)
    st.divider()
    admin_pw = st.text_input("🔒 관리자 접속 (PW)", type="password")
    
    if admin_pw == "admin1234": # [임시 비밀번호]
        mode = "Admin"
        st.success("✅ 관리자 모드 활성화")
    else:
        mode = "User"

# ==========================================
# [화면 1] 관리자 대시보드 (Admin Mode)
# ==========================================
if mode == "Admin":
    st.title("📊 Bar Raiser Insight Dashboard")
    st.markdown("바레이저들이 생성한 데이터와 피드백을 실시간으로 분석합니다.")
    st.divider()
    
    # (가짜 데이터로 예시를 보여줍니다. 나중에 구글 시트와 연결되면 진짜 데이터가 뜹니다.)
    col1, col2, col3 = st.columns(3)
    col1.metric("총 생성된 질문 세트", "128건", "+12건")
    col2.metric("바레이저 평균 만족도", "4.8 / 5.0", "⭐️⭐️⭐️⭐️⭐️")
    col3.metric("가장 많이 선택된 레벨", "IC-L5 (Senior)", "42%")
    
    st.subheader("📈 트랙별 사용 현황")
    # 예시 차트 데이터
    chart_data = pd.DataFrame({
        'Level': ['IC-L3', 'IC-L4', 'IC-L5', 'IC-L6', 'M-L5'],
        'Usage': [10, 25, 45, 15, 33]
    })
    st.bar_chart(chart_data.set_index('Level'))

    st.subheader("💬 최신 바레이저 피드백 (Real-time)")
    st.info("바레이저들이 남긴 개선 의견입니다.")
    feedback_data = [
        {"날짜": "2024-02-12", "작성자": "익명", "의견": "JD 분석이 좀 더 구체적이었으면 좋겠어요."},
        {"날짜": "2024-02-11", "작성자": "익명", "의견": "질문 퀄리티가 아주 좋습니다! L5 전략 질문 굿."},
        {"날짜": "2024-02-10", "작성자": "익명", "의견": "Together 항목 질문이 좀 더 부드러웠으면 해요."}
    ]
    st.table(pd.DataFrame(feedback_data))

# ==========================================
# [화면 2] 일반 사용자 화면 (Bar Raiser View)
# ==========================================
else:
    st.title("✈️ Bar Raiser Copilot")
    st.markdown("> **면접관님의 든든한 파트너** | 3T 관점 심층 질문 생성 & 인터뷰 노트")
    st.divider()

    # 입력창 (사이드바에 있던 걸 위로 올리거나 유지 가능, 여기선 사이드바 유지)
    with st.sidebar:
        st.subheader("1. 타겟 레벨")
        selected_level = st.selectbox("레벨", ["IC-L3", "IC-L4", "IC-L5", "IC-L6", "IC-L7", "M-L5", "M-L6", "M-L7"])
        track_info = "Manager (리더십)" if "M-" in selected_level else "Individual Contributor (실무)"
        st.caption(f"🎯 {track_info}")
        
        st.subheader("2. JD (채용공고)")
        tab1, tab2 = st.tabs(["🔗 URL", "📝 텍스트"])
        jd_content = ""
        with tab1:
            url = st.text_input("URL 입력")
            if url and fetch_jd(url): jd_content = fetch_jd(url)
        with tab2:
            paste = st.text_area("직접 붙여넣기", height=100)
            if paste: jd_content = paste

        st.subheader("3. 이력서")
        resume_file = st.file_uploader("PDF 업로드", type="pdf")
        
        st.divider()
        btn = st.button("질문 리스트 생성 🚀", type="primary", use_container_width=True)

    # 메인 UI
    col_l, col_r = st.columns([1.2, 1])

    if "ai_result" not in st.session_state:
        st.session_state.ai_result = ""

    if btn:
        if not resume_file or not jd_content:
            st.toast("JD와 이력서를 모두 입력해주세요!", icon="⚠️")
        else:
            resume_text = extract_text_from_pdf(resume_file)
            prompt = f"""
            [Bar Raiser Assistant]
            타겟: {selected_level} ({track_info})
            JD: {jd_content[:5000]}
            이력서: {resume_text[:10000]}
            
            요청:
            1. 질문 30개 (3T 각 10개) 생성.
            2. 각 질문 아래 '> 💡 의도: ...' 포함.
            3. 인사말 생략, Markdown 리스트만 출력.
            """
            with st.spinner("분석 중..."):
                st.session_state.ai_result = call_gemini_direct(prompt)

    # 결과 화면
    if st.session_state.ai_result:
        with col_l:
            st.subheader("🤖 AI 제안 질문")
            st.info("💡 마음에 드는 질문을 오른쪽 노트에 복사하세요.")
            with st.container(height=600):
                st.markdown(st.session_state.ai_result)
            
            # [핵심] 피드백 수집 구간
            st.divider()
            st.markdown("##### ⭐️ 이 결과가 도움이 되셨나요?")
            rating = st.slider("만족도", 1, 5, 5)
            feedback = st.text_input("더 좋은 결과를 위해 의견을 남겨주세요 (선택)")
            if st.button("피드백 제출"):
                st.toast("소중한 의견 감사합니다! 데이터 개선에 활용됩니다.", icon="✅")
                # (여기서 나중에 구글 시트로 데이터를 쏘면 됩니다)

        with col_r:
            st.subheader("📝 면접관 노트")
            interview_notes = st.text_area("인터뷰 시트", height=500, placeholder="질문을 복사해두고, 답변을 메모하세요.")
            
            # 저장 기능
            file_name = f"Interview_{datetime.datetime.now().strftime('%Y%m%d')}.txt"
            save_content = f"Date: {datetime.datetime.now()}\nLevel: {selected_level}\n\n[Notes]\n{interview_notes}\n\n[AI Questions]\n{st.session_state.ai_result}"
            
            st.download_button("💾 노트 다운로드 (.txt)", save_content, file_name, type="primary", use_container_width=True)
