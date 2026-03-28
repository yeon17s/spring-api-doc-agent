import sys
from agents import get_spring_api_doc_agent

from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

model = ChatGroq(
    model="openai/gpt-oss-20b",
)

api_doc_agent = get_spring_api_doc_agent(model)

file_path = sys.argv[1] if len(sys.argv) > 1 else input("Java 파일 경로를 입력하세요: ")
title = input("API 문서 제목을 입력하세요 (엔터: 컨트롤러 이름 자동 사용): ").strip() or None
version = input("API 버전을 입력하세요 (엔터: 1.0.0): ").strip() or "1.0.0"

message = f"파일 경로: {file_path}\ntitle: {title or '(컨트롤러 이름 자동 사용)'}\nversion: {version}"

result = api_doc_agent.invoke({
    "messages": [
        {
            "role": "user",
            "content": message
        }
    ]
})

print(result)
print(result['messages'][-1].content)
