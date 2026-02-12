import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

# --- 1. 페이지 설정 ---
st.set_page_config(
    page_title="바레이저 면접 질문 생성기",
    page_icon="🧐",
    layout="wide"
)

# --- 2. API 키 설정 ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("🚨 API 키 오류! Streamlit Secrets 설정을 확인해주세요.")
    st.stop()

# --- 3. 함수 정의 ---

# JD URL 크롤링 함수
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

# AI 분석 함수 (핵심 변경: 파일을 통째로 넘김)
def get_ai_response(level, track, jd_text, resume_file):
    # 이미지/문서를 잘 읽는 'Gemini 1.5 Flash' 모델 사용
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # 프롬프트 (명령어)
    prompt_text = f"""
    당신은 '바레이저(Bar Raiser)' 면접관입니다.
    함께 제공된 [이력서 파일]과 아래 [JD 내용]을 분석하여 면접 질문 20개를 생성하세요.
    
    [분석 정보]
    - 타겟 레벨: {level} ({track})
    - JD 내용: {jd_text[:10000]}
    
    [요청 사항]
    1. 이력서가 이미지로 되어 있어도 내용을 꼼꼼히 읽어서 분석하세요.
    2. 질문은 반드시 'JD의 요구사항'과 '이력서의 경험'을 연결해야 합니다.
    3. 레벨 {level}에 맞는 난이도(실무 vs 전략)로 질문하세요.
    4. 출력은 Markdown 형식으로, 3T(Transform, Together, Tomorrow) 카테고리로 나누세요.
    5. 각 질문 밑에 '> 💡 평가 가이드'를 꼭 달아주세요.
    """
    
    # 이력서 파일을 제미나이가 읽을 수 있는 형태로 변환
    resume_data = {
        "mime_type": "application/pdf",
        "data": resume_file.getvalue()
    }
    
    # 프롬프트와 파일을 리스트로 묶어서 전송 (이게 핵심!)
    response = model.generate_content([prompt_text, resume_data])
    return response.text

# --- 4. 화면 구성 (UI) ---
st.title("🧐 바레이저 면접 질문 생성기 (이미지 인식 버전)")
st.markdown("이제 **스캔한 이미지 이력서**도 읽을 수 있습니다! 📸")

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
                st.warning("⚠️ 보안이 강한 사이트입니다. '텍스트 붙여넣기'를 써주세요.")
    else:
        jd_content = st.text_area("JD 내용 복사/붙여넣기", height=150)

    st.header("3. 이력서 (PDF)")
    resume_file = st.file_uploader("PDF 업로드 (이미지도 OK)", type="pdf")
    
    btn = st.button("질문 생성하기 ✨", type="primary", use_container_width=True)

# 메인 실행 로직
if btn:
    if not jd_content:
        st.warning("👈 JD 내용을 입력해주세요.")
    elif not resume_file:
        st.warning("👈 이력서 파일을 업로드해주세요.")
    else:
        with st.spinner("AI가 이력서(이미지 포함)를 읽고 분석 중입니다..."):
            try:
                result = get_ai_response(level, track, jd_content, resume_file)
                st.success("분석 완료!")
                st.markdown(result)
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
                st.info("혹시 파일이 너무 크거나(20MB 이상), 암호가 걸려있지 않나요?")
