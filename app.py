import streamlit as st
import google.generativeai as genai
import PyPDF2
import requests
from bs4 import BeautifulSoup

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="바레이저 면접 질문 생성기", layout="wide")

# --- 2. API 키 진단 및 설정 ---
api_key = None
try:
    # 1순위: Streamlit Secrets에서 가져오기
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    pass

# [비상용] Secrets가 죽어도 안 되면, 아래 따옴표 안에 키를 직접 넣고 테스트하세요. (성공 후엔 지우세요!)
# api_key = "여기에_AIza로_시작하는_키를_직접_넣으세요" 

if not api_key:
    st.error("🚨 API 키를 찾을 수 없습니다! [Manage app] > [Settings] > [Secrets] 설정을 확인해주세요.")
    st.stop()

genai.configure(api_key=api_key)

# --- 3. 함수 정의 ---
def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"Error: {e}"

def fetch_jd_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text(separator='\n', strip=True)
            return text
        return None
    except:
        return None

def get_ai_response(level, track, jd_text, resume_text):
    # 모델을 Flash로 고정 (가장 안정적)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    당신은 '바레이저(Bar Raiser)' 면접관입니다.
    
    [입력 정보]
    - 레벨: {level} ({track})
    - JD: {jd_text[:5000]}
    - 이력서: {resume_text[:10000]}
    
    [요청]
    위 정보를 바탕으로 3T 가치(Transform, Together, Tomorrow)를 검증할 질문 20개를 생성하세요.
    각 질문 아래에 [평가 가이드]를 포함하세요.
    """
    return model.generate_content(prompt).text

# --- 4. 화면 구성 ---
st.title("🧐 바레이저 면접 질문 생성기 (진단 모드)")

col1, col2 = st.columns([1, 2])

with col1:
    st.header("1. 정보 입력")
    track = st.radio("트랙", ["IC Track (전문가)", "Mg Track (매니저/리더)"], horizontal=True)
    level = st.selectbox("레벨", ["L3", "L4", "L5", "L6", "L7", "M-L5", "M-L6", "M-L7"])
    
    st.subheader("채용 공고 (JD)")
    input_method = st.radio("방식 선택", ["URL 입력", "텍스트 붙여넣기"], horizontal=True)
    
    jd_content = ""
    if input_method == "URL 입력":
        url = st.text_input("URL", placeholder="https://...")
        if url:
            fetched = fetch_jd_content(url)
            if fetched and len(fetched) > 50:
                st.success(f"✅ URL 내용 가져오기 성공! ({len(fetched)}자)")
                jd_content = fetched
            else:
                st.warning("⚠️ URL 보안이 강해 내용을 못 가져왔습니다. '텍스트 붙여넣기'를 이용해주세요.")
    else:
        jd_content = st.text_area("JD 내용 복사/붙여넣기", height=150)

    st.subheader("이력서 (PDF)")
    resume_file = st.file_uploader("PDF 업로드", type="pdf")
    
    btn = st.button("질문 생성하기", type="primary", use_container_width=True)

with col2:
    st.header("2. 결과 화면")
    
    if btn:
        # [진단 1] 재료 확인
        resume_text = ""
        if resume_file:
            resume_text = extract_text_from_pdf(resume_file)
        
        # [진단 2] 내용이 비었는지 확인
        if not jd_content:
            st.error("❌ JD 내용이 비어있습니다! URL을 확인하거나 직접 붙여넣어주세요.")
        elif not resume_text:
            st.error("❌ 이력서 내용을 읽을 수 없습니다! (이미지 파일일 수 있음)")
        elif len(resume_text) < 50:
            st.error("❌ 이력서 텍스트가 너무 짧습니다. 텍스트가 포함된 PDF인지 확인해주세요.")
        else:
            # [진단 3] AI 호출 시도
            try:
                with st.spinner("AI가 분석 중입니다..."):
                    result = get_ai_response(level, track, jd_content, resume_text)
                st.success("생성 성공!")
                st.markdown(result)
            except Exception as e:
                st.error(f"❌ AI 호출 중 에러 발생: {e}")
                st.info("팁: API 키가 올바른지, 혹은 사용량이 초과되지 않았는지 확인하세요.")
