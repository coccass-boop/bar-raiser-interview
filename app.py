import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="바레이저 면접 질문 생성기", layout="wide")

# --- 2. API 키 설정 ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("🚨 API 키 오류! [Manage app] > [Settings] > [Secrets]를 확인해주세요.")
    st.stop()

# --- 3. 함수 정의 ---
def fetch_jd(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup.get_text(separator='\n', strip=True)
        return None
    except:
        return None

def get_ai_response(level, track, jd_text, resume_file):
    # [핵심 수정] 에러 로그에 있던 '사용 가능한 모델' 중 하나인 2.0 Flash 사용
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    prompt = f"""
    당신은 '바레이저(Bar Raiser)' 면접관입니다.
    제공된 [이력서]와 [JD]를 분석하여 심층 면접 질문 20개를 생성하세요.
    
    [정보]
    - 레벨: {level} ({track})
    - JD 내용: {jd_text[:10000]}
    
    [규칙]
    1. JD의 핵심 요구사항과 이력서의 경험을 반드시 연결할 것.
    2. 레벨 {level}에 맞는 난이도로 질문할 것.
    3. 3T(Transform, Together, Tomorrow) 가치로 분류할 것.
    4. 각 질문에 '> 💡 평가 가이드'를 포함할 것.
    """
    
    # PDF 파일 처리
    resume_data = {
        "mime_type": "application/pdf",
        "data": resume_file.getvalue()
    }
    
    try:
        response = model.generate_content([prompt, resume_data])
        return response.text
    except Exception as e:
        return f"⚠️ 에러 발생: {str(e)}"

# --- 4. 화면 구성 ---
st.title("🧐 바레이저 면접 질문 생성기 (v2.0)")
st.caption("🚀 최신 Gemini 2.0 Flash 모델이 적용되었습니다.")

with st.sidebar:
    st.header("1. 입력 정보")
    track = st.radio("트랙", ["IC Track (전문가)", "Mg Track (매니저)"], horizontal=True)
    level = st.selectbox("레벨", ["L3", "L4", "L5", "L6", "L7", "M-L5", "M-L6", "M-L7"])
    
    st.header("2. 채용 공고 (JD)")
    tab1, tab2 = st.tabs(["🔗 URL 입력", "📝 직접 붙여넣기"])
    
    jd_content = ""
    with tab1:
        url = st.text_input("JD URL", placeholder="https://...")
        if url:
            fetched = fetch_jd(url)
            if fetched:
                st.success("URL 읽기 성공!")
                jd_content = fetched
            else:
                st.warning("URL 읽기 실패. 옆 탭에 직접 붙여넣어주세요.")
    with tab2:
        paste = st.text_area("JD 내용 붙여넣기", height=200)
        if paste: jd_content = paste

    st.header("3. 이력서 (PDF)")
    resume_file = st.file_uploader("PDF 업로드", type="pdf")
    
    btn = st.button("질문 생성하기 ✨", type="primary", use_container_width=True)

if btn:
    if not jd_content:
        st.warning("👈 JD 내용을 입력해주세요!")
    elif not resume_file:
        st.warning("👈 이력서를 업로드해주세요!")
    else:
        with st.spinner("Gemini 2.0이 분석 중입니다..."):
            result = get_ai_response(level, track, jd_content, resume_file)
            st.markdown(result)
