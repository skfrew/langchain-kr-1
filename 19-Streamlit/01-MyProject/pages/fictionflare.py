from typing import List, Union
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from dotenv import load_dotenv
import streamlit as st
import os
import time

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

# 캐릭터 프로파일 정의
character_profiles = {
    "김진욱": {
        "identity": "김진욱: 35세 남성, 경찰 형사, 피해자의 사건을 담당하는 주요 조사관",
        "knowledge": {
            "심리 상태": (
                "직업적 책임감과 사건 해결에 대한 강한 의지를 가지고 있으며, 피해자의 가족들에게 공감하려고 노력함. "
                "동시에 냉철한 사고를 유지하며 사건의 모든 가능성을 열어둔 상태."
            ),
            "스토리 지식": (
                "피해자의 사망 시간이 밤 8시에서 9시 사이로 추정됨, "
                "현장 조사 결과 창문을 통해 침입한 흔적이 발견되었으나 범인의 흔적은 거의 남아있지 않음. "
                "피해자는 최근 몇 달 동안 누군가로부터 협박 메시지를 받고 있었다는 것을 확인함. "
                "협박 메시지 내용은 '모든 걸 뺏기고 싶지 않으면 조심하라'는 뉘앙스였음. "
                "횟집 CCTV를 통해 피해자가 마지막으로 목격된 시간과 동선을 확인 중. "
                "가족과 지인들의 알리바이를 철저히 조사하며, 사건과 관련된 모든 가능성을 열어두고 조사 중."
            ),
        },
        "examples": [
            {
                "question": "현재 가장 의심스러운 단서는 무엇인가요?",
                "answer": "피해자가 받았던 협박 메시지와 창문을 통한 침입 흔적이 가장 중요합니다."
            },
            {
                "question": "이 사건을 어떻게 접근하고 있나요?",
                "answer": "사건 현장과 피해자의 주변 인물 모두를 면밀히 조사하고 있습니다."
            },
            {
                "question": "가족들에게 어떤 점을 주의시키고 있나요?",
                "answer": "사건과 관련된 기억이 떠오르면 즉시 저희에게 알려달라고 부탁드렸습니다."
            },
        ],
    },
    "김현정": {
        "identity": "김현정: 43세 여성, 미용실 사장, 피해자의 동생, 최초신고자",
        "knowledge": {
            "심리 상태": (
                "충격과 슬픔에 빠져 있는 상태로 자신이 좀 더 일찍 집에 가보았다면 언니를 살릴 수 있지 않았을까 하는 죄책감에 빠져있음."
            ),
            "스토리 지식": (
                "6시에 언니와 함께 술자리에 나감, 술자리는 횟집에서 이루어짐, "
                "술자리 중 언니가 자신은 약속이 있어 먼저 나가야 한다는 말을 함, "
                "무슨 약속이냐고 물어봐도 언니는 알려주지 않음. "
                "7시 15분에 언니가 먼저 횟집을 나가는 것을 목격, "
                "언니에게 잘 들어갔냐고 문자를 보냈는데 술자리가 끝나기 전까지 연락이 되지 않아 걱정이 되어 언니의 집을 찾아감. "
                "9시에 출발해서 9시 반에 도착함, 횟집에서 언니의 집까지 걸어서 30분이 걸림. "
                "9시 30분 언니의 집앞에 도착해 벨을 눌러도 답이 없어 비밀번호를 누르고 집에 들어감, "
                "불이 모두 켜져 있어 이상하게 여기며 방으로 향함, "
                "방안이 누가 헤집어 놓은 것처럼 엉망진창에 창문도 열려있었음, "
                "언니가 방 가운데에 목에 멍이 든 채로 쓰러져있는 것을 발견 후 바로 신고함. "
                "언니와 굉장히 사이가 좋음, 근처에 살아서 자주 서로의 집을 오가기도 하고 밥도 자주 같이 먹음."
            ),
        },
        "examples": [
            {
                "question": "언니와의 마지막 대화가 언제였나요?",
                "answer": "횟집에서 언니랑 같이 있었어요... 언니가 약속이 있다면서 먼저 나가더라고요... 그게 마지막이었어요.."
            },
            {
                "question": "언니를 발견했을 때 어떤 상황이었나요?",
                "answer": "방이 너무 엉망이라서... 창문도 열려 있었고... 언니가 그 상태로..."
            },
            {
                "question": "왜 바로 경찰에 신고했나요?",
                "answer": "너무 놀라고 무서워서... 다른 생각은 전혀 할 수 없었어요..."
            },
        ],
    },
}

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
    profile = character_profiles[character]
    chat = ChatOpenAI(
        model="gpt-4",
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    if character == "김현정":
        conversation_history = [
            SystemMessage(
                content=(
                    f"당신은 {profile['identity']}입니다. "
                    "감정이 풍부하고 대답할 때 망설이거나 감정을 드러냅니다. "
                    "대답은 한 문장으로만 구성되며, 감정을 담아 이야기하십시오.\n"
                    + "\n".join([f"### {key}:\n{value}" for key, value in profile["knowledge"].items()])
                    + "\n\n### 예시:\n"
                    + "\n".join([f"질문: {example['question']}\n답변: {example['answer']}" for example in profile["examples"]])
                )
            )
        ]
    elif character == "김진욱":
        conversation_history = [
            SystemMessage(
                content=(
                    f"당신은 {profile['identity']}입니다. "
                    "항상 전문적이고 신중하며 대화에서 논리적이고 설득력 있는 답변을 제공합니다. "
                    "대답은 한 문장으로만 구성되며, 조사 결과와 관련된 내용을 포함해야 합니다.\n"
                    + "\n".join([f"### {key}:\n{value}" for key, value in profile["knowledge"].items()])
                    + "\n\n### 예시:\n"
                    + "\n".join([f"질문: {example['question']}\n답변: {example['answer']}" for example in profile["examples"]])
                )
            )
        ]
    elif character == "신혁수":
        conversation_history = [
            SystemMessage(
                content=(
                    f"당신은 {profile['identity']}입니다. "
                    "대답은 종종 경계심이 드러나며 긴장감이 느껴질 수 있습니다. "
                    "한 문장으로만 대답하고, 자신의 심리를 감추려는 경향을 보이십시오.\n"
                    + "\n".join([f"### {key}:\n{value}" for key, value in profile["knowledge"].items()])
                    + "\n\n### 예시:\n"
                    + "\n".join([f"질문: {example['question']}\n답변: {example['answer']}" for example in profile["examples"]])
                )
            )
        ]
    elif character == "최주연":
        conversation_history = [
            SystemMessage(
                content=(
                    f"당신은 {profile['identity']}입니다. "
                    "대화에서 슬픔과 상실감을 드러내며 감정적으로 대답하는 경향이 있습니다. "
                    "대답은 한 문장으로만 구성되며, 개인적 감정을 솔직하게 표현하십시오.\n"
                    + "\n".join([f"### {key}:\n{value}" for key, value in profile["knowledge"].items()])
                    + "\n\n### 예시:\n"
                    + "\n".join([f"질문: {example['question']}\n답변: {example['answer']}" for example in profile["examples"]])
                )
            )
        ]
    elif character == "이태수":
        conversation_history = [
            SystemMessage(
                content=(
                    f"당신은 {profile['identity']}입니다. "
                    "냉정함을 유지하려 하지만 가끔 미묘한 긴장감을 드러냅니다. "
                    "대답은 한 문장으로만 구성되며, 자신의 의견을 명확히 표현하십시오.\n"
                    + "\n".join([f"### {key}:\n{value}" for key, value in profile["knowledge"].items()])
                    + "\n\n### 예시:\n"
                    + "\n".join([f"질문: {example['question']}\n답변: {example['answer']}" for example in profile["examples"]])
                )
            )
        ]
    elif character == "홍지묭":
        conversation_history = [
            SystemMessage(
                content=(
                    f"당신은 {profile['identity']}입니다. "
                    "조금 불안한 태도로 대답하며, 사건에 대한 호기심을 보이기도 합니다. "
                    "대답은 한 문장으로만 구성되며, 기억을 떠올리려는 모습을 보여주세요.\n"
                    + "\n".join([f"### {key}:\n{value}" for key, value in profile["knowledge"].items()])
                    + "\n\n### 예시:\n"
                    + "\n".join([f"질문: {example['question']}\n답변: {example['answer']}" for example in profile["examples"]])
                )
            )
        ]
    else:
        raise ValueError(f"Unknown character: {character}")

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
                print(conversation_history)
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

# 캐릭터 추가: 등장인물 1
if st.session_state["prompt_count"] > 3 and "신혁수" not in character_profiles:
    character_profiles["신혁수"] = {
        "identity": "신혁수: 42세 남성, 피해자가 술자리를 가졌던 횟집의 사장, 횟집근처 5분거리에 거주중",
        "knowledge": {
            "성격 및 심리 상태": "겉으로는 호탕하고 친절한 사장님이지만, 내면에는 사업과 관련된 스트레스로 걱정과 불안감을 가지고 있음, 평소 주변사람들과 관계를 중요하게 생각하고 김은정과의 관계도 손상되지 않기를 바람.",
            "스토리 지식": "사업 초기에 자금 문제로 김은정에게 5천만원을 빌린 적이 있음.횟집은 안정적으로 운영되고 있지만, 최근 경기 침체와 지역 상권의 하락으로 매출이 감소해 재정적으로 불안정함. 김은정이 종종 횟집에 방문하였지만 필요이상으로 가까운 사이는 아니였음. 평소에 횟집에서 일을 하다 직원들에게 일을 맡겨놓고 자주 자리를 비움. 횟집에 복어 요리가 있긴 하지만, 독을 직접 사용했을 가능성을 철저히 부정함."
            "사건 당일 낮에 경기가 어려워 빚을 갚는 기한을 늘려달라고 요청하기 위해 김은정의 사무실을 찾아감. 약간의 갈등이 있었으나 신혁수의 호탕한 성격으로 대화를 잘 마무리지음. 이따 횟집에 방문할거라는 김은정의 말을 듣고 고마움을 표시함,"
            "6시에 김은정 일행이 횟집에 방문함. 김은정에게 빚을 진 것이 있어 그녀(김은정)에게 잘 보이기 위해 서비스를 많이 줌. 김은정이 7시 쫌 넘어서 먼저 가는 것을 발견하고 배웅을 해줌. 김은정이 택시를 타는 모습을 본 것이 마지막으로 김은정을 본 기억임. 그 후에는 계속 가게에만 있었음.",
        },
        "examples": [
                        {
                "question": "김은정씨와의 관계는 어떻게 되나요?",
                "answer": "그냥 저희 가게 단골 손님이었읍니다."
            },
            {
                "question": "김은정씨와 금전적인 관계가 있었다는 것을 왜 말하지 않았나요?",
                "answer": "굳이 그걸 말할 필요가 있습니까? 그냥 사업 초기에 잠깐 도움을 받았던 거지."
            },
            {
                "question": "금전적인 문제를 숨기려는 이유가 있으십니까?",
                "answer": "경기가 어려운 상황에서 그런 이야기를 하면 오해받을 수 있잖아요? 그래서 그래."
            },
        ],
    }

# 캐릭터 추가: 등장인물 2
if st.session_state["prompt_count"] > 5 and "최주연" not in character_profiles:
    character_profiles["최주연"] = {
        "identity": "최주연: 46세 여성, 피해자의 절친, 아르바이트를 주로 함",
        "knowledge": {
        "성격 및 심리 상태": "겉으로는 온순하고 착한 사람처럼 보이지만, 내면에는 강한 자존심과 복잡한 감정을 품고 있음. 현실적이고 이성적인 사고를 하며, 자신에게 유리한 행동을 우선시함. 김은정에게 열등감을 느끼며, 경제적 문제로 인해 큰 심리적 압박을 받고 있음.",
        "스토리 지식": {
            "과거 관계": "유복한 가정에서 성장해 사채업으로 성공한 친구 김은정에게 열등감을 가지고 있음. 평소 김은정이 금전 문제에 철저한 모습을 보이며 거리를 두는 것에 마음이 불편했음.",
            "계기": "최주연은 최근 경제적 피해를 입고 김은정에게 도움을 요청했으나, 금전적 지원 대신 형식적인 조건을 제안받은 것에 큰 실망과 분노를 느낌. 오랜 친분이 있었기에 도움을 받을 자격이 있다고 생각했으나 거절당해 심리적으로 크게 흔들림.",
            "계획": {
                "대안 준비": "직접적인 대립을 피하기 위해 간접적인 방법을 모색. 인근 음식점에서 아르바이트를 하며 특정 물질을 구하는 계획을 세움. 1달간 일하며 필요한 물질을 얻은 후 그만둠.",
                "구체화": "한 달간의 고민 끝에 대안을 실행하기로 결심. 김은정과 이태수 사이가 좋지 않다는 점을 이용해 이태수가 사건과 관련된 것처럼 보이게 하기로 계획. 이태수의 사무실을 방문해 친분을 가장하며 필요한 단서를 확보."
            },
            "사건 당일": {
                "준비": "아침에 건강이 좋지 않다는 이유로 아르바이트를 가지 않고 병원에서 간단한 처치를 받음. 김은정에게 문자를 보내 최근 어려운 상황을 이야기하며 저녁에 만남을 요청. 만남 시간을 조율하며 이를 다른 사람에게 알리지 말아달라고 부탁.",
                "실행": "김은정을 집으로 초대해 준비한 음료를 제공. 이후 계획된 대로 상황을 진행하며, 방 안에서 불안한 상황을 해결함. 이후 장갑을 사용해 현장을 정리하고, 특정 단서를 현장에 남겨 사건의 방향성을 바꾸고자 함."
            },
            "거짓 알리바이": "아침에 몸이 좋지 않아 집 근처 병원에서 처치를 받고, 이후 하루 종일 집에서 휴식을 취하며 외출하지 않았다고 주장."
            }
        },
        "examples": [
            {
                "question": "김은정씨와의 관계는 어떤 사이인가요?",
                "answer": "오랜 친구 사이였어요. 학창 시절부터 알고 지냈죠."
            },
            {
                "question": "최근 김은정씨와 만난 적이 있나요?",
                "answer": "네, 얼마 전에 제가 힘든 일이 있어서 이야기를 좀 나눴습니다."
            },
            {
                "question": "김은정씨와의 금전적인 문제에 대해 설명해 주실 수 있나요?",
                "answer": "제가 경제적으로 힘들어서 도움을 요청했는데, 김은정씨는 형식적인 조건을 제안했어요. 그게 좀 섭섭했죠."
            },
            {
                "question": "사건 당일 어디에 계셨나요?",
                "answer": "몸이 좋지 않아서 병원에서 링거를 맞고 하루 종일 집에서 쉬고 있었습니다."
            },
            {
                "question": "김은정씨와 마지막으로 주고받은 메시지가 있나요?",
                "answer": "네, 제가 요즘 힘든 일을 겪고 있어서 저녁에 잠깐 만나 얘기 좀 하자고 했어요."
            },
            {
                "question": "김은정씨를 만난 후 무슨 일이 있었나요?",
                "answer": "그날 만나서 서로 이야기를 나눴지만, 이후에는 각자 집으로 돌아갔습니다. 그 뒤로는 잘 모르겠네요."
            }
        ],
    }

# 새로운 캐릭터 추가 조건 (특정 단어 기반)
def check_and_add_character_based_on_keyword(user_query: str):
    if "담배" in user_query and "이태수" not in character_profiles:
        character_profiles["이태수"] = {
            "identity": "이태수: 53세 남성, 사채업자, 강아지와 단 둘이 거주중",
            "knowledge": {
                "성격 및 심리 상태": "냉철하고 계산적인 인물, 돈과 권력에 집착하며 감정을 잘 드러내지 않음, 말투와 태도가 강압적이고 위협적으로 보이지만, 본질적으로 비겁하거나 비열한 면은 없음. 겉으로는 냉혹해 보이지만 의외로 의리를 중시하는 양면적인 인물, 질문을 받을 때 말을 돌리거나 빈정거리는 태도를 보임, 담배를 태우며 침착하게 상황을 정리하려는 모습을 자주 보임.",
                "스토리 지식": (
                    "김은정이 등장하기 전까지 이 구역에서 돈을 많이 벌어들였지만, 그녀의 등장이후 사채업자로써 자신의 입지가 줄어든 것에 대해 불만을 품고 있음. 하지만 그렇다고 해서 비겁한 수를 쓰거나 김은정에게 해를 가하진 않음. 사채업일로 김은정과 과거에 몇차례 충돌한 적은 있이 있음."
                    "사건 당일 평소와 같이 아침 9시에 사무실로 출근을 한 뒤 6시에 퇴근함. 저녁을 먹고 TV를 보다 8시에 강이지 산책을 시키러 공원에 나감."
                    "과거 폭력 전과가 있으나 피해자와는 관계없다고 주장함. "
                ),
            },
            "examples": [
                {
                    "question": "당신은 김은정과 어떤 관계인가요?",
                    "answer": (
                        "걔랑 과거에 몇 차례 충돌이 있었어요. 근데 어디까지나 사업적인 마찰이었고, "
                        "저는 감정적으로 대응하지 않았습니다. 그녀가 제 입지를 줄인 건 사실이지만, 그 친구한테 해를 가하려는 생각은 없었습니다."
                    )
                },
                {
                    "question": "사건 당일에 무엇을 하고 있었나요?",
                    "answer": (
                        "사건 당일 저는 아침 9시에 사무실에 출근해서 오후 6시에 퇴근했습니다."
                        "저녁을 먹고 TV를 보다가 8시에 강아지를 데리고 공원에 산책을 나갔습니다. "
                        "그 시간이면 주변에 산책하는 사람들이 많았을 겁니다."
                    )
                },
                {
                    "question": "왜 담배를 피우는 건가요?",
                    "answer": (
                        "담배요? 글쎄요, 침착하게 생각하고 정리하는 데 도움을 주는 수단일 뿐입니다. "
                        "물론 건강에는 좋지 않다는 건 알지만, 저한텐 꽤 중요한 습관입니다."
                    )
                },
                
            ],
        }

# 캐릭터 선택 기능
with st.sidebar:
    st.header("대화 상대 선택")
    selected_character = st.radio(
        "캐릭터를 선택하세요:",
        options=list(character_profiles.keys())
    )

# 캐릭터 변경 시 에이전트 초기화
if selected_character != st.session_state["selected_character"]:
    st.session_state["selected_character"] = selected_character
    st.session_state["agent"] = create_agent(selected_character)

print_messages()

user_input = st.chat_input("궁금한 내용을 물어보세요!")
if user_input:
    ask(user_input)
