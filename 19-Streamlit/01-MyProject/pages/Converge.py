import pytesseract
from PIL import Image
import pdfplumber
import streamlit as st
from typing import List, Union
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from dotenv import load_dotenv

# API 키 및 프로젝트 설정
load_dotenv()

# Streamlit 앱 설정
st.title("PDF 및 이미지 데이터 분석 챗봇 💬")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# 상수 정의
class MessageRole:
    USER = "user"
    ASSISTANT = "assistant"

class MessageType:
    TEXT = "text"

# PDF 텍스트 처리 함수
def extract_pdf_data(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        text_data = []
        for page in pdf.pages:
            text_data.append(page.extract_text())
    combined_text = "\n".join(text_data)
    return combined_text

# 이미지 텍스트 처리 함수
def extract_image_data(image_file):
    try:
        image = Image.open(image_file)
        # 이미지 모드가 RGB가 아닌 경우 변환
        if image.mode != "RGB":
            image = image.convert("RGB")
        text = pytesseract.image_to_string(image, lang='eng')
        return text
    except Exception as e:
        st.error(f"이미지 처리 중 오류가 발생했습니다: {e}")
        return ""

# 메시지 출력
def print_messages():
    for role, content_list in st.session_state["messages"]:
        with st.chat_message(role):
            for content in content_list:
                if isinstance(content, list):
                    message_type, message_content = content
                    if message_type == MessageType.TEXT:
                        st.markdown(message_content)
                else:
                    raise ValueError(f"Unknown content type: {content}")

def add_message(role: MessageRole, content: List[Union[MessageType, str]]):
    messages = st.session_state["messages"]
    if messages and messages[-1][0] == role:
        messages[-1][1].extend([content])
    else:
        messages.append([role, [content]])

# 에이전트 생성 함수
def create_agent(text_data, selected_model="o1-preview"):
    # OpenAI API 초기화
    chat = ChatOpenAI(model=selected_model, temperature=0)

    # 시스템 메시지 초기화: 텍스트 데이터를 포함
    system_message = SystemMessage(
        content=(
            f"You are a professional data analyst and expert in understanding document content. "
            f"Here is the content that you should use to answer questions: {text_data} "
        )
    )

    # 에이전트 초기화
    return chat, [system_message]

# 질문 처리 함수
def ask(query):
    if "agent" in st.session_state:
        st.chat_message("user").write(query)
        add_message(MessageRole.USER, [MessageType.TEXT, query])

        chat, conversation_history = st.session_state["agent"]
        ai_answer = ""

        # 사용자 메시지 추가
        conversation_history.append(HumanMessage(content=query))

        with st.chat_message("assistant"):
            try:
                # 모델로부터 응답 생성
                response = chat(conversation_history)

                # 모델 응답 추가
                ai_answer = response.content
                st.write(ai_answer)
                add_message(MessageRole.ASSISTANT, [MessageType.TEXT, ai_answer])

                # 대화 내역 업데이트
                conversation_history.append(response)
            except Exception as e:
                error_message = f"An error occurred: {e}"
                st.error(error_message)
                add_message(MessageRole.ASSISTANT, [MessageType.TEXT, error_message])

# 메인 로직
with st.sidebar:
    clear_btn = st.button("대화 초기화")
    uploaded_file = st.file_uploader("PDF 또는 이미지 파일을 업로드 해주세요.", type=["pdf", "jpg", "jpeg", "png"])
    selected_model = st.selectbox("OpenAI 모델을 선택해주세요.", ["gpt-4o", "gpt-4o-mini"], index=0)
    apply_btn = st.button("데이터 분석 시작")

if clear_btn:
    st.session_state["messages"] = []

if apply_btn and uploaded_file:
    try:
        if uploaded_file.type == "application/pdf":
            text_data = extract_pdf_data(uploaded_file)
        else:
            text_data = extract_image_data(uploaded_file)

        if text_data:
            st.session_state["text_data"] = text_data
            st.session_state["agent"] = create_agent(text_data, selected_model)
            st.success("설정이 완료되었습니다. 대화를 시작해 주세요!")
        else:
            st.error("파일에서 텍스트 데이터를 추출할 수 없습니다.")
    except Exception as e:
        st.error(f"파일 처리 중 오류가 발생했습니다: {e}")
elif apply_btn:
    st.warning("PDF 또는 이미지 파일을 업로드 해주세요.")

print_messages()

user_input = st.chat_input("궁금한 내용을 물어보세요!")
if user_input:
    ask(user_input)