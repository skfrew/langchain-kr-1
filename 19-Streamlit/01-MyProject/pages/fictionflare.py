from typing import List, Union
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from dotenv import load_dotenv
import streamlit as st
import os
import time
import json
import shutil

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
    IMAGE = "image"

def load_json(filepath):
    """JSON 파일 로드."""
    with open(filepath, 'r', encoding='utf-8') as file:
        return json.load(file)

def save_json(filepath, data):
    """JSON 파일 저장."""
    with open(filepath, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# 캐릭터 데이터 파일 경로
default_characters_filepath = os.path.join(os.path.dirname(__file__), "default_characters.json")
characters_filepath = os.path.join(os.path.dirname(__file__), "characters.json")
add_characters_filepath = os.path.join(os.path.dirname(__file__), "add_characters.json")

# 캐릭터 데이터 로드 및 초기화
if "messages" not in st.session_state:  # 세션 상태가 없는 경우 (새로고침 시 초기화)
    st.session_state["messages"] = {}
    st.session_state["selected_character"] = None
    st.session_state["agent"] = None
    st.session_state["prompt_count"] = 0

    # 캐릭터 데이터 초기화
    shutil.copy(default_characters_filepath, characters_filepath)
    character_profiles = load_json(characters_filepath)
    st.session_state["reset_characters"] = True  # 초기화 상태 플래그 설정

# Streamlit 실행 시 characters.json 초기화
if not os.path.exists(characters_filepath):  # 파일이 없을 때만 초기화
    shutil.copy(default_characters_filepath, characters_filepath)
elif "reset_characters" not in st.session_state:  # 세션 상태에 없는 경우 초기화 방지
    st.session_state["reset_characters"] = False  # 초기화 방지 상태 설정

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
                        elif message_type == MessageType.IMAGE:
                            st.image(message_content)
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

# 초기 메시지 출력 함수
def display_initial_messages(character):
    # 이미 메시지가 있는 경우 초기 메시지를 표시하지 않음
    if character in st.session_state["messages"] and st.session_state["messages"][character]:
        print_messages()
        return False

    if character == "김진욱(경찰대 32기)":
        initial_messages = [
            "안녕하세요. 저는 경찰대 32기 출신 김진욱입니다. 이번 사건 수사에서 함께하게 된 동료 형사입니다. 앞으로 잘 부탁드립니다.",
            "그럼 바로 사건 내용을 간단히 브리핑하겠습니다.",
            "2023년 12월 20일, 수요일 오후 한 가정집에서 40대 여성 김은정 씨가 숨진 채 발견됐습니다. 시신을 처음 발견한 건 그녀의 동생 김현정 씨였고, 경찰에 직접 신고했습니다. 신고 당시 '언니가 방 안에서 죽어있다'고 말한 걸로 확인됐습니다.",
            "우선 사건 현장에서 찍은 사진을 전달해 드리겠습니다."
        ]

        # 이미지 경로
        crime_scene_image = os.path.join(os.path.dirname(__file__), "../assets/crime_scene.png")
        hyeonjeong_profile = os.path.join(os.path.dirname(__file__), "../assets/hyeonjeong_profile.png")

        # 추가 메시지
        follow_up_message = "현재 김현정씨에 관한 정보만 입수해서, 읽어보시면 좋겠습니다."
        follow_up_message_2 = "김현정 씨는 피해자의 친동생이며, 이번 사건의 최초 신고자입니다. 피해자를 마지막으로 본 사람 중 한 명이기도 해서, 이야기를 들어볼 필요가 있어 보입니다."

        # 메시지 저장 및 출력
        if character not in st.session_state["messages"]:
            st.session_state["messages"][character] = []

        # 텍스트 메시지 출력
        for msg in initial_messages:
            with st.chat_message("assistant"):
                time.sleep(len(msg) * 0.1)
                st.markdown(msg)
                add_message(MessageRole.ASSISTANT, [MessageType.TEXT, msg])
        
        # 첫 번째 이미지(범죄 현장) 메시지 출력
        with st.chat_message("assistant"):
            time.sleep(3)
            st.image(crime_scene_image)
            add_message(MessageRole.ASSISTANT, [MessageType.IMAGE, crime_scene_image])
            
        # 마지막 설명 메시지 출력
        with st.chat_message("assistant"):
            time.sleep(len(follow_up_message) * 0.1)
            st.markdown(follow_up_message)
            add_message(MessageRole.ASSISTANT, [MessageType.TEXT, follow_up_message])
            
        # 두 번째 이미지(현정 프로필) 메시지 출력
        with st.chat_message("assistant"):
            time.sleep(3)
            st.image(hyeonjeong_profile)
            add_message(MessageRole.ASSISTANT, [MessageType.IMAGE, hyeonjeong_profile])
        
        # 마지막 설명 메시지 출력
        with st.chat_message("assistant"):
            time.sleep(len(follow_up_message_2) * 0.1)
            st.markdown(follow_up_message_2)
            add_message(MessageRole.ASSISTANT, [MessageType.TEXT, follow_up_message_2])
        
        return True
    return False

# 에이전트 생성 함수
def create_agent(character):
    if character not in character_profiles:
        raise ValueError(f"Unknown character: {character}")
    
    # 캐릭터 정보 로드
    profile = character_profiles[character]
    
    # ChatOpenAI 에이전트 초기화
    chat = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    # 캐릭터 템플릿 구성
    if "template" in profile:
        # JSON의 "template" 필드를 사용
        template = profile["template"]
        system_message_content = template.format(
            identity=profile["data"]["identity"],
            data="\n".join([f"- {key}: {value}" for key, value in profile["data"]["knowledge"].items()]),
            examples="\n".join(
                [f"질문: {example['question']}\n답변: {example['answer']}" for example in profile["data"]["examples"]]
            )
        )
    else:
        # "template" 필드가 없는 경우 기본 포맷 사용
        system_message_content = (
            f"당신은 {profile['data']['identity']}입니다. 대답의 포맷은 메신저 앱이므로 실제 문자를 보낸다는 형식입니다. 대답은 한 문장으로만 구성됩니다.\n\n"
            + "\n".join([f"- {key}: {value}" for key, value in profile["data"]["knowledge"].items()])
            + "\n\n### 예시:\n"
            + "\n".join([f"질문: {example['question']}\n답변: {example['answer']}" for example in profile["data"]["examples"]])
        )

    # 대화 기록 초기화
    conversation_history = [SystemMessage(content=system_message_content)]

    return chat, conversation_history

# 질문 처리 함수
def ask(query):
    # 특정 단어에 대한 캐릭터 추가 체크
    new_character_name = check_and_add_character_based_on_keyword(query)

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
                # print(conversation_history) #디버깅용

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

    # 새로운 캐릭터 추가 시 김진욱이 알림을 전송
    if new_character_name:  # 캐릭터가 추가되었다면
        notify_character_added_to_jinwook(new_character_name, character_profiles[new_character_name]["data"])

# 새로운 캐릭터 추가 조건 (특정 단어 기반)
def check_and_add_character_based_on_keyword(user_query: str):
    global character_profiles, add_characters

    new_character_name = None  # 새로운 캐릭터 이름을 저장

    for char_name, char_data in add_characters.items():
        condition = char_data["condition"]
        if eval(condition):  # 조건 평가
            if char_name not in character_profiles:
                # 캐릭터 데이터 추가
                character_profiles[char_name] = {"data": char_data["data"]}
                save_json(characters_filepath, character_profiles)  # 업데이트된 캐릭터 저장
                new_character_name = char_name  # 새로 추가된 캐릭터 이름 저장
                
                # 새로운 캐릭터 알림 메시지 추가
                notify_character_added_to_jinwook(char_name, char_data["data"])
    return new_character_name  # 새로 추가된 캐릭터 이름 반환

# 새로운 인물 알림 저장
def notify_character_added_to_jinwook(new_character_name, new_character_data):
    # 알림 메시지 구성
    message = (
        f"새로운 관련 인물 정보를 입수했습니다: **{new_character_name}**\n\n"
        f"{new_character_data['identity']}\n"
        f"추가로 질문이 필요하다면 알려주세요."
    )

    # 알림 저장 공간 초기화
    if "jinwook_notifications" not in st.session_state:
        st.session_state["jinwook_notifications"] = []

    # 알림 메시지 저장
    st.session_state["jinwook_notifications"].append(message)

# 김진욱(경찰대 32기) 클릭 시 알림 표시
def show_jinwook_notifications():
    if "jinwook_notifications" in st.session_state:
        notifications = st.session_state["jinwook_notifications"]

        if notifications:
            for message in notifications:
                st.chat_message("assistant").write(message)

            # 알림 표시 후 삭제
            st.session_state["jinwook_notifications"] = []

# 김진욱(경찰대 32기) 선택 이벤트 처리
def on_character_selected(character_name):
    if character_name == "김진욱(경찰대 32기)":
        show_jinwook_notifications()


# 캐릭터 선택 기능
with st.sidebar:
    st.header("대화 상대 선택")
    selected_character = st.radio(
        "캐릭터를 선택하세요:",
        options=list(character_profiles.keys())
    )

    # 캐릭터 초기화 버튼 추가
    if st.sidebar.button("캐릭터 초기화"):
        shutil.copy(default_characters_filepath, characters_filepath)
        st.session_state["reset_characters"] = True  # 초기화 상태 업데이트
        character_profiles = load_json(characters_filepath)  # 캐릭터 데이터 다시 로드
        
        # 이전 대화 기록 초기화
        st.session_state["messages"] = {}
        
        st.sidebar.success("캐릭터 데이터와 대화 기록이 초기화되었습니다!")
st.sidebar.markdown(
    "캐릭터 초기화 버튼은 테스트의 리셋용으로, 실제 UI에는 필요없는 기능임."
)
st.sidebar.markdown(
    "새로고침해도 캐릭터 세팅이 초기화가 안되어서 **초기화 버튼 누르고 새로고침** 하면 제일 처음 세팅으로 돌아감"
)

# 캐릭터 선택 시 JSON으로부터 캐릭터 불러오기
if st.session_state.get("selected_character") != selected_character:
    st.session_state["selected_character"] = selected_character
    st.session_state["agent"] = create_agent(selected_character)
    
    display_initial_messages(selected_character)  # 초기 대화 표시
    
    # 김진욱(경찰대 32기)이 선택된 경우만 알림 표시
    if selected_character == "김진욱(경찰대 32기)":
        show_jinwook_notifications()  # 김진욱의 알림 표시 함수 호출
else:
    print_messages()  # 기존 대화 기록 표시
    # 김진욱(경찰대 32기)이 선택된 경우만 알림 표시
    if selected_character == "김진욱(경찰대 32기)":
        show_jinwook_notifications()  # 김진욱의 알림 표시 함수 호출

# 사용자 입력 처리
user_input = st.chat_input("궁금한 내용을 물어보세요!")
if user_input:
    ask(user_input)

