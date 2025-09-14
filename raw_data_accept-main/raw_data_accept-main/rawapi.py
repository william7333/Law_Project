import os
import time
import json
import math
import random
import requests
from requests.adapters import HTTPAdapter, Retry
from tqdm import tqdm

# -----------------------------
# 1) 검색 대상 필드 & 키워드
# -----------------------------
TEXT_FIELDS = [
    "사건명", "판결요지", "판시사항", "참조조문", "참조판례",
    "주문", "이유", "판례내용", "본문"
]
KEYWORD = "임대차"


def match_rental(prec: dict) -> bool:
    """여러 텍스트 필드를 모아 '임대차'라는 키워드가 있으면 True."""
    for k in TEXT_FIELDS:
        v = prec.get(k)
        if isinstance(v, str) and KEYWORD in v:
            return True
    return False


# -----------------------------
# 2) HTTP 세션 (재시도/타임아웃)
# -----------------------------
def make_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"])
    )
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s


def get_json(session: requests.Session, url: str, timeout: float = 10.0) -> dict:
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    try:
        return resp.json()
    except Exception:
        return {}


# -----------------------------
# 3) 메인 수집 로직
# -----------------------------
def raw_api_year(OC: str, year1: int, year2: int, sleep_base: float = 0.25):
    session = make_session()

    for year in range(year1, year2 + 1):
        print(f"\n===== {year}년도 수집 시작 =====")
        folder_name = str(year)
        os.makedirs(folder_name, exist_ok=True)

        base_url = (
            f"http://www.law.go.kr/DRF/lawSearch.do?OC={OC}"
            "&target=prec&type=JSON"
            "&display=100"
            f"&prncYd={year}0101~{year}1231"
            "&search=2"
        )

        data = get_json(session, base_url)
        totalCnt = int(data.get("PrecSearch", {}).get("totalCnt") or 0)
        if totalCnt == 0:
            print(f"{year}년도: 목록 없음")
            continue

        print(f"{year}년도 총 건수(원천): {totalCnt}")
        pages = math.floor(totalCnt / 100) + 1

        saved_cnt = 0
        seen_ids = set()

        for page in tqdm(range(1, pages + 1), desc=f"{year} 목록 페이지"):
            url = f"{base_url}&page={page}"
            page_data = get_json(session, url)
            items = page_data.get("PrecSearch", {}).get("prec", [])
            if isinstance(items, dict):
                items = [items]

            for node in items:
                case_id = node.get("판례일련번호")
                if not case_id or case_id in seen_ids:
                    continue
                seen_ids.add(case_id)

                # 상세 API
                detail_url = (
                    f"http://www.law.go.kr/DRF/lawService.do?OC={OC}"
                    f"&target=prec&ID={case_id}&type=JSON"
                )
                detail_json = get_json(session, detail_url)
                prec = detail_json.get("PrecService", {})
                if not isinstance(prec, dict) or not prec:
                    continue

                # ---- 키워드 필터 ----
                if not match_rental(prec):
                    continue

                file_name = os.path.join(folder_name, f"임대차_판례_{year}_{case_id}.json")
                with open(file_name, "w", encoding="utf-8") as f:
                    json.dump(prec, f, ensure_ascii=False, indent=2)
                saved_cnt += 1

                time.sleep(sleep_base + random.random() * 0.2)

        print(f"{year}년도 저장 건수(임대차 필터 후): {saved_cnt}")


# -----------------------------
# 4) main
# -----------------------------
if __name__ == "__main__":
    OC = "rlawnsrb731"  # 발급받은 OC 값
    year1 = int(input("첫 번째 연도를 입력하세요: ").strip())
    year2 = int(input("두 번째 연도를 입력하세요: ").strip())
    if year1 > year2:
        year1, year2 = year2, year1

    raw_api_year(OC, year1, year2)
