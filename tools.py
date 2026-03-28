"""
Spring Boot API 문서 변환 에이전트 도구
"""
from langchain_core.tools import tool
from models import ClassLevel, MethodLevel, ParameterLevel, ControllerSpec, ParameterType, HttpMethod
from mock_db import get_store
from typing import Optional
import re
import yaml
import os


@tool
def read_java_file(file_path: str) -> str:
    """
    Java 소스 파일을 읽어 문자열로 반환합니다.

    Args:
        file_path: 읽을 Java 파일의 경로 (절대 경로 또는 상대 경로)

    Returns:
        str: 파일 내용
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


JAVA_TYPE_MAP = {
    "String": "string",
    "Long": "integer",
    "long": "integer",
    "Integer": "integer",
    "int": "integer",
    "Boolean": "boolean",
    "boolean": "boolean",
    "Double": "number",
    "double": "number",
    "Float": "number",
    "float": "number",
    "List": "array",
    "void": "null",
}


def _parse_class_level(
    source_code: str,
) -> ClassLevel:
    # Controller 이름 추출
    class_match = re.search(r"public\s+class\s+(\w+)", source_code)
    controller = class_match.group(1) if class_match else ""

    # Base Path 추출
    path_match = re.search(r'@RequestMapping\((?:value\s*=\s*)?["\']([^"\']+)["\']', source_code)
    base_path = path_match.group(1) if path_match else "/"

    return ClassLevel(
        controller=controller,
        base_path=base_path
    )


def _parse_method_level(
    source_code: str,
    base_path: str = "",
) -> list[MethodLevel]:
    methods = []

    annotation_pattern = re.compile(
        r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)'
        r'(?:\((?:value\s*=\s*)?["\']([^"\']*)["\']\s*\))?\s*\n'
        r'\s*public\s+(\S+)\s+(\w+)\s*\(([^)]*)\)',
        re.MULTILINE
    )

    for match in annotation_pattern.finditer(source_code):
        http_verb = match.group(1).replace("Mapping", "").upper()
        detail_path = match.group(2) or ""
        return_type_raw = match.group(3)
        java_method = match.group(4)
        params_str = match.group(5)

        # ResponseEntity<T>에서 T 추출
        re_match = re.search(r'ResponseEntity<(.+)>', return_type_raw)
        return_type = re_match.group(1) if re_match else return_type_raw

        if detail_path:
            full_path = base_path.rstrip("/") + "/" + detail_path.lstrip("/")
        else:
            full_path = base_path

        parameters = _parse_parameter_level(params_str)

        methods.append(MethodLevel(
            http_method=HttpMethod[http_verb],
            base_path=base_path,
            detail_path=detail_path,
            full_path=full_path,
            java_method=java_method,
            return_type=return_type,
            parameters=parameters,
        ))

    return methods


def _parse_parameter_level(
    method_source: str,
) -> list[ParameterLevel]:
    parameters = []

    # @PathVariable Long id  /  @PathVariable(value = "id") Long id
    for match in re.finditer(
        r'@PathVariable(?:\((?:value\s*=\s*)?["\'](\w+)["\']\))?\s+(\w+)\s+(\w+)',
        method_source
    ):
        param_name = match.group(1) or match.group(3)  # value 명시 or 변수명
        parameters.append(ParameterLevel(
            parameter_type=ParameterType.PATH,
            parameter_name=param_name,
            java_type=match.group(2),
            required=True,          # PathVariable은 항상 필수
            default_value=None,
        ))

    # @RequestParam(required=false, defaultValue="0") int page
    for match in re.finditer(
        r'@RequestParam(?:\(([^)]*)\))?\s+(\w+)\s+(\w+)',
        method_source
    ):
        options = match.group(1) or ""
        required = "required=false" not in options.replace(" ", "")
        default_match = re.search(r'defaultValue\s*=\s*["\']([^"\']+)["\']', options)
        default_value = default_match.group(1) if default_match else None

        parameters.append(ParameterLevel(
            parameter_type=ParameterType.QUERY,
            parameter_name=match.group(3),
            java_type=match.group(2),
            required=required,
            default_value=default_value,
        ))

    # @RequestBody UserCreateRequest req
    body_match = re.search(r'@RequestBody\s+(\w+)\s+(\w+)', method_source)
    if body_match:
        parameters.append(ParameterLevel(
            parameter_type=ParameterType.BODY,
            parameter_name=body_match.group(2),
            java_type=body_match.group(1),
            required=True,
            default_value=None,
        ))

    return parameters


@tool
def parse_class_level(
    source_code: str
) -> ClassLevel:
    """
    Spring Boot Controller 클래스 레벨 정보를 파싱합니다.
    @RestController, @RequestMapping 어노테이션에서 정보를 추출합니다.

    Args:
        source_code: Spring Boot Controller 소스코드 전문

    Returns:
        ClassLevel: base_path와 controller 이름 정보
    """
    return _parse_class_level(source_code)


@tool
def parse_method_level(
    source_code: str,
) -> list[MethodLevel]:
    """
    Spring Boot Controller 메서드 레벨 정보를 파싱합니다.
    @GetMapping, @PostMapping 어노테이션에서 엔드포인트 정보를 추출합니다.

    Args:
        source_code: Spring Boot Controller 소스코드 전문

    Returns:
        list[MethodLevel]: 엔드포인트 목록
    """
    return _parse_method_level(source_code)

@tool
def parse_parameter_level(
    method_source: str,
) -> list[ParameterLevel]:
    """
    단일 메서드의 파라미터 정보를 파싱합니다.
    @PathVariable, @RequestParam, @RequestBody 어노테이션에서 정보를 추출합니다.

    Args:
        method_source: 단일 메서드 소스코드

    Returns:
        list[ParameterLevel: 파라미터 목록
    """
    return _parse_parameter_level(method_source)

@tool
def build_controller_spec(
    source_code: str,
) -> str:
    """
    소스코드 전체를 분석해 ControllerSpec를 완성하고 내부 저장소에 저장합니다.
    parse_class_level, parse_method_level, parse_parameter_level을 순서대로 호출합니다.

    Args:
        source_code: Spring Boot Controller 소스코드 전문

    Returns:
        str: 파싱된 메서드 수와 컨트롤러 이름 요약
    """
    class_info = _parse_class_level(source_code)
    methods = _parse_method_level(source_code, base_path=class_info.base_path)

    spec = ControllerSpec(
        class_info=class_info,
        methods=methods,
    )

    get_store()["build_controller_spec"] = spec

    return f"{class_info.controller}: {len(methods)}개 메서드 파싱 완료 ({', '.join(m.java_method for m in methods)})"


@tool
def generate_openapi_yaml(
    title: Optional[str] = "API 문서",
    version: Optional[str] = "1.0.0"
) -> str:
    """
    build_controller_spec으로 저장된 ControllerSpec을 OpenAPI 3.0 YAML 문자열로 변환합니다.
    반드시 build_controller_spec을 먼저 호출한 후 사용하세요.

    Args:
        title: API 문서 제목 (기본값: "API 문서"),
        version: API 버전 (기본값: "1.0.0")

    Returns:
        str: OpenAPI 3.0 YAML 문자열
    """
    spec: ControllerSpec = get_store().get("build_controller_spec")
    if spec is None:
        raise RuntimeError("build_controller_spec을 먼저 호출하세요.")

    resolved_title = title or spec.class_info.controller

    openapi_dict = {
        "openapi": "3.0.0",
        "info": {
            "title": resolved_title,
            "version": version,
        },
        "paths": {}
    }

    for method in spec.methods:
        path = method.full_path
        http = method.http_method.value.lower()

        if path not in openapi_dict["paths"]:
            openapi_dict["paths"][path] = {}

        parameters = []
        request_body = None

        for param in method.parameters:
            if param.parameter_type == ParameterType.BODY:
                request_body = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": JAVA_TYPE_MAP.get(param.java_type, "object")
                            }
                        }
                    }
                }
            else:
                param_dict = {
                    "name": param.parameter_name,
                    "in": param.parameter_type.value,
                    "required": param.required,
                    "schema": {
                        "type": JAVA_TYPE_MAP.get(param.java_type, "string")
                    }
                }
                if param.default_value is not None:
                    param_dict["schema"]["default"] = param.default_value
                parameters.append(param_dict)

        operation = {"summary": method.java_method, "parameters": parameters}
        if request_body is not None:
            operation["requestBody"] = request_body
        operation["responses"] = {
            "200": {
                "description": "성공",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": JAVA_TYPE_MAP.get(method.return_type, "object"),
                        }
                    }
                }
            }
        }

        openapi_dict["paths"][path][http] = operation

    return yaml.dump(openapi_dict, allow_unicode=True, sort_keys=False)


@tool
def save_yaml_file(
    yaml_content: str,
    output_path: Optional[str] = None,
) -> str:
    """
    생성된 YAML 문자열을 파일로 저장합니다.
    output_path를 지정하지 않으면 컨트롤러 이름을 파일명으로 사용합니다. (예: UserController.yaml)

    Args:
        yaml_content: OpenAPI YAML 문자열
        output_path: 저장할 파일 경로 (기본값: "{컨트롤러명}.yaml")

    Returns:
        str: 저장된 파일 경로
    """
    if output_path is None:
        spec: ControllerSpec = get_store().get("build_controller_spec")
        controller_name = spec.class_info.controller if spec else "openapi"
        output_path = f"{controller_name}.yaml"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    return output_path
