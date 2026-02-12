import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import time

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

def get_ai_response(level, track, jd_text, resume_file):
    # [핵심] 최신 라이브러리에서 작동하는 모델명 지정
    # 만약 Flash가 안되면 'gemini-1.5-pro'로 자동 변경하도록 유도할 수도 있음
    model_name = 'gemini-1.5-flash' 
    
    try:
        model = genai.GenerativeModel(model_name)
    except:
        # Flash 모델을 못 찾으면 Pro 모델로 재시도 (안전장치)
        st.warning("⚠️ Flash 모델 로딩 실패, Pro 모델로 전환합니다.")
        model = genai.GenerativeModel('gemini-1.5-pro')

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
    
    # 파일 데이터 처리
    resume_data = {
        "mime_type": "application/pdf",
        "data": resume_file.getvalue()
    }
    
    response = model.generate_content([prompt_text, resume_data])
    return response.text

# --- 4. 화면 구성 ---
st.title("🧐 바레이저 면접 질문 생성기 (Final)")

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
    resume_file = st.file_uploader("PDF 업로드 (이미지/스캔본 가능)", type="pdf")
    
    btn = st.button("질문 생성하기 ✨", type="primary", use_container_width=True)

if btn:
    if not jd_content:
        st.warning("👈 JD 내용을 입력해주세요.")
    elif not resume_file:
        st.warning("👈 이력서 파일을 업로드해주세요.")
    else:
        with st.spinner("AI가 이력서를 분석 중입니다... (최대 30초 소요)"):
            try:
                result = get_ai_response(level, track, jd_content, resume_file)
                st.success("분석 완료!")
                st.markdown(result)
            except Exception as e:
                st.error(f"오류 발생: {e}")
                st.info("팁: 잠시 후 다시 시도해보세요.")
