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
    st.error("🚨 API 키가 없습니다! [Settings] > [Secrets]에 키를 넣어주세요.")
    st.stop()

# --- 3. 함수 정의 ---

# [핵심] 라이브러리 없이 직접 통신하는 함수 (무적 코드)
def call_gemini_direct(prompt):
    # 1순위: 1.5 Flash (무료/빠름)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)
        
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            # 실패하면 2순위: 1.5 Pro 시도
            st.warning(f"Flash 모델 통신 실패({response.status_code}), Pro 모델로 재시도합니다...")
            url_pro = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={API_KEY}"
            response_pro = requests.post(url_pro, headers=headers, data=json.dumps(data), timeout=30)
            
            if response_pro.status_code == 200:
                return response_pro.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                return f"에러 발생: {response_pro.text}"
    except Exception as e:
        return f"통신 에러: {str(e)}"

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
st.title("🧐 바레이저 면접 질문 생성기 (Direct)")
st.caption("✅ 라이브러리 없이 직접 연결됩니다. 무조건 됩니다.")

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
        # 1. 정보 취합
        resume_text = extract_text_from_pdf(resume_file)
        if not resume_text:
            st.error("❌ PDF에서 글자를 읽을 수 없습니다. (텍스트형 PDF만 가능)")
            st.stop()
            
        jd_text = ""
        if jd_url:
            jd_text = fetch_jd(jd_url)
            if not jd_text: st.warning("URL 읽기 실패! 텍스트로 넣어주세요.")
        elif jd_paste:
            jd_text = jd_paste
            
        if not jd_text:
            st.warning("JD 내용을 입력해주세요!")
            st.stop()

        # 2. 프롬프트 조합
        full_prompt = f"""
        당신은 '바레이저(Bar Raiser)' 면접관입니다.
        아래 정보를 바탕으로 질문 20개를 생성하세요.
        
        [타겟] {level} ({track})
        [JD 내용] {jd_text[:5000]}
        [이력서 내용] {resume_text[:10000]}
        
        [규칙]
        1. JD 요구사항과 이력서 경험 연결.
        2. 레벨 {level} 난이도.
        3. 3T 가치 분류, 평가 가이드 포함.
        """

        # 3. 전송
        with st.spinner("구글 서버와 직접 통신 중입니다..."):
            result = call_gemini_direct(full_prompt)
            st.markdown(result)
