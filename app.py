import streamlit as st
import requests
import json
import base64
import datetime
from bs4 import BeautifulSoup

# --- 1. 페이지 설정 및 섬세한 UI 보정 CSS ---
st.set_page_config(page_title="Bar Raiser Copilot", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    /* 버튼 주위의 여백과 높이를 강제 조절하여 텍스트와 수직 균형을 맞춤 */
    div.stButton > button {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 0px !important;
        height: 28px !important;
        width: 28px !important;
        margin-top: 4px !important;
        font-size: 14px !important;
    }
    /* 텍스트 줄바꿈 및 간격 최적화 */
    .stTextArea textarea {
        font-size: 15px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API 키 설정 ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("🚨 API 키를 설정해주세요.")
    st.stop()

# --- 3. 세션 상태 관리 ---
if "ai_questions" not in st.session_state:
    st.session_state.ai_questions = {"Transform": [], "Tomorrow": [], "Together": []}
if "selected_questions" not in st.session_state:
    st.session_state.selected_questions = []
if "wide_mode" not in st.session_state:
    st.session_state.wide_mode = False

BAR_RAISER_CRITERIA = {
    "Transform": "Create Enduring Value (시간이 지날수록 더 큰 가치를 만들어내는 솔루션 구축)",
    "Tomorrow": "Forward Thinking (미래를 고려해 확장성과 지속성을 갖춘 솔루션을 구축합니다)",
    "Together": "Trust & Growth (서로의 발전을 지원하며 함께 성장합니다)"
}

# --- 4. 핵심 함수 (유지) ---
def fetch_jd(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            return soup.get_text(separator='\n', strip=True)
    except: return None

def generate_questions_by_category(category, level, resume_file, jd_text):
    prompt = f"[Role] Bar Raiser. [Category] {category}. [Focus] {BAR_RAISER_CRITERIA[category]}. [Task] 10 Questions JSON."
    try:
        pdf_base64 = base64.b64encode(resume_file.getvalue()).decode('utf-8')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={API_KEY}"
        data = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "application/pdf", "data": pdf_base64}}]}]}
        res = requests.post(url, json=data, timeout=60)
        cleaned = res.json()['candidates'][0]['content']['parts'][0]['text'].replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except: return []

# --- 5. 사이드바 (유지) ---
with st.sidebar:
    st.title("✈️ Copilot Menu")
    selected_level = st.selectbox("레벨 선택", ["IC-L3", "IC-L4", "IC-L5", "IC-L6", "IC-L7", "M-L5", "M-L6", "M-L7"])
    tab1, tab2 = st.tabs(["🔗 URL", "📝 텍스트"])
    with tab1:
        url_input = st.text_input("URL 입력")
        jd_final = fetch_jd(url_input) if url_input else ""
    with tab2:
        jd_final = st.text_area("내용 붙여넣기", height=150) if not url_input else fetch_jd(url_input)

    resume_file = st.file_uploader("PDF 업로드", type="pdf")
    if st.button("질문 생성 시작 🚀", type="primary", use_container_width=True):
        if resume_file and jd_final:
            with st.spinner("분석 중..."):
                for cat in ["Transform", "Tomorrow", "Together"]:
                    st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final)

# --- 6. 메인 화면 ---
st.title("✈️ Bar Raiser Copilot")

if st.session_state.wide_mode:
    col_q_ratio, col_n_ratio = 10, 0.01
    toggle_label = "🔙 면접관 노트 다시 열기"
else:
    col_q_ratio, col_n_ratio = 1.1, 1
    toggle_label = "↔️ 질문 리스트 넓게 보기 (노트 접기)"

col_q, col_n = st.columns([col_q_ratio, col_n_ratio])

# [왼쪽] 제안 질문 리스트
with col_q:
    st.subheader("🎯 제안 질문 리스트")
    if st.button(toggle_label):
        st.session_state.wide_mode = not st.session_state.wide_mode
        st.rerun()

    for cat in ["Transform", "Tomorrow", "Together"]:
        with st.expander(f"📌 {cat} 리스트 ({BAR_RAISER_CRITERIA[cat].split('(')[0]})", expanded=True):
            # [이동] 새로고침 버튼을 파란색 박스 위치(우측 상단)로 고정
            h_col, ref_col = st.columns([0.96, 0.04])
            h_col.markdown(f"<small style='color:gray;'>{BAR_RAISER_CRITERIA[cat]}</small>", unsafe_allow_html=True)
            if ref_col.button("🔄", key=f"ref_{cat}"):
                if resume_file and jd_final:
                    st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final)
                    st.rerun()
            
            st.divider()
            for i, q in enumerate(st.session_state.ai_questions[cat]):
                # [보정] 질문 텍스트와 + 버튼의 수평 균형
                qc, ac = st.columns([0.96, 0.04])
                qc.write(f"**Q. {q['q']}**")
                if ac.button("➕", key=f"add_{cat}_{i}"):
                    if q['q'] not in [sq['q'] for sq in st.session_state.selected_questions]:
                        st.session_state.selected_questions.append({"q": q['q'], "cat": cat, "memo": ""})
                st.caption(f"🎯 의도: {q['i']}")
                st.divider()

# [오른쪽] 면접관 노트
if not st.session_state.wide_mode:
    with col_n:
        st.subheader("📝 면접관 노트")
        if st.button("➕ 질문을 직접 입력하세요.", use_container_width=True):
            st.session_state.selected_questions.append({"q": "", "cat": "Custom", "memo": ""})
        
        st.divider()
        for idx, item in enumerate(st.session_state.selected_questions):
            # [보정] 질문 헤더와 ✕ 버튼의 정렬
            tag_col, del_col = st.columns([0.96, 0.04])
            tag_col.markdown(f"<span style='font-size:0.8rem; color:gray;'>Q{idx+1}</span> <span style='background-color:#f0f2f6; padding:2px 6px; border-radius:4px; font-size:0.7rem; font-weight:bold;'>{item.get('cat','Custom')}</span>", unsafe_allow_html=True)
            if del_col.button("✕", key=f"del_{idx}"):
                st.session_state.selected_questions.pop(idx)
                st.rerun()
            
            # 질문 및 답변 영역 가독성 확보
            q_text = item['q']
            q_h = max(70, (len(q_text) // 35) * 25 + 30)
            st.session_state.selected_questions[idx]['q'] = st.text_area(f"q_{idx}", value=q_text, label_visibility="collapsed", height=q_h, key=f"area_q_{idx}")
            st.session_state.selected_questions[idx]['memo'] = st.text_area(f"m_{idx}", value=item.get('memo',''), placeholder="답변 메모...", label_visibility="collapsed", height=150, key=f"area_m_{idx}")
            st.markdown("<div style='margin-bottom:15px; border-bottom:1px solid #eee;'></div>", unsafe_allow_html=True)

        if st.session_state.selected_questions:
            output = f"Target: {selected_level}\n" + "\n".join([f"[{s.get('cat','Custom')}] Q: {s['q']}\nA: {s.get('memo','')}" for s in st.session_state.selected_questions])
            st.download_button("💾 결과 저장 (.txt)", output, f"Interview.txt", type="primary", use_container_width=True)
