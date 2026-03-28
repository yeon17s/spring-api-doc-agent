### Spring Boot API 문서 변환 에이전트

Spring Boot Controller 소스코드(.java)를 입력하면 OpenAPI 3.0 YAML 문서를 자동으로 생성하는 LangGraph 기반 에이전트입니다.

---

### 프로젝트 구조

```
spring-api-doc-agent/
├── app.py          # 진입점 — 파일 경로 및 문서 정보 입력
├── agents.py       # LangGraph 에이전트 정의 및 시스템 프롬프트
├── tools.py        # 파싱·변환·저장 도구 모음
├── models.py       # Pydantic 데이터 모델
├── mock_db.py      # 도구 간 데이터 공유 저장소
└── requirements.txt
```

---

### 동작 흐름

```
.java 파일 경로 입력
      ↓
read_java_file       — 파일 읽기
      ↓
build_controller_spec — @RequestMapping / @GetMapping 등 파싱
      ↓
generate_openapi_yaml — OpenAPI 3.0 YAML 문자열 생성
      ↓
save_yaml_file        — {컨트롤러명}.yaml 저장
```

---

### 지원 범위

| 항목 | 지원 목록 |
|------|-----------|
| HTTP 메서드 | `@GetMapping` `@PostMapping` `@PutMapping` `@DeleteMapping` `@PatchMapping` |
| 파라미터 | `@PathVariable` `@RequestParam` `@RequestBody` |
| 반환 타입 | `ResponseEntity<T>` 에서 T 자동 추출 |

---

### 실행 방법

```bash
# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 실행
python app.py
```

실행하면 아래 순서로 입력을 받습니다.

```
Java 파일 경로를 입력하세요: UserController.java
API 문서 제목을 입력하세요 (엔터: 컨트롤러 이름 자동 사용):
API 버전을 입력하세요 (엔터: 1.0.0):
```

또는 파일 경로를 인자로 바로 전달할 수 있습니다.

```bash
python app.py UserController.java
```

---

### 실행 결과

`UserController.java` 입력 시 `UserController.yaml` 생성:

```yaml
openapi: 3.0.0
info:
  title: UserController
  version: 1.0.0
paths:
  /api/users/{id}:
    get:
      summary: getUser
      parameters:
      - name: id
        in: path
        required: true
        schema:
          type: integer
      responses:
        '200':
          description: 성공
          content:
            application/json:
              schema:
                type: object
  /api/users:
    post:
      summary: createUser
      parameters: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
      responses:
        '200':
          description: 성공
          content:
            application/json:
              schema:
                type: object
```

---

### 환경 변수

`.env` 파일에 Groq API 키를 설정합니다.

```
GROQ_API_KEY=your_api_key_here
```
