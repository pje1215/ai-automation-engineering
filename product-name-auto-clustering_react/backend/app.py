from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import pandas as pd
import numpy as np
import re
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from fastapi.middleware.cors import CORSMiddleware
from io import BytesIO
from pydantic import BaseModel
from typing import List, Dict, Any
import json

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서 모든 오리진 허용
    allow_credentials=False,  # "*"와 함께 사용하려면 False로 설정
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 변수로 모델 저장
model = None

def load_model():
    global model
    if model is None:
        model = SentenceTransformer("jhgan/ko-sroberta-multitask")
    return model

# Pydantic 모델들
class ClassificationRequest(BaseModel):
    data: List[Dict[str, Any]]
    site: str
    categories: List[str]

class Stage2Request(BaseModel):
    stage1Data: List[Dict[str, Any]]

# 텍스트 전처리 함수들
def clean_text(text):
    text = str(text)
    text = re.sub(r"[\[\]\(\)]", " ", text)
    text = re.sub(r"[^가-힣A-Za-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()

_WS_HARD = r"[\u00A0\u202F\u2007\u2000-\u2006\u2008-\u200A\u200B-\u200D\u2060]"

def _normalize_spaces(s: str) -> str:
    s = re.sub(_WS_HARD, " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def _build_fuzzy_pattern(cat: str) -> str:
    base = re.sub(_WS_HARD, "", cat)
    base = re.sub(r"[\s\W_]+", "", base)
    parts = [re.escape(ch) for ch in base]
    if not parts:
        return r"$^"
    return r"(?:[\s\W_]*)".join(parts)

def clean_and_trim_text(row):
    text = str(row["pname"])
    category = str(row["L_category"])
    site_name = str(row.get("사이트이름", ""))
    text = re.sub(r"[\[\]\(\)]", " ", text)
    text_norm = _normalize_spaces(text)
    if category and category != "nan":
        cat_pat = _build_fuzzy_pattern(_normalize_spaces(category))
        text_norm = re.sub(cat_pat, " ", text_norm, flags=re.IGNORECASE)
    if site_name and site_name != "nan":
        site_pat = _build_fuzzy_pattern(_normalize_spaces(site_name))
        text_norm = re.sub(site_pat, " ", text_norm, flags=re.IGNORECASE)
    text_norm = re.sub(r"[^가-힣A-Za-z0-9\s]", " ", text_norm)
    return _normalize_spaces(text_norm).lower()

def front_only_embedding(text, model, front_ratio=0.7, min_tokens=2, decay_rate=0.25):
    tokens = re.split(r"\s+", str(text).strip())
    n = len(tokens)
    if n == 0:
        return np.zeros(model.get_sentence_embedding_dimension())
    split_idx = max(min_tokens, int(n * front_ratio))
    front_tokens = tokens[:split_idx]
    back_tokens = tokens[split_idx:]
    front_emb = model.encode(front_tokens, show_progress_bar=False)
    front_weights = np.array([np.exp(-decay_rate * i) for i in range(len(front_tokens))])
    front_weights /= front_weights.sum()
    front_vec = np.average(front_emb, axis=0, weights=front_weights)
    back_vec = np.mean(model.encode(back_tokens, show_progress_bar=False), axis=0) * 0.01 if back_tokens else np.zeros(model.get_sentence_embedding_dimension())
    return front_vec + back_vec

def back_only_embedding(text, model, back_ratio=0.5, min_tokens=2, decay_rate=0.25):
    tokens = re.split(r"\s+", str(text).strip())
    n = len(tokens)
    if n == 0:
        return np.zeros(model.get_sentence_embedding_dimension())
    split_idx = max(n - max(min_tokens, int(n * back_ratio)), 0)
    front_tokens = tokens[:split_idx]
    back_tokens = tokens[split_idx:]
    back_emb = model.encode(back_tokens, show_progress_bar=False)
    back_weights = np.array([np.exp(-decay_rate * i) for i in range(len(back_tokens))])[::-1]
    back_weights /= back_weights.sum()
    back_vec = np.average(back_emb, axis=0, weights=back_weights)
    front_vec = np.mean(model.encode(front_tokens, show_progress_bar=False), axis=0) * 0.01 if front_tokens else np.zeros(model.get_sentence_embedding_dimension())
    return back_vec + front_vec

def extract_core_phrase(text):
    text = str(text)
    text = re.sub(r"\bv\d+|\bver\d+|\b\d{2,4}(\.\d+)?\b", "", text)
    text = re.sub(r"(교재|포함|미포함|only|온리|ver|버전)", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    tokens = text.split()
    core = " ".join(tokens[:3]) if len(tokens) > 3 else text
    return core.strip()

@app.get("/")
def root():
    return {"message": "상품명 분류 API 서버 정상 작동 중 ✅"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """파일 업로드 및 기본 정보 반환"""
    try:
        print(f"파일 업로드 시작: {file.filename}, 크기: {file.size}")
        print(f"파일 타입: {file.content_type}")
        
        # 파일 타입 검증
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.")
        
        # 엑셀 파일 로드
        print("엑셀 파일 로딩 중...")
        # UploadFile을 BytesIO로 변환
        file_content = await file.read()
        file_io = BytesIO(file_content)
        df = pd.read_excel(file_io)
        print(f"로드된 데이터 크기: {df.shape}")
        print(f"컬럼 목록: {df.columns.tolist()}")
        
        # 필수 컬럼 확인
        required_columns = ["pname", "L_category", "site_code"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(status_code=400, detail=f"필수 컬럼이 누락되었습니다: {missing_columns}. 필요한 컬럼: pname, L_category, site_code")
        
        # 기본 전처리
        print("텍스트 전처리 중...")
        df["상품명_clean"] = df["pname"].astype(str).apply(clean_text)
        df["상품명_trim"] = df.apply(clean_and_trim_text, axis=1)
        
        # 사이트와 카테고리 정보 추출
        print("사이트 및 카테고리 정보 추출 중...")
        sites = sorted(df["site_code"].unique().tolist())
        categories = sorted(df["L_category"].unique().tolist())
        print(f"발견된 사이트: {sites}")
        print(f"발견된 카테고리: {categories}")
        
        # 데이터를 딕셔너리로 변환
        print("데이터 직렬화 중...")
        data = df.to_dict(orient="records")
        
        # numpy 타입을 Python 기본 타입으로 변환
        for record in data:
            for key, value in record.items():
                if isinstance(value, (np.integer, np.floating)):
                    record[key] = value.item()
                elif isinstance(value, np.ndarray):
                    record[key] = value.tolist()
        
        print(f"업로드 완료: {len(df)}개 행, {len(sites)}개 사이트, {len(categories)}개 카테고리")
        
        return {
            "count": len(df),
            "sites": sites,
            "categories": categories,
            "data": data
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"업로드 에러 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"파일 처리 중 오류가 발생했습니다: {str(e)}")

@app.post("/classify/stage1")
async def classify_stage1(request: ClassificationRequest):
    """1단계 클러스터링"""
    try:
        print(f"받은 데이터 개수: {len(request.data)}")
        print(f"사이트: {request.site}, 카테고리: {request.categories}")
        
        # 데이터를 DataFrame으로 변환
        df = pd.DataFrame(request.data)
        print(f"DataFrame 컬럼: {df.columns.tolist()}")
        print(f"DataFrame 크기: {df.shape}")
        
        # 필수 컬럼 확인
        required_columns = ["pname", "L_category", "사이트이름", "상품명_trim"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(status_code=400, detail=f"필수 컬럼이 누락되었습니다: {missing_columns}")
        
        # 데이터가 비어있는지 확인
        if df.empty:
            raise HTTPException(status_code=400, detail="처리할 데이터가 없습니다.")
        
        # 모델 로드
        print("모델 로딩 중...")
        model = load_model()
        print("모델 로딩 완료")
        
        # 1단계 클러스터링 실행
        print("1단계 클러스터링 시작...")
        cluster_results = []
        for cat in sorted(df["L_category"].unique()):
            print(f"카테고리 '{cat}' 처리 중...")
            subset = df[df["L_category"] == cat].copy()
            print(f"  - 카테고리 '{cat}' 데이터 개수: {len(subset)}")
            
            if len(subset) < 2:
                print(f"  - 카테고리 '{cat}' 데이터가 부족하여 건너뜀")
                continue
                
            print(f"  - 임베딩 생성 중...")
            subset["embedding_front"] = subset["상품명_trim"].apply(lambda x: front_only_embedding(x, model))
            X_front = np.vstack(subset["embedding_front"].values)
            print(f"  - 임베딩 완료, 크기: {X_front.shape}")
            
            print(f"  - 클러스터링 실행 중...")
            cluster_front = AgglomerativeClustering(
                n_clusters=None, distance_threshold=9, linkage='ward'
            )
            subset["cluster_lv1"] = cluster_front.fit_predict(X_front)
            cluster_results.append(subset)
            print(f"  - 카테고리 '{cat}' 클러스터링 완료")

        if not cluster_results:
            raise HTTPException(status_code=400, detail="클러스터링할 데이터가 부족합니다.")

        print("결과 통합 중...")
        df_lv1 = pd.concat(cluster_results, ignore_index=True)
        df_lv1["대표핵심어"] = df_lv1["상품명_trim"].apply(extract_core_phrase)

        # 대표명 생성
        print("대표명 생성 중...")
        rep_lv1 = (
            df_lv1.groupby(["사이트이름", "L_category", "cluster_lv1"])
            .agg(대표핵심어=("대표핵심어", lambda x: x.mode()[0] if not x.mode().empty else x.iloc[0]))
            .reset_index()
        )
        rep_lv1["대표_lv1명"] = rep_lv1.apply(
            lambda row: f"{row['사이트이름']}_{row['L_category']}_{row['대표핵심어']}", axis=1
        )

        df_lv1 = df_lv1.merge(
            rep_lv1[["사이트이름", "L_category", "cluster_lv1", "대표_lv1명"]],
            on=["사이트이름", "L_category", "cluster_lv1"],
            how="left"
        )

        # 임베딩 컬럼 제거 (JSON 직렬화 불가)
        if "embedding_front" in df_lv1.columns:
            df_lv1 = df_lv1.drop(columns=["embedding_front"])
        
        # 결과를 딕셔너리로 변환
        print("결과 직렬화 중...")
        result_data = df_lv1.to_dict(orient="records")
        
        # numpy 타입을 Python 기본 타입으로 변환
        for record in result_data:
            for key, value in record.items():
                if isinstance(value, (np.integer, np.floating)):
                    record[key] = value.item()
                elif isinstance(value, np.ndarray):
                    record[key] = value.tolist()
        
        summary_dict = {
            "총_클러스터_수": int(len(df_lv1["cluster_lv1"].unique())),
            "카테고리별_클러스터_수": {
                str(k): int(v) for k, v in df_lv1.groupby("L_category")["cluster_lv1"].nunique().to_dict().items()
            }
        }
        
        print("1단계 클러스터링 완료!")
        return {
            "success": True,
            "count": int(len(df_lv1)),
            "data": result_data,
            "summary": summary_dict
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"에러 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"1단계 클러스터링 중 오류가 발생했습니다: {str(e)}")

@app.post("/classify/stage2")
async def classify_stage2(request: Stage2Request):
    """2단계 세분화"""
    try:
        print(f"2단계 세분화 시작 - 받은 데이터 개수: {len(request.stage1Data)}")
        
        # 데이터를 DataFrame으로 변환
        df_lv1 = pd.DataFrame(request.stage1Data)
        print(f"DataFrame 컬럼: {df_lv1.columns.tolist()}")
        print(f"DataFrame 크기: {df_lv1.shape}")
        
        # 필수 컬럼 확인
        required_columns = ["cluster_lv1", "상품명_trim"]
        missing_columns = [col for col in required_columns if col not in df_lv1.columns]
        if missing_columns:
            raise HTTPException(status_code=400, detail=f"2단계 세분화에 필요한 컬럼이 누락되었습니다: {missing_columns}")
        
        # 모델 로드
        print("모델 로딩 중...")
        model = load_model()
        print("모델 로딩 완료")
        
        # 2단계 세분화 실행
        print("2단계 세분화 시작...")
        cluster_results = []
        unique_clusters = sorted(df_lv1["cluster_lv1"].unique())
        print(f"처리할 1단계 클러스터 수: {len(unique_clusters)}")
        
        for rep in unique_clusters:
            print(f"1단계 클러스터 '{rep}' 처리 중...")
            subset = df_lv1[df_lv1["cluster_lv1"] == rep].copy()
            print(f"  - 클러스터 '{rep}' 데이터 개수: {len(subset)}")
            
            if len(subset) < 3:
                print(f"  - 클러스터 '{rep}' 데이터가 부족하여 세분화하지 않음")
                subset["cluster_lv2"] = 0
                cluster_results.append(subset)
                continue
                
            print(f"  - 임베딩 생성 중...")
            subset["embedding_back"] = subset["상품명_trim"].apply(lambda x: back_only_embedding(x, model))
            X_back = np.vstack(subset["embedding_back"].values)
            print(f"  - 임베딩 완료, 크기: {X_back.shape}")
            
            print(f"  - 세분화 클러스터링 실행 중...")
            cluster_back = AgglomerativeClustering(
                n_clusters=None, distance_threshold=5, linkage='ward'
            )
            subset["cluster_lv2"] = cluster_back.fit_predict(X_back)
            cluster_results.append(subset)
            print(f"  - 클러스터 '{rep}' 세분화 완료")

        print("결과 통합 중...")
        df_lv2 = pd.concat(cluster_results, ignore_index=True)
        
        # 임베딩 컬럼 제거 (JSON 직렬화 불가)
        if "embedding_back" in df_lv2.columns:
            df_lv2 = df_lv2.drop(columns=["embedding_back"])
        
        # 결과를 딕셔너리로 변환
        print("결과 직렬화 중...")
        result_data = df_lv2.to_dict(orient="records")
        
        # numpy 타입을 Python 기본 타입으로 변환
        for record in result_data:
            for key, value in record.items():
                if isinstance(value, (np.integer, np.floating)):
                    record[key] = value.item()
                elif isinstance(value, np.ndarray):
                    record[key] = value.tolist()

        summary_dict = {
            "총_세분화_클러스터_수": int(len(df_lv2["cluster_lv2"].unique())),
            "1단계_클러스터별_세분화_수": {
                str(k): int(v) for k, v in df_lv2.groupby("cluster_lv1")["cluster_lv2"].nunique().to_dict().items()
            }
        }
        
        print("2단계 세분화 완료!")
        return {
            "success": True,
            "count": int(len(df_lv2)),
            "data": result_data,
            "summary": summary_dict
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"2단계 세분화 에러 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"2단계 세분화 중 오류가 발생했습니다: {str(e)}")

@app.post("/classify/download")
async def classify_and_download(file: UploadFile = File(...)):
    """기존 다운로드 엔드포인트 (호환성 유지)"""
    try:
        # UploadFile을 BytesIO로 변환
        file_content = await file.read()
        file_io = BytesIO(file_content)
        df = pd.read_excel(file_io)
        df["상품명_clean"] =   df["pname"].astype(str).str.replace(r"[^가-힣A-Za-z0-9\s]", " ", regex=True)
        model = load_model()
        embeddings = model.encode(df["상품명_clean"].tolist(), show_progress_bar=False)
        cluster = AgglomerativeClustering(n_clusters=None, distance_threshold=9, linkage='ward')
        df["cluster_lv1"] = cluster.fit_predict(embeddings)

        output = BytesIO()
        df.to_csv(output, index=False, encoding="utf-8-sig")
        output.seek(0)
        return StreamingResponse(output, media_type="text/csv",
                                 headers={"Content-Disposition": "attachment; filename=result.csv"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"다운로드 처리 중 오류가 발생했습니다: {str(e)}")