import streamlit as st
import requests
import json
import PyPDF2
from bs4 import BeautifulSoup

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="바레이저 면접 질문 생성기", layout="wide")

# --- 2. API 키 가져오기 ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("🚨 API 키가 없습니다! [Settings] > [Secrets]를 확인해주세요.")
    st.stop()

# --- 3. 함수 정의 ---

def call_gemini_direct(prompt):
    # [핵심 수정] 선생님 로그에 있었던 '확실한 모델'들만 순서대로 시도합니다.
    # 1. gemini-2.0-flash (최신)
    # 2. gemini-flash-latest (1.5의 별칭)
    # 3. gemini-2.0-flash-lite-preview-02-05 (가벼운 모델)
    
    models_to_try = [
        "gemini-2.0-flash", 
        "gemini-flash-latest",
        "gemini-2.0-flash-lite-preview-02-05" 
    ]
    
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    last_error = ""
    
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)
            
            # 성공(200)하면 바로 결과 반환하고 끝냄
            if response.status_code == 200:
                return f"✅ **[{model_name}] 모델로 성공했습니다!**\n\n" + response.json()['candidates'][0]['content']['parts'][0]['text']
            
            # 실패하면 다음 모델 시도
            else:
                error_msg = response.text
                last_error = f"[{model_name}] 실패: {error_msg}"
                continue
                
        except Exception as e:
            last_error = str(e)
            continue
            
    # 다 해봤는데 안 되면
    return f"❌ 모든 모델 시도 실패.\n마지막 에러: {last_error}\n(잠시 후 다시 시도해주세요)"

def extract_text_from_pdf(file):
    try:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except: return ""

def fetch_jd(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            return soup.get_text(separator='\n', strip=True)
        return None
    except: return None

# --- 4. UI 구성 ---
st.title("🧐 바레이저 면접 질문 생성기 (2.0)")
st.caption("✅ 선생님 계정에서 사용 가능한 Gemini 2.0 모델을 강제로 연결합니다.")

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
        resume_text = extract_text_from_pdf(resume_file)
        if not resume_text:
            st.error("PDF 내용을 읽을 수 없습니다.")
            st.stop()
            
        jd_text = ""
        if jd_url:
            jd_text = fetch_jd(jd_url)
        elif jd_paste:
            jd_text = jd_paste
            
        if not jd_text:
            st.warning("JD 내용을 입력해주세요!")
        else:
            # 질문 생성 프롬프트
            full_prompt = f"""
            당신은 '바레이저(Bar Raiser)' 면접관입니다.
            아래 정보를 바탕으로 질문 20개를 생성하세요.
            
            [타겟] {level} ({track})
            [JD] {jd_text[:5000]}
            [이력서] {resume_text[:10000]}
            
            [규칙]
            1. JD 요구사항과 이력서 경험 연결 필수.
            2. 레벨 {level}에 맞는 질문 난이도.
            3. 3T(Transform, Together, Tomorrow) 분류.
            4. 각 질문에 '> 💡 평가 가이드' 포함.
            """

            with st.spinner("Gemini 2.0 모델 접속 중..."):
                result = call_gemini_direct(full_prompt)
                st.markdown(result)
