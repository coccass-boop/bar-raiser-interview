import streamlit as st
import google.generativeai as genai
import PyPDF2
import requests
from bs4 import BeautifulSoup
import os

# --- 페이지 설정 ---
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
    st.error("🚨 API 키 오류! Streamlit 배포 화면의 Settings > Secrets에 키를 등록해주세요.")
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
        # 사람인 척 하기 위한 헤더 (보안 뚫기용)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # 텍스트만 깔끔하게 가져오기
            text = soup.get_text(separator='\n', strip=True)
            if len(text) < 50: # 내용이 너무 짧으면 실패로 간주
                return None
            return text
        else:
            return None
    except Exception as e:
        return None

def get_ai_response(level, track, jd_text, resume_text):
    # [수정] Pro 모델 대신 Flash 모델 사용 (속도/안정성 UP)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    당신은 우리 회사의 최고 면접관 '바레이저(Bar Raiser)'입니다.
    아래 정보를 바탕으로 [3T 가치]를 검증할 질문 20개를 생성해주세요.
    
    [입력 정보]
    - 레벨: {level} ({track})
    - JD 내용(채용공고): {jd_text[:10000]} 
    *참고: JD 내용 중 '하는 일', '필수 조건', '우대 사항'을 중점적으로 분석하세요.
    - 이력서 요약: {resume_text[:15000]}
    
    [필수 규칙]
    1. 질문은 반드시 'JD의 요구사항(하는 일/필수조건)'과 '이력서의 경험'을 연결해서 만드세요.
    2. 레벨 {level}에 맞는 난이도로 질문하세요. (L5 이상은 전략/시스템/영향력 위주)
    3. 출력은 가독성 좋게 Markdown 형식으로, 3T(Transform, Together, Tomorrow) 카테고리로 나누세요.
    4. 각 질문 밑에 '> 💡 평가 가이드: (Good/Bad 답변 포인트)'를 달아주세요.
    """
    
    # 에러 방지를 위한 예외 처리
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"죄송합니다. AI 응답 생성 중 오류가 발생했습니다.\n원인: {str(e)}"

# --- 화면 구성 (UI) ---
st.title("🧐 바레이저 면접 질문 리스트")
st.markdown("---")

# 왼쪽 사이드바
with st.sidebar:
    st.header("1. 후보자 정보 입력")
    track = st.radio("트랙 선택", ["IC Track (매니저)", "Mg Track (유닛리더)"], horizontal=True)
    level = st.selectbox("레벨 선택", ["L3", "L4", "L5", "L6", "L7", "M-L5", "M-L6", "M-L7"])
    
    st.header("2. 채용 공고 (JD)")
    # URL과 텍스트 입력 선택 가능하게 변경 (URL 실패 대비)
    input_type = st.radio("입력 방식", ["🔗 URL 입력", "📝 직접 붙여넣기"], horizontal=True)
    
    jd_text = ""
    if input_type == "🔗 URL 입력":
        jd_url = st.text_input("JD URL을 입력하세요", placeholder="https://...")
    else:
        jd_paste = st.text_area("JD 내용을 복사해 붙여넣으세요", height=200)

    st.header("3. 이력서 (PDF)")
    resume_file = st.file_uploader("이력서 파일 업로드", type="pdf")
    
    btn = st.button("질문 리스트 생성하기 ✨", type="primary", use_container_width=True)

# 메인 화면 로직
if btn:
    # 1. 이력서 확인
    if not resume_file:
        st.warning("👈 이력서 파일을 업로드해주세요!")
        st.stop()
        
    resume_text = extract_text_from_pdf(resume_file)
    if not resume_text:
        st.error("이력서 파일에서 텍스트를 읽을 수 없습니다. (이미지 파일인가요?)")
        st.stop()

    # 2. JD 내용 가져오기
    with st.status("정보를 분석 중입니다...", expanded=True) as status:
        if input_type == "🔗 URL 입력":
            if not jd_url:
                st.warning("👈 URL을 입력해주세요!")
                st.stop()
            
            status.write("🌐 URL에서 JD 내용을 가져오는 중...")
            fetched_jd = fetch_jd_content(jd_url)
            
            if fetched_jd:
                jd_text = fetched_jd
                status.write("✅ JD 가져오기 성공!")
            else:
                status.update(label="⚠️ URL 보안 문제 발생", state="error")
                st.error("이 사이트는 로봇 접근을 막고 있습니다. '📝 직접 붙여넣기' 방식을 이용해주세요!")
                st.stop()
        else:
            if not jd_paste:
                st.warning("👈 JD 내용을 붙여넣어주세요!")
                st.stop()
            jd_text = jd_paste
            status.write("✅ JD 내용 확인 완료")

        # 3. AI 질문 생성
        status.write("🤖 AI가 질문을 생성하고 있습니다...")
        result = get_ai_response(level, track, jd_text, resume_text)
        status.update(label="완료!", state="complete", expanded=False)

    st.success("생성 완료! 아래 질문 리스트를 확인하세요.")
    st.markdown(result)

else:
    st.info("👈 왼쪽 사이드바에 정보를 입력하고 버튼을 눌러주세요.")
