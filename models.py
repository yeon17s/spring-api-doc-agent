"""
Spring Boot의 API를 문서 변환하는 에이전트의 데이터 모델
"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"

class ParameterType(str, Enum):
    PATH = "path"
    QUERY = "query"
    BODY = "body"


class ClassLevel(BaseModel):
    controller: str = Field(description="Controller 클래스 이름 (예: UserController)")
    base_path: str = Field(description="클래스에 선언된 기본 경로 (예: /api/users)")

class ParameterLevel(BaseModel):
    parameter_type: ParameterType = Field(description="파라미터 종류 (path / query / body)")
    parameter_name: str = Field(description="파라미터 변수명 (예: id)")
    java_type: str = Field(description="Java 타입 (예: Long, String, List<UserDto>)")
    required: bool = Field(default=True, description="필수 여부")
    default_value: Optional[str] = Field(default=None, description="기본값 (없으면 None)")

class MethodLevel(BaseModel):
    http_method: HttpMethod = Field(description="HTTP 메서드 (GET / POST 등)")
    base_path: str = Field(description="클래스 레벨 기본 경로 (예: /api/users)")
    detail_path: str = Field(description="메서드 레벨 세부 경로 (예: /{id})")
    full_path: str = Field(description="전체 경로 = base_path + detail_path (예: /api/users/{id})")
    java_method: str = Field(description="Java 메서드명 (예: getUser)")
    return_type: str = Field(description="응답 타입 (ResponseEntity<T>에서 T 추출, 예: UserDto)")
    parameters: list[ParameterLevel] = Field(default_factory=list, description="파라미터 목록")

class ControllerSpec(BaseModel):
    class_info: ClassLevel = Field(description="클래스 레벨 정보")
    methods: list[MethodLevel] = Field(default_factory=list, description="엔드포인트 목록")
