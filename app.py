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
    st.error("🚨 API 키 오류! 앱을 새로 만들고 [Settings] > [Secrets]에 키를 꼭 다시 넣어주세요.")
    st.stop()

# --- 3. 함수 정의 ---
def fetch_jd(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            return soup.get_text(separator='\n', strip=True)
        return None
    except: return None

def get_ai_response(level, track, jd_text, resume_file):
    # [무적 로직] 사용 가능한 모델을 순서대로 다 시도해봅니다.
    # 1순위: 1.5 Flash (빠르고 무료)
    # 2순위: 1.5 Flash Latest (최신 버전 별칭)
    # 3순위: 1.5 Pro (성능 좋음)
    # 4순위: Pro (구버전, 가장 안전)
    candidate_models = [
        'gemini-1.5-flash',
        'gemini-1.5-flash-latest',
        'gemini-1.5-pro',
        'gemini-pro'
    ]
    
    prompt = f"""
    당신은 '바레이저(Bar Raiser)' 면접관입니다.
    [이력서 파일]과 [JD]를 분석하여 질문 20개를 생성하세요.
    
    - 타겟: {level} ({track})
    - JD: {jd_text[:10000]}
    
    [규칙]
    1. JD 요구사항과 이력서 경험을 연결할 것.
    2. 레벨 {level}에 맞는 난이도로 질문할 것.
    3. Markdown 형식, 3T 분류, 평가 가이드 포함.
    """
    
    resume_data = {"mime_type": "application/pdf", "data": resume_file.getvalue()}
    
    # 모델 돌려막기 시도
    last_error = ""
    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content([prompt, resume_data])
            return f"✅ **[{model_name}] 모델로 생성되었습니다.**\n\n" + response.text
        except Exception as e:
            # 실패하면 다음 모델로 넘어감
            last_error = str(e)
            continue
            
    # 모든 모델이 실패했을 때만 에러 출력
    return f"죄송합니다. 모든 모델 접속에 실패했습니다.\n마지막 에러: {last_error}"

# --- 4. UI 구성 ---
st.title("🧐 바레이저 면접 질문 생성기 (Final)")
st.caption("🚀 되는 모델을 자동으로 찾아 실행합니다.")

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
            with st.spinner("최적의 모델을 찾아 질문을 생성 중입니다..."):
                st.markdown(get_ai_response(level, track, jd_text, resume_file))
