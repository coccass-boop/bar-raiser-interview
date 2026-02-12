import streamlit as st
import requests
import json
import base64
from bs4 import BeautifulSoup
import datetime
import pandas as pd
import PyPDF2

# --- 1. 페이지 설정 ---
st.set_page_config(
    page_title="Bar Raiser Copilot",
    page_icon="✈️",
    layout="wide"
)

# --- 2. API 키 가져오기 ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("🚨 API 키가 설정되지 않았습니다. [Settings > Secrets]를 확인해주세요.")
    st.stop()

# ==============================================================================
# [공식 문서 기준] 3T & 9VALUE 정의 (보내주신 이미지 완벽 반영)
# ==============================================================================
VALUE_SYSTEM = {
    "Transform": [
        "1. Customer-First Innovation: 모든 결정은 고객에게 미치는 영향을 가장 먼저 고려해 이뤄집니다.",
        "2. Enduring Value Creation: 시간이 지날수록 더 큰 가치를 만들어내는 솔루션을 구축합니다.",
        "3. Excellence in Execution: 디지털 전환의 새로운 기준을 세웁니다."
    ],
    "Tomorrow": [
        "4. Active Learning: 고객 접점에서 발생하는 모든 경험을 공동의 지식으로 전환합니다.",
        "5. Forward Thinking: 미래를 고려해 확장성과 지속성을 갖춘 솔루션을 구축합니다.",
        "6. Speed with Impact: 성과는 빠르게 달성하면서도 장기적인 가치를 쌓아갑니다."
    ],
    "Together": [
        "7. Power of Three: 고객, 파트너, 그리고 우리 팀이 하나로 연결됩니다.",
        "8. Trust & Growth: 서로의 발전을 지원하며 함께 성장합니다.",
        "9. Global Perspective: 문화와 시장을 연결하는 가교 역할을 합니다."
    ]
}

# ==============================================================================
# [공식 문서 기준] 직무 레벨별 공통 기대수준 정의 (Role Persona 이미지 반영)
# ==============================================================================
LEVEL_GUIDELINES = {
    # === IC Track (전문가) ===
    "IC-L3": "[기본기를 확립하는 실무자] 명확한 지시와 가이드 하에 업무 수행, 직무 기초 지식과 기술 학습. (Unit의 룰과 문화를 존중하며 긍정적 태도로 협력)",
    "IC-L4": "[자기완결성을 갖춘 독립적 실무자] 실무 지식/경험으로 일상 문제를 해결. 목표 내 업무를 독립적으로 계획/실행. (주어진 목표 안에서는 독립적으로 업무 실행)",
    "IC-L5": "[성장을 지원하는 핵심 직무 전문가] 직무 분야의 깊이 있는 전문성. 데이터 및 경험 기반의 최적 대안 제시. (복잡/다면적 문제를 분석하고 해결책 설계, 지식 전파)",
    "IC-L6": "[조직 변화를 이끄는 선도적 전문가] 특정 전문 영역이나 파트를 리드. 높은 자율성과 책임감으로 전략 실행 주도. (비효율을 제거하고 성과가 재생산되는 선순환 구조를 만듦)",
    "IC-L7": "[전사 혁신을 주도하는 최고 권위자] 가장 복잡하고 전례 없는 문제를 해결. 회사의 핵심 목표 달성과 혁신에 결정적 기여. (업계 표준을 정의하는 최고 수준의 전문성)",

    # === Mg Track (매니저) ===
    "M-L5": "[단일 기능의 유닛 성장을 이끄는 리더] 소속 유닛의 과제 운영 및 프로젝트/제품의 개선과 성공을 만들어 냄. (유닛원들에게 영향력을 끼치며 리더십 개발 시작)",
    "M-L6": "[하나의 독립적인 유닛 혹은 기능이 모인 유닛의 성장을 이끄는 리더] 유닛의 성과와 동시에 유닛원들의 육성을 성공적으로 만듦. (업무 프로세스 표준화, 자원 배분에 큰 영향력)",
    "M-L7": "[회사의 핵심 부서 또는 독립적 유닛이 모인 조직의 성장을 이끄는 리더] 한 직무/분야의 리더로서 유닛간의 시너지를 만듦. (전략 방향, 사업 계획, 예산 배분, 조직 구조 총괄)"
}

# --- 3. 함수 정의 ---

def call_gemini_vision(prompt, pdf_file):
    """
    [핵심] 이미지/PDF를 직접 인식하는 멀티모달 함수
    """
    try:
        # 1. PDF 파일을 Base64로 인코딩 (AI가 볼 수 있게 변환)
        pdf_bytes = pdf_file.getvalue()
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        # 2. 모델 설정 (Vision 기능이 있는 2.0 모델 우선 사용)
        models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash"]
        headers = {'Content-Type': 'application/json'}
        
        # 3. 데이터 패키징 (텍스트 프롬프트 + PDF 파일)
        data = {
            "contents": [{
                "parts": [
                    {"text": prompt},  # 우리의 명령 (3T, 9Value, 레벨 정의 등)
                    {
                        "inline_data": {
                            "mime_type": "application/pdf",
                            "data": pdf_base64
                        }
                    }
                ]
            }]
        }
        
        # 4. 전송 (순차 시도)
        last_error = ""
        for model_name in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
            try:
                response = requests.post(url, headers=headers,
