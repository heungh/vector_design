# Vector Knowledge Base Streamlit App

벡터 저장소(Knowledge Base)에서 검색하고 새로운 문서를 업로드할 수 있는 Streamlit 웹 애플리케이션입니다.

## 기능

- 🔍 **벡터 검색**: 자연어로 Knowledge Base에서 관련 문서 검색
- 📤 **문서 업로드**: 텍스트 파일 업로드 또는 직접 입력으로 새로운 지식 추가
- 💾 **자동 저장**: 로컬 디렉토리, S3 버킷, Knowledge Base에 자동 동기화

## 설치 및 실행

1. 의존성 설치:
```bash
pip install -r requirements.txt
```

2. AWS 자격 증명 설정 (AWS CLI 또는 환경 변수)

3. 애플리케이션 실행:
```bash
streamlit run vector_knowledge_app.py
```

## 설정

`vector_knowledge_app.py` 파일에서 다음 설정을 확인/수정하세요:

- `KNOWLEDGE_BASE_ID`: Knowledge Base ID
- `S3_BUCKET_NAME`: S3 버킷명
- `VECTOR_DIR`: 로컬 저장 디렉토리

## 사용법

### 검색 모드
- 검색어를 입력하고 최대 결과 수를 설정
- 자연어로 질문 (예: "데이터베이스 성능 최적화 방법")

### 업로드 모드
- 파일 업로드 또는 텍스트 직접 입력
- 주제, 카테고리, 태그 설정
- 저장 시 자동으로 로컬/S3/Knowledge Base에 동기화
