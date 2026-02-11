import streamlit as st
import google.generativeai as genai
import PyPDF2
import requests
from bs4 import BeautifulSoup
import os

# --- 페이지 기본 설정 ---
st.set_page_config(
    page_title="바레이저 면접 질문 리스트",
    page_icon="🧐",
    layout="wide"
)

# --- API 키 설정 ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("🚨 API 키가 설정되지 않았습니다. Streamlit 설정에서 Secrets를 등록해주세요.")
    st.stop()

# --- 함수 정의 ---
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
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # 웹페이지의 모든 텍스트를 가져오되, 불필요한 공백 제거
            text = soup.get_text(separator='\n', strip=True)
            return text
        else:
            return None
    except Exception as e:
        return None

def get_ai_response(level, track, jd_text, resume_text):
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    prompt = f"""
    당신은 우리 회사의 최고 면접관 '바레이저(Bar Raiser)'입니다.
    아래 정보를 바탕으로 [3T 가치]를 검증할 질문 20개를 생성해주세요.
    
    [입력 정보]
    - 레벨: {level} ({track})
    - JD 내용(URL 추출): {jd_text[:5000]} 
    *참고: JD 내용 중 '하는 일', '필수 조건', '우대 사항'을 중점적으로 분석하세요.
    - 이력서 요약: {resume_text[:10000]}
    
    [필수 규칙]
    1. 질문은 반드시 'JD의 요구사항(하는 일/필수조건)'과 '이력서의 경험'을 연결해서 만드세요.
    2. 레벨 {level}에 맞는 난이도로 질문하세요. (L5 이상은 전략/시스템/영향력 위주)
    3. 출력은 가독성 좋게 Markdown 형식으로, 3T(Transform, Together, Tomorrow) 카테고리로 나누세요.
    4. 각 질문 밑에 '> 💡 평가 가이드: (Good/Bad 답변 포인트)'를 달아주세요.
    """
    
    with st.spinner("AI가 JD URL과 이력서를 분석하여 바레이징 질문을 추출 중입니다..."):
        response = model.generate_content(prompt)
    return response.text

# --- 화면 구성 (UI) ---
st.title("🧐 바레이저 면접 질문 리스트")
st.markdown("---")

# 왼쪽 사이드바
with st.sidebar:
    st.header("1. 후보자 정보 입력")
    # 요청하신 대로 트랙 명칭 변경
    track = st.radio("트랙 선택", ["IC Track (매니저)", "Mg Track (유닛리더)"], horizontal=True)
    
    # 요청하신 대로 M-L7 추가
    level = st.selectbox("레벨 선택", ["L3", "L4", "L5", "L6", "L7", "M-L5", "M-L6", "M-L7"])
    
    st.header("2. 채용 공고 (JD)")
    # URL 입력 방식으로 변경
    jd_url = st.text_input("JD URL을 입력하세요", placeholder="https://...")
    
    st.header("3. 이력서 (PDF)")
    resume_file = st.file_uploader("이력서 파일 업로드", type="pdf")
    
    btn = st.button("질문 리스트 생성하기 ✨", type="primary", use_container_width=True)

# 메인 화면
if btn:
    if not jd_url:
        st.warning("👈 채용공고 URL을 입력해주세요!")
    elif not resume_file:
        st.warning("👈 이력서 파일을 업로드해주세요!")
    else:
        # 1. JD URL 크롤링
        with st.status("채용공고(JD) 내용을 가져오는 중...", expanded=True) as status:
            jd_text = fetch_jd_content(jd_url)
            if jd_text:
                status.update(label="✅ JD 가져오기 성공!", state="complete", expanded=False)
            else:
                status.update(label="⚠️ URL 내용을 가져오지 못했습니다. (보안이 강한 사이트일 수 있음)", state="error")
                st.error("URL에서 내용을 읽을 수 없습니다. JD 내용을 직접 복사해서 AI에게 주는 방식을 고려해보세요.")
                st.stop()
        
        # 2. 이력서 분석 및 질문 생성
        resume_text = extract_text_from_pdf(resume_file)
        result = get_ai_response(level, track, jd_text, resume_text)
            
        st.success("생성 완료! 아래 질문 리스트를 확인하세요.")
        st.markdown(result)

else:
    st.info("👈 왼쪽 사이드바에 URL과 이력서를 넣고 버튼을 눌러주세요.")
