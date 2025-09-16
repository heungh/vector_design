import streamlit as st
import boto3
import os
import yaml
import re
import json
from datetime import datetime
import asyncio
from typing import Dict, List, Optional, Tuple
import hashlib
from collections import Counter
import time
from concurrent.futures import ThreadPoolExecutor
import logging

# 설정
KNOWLEDGE_BASE_ID = ""  # 입력필요
S3_BUCKET_NAME = ""  # 입력필요
VECTOR_DIR = "vector"
SIMILARITY_THRESHOLD = 70
MAX_RETRIES = 3
BATCH_SIZE = 10

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedVectorKnowledgeApp:
    def __init__(self):
        self.bedrock_agent_client = boto3.client(
            "bedrock-agent-runtime", region_name="us-east-1"
        )
        self.bedrock_runtime_client = boto3.client(
            "bedrock-runtime", region_name="us-east-1"
        )
        # S3 클라이언트 설정 개선
        try:
            self.s3_client = boto3.client("s3", region_name="us-east-1")
            # S3 연결 테스트
            self.s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
            logger.info(f"S3 버킷 {S3_BUCKET_NAME} 연결 성공")
        except Exception as e:
            logger.error(f"S3 초기화 오류: {e}")
            self.s3_client = None

        os.makedirs(VECTOR_DIR, exist_ok=True)
        self._file_cache = {}

    def _normalize_text(self, text: str) -> str:
        """텍스트 정규화"""
        return re.sub(r"[^\w\s]", "", text.lower().strip())

    def _extract_keywords(self, content: str) -> List[str]:
        """키워드 추출 및 기본 태그 추가"""
        normalized = self._normalize_text(content)
        words = normalized.split()

        # 불용어 제거
        stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }
        words = [w for w in words if w not in stopwords and len(w) > 2]

        # 빈도 기반 키워드 선별
        word_freq = Counter(words)
        keywords = [word for word, freq in word_freq.most_common(10)]

        # 기본 태그 추가
        content_lower = content.lower()
        if any(
            term in content_lower
            for term in ["database", "db", "sql", "mysql", "postgresql"]
        ):
            keywords.append("database")
        if any(
            term in content_lower
            for term in ["performance", "optimization", "tuning", "speed"]
        ):
            keywords.append("performance")
        if any(
            term in content_lower
            for term in ["error", "troubleshoot", "debug", "fix", "issue"]
        ):
            keywords.append("troubleshooting")

        return list(set(keywords))

    def _check_content_similarity(self, new_content: str) -> Tuple[bool, Dict]:
        """콘텐츠 유사도 검사"""
        if not os.path.exists(VECTOR_DIR):
            return False, {}

        new_keywords = set(self._normalize_text(new_content).split())
        max_similarity = 0
        similar_file = None

        for filename in os.listdir(VECTOR_DIR):
            if not filename.endswith(".md"):
                continue

            filepath = os.path.join(VECTOR_DIR, filename)

            # 파일 캐싱
            if filepath not in self._file_cache:
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        self._file_cache[filepath] = f.read()
                except Exception as e:
                    logger.error(f"파일 읽기 오류 {filepath}: {e}")
                    continue

            existing_content = self._file_cache[filepath]
            existing_keywords = set(self._normalize_text(existing_content).split())

            # 유사도 계산
            if existing_keywords:
                intersection = len(new_keywords & existing_keywords)
                union = len(new_keywords | existing_keywords)
                similarity = (intersection / union) * 100 if union > 0 else 0

                if similarity > max_similarity:
                    max_similarity = similarity
                    similar_file = filename

        is_similar = max_similarity >= SIMILARITY_THRESHOLD
        return is_similar, {
            "max_similarity": max_similarity,
            "similar_file": similar_file,
            "threshold": SIMILARITY_THRESHOLD,
        }

    async def _analyze_content_conflicts(
        self, new_content: str, existing_content: str
    ) -> Tuple[bool, str]:
        """Claude를 사용한 콘텐츠 충돌 분석"""
        prompt = f"""
다음 두 콘텐츠를 비교하여 실제 충돌이나 모순이 있는지 분석해주세요:

기존 콘텐츠:
{existing_content[:1000]}

새 콘텐츠:
{new_content[:1000]}

분석 결과를 다음 형식으로 답변해주세요:
CONFLICT: [YES/NO]
REASON: [충돌 이유 또는 보완 관계 설명]
"""

        try:
            response = self.bedrock_runtime_client.invoke_model(
                modelId="anthropic.claude-3-sonnet-20240229-v1:0",
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 500,
                        "messages": [{"role": "user", "content": prompt}],
                    }
                ),
            )

            result = json.loads(response["body"].read())
            analysis = result["content"][0]["text"]

            has_conflict = "CONFLICT: YES" in analysis
            return has_conflict, analysis

        except Exception as e:
            logger.error(f"충돌 분석 오류: {e}")
            return False, "분석 실패"

    def _retry_operation(self, operation, *args, **kwargs):
        """재시도 메커니즘"""
        for attempt in range(MAX_RETRIES):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise e
                logger.warning(f"재시도 {attempt + 1}/{MAX_RETRIES}: {e}")
                time.sleep(2**attempt)

    def _batch_s3_upload(self, files: List[Tuple[str, str]]) -> List[bool]:
        """배치 S3 업로드"""
        results = []

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for local_path, s3_key in files:
                future = executor.submit(self._upload_to_s3, local_path, s3_key)
                futures.append(future)

            for future in futures:
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    logger.error(f"배치 업로드 오류: {e}")
                    results.append(False)

        return results

    def _upload_to_s3(self, local_path: str, s3_key: str) -> bool:
        """S3 업로드 with 재시도"""
        if not self.s3_client:
            logger.error("S3 클라이언트가 초기화되지 않음")
            return False

        try:
            logger.info(
                f"S3 업로드 시도: {local_path} -> s3://{S3_BUCKET_NAME}/{s3_key}"
            )

            # 파일 존재 확인
            if not os.path.exists(local_path):
                logger.error(f"로컬 파일이 존재하지 않음: {local_path}")
                return False

            self._retry_operation(
                self.s3_client.upload_file, local_path, S3_BUCKET_NAME, s3_key
            )
            logger.info(f"S3 업로드 성공: {s3_key}")
            return True
        except Exception as e:
            logger.error(f"S3 업로드 실패 {s3_key}: {e}")
            return False

    async def save_to_vector_store(
        self,
        content: str,
        topic: str,
        category: str = "examples",
        tags: List[str] = None,
        force_save: bool = False,
    ) -> Dict:
        """향상된 벡터 저장소 저장"""
        try:
            # 1. force_save가 아닌 경우 중복/충돌 검사
            if not force_save:
                is_similar, similarity_info = self._check_content_similarity(content)

                if is_similar:
                    # 유사한 파일이 있으면 충돌 분석
                    similar_filepath = os.path.join(
                        VECTOR_DIR, similarity_info["similar_file"]
                    )
                    with open(similar_filepath, "r", encoding="utf-8") as f:
                        existing_content = f.read()

                    has_conflict, analysis = await self._analyze_content_conflicts(
                        content, existing_content
                    )

                    if has_conflict:
                        return {
                            "success": False,
                            "message": "콘텐츠 충돌 감지",
                            "similarity_info": similarity_info,
                            "conflict_analysis": analysis,
                        }

            # 2. 키워드 추출 및 메타데이터 생성
            keywords = self._extract_keywords(content)
            if tags:
                keywords.extend(tags)
            keywords = list(set(keywords))

            # 3. 파일 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{topic}.md"
            filepath = os.path.join(VECTOR_DIR, filename)

            metadata = {
                "title": topic,
                "category": category,
                "tags": keywords,
                "version": 1,
                "last_updated": datetime.now().isoformat(),
                "author": "DB Assistant",
                "source": "conversation",
                "similarity_check": similarity_info if not force_save else None,
            }

            # YAML 헤더 + 콘텐츠
            file_content = (
                f"---\n{yaml.dump(metadata, default_flow_style=False)}---\n\n{content}"
            )

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(file_content)

            # 4. S3 업로드 (배치 처리)
            s3_key = f"{category}/{filename}"
            upload_success = self._upload_to_s3(filepath, s3_key)

            return {
                "success": True,
                "message": "저장 완료",
                "filename": filename,
                "filepath": filepath,
                "s3_uploaded": upload_success,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"저장 오류: {e}")
            return {"success": False, "message": f"저장 실패: {str(e)}"}

    def update_vector_content(
        self, filename: str, new_content: str, update_mode: str = "append"
    ) -> Dict:
        """콘텐츠 업데이트"""
        filepath = os.path.join(VECTOR_DIR, filename)

        if not os.path.exists(filepath):
            return {"success": False, "message": "파일을 찾을 수 없습니다"}

        try:
            # 기존 파일 읽기
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # YAML 헤더 분리
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    yaml_header = parts[1]
                    existing_content = parts[2].strip()
                    metadata = yaml.safe_load(yaml_header)
                else:
                    metadata = {}
                    existing_content = content
            else:
                metadata = {}
                existing_content = content

            # 콘텐츠 업데이트
            if update_mode == "append":
                updated_content = existing_content + "\n\n" + new_content
            else:  # replace
                updated_content = new_content

            # 메타데이터 업데이트
            metadata["last_updated"] = datetime.now().isoformat()
            metadata["version"] = metadata.get("version", 1) + 1

            # 파일 저장
            file_content = f"---\n{yaml.dump(metadata, default_flow_style=False)}---\n\n{updated_content}"

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(file_content)

            # S3 업로드
            category = metadata.get("category", "examples")
            s3_key = f"{category}/{filename}"
            upload_success = self._upload_to_s3(filepath, s3_key)

            return {
                "success": True,
                "message": "업데이트 완료",
                "filename": filename,
                "s3_uploaded": upload_success,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"업데이트 오류: {e}")
            return {"success": False, "message": f"업데이트 실패: {str(e)}"}

    def query_vector_store(self, query: str, max_results: int = 5) -> str:
        """향상된 벡터 검색"""
        try:
            response = self._retry_operation(
                self.bedrock_agent_client.retrieve,
                knowledgeBaseId=KNOWLEDGE_BASE_ID,
                retrievalQuery={"text": query},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {"numberOfResults": max_results}
                },
            )

            if not response.get("retrievalResults"):
                return "🔍 검색 결과가 없습니다."

            results = []
            for i, result in enumerate(response["retrievalResults"], 1):
                content = result["content"]["text"]
                score = result.get("score", 0)
                metadata = result.get("metadata", {})
                source = metadata.get("x-amz-bedrock-kb-source-uri", "알 수 없음")

                results.append(
                    f"""
**결과 {i}** (점수: {score:.3f})
📄 출처: {source}
📝 내용: {content[:500]}{'...' if len(content) > 500 else ''}
---
"""
                )
            return "\n".join(results)

        except Exception as e:
            logger.error(f"검색 오류: {e}")
            return f"❌ 검색 실패: {str(e)}"

    def sync_knowledge_base(self) -> Dict:
        """Knowledge Base 동기화"""
        try:
            bedrock_agent = boto3.client("bedrock-agent", region_name="us-east-1")

            # 데이터 소스 조회
            kb_response = bedrock_agent.get_knowledge_base(
                knowledgeBaseId=KNOWLEDGE_BASE_ID
            )
            data_source_id = None

            # 첫 번째 데이터 소스 사용
            ds_response = bedrock_agent.list_data_sources(
                knowledgeBaseId=KNOWLEDGE_BASE_ID
            )
            if ds_response.get("dataSourceSummaries"):
                data_source_id = ds_response["dataSourceSummaries"][0]["dataSourceId"]

            if not data_source_id:
                return {"success": False, "message": "데이터 소스를 찾을 수 없습니다"}

            # 동기화 작업 시작
            sync_response = bedrock_agent.start_ingestion_job(
                knowledgeBaseId=KNOWLEDGE_BASE_ID, dataSourceId=data_source_id
            )

            job_id = sync_response["ingestionJob"]["ingestionJobId"]
            status = sync_response["ingestionJob"]["status"]

            return {
                "success": True,
                "message": f"동기화 시작됨 (Job ID: {job_id})",
                "job_id": job_id,
                "status": status,
            }

        except Exception as e:
            logger.error(f"동기화 오류: {e}")
            return {"success": False, "message": f"동기화 실패: {str(e)}"}

    async def chat_with_claude(
        self,
        message: str,
        include_vector_search: bool = True,
        chat_history: List = None,
    ) -> Tuple[str, List]:
        """Claude와 채팅 (벡터 검색 결과 포함)"""
        try:
            context = ""
            if include_vector_search:
                search_results = self.query_vector_store(message, max_results=3)
                context = f"\n\n참고 자료:\n{search_results}\n\n"

            # 채팅 히스토리 구성
            messages = []
            if chat_history:
                messages.extend(chat_history)

            user_message = f"{context}질문: {message}"
            messages.append({"role": "user", "content": user_message})

            # Claude 4 시도
            try:
                response = self.bedrock_runtime_client.invoke_model(
                    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                    body=json.dumps(
                        {
                            "anthropic_version": "bedrock-2023-05-31",
                            "max_tokens": 2000,
                            "messages": messages,
                        }
                    ),
                )
            except:
                # Fallback to Claude 3.7
                response = self.bedrock_runtime_client.invoke_model(
                    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
                    body=json.dumps(
                        {
                            "anthropic_version": "bedrock-2023-05-31",
                            "max_tokens": 2000,
                            "messages": messages,
                        }
                    ),
                )

            result = json.loads(response["body"].read())
            assistant_response = result["content"][0]["text"]

            # 히스토리 업데이트
            messages.append({"role": "assistant", "content": assistant_response})

            return assistant_response, messages

        except Exception as e:
            logger.error(f"채팅 오류: {e}")
            return f"❌ 채팅 실패: {str(e)}", chat_history or []


def main():
    st.set_page_config(
        page_title="Enhanced Vector Knowledge Base", page_icon="🧠", layout="wide"
    )

    st.title("🧠 Enhanced Vector Knowledge Base with AI Chat")
    st.markdown("향상된 벡터 검색, AI 채팅, 스마트 업로드 기능")

    app = EnhancedVectorKnowledgeApp()

    # 사이드바 설정
    st.sidebar.title("⚙️ 설정")
    mode = st.sidebar.selectbox(
        "모드 선택", ["🔍 검색", "💬 AI 채팅", "📤 업로드", "🔄 동기화"]
    )

    if mode == "🔍 검색":
        st.header("🔍 벡터 검색")

        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_input(
                "검색어를 입력하세요:", placeholder="예: 데이터베이스 성능 최적화"
            )
        with col2:
            max_results = st.number_input(
                "최대 결과 수", min_value=1, max_value=20, value=5
            )

        if st.button("🔍 검색", type="primary"):
            if query:
                with st.spinner("검색 중..."):
                    results = app.query_vector_store(query, max_results)
                st.markdown("### 검색 결과")
                st.markdown(results)
            else:
                st.warning("검색어를 입력해주세요.")

    elif mode == "💬 AI 채팅":
        st.header("💬 AI 채팅")

        # 채팅 히스토리 초기화
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        # 설정
        include_search = st.checkbox("벡터 검색 결과 포함", value=True)

        # 채팅 히스토리 표시
        for i, msg in enumerate(st.session_state.chat_history):
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            else:
                st.chat_message("assistant").write(msg["content"])

        # 새 메시지 입력
        if prompt := st.chat_input("Claude에게 질문하세요..."):
            st.chat_message("user").write(prompt)

            with st.spinner("Claude가 답변 중..."):
                response, updated_history = asyncio.run(
                    app.chat_with_claude(
                        prompt, include_search, st.session_state.chat_history
                    )
                )

            st.chat_message("assistant").write(response)
            st.session_state.chat_history = updated_history

        # 히스토리 초기화 버튼
        if st.button("🗑️ 채팅 히스토리 초기화"):
            st.session_state.chat_history = []
            st.rerun()

    elif mode == "📤 업로드":
        st.header("📤 스마트 문서 업로드")

        # 업로드 방식 선택
        upload_type = st.radio("업로드 방식", ["📁 파일 업로드", "✏️ 직접 입력"])

        content = ""
        if upload_type == "📁 파일 업로드":
            uploaded_file = st.file_uploader("텍스트 파일 선택", type=["txt", "md"])
            if uploaded_file:
                content = uploaded_file.read().decode("utf-8")
                st.text_area("파일 내용 미리보기", content, height=200, disabled=True)
        else:
            content = st.text_area("내용을 입력하세요:", height=300)

        if content:
            col1, col2 = st.columns(2)
            with col1:
                topic = st.text_input("주제 (10자 이내)", max_chars=10)
                category = st.selectbox(
                    "카테고리",
                    [
                        "database-standards",
                        "performance-optimization",
                        "troubleshooting",
                        "examples",
                    ],
                )
            with col2:
                tags_input = st.text_input(
                    "태그 (쉼표로 구분)", placeholder="sql, optimization, mysql"
                )
                force_save = st.checkbox(
                    "중복 검사 건너뛰기", help="유사한 내용이 있어도 강제로 저장"
                )

            tags = (
                [tag.strip() for tag in tags_input.split(",") if tag.strip()]
                if tags_input
                else []
            )

            if st.button("💾 저장", type="primary"):
                if topic:
                    with st.spinner("저장 중... (유사도 검사 및 충돌 분석 포함)"):
                        result = asyncio.run(
                            app.save_to_vector_store(
                                content, topic, category, tags, force_save
                            )
                        )

                    if result["success"]:
                        st.success(f"✅ {result['message']}")
                        st.json(result["metadata"])
                        if not result.get("s3_uploaded"):
                            st.warning("⚠️ S3 업로드 실패 - 로컬에만 저장됨")
                    else:
                        st.error(f"❌ {result['message']}")
                        if "similarity_info" in result:
                            st.warning(
                                f"유사한 파일: {result['similarity_info']['similar_file']} "
                                f"(유사도: {result['similarity_info']['max_similarity']:.1f}%)"
                            )
                        if "conflict_analysis" in result:
                            st.text_area(
                                "충돌 분석 결과",
                                result["conflict_analysis"],
                                height=150,
                            )
                else:
                    st.warning("주제를 입력해주세요.")

    elif mode == "🔄 동기화":
        st.header("🔄 Knowledge Base 동기화")
        st.markdown("S3의 최신 파일들을 Knowledge Base에 동기화합니다.")

        if st.button("🔄 동기화 시작", type="primary"):
            with st.spinner("동기화 중..."):
                result = app.sync_knowledge_base()

            if result["success"]:
                st.success(f"✅ {result['message']}")
                st.info(f"상태: {result.get('status', 'Unknown')}")
            else:
                st.error(f"❌ {result['message']}")

    # 성능 모니터링 사이드바
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📊 시스템 상태")

        # 캐시 상태
        cache_size = len(app._file_cache)
        st.metric("파일 캐시", f"{cache_size}개")

        # 로컬 파일 수
        if os.path.exists(VECTOR_DIR):
            local_files = len([f for f in os.listdir(VECTOR_DIR) if f.endswith(".md")])
            st.metric("로컬 파일", f"{local_files}개")

        if st.button("🗑️ 캐시 초기화"):
            app._file_cache.clear()
            st.success("캐시가 초기화되었습니다.")


if __name__ == "__main__":
    main()
