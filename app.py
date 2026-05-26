import streamlit as st
import PyPDF2
import pandas as pd
import os
import json
from google import genai

# 1. 설정 및 데이터베이스 관리 함수
st.set_page_config(page_title="PSC 연구실 AI", layout="wide")
DATA_FILE = "paper_database.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=["title", "process_type", "coating_method", "max_efficiency", "device_type", "materials", "summary"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')

# 2. 사이드바 메뉴
st.sidebar.title("☀️ NPLA")
st.sidebar.markdown("*Najeha PSCs Lab Assistant*")
# 메뉴 이름 통일
menu = st.sidebar.radio("Menu", ["🏠 Home", "📖 Paper 분석기", "📋 Paper DataBase"])

# --- 홈 화면 ---
if menu == "🏠 Home":
    st.title("PSC 연구실 AI 어시스턴트")
    st.markdown("논문 분석기에서 데이터를 추출하고, 데이터베이스에서 논문별로 관리 및 채팅을 진행하세요.")

# --- 논문 분석기 화면 ---
elif menu == "📖 Paper 분석기":
    st.title("🤖 논문 분석기")
    with st.expander("⚙️ API 키 설정", expanded=False):
        api_key = st.text_input("Gemini API 키", type="password")
    
    uploaded_papers = st.file_uploader("PDF 논문 업로드", type=["pdf"])

    if st.button("분석 시작"):
        if not api_key: st.error("API 키를 먼저 입력해주세요!"); st.stop()
        if not uploaded_papers: st.warning("논문을 업로드해주세요."); st.stop()
        
        with st.spinner("논문 분석 중..."):
            reader = PyPDF2.PdfReader(uploaded_papers)
            text = "".join([page.extract_text() for page in reader.pages])
            client = genai.Client(api_key=api_key)
            
            prompt = f"""
            논문을 분석하여 다음 JSON 형식으로만 응답해줘. 
            - title: 논문 제목
            - process_type: "Vaccum Deposition" 또는 "Solution Process"
            - coating_method: "N/A" 또는 방법명
            - max_efficiency: 효율 수치(예: 25.2%)
            - device_type: "Single-junction" 또는 "Tandem"
            - materials: 핵심 재료 리스트
            - summary: 핵심 요약
            [내용]{text[:30000]}
            """
            response = client.models.generate_content(model='gemini-3.5-flash', contents=prompt)
            try:
                analysis = json.loads(response.text.replace("```json", "").replace("```", "").strip())
                st.session_state.analysis = analysis
                st.session_state.messages = [] 
                st.success("분석 완료!")
            except: st.error("데이터 추출에 실패했습니다.")

    if "analysis" in st.session_state:
        res = st.session_state.analysis
        st.info(f"제목: {res.get('title')}")
        cols = st.columns(4)
        cols[0].metric("공정 방식", res.get('process_type', 'N/A'))
        cols[1].metric("코팅 방법", res.get('coating_method', 'N/A'))
        cols[2].metric("최고 효율", res.get('max_efficiency', 'N/A'))
        cols[3].metric("구조", res.get('device_type', 'N/A'))
        
        if st.button("💾 이 결과 데이터 저장하기"):
            df = load_data()
            df = pd.concat([df, pd.DataFrame([res])], ignore_index=True)
            save_data(df)
            st.success("데이터베이스에 저장되었습니다!")
        
        st.divider()
        for msg in st.session_state.get("messages", []):
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
        if prompt := st.chat_input("이 논문에 대해 질문하세요."):
            if not api_key: st.warning("API 키를 확인해주세요!"); st.stop()
            st.session_state.messages.append({"role": "user", "content": prompt})
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(model='gemini-3.5-flash', contents=f"정보: {res}, 질문: {prompt}")
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            st.rerun()

# --- 데이터베이스 화면 ---
elif menu == "📋 Paper DataBase":
    st.title("📋 연구실 논문 데이터베이스")
    df = load_data()
    
    # 수정 가능한 표
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    
    col_save, col_del = st.columns([1, 5])
    if col_save.button("💾 변경사항 저장"):
        save_data(edited_df)
        st.success("데이터베이스가 업데이트되었습니다!")

    if not df.empty:
        st.divider()
        # 채팅 로드
        chat_idx = st.number_input("채팅할 논문 번호(인덱스)", min_value=0, max_value=len(df)-1, step=1)
        if st.button("이 논문으로 채팅 시작하기"):
            st.session_state.analysis = df.iloc[chat_idx].to_dict()
            st.session_state.messages = []
            st.success(f"'{df.iloc[chat_idx]['title']}' 로드 완료! 'Paper 분석기' 메뉴로 이동하세요.")