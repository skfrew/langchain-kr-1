from typing import List, Union
from langchain.chat_models import ChatOpenAI
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain_teddynote import logging
from dotenv import load_dotenv
import streamlit as st
import os
import time
import json
import shutil
from PIL import Image

# API 키 및 프로젝트 설정
load_dotenv()

st.set_page_config(
    page_title="Sleuth",
    page_icon="favicon.png"
)

#유저 넘버 부여
def get_next_user_number():
    # 사용자 번호를 저장할 파일 경로
    user_file = "user_numbers.json"
    
    try:
        # 파일이 존재하면 읽어오기
        if os.path.exists(user_file):
            with open(user_file, 'r') as f:
                user_data = json.load(f)
                last_number = user_data.get("last_number", 0)
        else:
            last_number = 0
            
        # 다음 번호 생성
        next_number = last_number + 1
        
        # 새로운 번호 저장
        with open(user_file, 'w') as f:
            json.dump({"last_number": next_number}, f)
            
        return f"customer_{next_number}"
        
    except Exception as e:
        print(f"Error managing user numbers: {e}")
        return f"customer_unknown"

# 사용자 ID 생성 로직 수정
if "user_id" not in st.session_state:
    st.session_state["user_id"] = get_next_user_number()
user_id = st.session_state["user_id"]

# set_enable=False 로 지정하면 추적을 하지 않습니다.
logging.langsmith(
    "Fictionflare_Test",
    set_enable=1
)

# Streamlit 앱 설정
st.title("대화를 통해 범인을 찾아라!")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state["messages"] = {}
if "selected_character" not in st.session_state:
    st.session_state["selected_character"] = None
if "agent" not in st.session_state:
    st.session_state["agent"] = None
if "prompt_count" not in st.session_state:
    st.session_state["prompt_count"] = 0  # 프롬프트 횟수 초기화
# 게임 진행률을 세션 상태로 관리
if "game_process" not in st.session_state:
    st.session_state.game_process = 0
if "guideline" not in st.session_state:
    st.session_state["guideline"] = True

@st.dialog("추리게임 슬루스(Sleuth)")
def show_guide_dialog():
    st.subheader("📖 게임 플레이 가이드라인")
    st.markdown("""
    당신은 현재 범죄가 일어난 사건에서 피해자와 관련된 사람들과 대화를 나누며 유력한 용의자가 누군지, 어떤 범행을 저질렀는지 추리하는 형사입니다.
    - **캐릭터 선택:** 왼쪽 사이드바에서 캐릭터를 선택하여 대화를 시작하세요. 어떤 질문을 하셔도 괜찮습니다. 질문을 하면서 증거를 모아보세요.
    - **수사 보고서 작성:** 여러 인물과 대화를 통해 증거를 충분히 수집했고, 합당한 결론이 났다면 이 버튼을 통해 사건의 진상을 말씀해주세요.""")
    st.subheader("💡 Tip")
    st.markdown("""
    - **누군가는 실수로 거짓말을 할 수도 있고, 누군가는 일부러 거짓말을 할 수도 있습니다.**
    - **인물에게 질문했을 때 "잘 모르겠습니다" 또는 "기억이 나지 않습니다" 와 같은 답변을 받았다면, 해당 질문은 본 사건 해결에 있어 중요한 정보가 아날 가능성이 높습니다. 다른 방향으로 질문을 시도해보세요.**
    
    **※** 인물이 기억하지 못하거나 잘 모르는 사항에 답변을 강요하는 강압 수사는 **허위 진술**로 이어져 사실과 다른 답변을 받을 위험이 있으니 주의하시기 바랍니다.
    
    **대화 초기화:** 이 버튼은 개발진이 테스트 용도로 만든 버튼이니, 무시하시면 됩니다. (사용 X)
    """)
    
    if st.button("닫기", key="close_guide_button"):
        st.session_state["guideline"] = False
        st.rerun()

# 가이드라인 표시
if st.session_state["guideline"]:
    show_guide_dialog()

# 대화 기록 파일 경로 설정
history_dir = os.path.join(os.path.dirname(__file__), "history")
os.makedirs(history_dir, exist_ok=True)  # history 폴더 생성

def get_history_filepath(character_name):
    """캐릭터별 대화 기록 파일 경로 반환"""
    return os.path.join(history_dir, f"{character_name}.json")

def load_history(character_name):
    """캐릭터별 대화 기록 로드"""
    filepath = get_history_filepath(character_name)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as file:
            return json.load(file)
    return []

def save_history(character_name, history):
    """캐릭터별 대화 기록 저장"""
    filepath = get_history_filepath(character_name)
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=4)

def clear_history(character_name):
    """특정 캐릭터의 대화 기록 삭제"""
    filepath = get_history_filepath(character_name)
    if os.path.exists(filepath):
        os.remove(filepath)

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

    # 대화 기록 파일에 저장
    save_history(character, st.session_state["messages"][character])

# 초기 메시지 출력 함수
def display_initial_messages(character):
    # 이미 메시지가 있는 경우 초기 메시지를 표시하지 않음
    if character in st.session_state["messages"] and st.session_state["messages"][character]:
        print_messages()
        return False

    if character == "김진욱(경찰대 32기)":
        initial_messages = [
            "안녕하세요. 저는 경찰대 32기 출신 김진욱입니다. 이번 사건 수사에서 함께하게 된 동료 형사입니다. 제가 사건의 기본 정보를 제공하고 수사를 원활히 진행할 수 있도록 도울 예정입니다.",
            "다만, 저는 수사 진행에 필요한 정보를 제공하는 역할을 맡고 있으니 저와의 직접적인 소통보다는 제공된 정보를 활용해 사건을 풀어나가 주시길 바랍니다.",
            "앞으로 잘 부탁드립니다. "
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
                time.sleep(len(msg) * 0) # 0.1
                st.markdown(msg)
                add_message(MessageRole.ASSISTANT, [MessageType.TEXT, msg])
        
        # 첫 번째 이미지(범죄 현장) 메시지 출력
        with st.chat_message("assistant"):
            time.sleep(0) # 3
            st.image(crime_scene_image)
            add_message(MessageRole.ASSISTANT, [MessageType.IMAGE, crime_scene_image])
            
        # 마지막 설명 메시지 출력
        with st.chat_message("assistant"):
            time.sleep(len(follow_up_message) * 0) # 0.1
            st.markdown(follow_up_message)
            add_message(MessageRole.ASSISTANT, [MessageType.TEXT, follow_up_message])
            
        # 두 번째 이미지(현정 프로필) 메시지 출력
        with st.chat_message("assistant"):
            time.sleep(0) # 3
            st.image(hyeonjeong_profile)
            add_message(MessageRole.ASSISTANT, [MessageType.IMAGE, hyeonjeong_profile])
        
        # 마지막 설명 메시지 출력
        with st.chat_message("assistant"):
            time.sleep(len(follow_up_message_2) * 0) # 0.1
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
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        tags=[f"character_{character}"],
        metadata={                        # 메타데이터 추가
            "character": character,
            "user_id": st.session_state["user_id"]
        }
    )

    # 캐릭터 템플릿 구성
    if "template" in profile:
        template = profile["template"]
        system_message_content = template.format(
            identity=profile["data"]["identity"],
            data="\n".join([f"- {key}: {value}" for key, value in profile["data"]["knowledge"].items()]),
            examples="\n".join(
                [f"질문: {example['question']}\n답변: {example['answer']}" for example in profile["data"]["examples"]]
            )
        )
    else:
        system_message_content = (
            f"당신은 {profile['data']['identity']}입니다. 대답의 포맷은 메신저 앱이므로 실제 문자를 보낸다는 형식입니다. 대답은 한 문장으로만 구성됩니다.\n\n"
            + "\n".join([f"- {key}: {value}" for key, value in profile["data"]["knowledge"].items()])
            + "\n\n### 예시:\n"
            + "\n".join([f"질문: {example['question']}\n답변: {example['answer']}" for example in profile["data"]["examples"]])
        )
    
    # 대화 기록을 세션 상태에서 가져오기
    conversation_history = []
    
    # SystemMessage 추가 시 명시적으로 추가 속성 지정
    system_message = SystemMessage(
        content=system_message_content,
        additional_kwargs={"User_ID": user_id},
        response_metadata={"character": character}
    )
    conversation_history.append(system_message)

    if character in st.session_state["messages"]:
        for role, content_list in st.session_state["messages"][character]:
            for content in content_list:
                if isinstance(content, list) and len(content) == 2:
                    _, text_content = content
                    if role == "user":
                        conversation_history.append(
                            HumanMessage(
                                content=text_content,
                                additional_kwargs={"User_ID": user_id},
                                response_metadata={"character": character}
                            )
                        )
                    elif role == "assistant":
                        conversation_history.append(
                            AIMessage(
                                content=text_content,
                                additional_kwargs={"User_ID": user_id},
                                response_metadata={"character": character}
                            )
                        )
                else:
                    raise ValueError(f"Invalid message format: {content}")

    # print(conversation_history)
    return chat, conversation_history

# 질문 처리 함수
def ask(query):
    # 최대 허용 자수
    MAX_INPUT_LENGTH = 100  # 원하는 제한 글자 수 설정 (예: 300자)
    
    # 입력 길이 초과 시 경고 메시지와 입력 차단
    if len(query) > MAX_INPUT_LENGTH:
        st.warning(f"입력이 너무 깁니다! 메시지는 최대 {MAX_INPUT_LENGTH}자까지만 가능합니다. 현재 입력: {len(query)}자")
        return  # 입력이 너무 길면 함수를 종료하여 처리하지 않음
    
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

                # 출력 전에 딜레이 추가
                delay_time = len(ai_answer) * 0.1  # 0.1, 텍스트 길이에 비례한 딜레이 (예: 글자당 0.1초)
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
        notify_character_added_to_jinwook(new_character_name)

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
                
                # 새로운 캐릭터 알림 메시지 추가 (단일 인자만 전달)
                notify_character_added_to_jinwook(char_name)
    return new_character_name  # 새로 추가된 캐릭터 이름 반환

# 김진욱의 새로운 인물 노트 불러오기 (jinwook_memo.json)
# 새로운 인물 알림 저장
def notify_character_added_to_jinwook(new_character_name):
    # 현재 파일의 디렉토리 경로 가져오기
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # JSON 파일 불러오기
    try:
        with open(os.path.join(current_dir, "jinwook_memo.json"), "r", encoding="utf-8") as file:
            character_data = json.load(file)
    except FileNotFoundError:
        st.error("jinwook_memo.json 파일을 찾을 수 없습니다.")
        return
    except json.JSONDecodeError:
        st.error("jinwook_memo.json 파일이 올바른 JSON 형식이 아닙니다.")
        return

    # 특정 인물에 대한 정보 가져오기
    character_info = character_data.get("characters", {}).get(new_character_name)
    if not character_info:
        st.warning(f"'{new_character_name}'에 대한 정보가 없습니다.")
        return

    # 메시지와 이미지 가져오기
    message = character_info.get("message", "새로운 인물 정보가 없습니다.")
    image_path_2 = character_info.get("image", None)
    if image_path_2:
        image_path = os.path.join(os.path.dirname(__file__), image_path_2)
        # 이미지 파일 열기
        image = Image.open(image_path)

    # 알림 저장 공간 초기화
    if "jinwook_notifications" not in st.session_state:
        st.session_state["jinwook_notifications"] = []

    # 중복 메시지 방지
    if message not in st.session_state["jinwook_notifications"]:
        st.session_state["jinwook_notifications"].append(message)
        st.session_state["jinwook_notifications"].append(image)
        

        # 팝업 알림 표시
        st.toast(f"📢 새로운 인물이 추가되었습니다! 동료 형사 김진욱과의 대화를 통해 확인해보세요", icon="🔔")

loan_book = os.path.join(os.path.dirname(__file__), "../assets/loan_book.png")
hyeonjeong_profile = os.path.join(os.path.dirname(__file__), "../assets/hyeonjeong_profile.png")
hyuksoo_profile = os.path.join(os.path.dirname(__file__), "../assets/hyuksoo_profile.png")
jooyeon_profile = os.path.join(os.path.dirname(__file__), "../assets/jooyeon_profile.png")
taesoo_profile = os.path.join(os.path.dirname(__file__), "../assets/taesoo_profile.png")
haejin_profile = os.path.join(os.path.dirname(__file__), "../assets/haejin_profile.png")

# 김진욱(경찰대 32기) 클릭 시 알림 표시
def show_jinwook_notifications():
    if "jinwook_notifications" in st.session_state and st.session_state["jinwook_notifications"]:
        notifications = st.session_state["jinwook_notifications"]

        # 텍스트와 이미지를 분리해서 처리
        text_notifications = [n for n in notifications if isinstance(n, str)]
        image_notifications = [n for n in notifications if isinstance(n, Image.Image)]

        # 텍스트 알림을 하나로 합침
        combined_message = "\n\n".join(text_notifications)

        with st.chat_message("assistant"):
            # 텍스트 알림 출력
            if combined_message:
                st.markdown(combined_message)
                add_message(MessageRole.ASSISTANT, [MessageType.TEXT, combined_message])

            # 이미지 알림 출력
            for img in image_notifications:
                st.image(img)
                if "장부" in combined_message:
                    st.image(haejin_profile)
                    add_message(MessageRole.ASSISTANT, [MessageType.IMAGE, loan_book])
                    add_message(MessageRole.ASSISTANT, [MessageType.IMAGE, haejin_profile])
                elif "최주연이라는" in combined_message:
                    add_message(MessageRole.ASSISTANT, [MessageType.IMAGE, jooyeon_profile])
                elif "신혁수라는" in combined_message:
                    add_message(MessageRole.ASSISTANT, [MessageType.IMAGE, hyuksoo_profile])
                elif "이태수라는" in combined_message:
                    add_message(MessageRole.ASSISTANT, [MessageType.IMAGE, taesoo_profile])
        
        # 게임 진행률 업데이트
        st.session_state.game_process += 20
        # st.toast(f"🎮 게임 진행률이 {st.session_state.game_process}%가 되었습니다! ")
        
        # 알림 표시 후 삭제
        st.session_state["jinwook_notifications"] = []


# 김진욱(경찰대 32기) 선택 이벤트 처리
def on_character_selected(character_name):
    if character_name == "김진욱(경찰대 32기)":
        show_jinwook_notifications()

@st.dialog("이어서 진행하기")
def show_selection_dialog():
    st.subheader("인물에게 질문할 수 있는 횟수(질문권)가 초과되었습니다!")
    st.markdown("아래 버튼 중 하나를 선택해주세요.")
    
    # 버튼 3개
    if st.button("30초 광고보고 20회 질문권 충전", key="option_1"):
        st.session_state["selected_option"] = "옵션 1"
        st.rerun()
    elif st.button("1000원 지불하고 100회 질문권 충전", key="option_2"):
        st.session_state["selected_option"] = "옵션 2"
        st.rerun()
    elif st.button("1시간 기다리고 10회 질문권 얻기", key="option_3"):
        st.session_state["selected_option"] = "옵션 3"
        st.rerun()

medic_report = os.path.join(os.path.dirname(__file__), "../assets/medical_examination_report.png")

#김진욱 새로운 고지 트리거
# 복어 독 발견 트리거
if st.session_state['prompt_count'] >= 35 and st.session_state.get("selected_character") == "김진욱(경찰대 32기)" and not st.session_state.get("poison_triggered", False):
    # 팝업 알림 표시
    st.toast(f"📢 새로운 증거가 발견되었습니다! 동료 형사 김진욱을 통해 확인해보세요.", icon="🔔")
    # 메시지 출력
    end_message = "피해자의 몸에서 테트로도톡신(복어 독)이 발견되었습니다! \n독에 중독된 뒤 숨을 거두기 직전에 목이 졸린 것으로 보입니다. 사망 추정 시간은 저녁 8시로 확인되었습니다."
    process_message = "지금까지 확보된 증거와 관련된 인물은 모두 파악된 상태입니다. 추가로 새로운 증거나 인물이 나올 가능성은 없을 것으로 보입니다. 이제 이 자료들을 바탕으로 형사님께서 추측되는 범인과 범행에 대해 수사보고서에 작성해 주시길 부탁드립니다!"
    add_message(MessageRole.ASSISTANT, [MessageType.TEXT, end_message])
    add_message(MessageRole.ASSISTANT, [MessageType.IMAGE, medic_report])
    add_message(MessageRole.ASSISTANT, [MessageType.TEXT, process_message])
    
    st.session_state.game_process += 15
    # st.toast(f"🎮 게임 진행률이 {st.session_state.game_process}%가 되었습니다! ")

    # 트리거 플래그 업데이트
    st.session_state["poison_triggered"] = True

if st.session_state['prompt_count'] == 36 and not st.session_state.get("keep_going", False):
    show_selection_dialog()
    
    # 트리거 플래그 업데이트
    st.session_state["keep_going"] = True

# 제출 팝업창 정의
@st.dialog("수사보고서(Investigation Report)")
def submit_dialog():
    st.subheader("사망원인 수사 및 사건처리 관련 보고")
    
    # 사용자 입력란
    user_response = st.text_area("1. 범행 장소", placeholder="여기에 내용을 입력하세요...")
    user_response_2 = st.text_area("2. 피의자", placeholder="여기에 내용을 입력하세요...")
    user_response_3 = st.text_area("3. 도난 물품", placeholder="여기에 내용을 입력하세요...")
    user_response_4 = st.text_area("4. 범행 동기", placeholder="여기에 내용을 입력하세요...")
    user_response_5 = st.text_area("5. 독 획득 과정", placeholder="여기에 내용을 입력하세요...")
    st.markdown("<br><div style='text-align: center; font-weight: bold;'>나는 본 보고서를 양심에 따라 사실에 근거하여 성실히 작성하였음을 선언합니다.</div>", unsafe_allow_html=True)
    
    # 팝업 내 제출 버튼
    if st.button("서명 및 제출", key="submit_modal_button"):
        if user_response and user_response_2 and user_response_3 and user_response_4 and user_response_5:
            # AI 평가 함수 정의
            def evaluate_response(user_input_1, user_input_2, user_input_3, user_input_4, user_input_5):
                # 채팅 에이전트 초기화
                chat = ChatOpenAI(
                    model="gpt-4o-mini",  # 모델 선택
                    temperature=0,
                    openai_api_key=os.getenv("OPENAI_API_KEY"),
                )
                
                # AI에게 주어질 프롬프트 작성
                evaluation_prompt = f"""
                당신은 사용자의 답안을 1, 2, 3 중 하나의 숫자로만 평가하는 AI입니다. 
                정답 기준과 사용자의 답안을 비교하여 채점 기준에 맞게 채점해주세요.

                ### 채점 기준
                1️⃣ (모두 틀린 경우) → "1"
                2️⃣ (피의자는 맞췄지만, 다른 내용이 틀린 경우) → "2"
                3️⃣ (모든 정답을 맞춘 경우) → "3"

                ### 정답 기준
                1. 범행 장소: "김은정(피해자)의 집"
                2. 피의자: "최주연"
                3. 도난 물품: "최주연의 차용증", "김은정의 휴대폰"
                4. 범행 동기: "전세사기로 어려움을 겪던 최주연에게 김은정이 금전적인 도움을 주지 않음"
                5. 독 획득 과정: "(복어요리가 있는)신혁수의 횟집에서 아르바이트를 하면서 복어 독을 빼돌림"

                ### 사용자의 답안
                1. 범행 장소: "{user_input_1}"
                2. 피의자: "{user_input_2}"
                3. 도난 물품: "{user_input_3}"
                4. 범행 동기: "{user_input_4}"
                5. 독 획득 과정: "{user_input_5}"

                ### 출력 형식
                - 반드시 "1", "2", "3" 중 하나만 출력하세요.
                - 추가 설명 없이 정확한 숫자 하나만 반환하세요.
                - 유사한 의미의 표현은 정답으로 인정하세요.
                """
                
                # 시스템 메시지 구성
                system_message = SystemMessage(content=evaluation_prompt)
                
                # AI 응답 가져오기
                response = chat([system_message])
                return response.content
            # AI 평가 호출
            try:
                ai_evaluation = evaluate_response(user_response, user_response_2, user_response_3, user_response_4, user_response_5)
                
                # 결과 출력
                st.success("AI 평가 결과:")
                st.text(ai_evaluation)
            except Exception as e:
                st.error(f"AI 평가 중 오류가 발생했습니다: {e}")
        else:
            st.error("내용을 입력해주세요.")

# 기존 캐릭터 선택 기능
with st.sidebar:
    st.header("대화 상대 선택")
    selected_character = st.radio(
        "캐릭터를 선택하세요:",
        options=list(character_profiles.keys())
    )
    
    # 가이드라인 버튼 추가
    if st.button("게임 가이드라인", key="show_guide_button"):
        show_guide_dialog()  # 가이드라인 다이얼로그 호출

    # 제출 버튼 추가
    if st.sidebar.button("수사보고서 작성", key="submit_sidebar_button"):
        submit_dialog()  # 팝업 다이얼로그 호출
        
    # 캐릭터 초기화 버튼 추가
    if st.sidebar.button("캐릭터 초기화(개발자용)"):
        shutil.copy(default_characters_filepath, characters_filepath)
        st.session_state["reset_characters"] = True  # 초기화 상태 업데이트
        character_profiles = load_json(characters_filepath)  # 캐릭터 데이터 다시 로드
        
        # 이전 대화 기록 초기화
        st.session_state["messages"] = {}
        
        st.sidebar.success("캐릭터 데이터와 대화 기록이 초기화되었습니다!")

# 캐릭터 선택 시 JSON으로부터 캐릭터 불러오기
if st.session_state.get("selected_character") != selected_character:
    st.session_state["selected_character"] = selected_character
    st.session_state["agent"] = create_agent(selected_character)
    
    display_initial_messages(selected_character)  # 초기 대화 표시
    
    # 김진욱(경찰대 32기)이 선택된 경우만 알림 표시
    if selected_character == "김진욱(경찰대 32기)" and st.session_state.get("jinwook_notifications"):
        show_jinwook_notifications()  # 김진욱의 알림 표시 함수 호출
else:
    print_messages()  # 기존 대화 기록 표시

# 사용자 입력 처리
user_input = st.chat_input("궁금한 내용을 물어보세요!")
if user_input:
    ask(user_input)