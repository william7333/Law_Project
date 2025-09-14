import os
import json
import shutil
from pathlib import Path
from tqdm import tqdm
import re

def sanitize_folder_name(name):
    """폴더명에 사용할 수 없는 문자를 제거하고 정리"""
    if not name or name.strip() == "":
        return "None"
    
    # Windows에서 사용할 수 없는 문자들을 제거
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        name = name.replace(char, '_')
    
    return name.strip()

def get_case_info_from_json(file_path):
    """JSON 파일에서 사건종류명과 년도를 추출"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 사건종류명 추출 (raw_data는 PrecService 구조가 없음)
        case_type = data.get('사건종류명', None)
        case_type = sanitize_folder_name(case_type)
        
        # 년도 추출 - 파일명에서 추출 (예: 임대차_판례_2011_148163.json)
        file_name = file_path.name
        year_match = re.search(r'_(\d{4})_', file_name)
        if year_match:
            year = year_match.group(1)
        else:
            # 파일명에서 추출 실패 시 부모 폴더명에서 추출
            parent_folder = file_path.parent.name
            if parent_folder.isdigit() and len(parent_folder) == 4:
                year = parent_folder
            else:
                year = "Unknown"
        
        return case_type, year
    
    except Exception as e:
        print(f"❌ 파일 읽기 오류 ({file_path}): {e}")
        return "None", "Unknown"

def group_files_by_case_type_and_year():
    """사건종류명과 년도를 기준으로 파일들을 이중 그룹화"""
    
    source_dir = Path("./raw_data_accept-main/raw_data_accept-main")
    if not source_dir.exists():
        print("❌ raw_data_accept-main/raw_data_accept-main 폴더가 존재하지 않습니다.")
        return
    
    output_dir = Path("./grouped_data")
    output_dir.mkdir(exist_ok=True)
    
    # 모든 JSON 파일 찾기
    json_files = []
    for file_path in source_dir.rglob("*.json"):
        # data 폴더 내의 파이썬 파일 등 제외
        if file_path.suffix == ".json" and "임대차_판례_" in file_path.name:
            json_files.append(file_path)
    
    if not json_files:
        print("❌ 처리할 JSON 파일이 없습니다.")
        return
    
    print(f"📊 총 {len(json_files)}개의 JSON 파일을 처리합니다.")
    
    # 사건종류명 + 년도별로 파일 분류
    grouped_files = {}
    
    print("\n🔍 파일 분석 중...")
    with tqdm(total=len(json_files), desc="📋 파일 분석", unit="파일") as pbar:
        for file_path in json_files:
            case_type, year = get_case_info_from_json(file_path)
            
            # 사건종류명별 그룹 생성
            if case_type not in grouped_files:
                grouped_files[case_type] = {}
            
            # 년도별 하위 그룹 생성
            if year not in grouped_files[case_type]:
                grouped_files[case_type][year] = []
            
            grouped_files[case_type][year].append(file_path)
            
            # 진행상황 업데이트
            pbar.set_postfix({'현재': f"{case_type}/{year}", '분류됨': len(grouped_files)})
            pbar.update(1)
    
    print(f"\n📋 발견된 사건종류명: {len(grouped_files)}개")
    
    # 사건종류명별 통계 표시
    total_files_by_case = {}
    for case_type, years in grouped_files.items():
        total_count = sum(len(files) for files in years.values())
        total_files_by_case[case_type] = total_count
    
    # 파일 수 기준 내림차순 정렬
    sorted_case_types = sorted(total_files_by_case.items(), key=lambda x: x[1], reverse=True)
    for case_type, total_count in sorted_case_types:
        years_info = []
        for year in sorted(grouped_files[case_type].keys()):
            count = len(grouped_files[case_type][year])
            years_info.append(f"{year}년({count}개)")
        print(f"  📂 {case_type}: 총 {total_count}개 [{', '.join(years_info)}]")
    
    # 사건종류명별, 년도별로 폴더 생성 및 파일 이동
    print("\n📁 폴더 생성 및 파일 이동 중...")
    
    # 전체 파일 이동 진행상황을 위한 카운터
    total_files_to_move = sum(
        len(files) 
        for case_years in grouped_files.values() 
        for files in case_years.values()
    )
    moved_count = 0
    
    with tqdm(total=total_files_to_move, desc="📦 파일 이동", unit="파일") as main_pbar:
        for case_type, years in grouped_files.items():
            # 사건종류명별 최상위 폴더 생성
            case_dir = output_dir / case_type
            case_dir.mkdir(exist_ok=True)
            
            for year, files in years.items():
                # 년도별 하위 폴더 생성
                year_dir = case_dir / year
                year_dir.mkdir(exist_ok=True)
                
                # 파일 이동
                for file_path in files:
                    try:
                        target_file = year_dir / file_path.name
                        
                        # 파일이 이미 해당 폴더에 있으면 건너뛰기
                        if file_path.parent == year_dir:
                            main_pbar.update(1)
                            continue
                        
                        # 같은 이름의 파일이 있으면 덮어쓰기
                        if target_file.exists():
                            target_file.unlink()
                        
                        shutil.copy2(str(file_path), str(target_file))
                        moved_count += 1
                        
                        # 진행상황 업데이트
                        main_pbar.set_postfix({
                            '현재': f"{case_type}/{year}",
                            '완료': moved_count
                        })
                        main_pbar.update(1)
                        
                    except Exception as e:
                        print(f"❌ 파일 복사 오류 ({file_path}): {e}")
                        main_pbar.update(1)
    
    print(f"\n✅ 이중 그룹화 완료! 총 {moved_count}개 파일 복사")
    print(f"📂 생성된 사건종류명 폴더: {len(grouped_files)}개")
    
    # 최종 결과 요약
    print("\n" + "="*60)
    print("📊 최종 이중 그룹화 결과 (사건종류명 > 년도)")
    print("="*60)
    
    total_files = 0
    total_years = 0
    
    for case_type in sorted_case_types:
        case_name = case_type[0]
        case_total = case_type[1]
        total_files += case_total
        
        print(f"\n📁 {case_name}: 총 {case_total:,}개")
        
        # 년도별 상세 정보
        years = grouped_files[case_name]
        total_years += len(years)
        
        for year in sorted(years.keys()):
            file_count = len(years[year])
            percentage = (file_count / case_total * 100) if case_total > 0 else 0
            print(f"  └─ 📅 {year}년: {file_count:,}개 ({percentage:.1f}%)")
    
    print("\n" + "-"*60)
    print(f"🎯 총 파일 수: {total_files:,}개")
    print(f"📂 총 사건종류명: {len(grouped_files)}개")
    print(f"📅 총 년도 폴더: {total_years}개")
    print(f"💾 저장 위치: ./grouped_data/")
    
    # 폴더 구조 예시 표시
    print(f"\n📂 생성된 폴더 구조:")
    print(f"./grouped_data/")
    example_shown = 0
    for case_type, years in grouped_files.items():
        if example_shown >= 2:  # 처음 2개만 예시로 표시
            print(f"├─ ... (총 {len(grouped_files)}개 사건종류명)")
            break
        print(f"├─ {case_type}/")
        year_count = 0
        for year in sorted(years.keys()):
            if year_count >= 3:  # 각 사건종류별로 3개년도만 표시
                print(f"│  ├─ ... (총 {len(years)}개 년도)")
                break
            file_count = len(years[year])
            print(f"│  ├─ {year}/ ({file_count}개 파일)")
            year_count += 1
        example_shown += 1

if __name__ == "__main__":
    print("🚀 사건종류명 + 년도별 이중 그룹화 시작")
    print("=" * 60)
    group_files_by_case_type_and_year()


