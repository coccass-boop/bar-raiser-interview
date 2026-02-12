import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

# --- 페이지 설정 ---
st.set_page_config(page_title="바레이저 면접 질문 생성기", layout="wide")

# --- API 키 설정 ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("🚨 API 키를 찾을 수 없습니다! 앱 설정(Secrets)에 키를 넣어주세요.")
    st.stop()

# --- 함수 정의 ---
def fetch_jd(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            return soup.get_text(separator='\n', strip=True)
        return None
    except: return None

def get_ai_response(level, track, jd, resume_file):
    # 최신 모델 사용
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    당신은 '바레이저(Bar Raiser)' 면접관입니다.
    [이력서 파일]과 [JD]를 분석하여 질문 20개를 생성하세요.
    
    - 타겟: {level} ({track})
    - JD: {jd[:10000]}
    
    [규칙]
    1. JD 요구사항과 이력서 경험을 연결할 것.
    2. 레벨 {level}에 맞는 난이도로 질문할 것.
    3. Markdown 형식, 3T 분류, 평가 가이드 포함.
    """
    
    # PDF 처리
    resume_data = {"mime_type": "application/pdf", "data": resume_file.getvalue()}
    
    try:
        return model.generate_content([prompt, resume_data]).text
    except Exception as e:
        # 에러 발생 시, 사용 가능한 모델 목록을 보여줌 (디버깅용)
        st.error(f"⚠️ 에러 발생: {e}")
        try:
            available = [m.name for m in genai.list_models()]
            st.warning(f"현재 사용 가능한 모델 목록: {available}")
        except:
            pass
        return "죄송합니다. 오류가 발생했습니다."

# --- UI 구성 ---
st.title("🧐 바레이저 면접 질문 생성기 (Final)")

with st.sidebar:
    st.header("입력 정보")
    track = st.radio("트랙", ["IC Track", "Mg Track"], horizontal=True)
    level = st.selectbox("레벨", ["L3", "L4", "L5", "L6", "L7", "M-L5", "M-L6", "M-L7"])
    
    tab1, tab2 = st.tabs(["🔗 URL", "📝 텍스트"])
    with tab1: jd_url = st.text_input("JD URL")
    with tab2: jd_paste = st.text_area("JD 내용")
    
    resume_file = st.file_uploader("이력서 PDF", type="pdf")
    btn = st.button("질문 생성", type="primary")

if btn:
    if not resume_file:
        st.warning("이력서를 넣어주세요!")
    else:
        jd_text = ""
        if jd_url:
            jd_text = fetch_jd(jd_url)
            if not jd_text: st.warning("URL 읽기 실패! 텍스트로 넣어주세요.")
        elif jd_paste:
            jd_text = jd_paste
            
        if jd_text:
            with st.spinner("AI 분석 중..."):
                st.markdown(get_ai_response(level, track, jd_text, resume_file))
