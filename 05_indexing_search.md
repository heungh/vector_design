# 인덱싱 및 검색 최적화 다이어그램

## 1. 다중 인덱스 전략

```mermaid
graph TB
    A[문서 데이터] --> B[인덱싱 엔진<br/>🔧 Multi-Index Builder]
    
    B --> C[벡터 인덱스<br/>🔢 HNSW Algorithm]
    B --> D[메타데이터 인덱스<br/>🏷️ B-Tree Structure]
    B --> E[전문 검색 인덱스<br/>📝 GIN Index]
    B --> F[복합 인덱스<br/>🔗 Composite Keys]
    
    C --> G[유사도 검색<br/>⚡ < 10ms]
    D --> H[필터링<br/>⚡ < 5ms]
    E --> I[키워드 검색<br/>⚡ < 20ms]
    F --> J[복합 조건<br/>⚡ < 15ms]
    
    G --> K[통합 검색 결과<br/>🎯 Hybrid Ranking]
    H --> K
    I --> K
    J --> K
    
    style A fill:#e3f2fd
    style B fill:#f3e5f5
    style K fill:#4caf50
```

## 2. HNSW 벡터 인덱스 구조

```mermaid
graph TD
    subgraph "Layer 2 (최상위)"
        A1[Node A] --- A2[Node B]
        A2 --- A3[Node C]
    end
    
    subgraph "Layer 1 (중간층)"
        B1[Node A] --- B2[Node B]
        B2 --- B3[Node C]
        B1 --- B4[Node D]
        B3 --- B5[Node E]
        B4 --- B5
    end
    
    subgraph "Layer 0 (기본층)"
        C1[Node A] --- C2[Node B]
        C2 --- C3[Node C]
        C1 --- C4[Node D]
        C3 --- C5[Node E]
        C4 --- C5
        C2 --- C6[Node F]
        C5 --- C7[Node G]
        C6 --- C7
    end
    
    A1 -.-> B1
    A2 -.-> B2
    A3 -.-> B3
    
    B1 -.-> C1
    B2 -.-> C2
    B3 -.-> C3
    B4 -.-> C4
    B5 -.-> C5
    
    D[검색 쿼리<br/>🔍 Query Vector] --> A1
    
    style D fill:#e3f2fd
    style A1 fill:#4caf50
    style B1 fill:#8bc34a
    style C1 fill:#cddc39
```

## 3. 적응형 검색 (Adaptive Search) 프로세스

```mermaid
flowchart TD
    A[사용자 쿼리<br/>🔍 "MySQL 성능 최적화"] --> B[쿼리 분석<br/>🧠 Intent Classification]
    
    B --> C[벡터 검색<br/>🔢 Semantic Similarity]
    B --> D[키워드 검색<br/>📝 Exact Match]
    B --> E[메타데이터 필터<br/>🏷️ Category Filter]
    
    C --> F[벡터 스코어<br/>📊 0.85]
    D --> G[키워드 스코어<br/>📊 0.92]
    E --> H[메타데이터 스코어<br/>📊 0.78]
    
    F --> I[하이브리드 스코어링<br/>🎯 Weighted Combination]
    G --> I
    H --> I
    
    I --> J[신선도 보정<br/>📅 Freshness Boost]
    I --> K[사용빈도 보정<br/>📈 Usage Boost]
    I --> L[품질 보정<br/>⭐ Quality Boost]
    
    J --> M[최종 랭킹<br/>🏆 Final Score]
    K --> M
    L --> M
    
    M --> N[결과 반환<br/>✅ Top-K Results]
    
    style A fill:#e3f2fd
    style B fill:#f3e5f5
    style I fill:#fff3e0
    style M fill:#e8f5e8
    style N fill:#4caf50
```

## 4. 캐싱 전략 아키텍처

```mermaid
graph TB
    A[사용자 요청] --> B{캐시 확인<br/>🔍 Cache Lookup}
    
    B -->|Hit| C[캐시에서 반환<br/>⚡ < 1ms]
    B -->|Miss| D[검색 엔진<br/>🔍 Search Engine]
    
    D --> E[쿼리 캐시<br/>💾 LRU Cache<br/>TTL: 1시간]
    D --> F[임베딩 캐시<br/>💾 Redis<br/>TTL: 24시간]
    D --> G[메타데이터 캐시<br/>💾 Memory<br/>Write-Through]
    
    E --> H[결과 저장<br/>💾 Cache Update]
    F --> H
    G --> H
    
    H --> I[사용자에게 반환<br/>📤 Response]
    C --> I
    
    subgraph "캐시 계층"
        J[L1: 메모리 캐시<br/>⚡ 초고속 접근]
        K[L2: Redis 캐시<br/>🔄 분산 캐시]
        L[L3: 디스크 캐시<br/>💾 영구 저장]
    end
    
    E -.-> J
    F -.-> K
    G -.-> L
    
    style A fill:#e3f2fd
    style C fill:#4caf50
    style D fill:#f3e5f5
    style I fill:#4caf50
```

## 5. 검색 성능 최적화 파이프라인

```mermaid
graph LR
    A[원시 쿼리<br/>📝 Raw Query] --> B[전처리<br/>🧹 Preprocessing]
    
    B --> C[쿼리 확장<br/>📈 Query Expansion]
    C --> D[동의어 처리<br/>🔄 Synonym Handling]
    D --> E[오타 수정<br/>✏️ Spell Correction]
    
    E --> F[병렬 검색<br/>⚡ Parallel Search]
    
    F --> G[벡터 검색<br/>🔢 Vector Search]
    F --> H[텍스트 검색<br/>📝 Text Search]
    F --> I[필터 검색<br/>🏷️ Filter Search]
    
    G --> J[결과 병합<br/>🔗 Result Fusion]
    H --> J
    I --> J
    
    J --> K[재랭킹<br/>📊 Re-ranking]
    K --> L[결과 반환<br/>✅ Final Results]
    
    style A fill:#e3f2fd
    style F fill:#fff3e0
    style J fill:#e8f5e8
    style L fill:#4caf50
```

## 6. 인덱스 성능 모니터링

```mermaid
graph TD
    A[인덱스 모니터링<br/>📊 Performance Monitor] --> B[검색 지연시간<br/>⏱️ Query Latency]
    A --> C[인덱스 크기<br/>💾 Index Size]
    A --> D[메모리 사용량<br/>🧠 Memory Usage]
    A --> E[캐시 적중률<br/>🎯 Cache Hit Rate]
    
    B --> F{성능 임계값<br/>⚠️ Threshold Check}
    C --> F
    D --> F
    E --> F
    
    F -->|정상| G[모니터링 계속<br/>✅ Continue Monitoring]
    F -->|경고| H[알림 발송<br/>📢 Alert Notification]
    F -->|위험| I[자동 최적화<br/>🔧 Auto Optimization]
    
    H --> J[수동 조치<br/>👨‍💻 Manual Action]
    I --> K[인덱스 재구성<br/>🔄 Index Rebuild]
    
    J --> L[성능 개선<br/>📈 Performance Boost]
    K --> L
    
    L --> A
    
    style A fill:#e3f2fd
    style F fill:#f3e5f5
    style G fill:#4caf50
    style H fill:#ff9800
    style I fill:#f44336
    style L fill:#4caf50
```

## 7. 검색 결과 품질 평가

```mermaid
graph TB
    A[검색 결과<br/>📋 Search Results] --> B[품질 평가<br/>📊 Quality Assessment]
    
    B --> C[정확도<br/>🎯 Precision<br/>관련 문서 비율]
    B --> D[재현율<br/>📈 Recall<br/>찾은 관련 문서 비율]
    B --> E[F1 스코어<br/>⚖️ F1 Score<br/>정확도 × 재현율 조화평균]
    B --> F[사용자 만족도<br/>😊 User Satisfaction<br/>클릭률, 체류시간]
    
    C --> G[종합 품질 지표<br/>🏆 Overall Quality]
    D --> G
    E --> G
    F --> G
    
    G --> H{품질 기준 충족?<br/>📏 Quality Threshold}
    
    H -->|Yes| I[현재 설정 유지<br/>✅ Keep Current Config]
    H -->|No| J[파라미터 조정<br/>🔧 Parameter Tuning]
    
    J --> K[인덱스 재구성<br/>🔄 Index Rebuild]
    J --> L[알고리즘 변경<br/>🧠 Algorithm Change]
    J --> M[가중치 조정<br/>⚖️ Weight Adjustment]
    
    K --> B
    L --> B
    M --> B
    
    style A fill:#e3f2fd
    style G fill:#fff3e0
    style H fill:#f3e5f5
    style I fill:#4caf50
    style J fill:#ff9800
```
