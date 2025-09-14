import requests
import json
import os
import re
from time import sleep
from tqdm import tqdm
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 판례 검색 API 설정
OC = os.getenv("OC")  # .env 파일에서 사용자 ID 로드
if not OC:
    raise ValueError("OC 값이 .env 파일에 설정되지 않았습니다. .env 파일에 OC=your_id 형태로 설정해주세요.")
BASE_URL_LIST = "http://www.law.go.kr/DRF/lawSearch.do"  # 판례 목록 조회 API
BASE_URL_DETAIL = "http://www.law.go.kr/DRF/lawService.do"  # 판례 상세 조회 API

# 검색 및 저장 설정
QUERY = "임대차"  # 검색 키워드
BASE_OUTPUT_DIR = "./JsonData"  # 판례 저장 폴더
os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)

def sanitize_name(name: str) -> str:
    """폴더/파일명에 쓸 수 없는 문자 제거"""
    return re.sub(r'[\\/*?:"<>|]', "_", name.strip())

def fetch_case_list(page=1, display=100):
    """판례 목록을 API로부터 조회"""
    params = {
        "OC": OC,
        "target": "prec",
        "type": "JSON",
        "query": QUERY,
        "search": 2,   # 본문 검색
        "display": display,
        "page": page,
        "prncYd": "20150101~20251231"  # 2015년 1월 1일부터 현재까지
    }
    
    r = requests.get(BASE_URL_LIST, params=params)
    r.raise_for_status()
    return r.json()

def fetch_case_detail(case_id):
    """특정 판례의 상세 정보를 API로부터 조회"""
    params = {
        "OC": OC,
        "target": "prec",
        "type": "JSON",
        "ID": case_id
    }
    r = requests.get(BASE_URL_DETAIL, params=params)
    r.raise_for_status()
    return r.json()

def get_main_subject(detail_json):
    """판례에서 중심주제를 추출 (참조조문, 사건명, 키워드 기반)"""
    참조조문 = detail_json.get("참조조문", "")
    사건명 = detail_json.get("사건명", "")
    사건종류명 = detail_json.get("사건종류명", "기타")
    
    # 1순위: 참조조문에서 구체적 주제 추출
    if 참조조문:
        # 임대차 관련 키워드 매핑
        if any(keyword in 참조조문 for keyword in ["618조", "임대차", "전세"]):
            return "임대차계약"
        elif any(keyword in 참조조문 for keyword in ["보증금", "임료"]):
            return "임대차보증금"
        elif any(keyword in 참조조문 for keyword in ["명도", "인도"]):
            return "명도소송"
        else:
            # 기본적으로 법명 추출
            law_name = 참조조문.split()[0] if 참조조문.split() else "기타"
            return sanitize_name(law_name)
    
    # 2순위: 사건명에서 주제 추출
    if 사건명:
        if "명도" in 사건명:
            return "명도소송"
        elif "보증금" in 사건명:
            return "임대차보증금"
        elif any(keyword in 사건명 for keyword in ["임대차", "전세", "월세"]):
            return "임대차계약"
    
    # 3순위: 사건종류명 사용
    return sanitize_name(사건종류명)

def main():
    all_cases = []
    
    print("📊 판례 검색 중...")
    first_page = fetch_case_list(page=1)
    
    # 응답 구조 수정: PrecSearch 래퍼 처리
    search_data = first_page.get("PrecSearch", first_page)
    total_count = int(search_data.get("totalCnt", 0))
    print(f"총 검색 결과: {total_count}건")

    display = 100
    total_pages = (total_count // display) + (1 if total_count % display else 0)
    
    # 전체 판례 수집을 위한 진행상황바
    with tqdm(total=total_count, desc="📋 판례 수집", unit="건") as pbar:
        for page in range(1, total_pages + 1):
            data = fetch_case_list(page=page, display=display)
            search_data = data.get("PrecSearch", data)

            if "prec" not in search_data:
                continue

            for item in search_data["prec"]:
                case_id = item.get("판례일련번호")
                사건종류명 = item.get("사건종류명", "")
                사건명 = item.get("사건명", "")

                # 사건종류명이 없거나 None인 경우 제외
                if not 사건종류명 or 사건종류명.strip() == "":
                    pbar.update(1)
                    continue
                
                # 민사 사건만 포함
                if 사건종류명 != "민사":
                    pbar.update(1)
                    continue

                try:
                    detail = fetch_case_detail(case_id)

                    # 중심주제 기준으로 그룹화
                    subject_name = get_main_subject(detail)
                    output_dir = os.path.join(BASE_OUTPUT_DIR, subject_name)
                    os.makedirs(output_dir, exist_ok=True)

                    # JSON 저장
                    file_path = os.path.join(output_dir, f"{case_id}.json")
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(detail, f, ensure_ascii=False, indent=2)

                    all_cases.append(detail)
                    
                    # 진행상황 업데이트
                    pbar.set_postfix({
                        '현재': f"{subject_name}/{case_id}",
                        '페이지': f"{page}/{total_pages}"
                    })
                    pbar.update(1)

                    sleep(0.3)
                except Exception as e:
                    pbar.write(f"❌ 에러 (ID={case_id}): {e}")
                    pbar.update(1)

    # 전체 합본 저장
    merged_path = os.path.join(BASE_OUTPUT_DIR, f"{QUERY}_전체.json")
    with open(merged_path, "w", encoding="utf-8") as f:
        json.dump(all_cases, f, ensure_ascii=False, indent=2)

    print(f"✅ 민사 판례 데이터 수집 완료! 총 {len(all_cases)}건이 중심주제별로 그룹화되어 JsonData 폴더에 저장되었습니다.")

if __name__ == "__main__":
    main()
