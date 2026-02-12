import streamlit as st
import google.generativeai as genai
import PyPDF2
import requests
from bs4 import BeautifulSoup

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="바레이저 면접 질문 생성기", layout="wide")

# --- 2. API 키 설정 ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("🚨 API 키 오류! Streamlit Secrets 설정을 확인해주세요.")
    st.stop()

# --- 3. 함수 정의 ---

# (구관이 명관) 가장 확실한 텍스트 추출 방식 사용
def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    except:
        return ""

def fetch_jd_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text(separator='\n', strip=True)
            return text
        return None
    except:
        return None

def get_ai_response(level, track, jd_text, resume_text):
    # [핵심 변경] 1.5 버전 대신, 에러가 절대 없는 'gemini-pro' (1.0 버전) 사용
    model = genai.GenerativeModel('gemini-pro')
    
    prompt = f"""
    당신은 '바레이저(Bar Raiser)' 면접관입니다.
    아래 정보를 바탕으로 3T 가치 기반 면접 질문 20개를 생성하세요.
    
    [정보]
    - 레벨: {level} ({track})
    - JD: {jd_text[:5000]}
    - 이력서: {resume_text[:10000]}
    
    [규칙]
    1. 질문은 'JD 요구사항'과 '이력서 경험'을 반드시 연결할 것.
    2. 레벨 {level}에 맞는 난이도로 질문할 것.
    3. Markdown 형식으로, 3T(Transform, Together, Tomorrow)로 분류할 것.
    4. 각 질문에 '> 💡 평가 가이드'를 포함할 것.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"죄송합니다. 오류가 발생했습니다: {str(e)}"

# --- 4. 화면 구성 ---
st.title("🧐 바레이저 면접 질문 생성기 (안전 모드)")
st.caption("✅ 가장 안정적인 버전으로 구동됩니다.")

with st.sidebar:
    st.header("1. 기본 정보")
    track = st.radio("트랙", ["IC Track (전문가)", "Mg Track (매니저/리더)"], horizontal=True)
    level = st.selectbox("레벨", ["L3", "L4", "L5", "L6", "L7", "M-L5", "M-L6", "M-L7"])
    
    st.header("2. 채용 공고 (JD)")
    input_method = st.radio("방식 선택", ["🔗 URL 입력", "📝 텍스트 붙여넣기"], horizontal=True)
    
    jd_content = ""
    if input_method == "🔗 URL 입력":
        url = st.text_input("URL", placeholder="https://...")
        if url:
            fetched = fetch_jd_content(url)
            if fetched and len(fetched) > 50:
                st.success(f"✅ 가져오기 성공!")
                jd_content = fetched
            else:
                st.warning("⚠️ 내용을 가져오지 못했습니다. 직접 붙여넣기를 이용해주세요.")
    else:
        jd_content = st.text_area("JD 내용 복사/붙여넣기", height=150)

    st.header("3. 이력서 (PDF)")
    resume_file = st.file_uploader("PDF 업로드", type="pdf")
    
    btn = st.button("질문 생성하기 ✨", type="primary", use_container_width=True)

if btn:
    if not jd_content:
        st.warning("👈 JD 내용을 입력해주세요.")
    elif not resume_file:
        st.warning("👈 이력서 파일을 업로드해주세요.")
    else:
        # 안전 모드: 텍스트 추출 후 AI 전송
        resume_text = extract_text_from_pdf(resume_file)
        
        if not resume_text:
            st.error("❌ 이력서에서 글자를 읽을 수 없습니다. (이미지 파일인가요?)")
            st.info("이 안전 모드 버전은 '텍스트로 된 PDF'만 읽을 수 있습니다.")
        else:
            with st.spinner("AI가 분석 중입니다..."):
                result = get_ai_response(level, track, jd_content, resume_text)
                st.success("완료!")
                st.markdown(result)
