# AI 기반 상품명 자동 분류 시스템 (React + FastAPI)

비정형 상품명을 AI로 자동 분류해 내부 분석 효율을 높이기 위한 웹 프로토타입입니다.  
엑셀 업로드 → 의미 유사도 기반 군집화 → 결과 다운로드까지 자동화합니다.  
본 로직은 사내 분석 서버의 기준 통합 구조로 확장 적용되었습니다.

---

## 1. 프로젝트 배경
- 사업부별로 상품명이 제각각 관리되어 동일 상품도 분리되어 분석되는 문제 발생
- 예: `365멤버십_교재포함_ver23.10` vs `365멤버십_교재미포함_ver23.10`
- 해결: **상품명 자동 군집화 모델 + 웹 인터페이스**로 기준 통합의 기반 마련

---

## 2. 주요 기능
- 엑셀 업로드 → 상품명 임베딩 및 자동 군집화 → 결과 엑셀 다운로드
- 클러스터별 대표 상품명 확인
- FastAPI 서버를 ngrok으로 외부 테스트, React 프런트는 Firebase Hosting 배포 실험
- 100% 로컬 환경에서도 실행 가능

---

## 3. 기술 스택

| 영역 | 기술 |
|---|---|
| Frontend | React, Axios, Firebase Hosting |
| Backend | FastAPI, Python |
| AI Model | Sentence-BERT, Agglomerative Clustering |
| 기타 | pandas, ngrok(테스트용), Excel 업/다운로드 처리 |

---

## 4. 폴더 구조

폴더구조.txt 참고

> `auto-classify-web/.env`는 ngrok 테스트 당시 주소가 남아 있으나 현재 만료됨.  
> 로컬 테스트 시 `REACT_APP_API_URL=http://localhost:8000` 로 설정 후 프런트 재시작 필요.

## 5. 실행 방법 (로컬 기준)
#### Backend (FastAPI + ML 모델)
```bash
cd backend
pip install -r requirements.txt
python run_server.py

#### Frontend (React + Axios)
- cd auto-classify-web
- npm install
- npm start

## 6. 개발 과정

1. 상품명 정제 로직 설계
괄호, 특수문자, 불필요한 버전 정보 등을 제거해 모델 입력 전 텍스트를 정규화.

2. Sentence-BERT 임베딩
상품명을 벡터화해 의미 유사도 기반으로 비교 가능하도록 처리.

3. Agglomerative Clustering 적용
의미적으로 가까운 상품명을 자동으로 묶어주는 방식 사용.

4. React 인터페이스 구현
엑셀 업로드 후 결과 미리보기 및 다운로드까지 가능하도록 구성.

5. Firebase 배포 / ngrok 테스트
FastAPI 서버를 ngrok으로 외부 노출해 실제 프론트-백 간 통신 검증.

## 7. 프로젝트 의의 및 확장 방향

### 의의

분석가/마케터가 직접 사용할 수 있는 AI 기반 실사용형 프로토타입 구현

내부 상품 기준 정합성 확보를 위한 자동화 가능성 실증

이후 사내 분석 서버 API 기반 운영 데이터 파이프라인에 통합 적용 완료

### 향후 확장 방향

클러스터링 결과에 대한 수동 보정 옵션 추가

“교재 포함/미포함, 기간, 유형” 등 분류 옵션화

상품 → 콘텐츠 → 강의까지 계층 기반 클러스터 자동 확장

