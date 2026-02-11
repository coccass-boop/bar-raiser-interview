import streamlit as st
import google.generativeai as genai
import PyPDF2
import os

# --- 페이지 기본 설정 (가장 먼저 와야 함) ---
st.set_page_config(
    page_title="Bar Raiser Interview",
    page_icon="🧐",
    layout="wide"
)

# --- API 키 설정 (Streamlit Secrets에서 가져옴) ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("🚨 API 키가 설정되지 않았습니다. Streamlit 설정에서 Secrets를 등록해주세요.")
    st.stop()

# --- 함수 정의 ---
def extract_text(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    except:
        return ""

def get_ai_response(level, track, jd, resume):
    model = genai.GenerativeModel('gemini-1.5-pro')
    prompt = f"""
    당신은 우리 회사의 최고 면접관 '바레이저(Bar Raiser)'입니다.
    아래 정보를 바탕으로 [3T 가치]를 검증할 질문 20개를 생성해주세요.
    
    [입력 정보]
    - 레벨: {level} ({track})
    - JD 요약: {jd[:3000]}
    - 이력서 요약: {resume[:10000]}
    
    [필수 규칙]
    1. 질문은 반드시 'JD의 요구사항'과 '이력서의 경험'을 연결해서 만드세요.
    2. 레벨 {level}에 맞는 난이도(실무 vs 전략)로 질문하세요.
    3. 출력은 가독성 좋게 Markdown 형식으로, 3T(Transform, Together, Tomorrow) 카테고리로 나누세요.
    4. 각 질문 밑에 '> 💡 평가 가이드: (Good/Bad 답변 포인트)'를 달아주세요.
    """
    response = model.generate_content(prompt)
    return response.text

# --- 화면 구성 (UI) ---
st.title("🧐 바레이저(Bar Raiser) 면접 가이드")
st.markdown("---")

# 왼쪽 사이드바 (입력창)
with st.sidebar:
    st.header("1. 후보자 정보 입력")
    track = st.radio("트랙 선택", ["IC Track (전문가)", "Mg Track (매니저)"], horizontal=True)
    level = st.selectbox("레벨 선택", ["L3", "L4", "L5", "L6", "L7", "M-L5", "M-L6"])
    
    st.header("2. 채용 공고 (JD)")
    jd_text = st.text_area("JD 주요 내용을 붙여넣으세요", height=150)
    
    st.header("3. 이력서 (PDF)")
    resume_file = st.file_uploader("파일 업로드", type="pdf")
    
    btn = st.button("질문 리스트 생성하기 ✨", type="primary", use_container_width=True)

# 메인 화면 (결과창)
if btn:
    if not jd_text or not resume_file:
        st.warning("👈 왼쪽에서 JD 내용과 이력서 파일을 모두 등록해주세요!")
    else:
        with st.spinner("AI가 이력서를 분석하여 바레이징 질문을 추출 중입니다..."):
            resume_text = extract_text(resume_file)
            result = get_ai_response(level, track, jd_text, resume_text)
            
        st.success("분석 완료! 아래 질문을 활용하여 면접을 진행하세요.")
        st.markdown(result)
else:
    st.info("👈 왼쪽 사이드바에 정보를 입력하면 질문이 여기에 표시됩니다.")
