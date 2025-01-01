from typing import List, Union
from openai import OpenAI
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
import base64
import io
from dotenv import load_dotenv

# API 키 및 프로젝트 설정
load_dotenv()

# Streamlit 앱 설정
st.title("이미지 분석 AI AGENT")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "agent" not in st.session_state:
    st.session_state["agent"] = None

# 상수 정의
class MessageRole:
    USER = "user"
    ASSISTANT = "assistant"

class MessageType:
    TEXT = "text"
    LATEX = "latex"

# 메시지 출력
def print_messages():
    for role, content_list in st.session_state["messages"]:
        with st.chat_message(role):
            for content in content_list:
                if isinstance(content, list):
                    message_type, message_content = content
                    if message_type == MessageType.TEXT:
                        st.markdown(message_content, unsafe_allow_html=True)
                    elif message_type == MessageType.LATEX:
                        st.latex(message_content)
                else:
                    raise ValueError(f"Unknown content type: {content}")

def add_message(role: MessageRole, content: List[Union[MessageType, str]]):
    messages = st.session_state["messages"]
    if messages and messages[-1][0] == role:
        messages[-1][1].extend([content])
    else:
        messages.append([role, [content]])

# 에이전트 생성 함수
def create_agent(image_file, selected_model="o1-mini"):
    # OpenAI 클라이언트 초기화
    client = OpenAI()

    # 이미지를 base64로 인코딩
    image_data = base64.b64encode(image_file.getvalue()).decode('utf-8')

    return client, image_data, selected_model

# 질문 처리 함수
def ask(query):
    if st.session_state["agent"]:
        st.chat_message("user").write(query)
        add_message(MessageRole.USER, [MessageType.TEXT, query])

        client, image_data, selected_model = st.session_state["agent"]
        ai_answer = ""

        with st.chat_message("assistant"):
            try:
                # Vision API 메시지 구성
                messages = [
                    {
                        "role": "system",
                        "content": "You are a teacher who is good at solving physics problems in pictures. Please explain in detail the problem and explanation process for the problem in the given photo. Use Korean for explanations."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            },
                            {
                                "type": "text",
                                "text": query
                            }
                        ]
                    }
                ]

                # 모델로부터 응답 생성
                response = client.chat.completions.create(
                    model=selected_model,
                    messages=messages,
                )

                # 모델 응답 추가
                ai_answer = response.choices[0].message.content
                st.write(ai_answer)
                add_message(MessageRole.ASSISTANT, [MessageType.TEXT, ai_answer])

            except Exception as e:
                error_message = f"An error occurred: {e}"
                st.error(error_message)
                add_message(MessageRole.ASSISTANT, [MessageType.TEXT, error_message])

# 이미지 처리 함수
def process_image(image_file):
    try:
        image = Image.open(image_file)
        return image
    except Exception as e:
        st.error(f"이미지를 처리하는 중 오류가 발생했습니다: {e}")
        return None

# 메인 로직
with st.sidebar:
    clear_btn = st.button("대화 초기화")
    uploaded_image = st.file_uploader("이미지 파일을 드래그하거나 업로드 해주세요.", type=["jpg", "jpeg", "png"])
    selected_model = st.selectbox("OpenAI 모델을 선택해주세요.", ["gpt-4o", "gpt-4o"], index=0)

    if uploaded_image:
        image = process_image(uploaded_image)
        if image:
            st.image(image, caption="업로드된 이미지", use_column_width=True)
            st.session_state["agent"] = create_agent(uploaded_image, selected_model)
            st.success("이미지가 성공적으로 업로드 및 분석 준비되었습니다!")
        else:
            st.error("이미지를 처리할 수 없습니다.")

if clear_btn:
    st.session_state["messages"] = []
    st.session_state["agent"] = None

print_messages()

user_input = st.chat_input("궁금한 내용을 물어보세요!")
if user_input:
    ask(user_input)