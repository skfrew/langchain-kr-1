from typing import List, Union
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from dotenv import load_dotenv
import streamlit as st
import os
import time
import json

# API 키 및 프로젝트 설정
load_dotenv()

# Streamlit 앱 설정
st.title("등장인물과 대화하기 💬")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state["messages"] = {}
if "selected_character" not in st.session_state:
    st.session_state["selected_character"] = None
if "agent" not in st.session_state:
    st.session_state["agent"] = None
if "prompt_count" not in st.session_state:
    st.session_state["prompt_count"] = 0  # 프롬프트 횟수 초기화

# 상수 정의
class MessageRole:
    USER = "user"
    ASSISTANT = "assistant"

class MessageType:
    TEXT = "text"

def load_json(filepath):
    """JSON 파일 로드."""
    with open(filepath, 'r', encoding='utf-8') as file:
        return json.load(file)

def save_json(filepath, data):
    """JSON 파일 저장."""
    with open(filepath, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# 캐릭터 데이터 파일 경로
characters_filepath = os.path.join(os.path.dirname(__file__), "characters.json")
add_characters_filepath = os.path.join(os.path.dirname(__file__), "add_characters.json")

# 캐릭터 데이터 로드
character_profiles = load_json(characters_filepath)
add_characters = load_json(add_characters_filepath)

# 메시지 출력
def print_messages():
    if st.session_state["selected_character"] in st.session_state["messages"]:
        for role, content_list in st.session_state["messages"][st.session_state["selected_character"]]:
            with st.chat_message(role):
                for content in content_list:
                    if isinstance(content, list):
                        message_type, message_content = content
                        if message_type == MessageType.TEXT:
                            st.markdown(message_content)
                    else:
                        raise ValueError(f"Unknown content type: {content}")

def add_message(role: MessageRole, content: List[Union[MessageType, str]]):
    character = st.session_state["selected_character"]
    if character not in st.session_state["messages"]:
        st.session_state["messages"][character] = []
    messages = st.session_state["messages"][character]
    if messages and messages[-1][0] == role:
        messages[-1][1].extend([content])
    else:
        messages.append([role, [content]])

# 에이전트 생성 함수
def create_agent(character):
    if character not in character_profiles:
        raise ValueError(f"Unknown character: {character}")
    
    profile = character_profiles[character]
    chat = ChatOpenAI(
        model="gpt-4",
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    system_message_content = (
        f"당신은 {profile['identity']}입니다.\n"
        + "\n".join([f"### {key}:\n{value}" for key, value in profile["knowledge"].items()])
        + "\n\n### 예시:\n"
        + "\n".join([f"질문: {example['question']}\n답변: {example['answer']}" for example in profile["examples"]])
    )

    conversation_history = [SystemMessage(content=system_message_content)]
    return chat, conversation_history

# 질문 처리 함수
def ask(query):
    # 특정 단어에 대한 캐릭터 추가 체크
    check_and_add_character_based_on_keyword(query)

    if st.session_state["agent"]:
        st.session_state["prompt_count"] += 1  # 프롬프트 횟수 증가
        st.chat_message("user").write(query)
        add_message(MessageRole.USER, [MessageType.TEXT, query])

        chat, conversation_history = st.session_state["agent"]
        ai_answer = ""

        # 사용자 메시지 추가
        conversation_history.append(HumanMessage(content=query))

        with st.chat_message("assistant"):
            try:
                response = chat(conversation_history)
                ai_answer = response.content

                # 출력 전에 딜레이 추가
                delay_time = len(ai_answer) * 0.1  # 텍스트 길이에 비례한 딜레이 (예: 글자당 0.1초)
                time.sleep(delay_time)

                # 전체 텍스트 출력
                st.write(ai_answer)
                add_message(MessageRole.ASSISTANT, [MessageType.TEXT, ai_answer])
                conversation_history.append(AIMessage(content=ai_answer))
            except Exception as e:
                error_message = f"An error occurred: {e}"
                st.error(error_message)
                add_message(MessageRole.ASSISTANT, [MessageType.TEXT, error_message])

# 새로운 캐릭터 추가 조건 (특정 단어 기반)
def check_and_add_character_based_on_keyword(user_query: str):
    global character_profiles, add_characters

    for char_name, char_data in add_characters.items():
        condition = char_data["condition"]
        if eval(condition):  # 조건 평가
            if char_name not in character_profiles:
                character_profiles[char_name] = char_data["data"]
                save_json(characters_filepath, character_profiles)  # 업데이트된 캐릭터 저장

# 캐릭터 선택 기능
with st.sidebar:
    st.header("대화 상대 선택")
    selected_character = st.radio(
        "캐릭터를 선택하세요:",
        options=list(character_profiles.keys())
    )

# 캐릭터 선택 시 JSON으로부터 캐릭터 불러오기
st.session_state["selected_character"] = selected_character

if selected_character:
    st.session_state["agent"] = create_agent(selected_character)

print_messages()

# 사용자 입력 처리
user_input = st.chat_input("궁금한 내용을 물어보세요!")
if user_input:
    ask(user_input)
