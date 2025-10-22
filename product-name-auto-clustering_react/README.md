# AI 기반 상품명 자동 분류 시스템 (React + FastAPI)

비정형 상품명을 AI로 자동 분류해 내부 분석 효율을 높이기 위해 개발한 웹 프로토타입입니다.
사용자가 엑셀 파일을 업로드하면, 모델이 의미 유사도를 기반으로 상품명을 군집화하고 결과 파일을 다시 내려받을 수 있습니다.
현업에서는 이 로직을 참고해 내부 서버에서 상품 기준을 통합하는 구조로 확장 적용했습니다.

## 1. 프로젝트 배경
- 각 사업부별로 상품명이 다르게 관리되면서, 동일 상품이라도 분석 시 기준이 불일치하는 문제가 있었습니다.
- 예를 들어 ‘365멤버십_교재포함_ver23.10’과 ‘365멤버십_교재미포함_ver23.10’이 서로 다른 상품으로 인식되는 식입니다.
- 이를 해결하기 위해 상품명을 AI가 스스로 그룹화할 수 있도록 하는 모델을 설계했고, 직접 결과를 시각적으로 확인할 수 있도록 웹앱 형태로 구현했습니다.



## 2. 주요 기능
- 엑셀 업로드 → 상품명 임베딩 및 자동 분류 → 결과 엑셀 다운로드
- 클러스터별 대표 상품명 확인 가능
- FastAPI를 ngrok으로 외부에 공개해 실시간 테스트 진행
- Firebase Hosting을 이용한 프론트엔드 배포 실험


### 기술 스택
- Frontend: React, Firebase Hosting
- Backend: FastAPI, Python
- AI Model: Sentence-BERT, Agglomerative Clustering
- 기타: pandas, axios, ngrok (FastAPI 외부 연동 테스트용)

### 폴더 구조
react_project/
 ├─ auto-classify-web/      # React 프론트엔드
 ├─ backend/                # FastAPI + ML 모델 서버
 └─ README.md

※ auto-classify-web/.env에는 ngrok 배포 당시의 FastAPI API 주소가 남아 있으며, 현재는 만료된 상태입니다.
로컬 테스트 시 http://localhost:8000 으로 변경하면 정상 실행됩니다.

### 실행 방법 (로컬 기준)
- Backend
cd backend
pip install -r requirements.txt
python run_server.py

- Frontend
cd auto-classify-web
npm install
npm start

## 3. 개발 과정

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

## 4. 프로젝트 의의 및 확장 방향

### 의의

분석가/마케터가 직접 사용할 수 있는 AI 기반 실사용형 프로토타입 구현

내부 상품 기준 정합성 확보를 위한 자동화 가능성 실증

이후 사내 분석 서버 API 기반 운영 데이터 파이프라인에 통합 적용 완료

### 향후 확장 방향

클러스터링 결과에 대한 수동 보정 옵션 추가

“교재 포함/미포함, 기간, 유형” 등 분류 옵션화

상품 → 콘텐츠 → 강의까지 계층 기반 클러스터 자동 확장

