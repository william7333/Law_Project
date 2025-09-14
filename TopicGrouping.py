import os
import json
import shutil
from pathlib import Path
from tqdm import tqdm
import re

def sanitize_folder_name(name):
    """폴더명에 사용할 수 없는 문자를 제거하고 정리"""
    if not name or name.strip() == "":
        return "기타"
    
    # Windows에서 사용할 수 없는 문자들을 제거
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        name = name.replace(char, '_')
    
    return name.strip()

def analyze_legal_topic(json_data):
    """JSON 데이터를 분석하여 법적 주제를 결정"""
    
    # 분석할 필드들
    사건명 = json_data.get('사건명', '')
    판시사항 = json_data.get('판시사항', '')
    판결요지 = json_data.get('판결요지', '')
    참조조문 = json_data.get('참조조문', '')
    
    # 모든 텍스트를 합쳐서 분석
    combined_text = f"{사건명} {판시사항} {판결요지} {참조조문}".lower()
    
    # 법적 주제 분류 규칙 (우선순위 순)
    topic_rules = [
        # 보증금 관련
        {
            'keywords': ['보증금반환', '보증금', '전세금', '임대차보증금', '전세보증금'],
            'topic': '보증금반환'
        },
        # 명도 관련
        {
            'keywords': ['명도', '건물인도', '토지인도', '퇴거', '점유회복'],
            'topic': '명도소송'
        },
        # 임대료 관련
        {
            'keywords': ['임대료', '차임', '월세', '임료', '차임증액', '임대료증액'],
            'topic': '임대료분쟁'
        },
        # 계약 관련
        {
            'keywords': ['임대차계약', '계약해지', '계약해제', '계약갱신', '계약연장'],
            'topic': '임대차계약'
        },
        # 우선변제권 관련
        {
            'keywords': ['우선변제', '대항력', '배당', '경매', '우선변제권'],
            'topic': '우선변제권'
        },
        # 손해배상 관련
        {
            'keywords': ['손해배상', '손해', '배상', '위약금', '지연손해금'],
            'topic': '손해배상'
        },
        # 상가임대차 관련
        {
            'keywords': ['상가건물', '상가임대차', '권리금', '영업권', '상가건물임대차보호법'],
            'topic': '상가임대차'
        },
        # 주택임대차 관련
        {
            'keywords': ['주택임대차', '주택임대차보호법', '전월세', '주거용'],
            'topic': '주택임대차'
        },
        # 부동산 등기 관련
        {
            'keywords': ['소유권이전등기', '등기', '소유권', '등기말소', '가등기'],
            'topic': '부동산등기'
        },
        # 사해행위 관련
        {
            'keywords': ['사해행위', '사해행위취소', '채권자취소권'],
            'topic': '사해행위취소'
        }
    ]
    
    # 규칙 기반 분류
    for rule in topic_rules:
        for keyword in rule['keywords']:
            if keyword in combined_text:
                return rule['topic']
    
    # 사건명 기반 추가 분류
    if '배당이의' in 사건명:
        return '배당이의'
    elif '부당이득' in 사건명:
        return '부당이득반환'
    elif '대여금' in 사건명:
        return '대여금반환'
    elif '매매' in 사건명:
        return '매매계약'
    
    # 기본 분류
    return '기타'

def group_by_legal_topics():
    """2015년 이후 데이터를 법적 주제별로 그룹화"""
    
    source_dir = Path("./grouped_data")
    if not source_dir.exists():
        print("❌ grouped_data 폴더가 존재하지 않습니다.")
        return
    
    output_dir = Path("./topic_grouped_data")
    output_dir.mkdir(exist_ok=True)
    
    # 2015년 이후 JSON 파일 수집
    json_files = []
    year_stats = {}
    
    print("🔍 2015년 이후 파일 수집 중...")
    
    for case_type_dir in source_dir.iterdir():
        if not case_type_dir.is_dir():
            continue
            
        for year_dir in case_type_dir.iterdir():
            if not year_dir.is_dir():
                continue
                
            year = year_dir.name
            try:
                year_int = int(year)
                if year_int >= 2015:  # 2015년 이후만
                    if year not in year_stats:
                        year_stats[year] = 0
                    
                    for json_file in year_dir.glob("*.json"):
                        json_files.append(json_file)
                        year_stats[year] += 1
            except ValueError:
                continue
    
    if not json_files:
        print("❌ 2015년 이후 JSON 파일이 없습니다.")
        return
    
    # 연도별 통계 출력
    print(f"\n📊 2015년 이후 데이터 현황:")
    total_files = 0
    for year in sorted(year_stats.keys()):
        count = year_stats[year]
        total_files += count
        print(f"  📅 {year}년: {count:,}개")
    
    print(f"  🎯 총 파일 수: {total_files:,}개 (총 {len(year_stats)}개 년도)")
    
    # 주제별 파일 분류
    topic_groups = {}
    
    print(f"\n🔍 법적 주제 분석 중...")
    with tqdm(total=len(json_files), desc="📋 주제 분석", unit="파일") as pbar:
        for file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                topic = analyze_legal_topic(data)
                
                if topic not in topic_groups:
                    topic_groups[topic] = []
                
                topic_groups[topic].append(file_path)
                
                # 진행상황 업데이트
                pbar.set_postfix({'현재주제': topic, '분류됨': len(topic_groups)})
                pbar.update(1)
                
            except Exception as e:
                pbar.write(f"❌ 파일 읽기 오류 ({file_path}): {e}")
                pbar.update(1)
    
    print(f"\n📋 발견된 법적 주제: {len(topic_groups)}개")
    
    # 주제별 통계 표시 (파일 수 기준 내림차순)
    sorted_topics = sorted(topic_groups.items(), key=lambda x: len(x[1]), reverse=True)
    for topic, files in sorted_topics:
        print(f"  📂 {topic}: {len(files):,}개")
    
    # 주제별 폴더 생성 및 파일 복사
    print("\n📁 주제별 폴더 생성 및 파일 복사 중...")
    
    copied_count = 0
    
    with tqdm(total=len(json_files), desc="📦 파일 복사", unit="파일") as main_pbar:
        for topic, files in topic_groups.items():
            # 주제별 폴더 생성
            topic_dir = output_dir / sanitize_folder_name(topic)
            topic_dir.mkdir(exist_ok=True)
            
            # 파일 복사
            for file_path in files:
                try:
                    target_file = topic_dir / file_path.name
                    
                    # 같은 이름의 파일이 있으면 덮어쓰기
                    if target_file.exists():
                        target_file.unlink()
                    
                    shutil.copy2(str(file_path), str(target_file))
                    copied_count += 1
                    
                    # 진행상황 업데이트
                    main_pbar.set_postfix({
                        '현재주제': topic,
                        '완료': copied_count
                    })
                    main_pbar.update(1)
                    
                except Exception as e:
                    main_pbar.write(f"❌ 파일 복사 오류 ({file_path}): {e}")
                    main_pbar.update(1)
    
    print(f"\n✅ 법적 주제별 그룹화 완료! 총 {copied_count:,}개 파일 복사")
    
    # 최종 결과 상세 출력
    print("\n" + "="*70)
    print("📊 최종 법적 주제별 그룹화 결과 (2015년~현재)")
    print("="*70)
    
    total_result_files = 0
    
    for i, (topic, files) in enumerate(sorted_topics, 1):
        file_count = len(files)
        total_result_files += file_count
        percentage = (file_count / total_files * 100) if total_files > 0 else 0
        
        print(f"{i:2d}. 📁 {topic}: {file_count:,}개 ({percentage:.1f}%)")
        
        # 각 주제별 연도 분포 분석
        year_distribution = {}
        for file_path in files:
            # 파일명에서 연도 추출
            year_match = re.search(r'_(\d{4})_', file_path.name)
            if year_match:
                year = year_match.group(1)
                if year not in year_distribution:
                    year_distribution[year] = 0
                year_distribution[year] += 1
        
        # 연도별 분포 표시 (상위 5개년도만)
        if year_distribution:
            sorted_years = sorted(year_distribution.items(), key=lambda x: x[1], reverse=True)[:5]
            year_info = []
            for year, count in sorted_years:
                year_info.append(f"{year}년({count}개)")
            remaining_years = len(year_distribution) - len(sorted_years)
            if remaining_years > 0:
                year_info.append(f"외 {remaining_years}개년도")
            print(f"     └─ 주요 연도: {', '.join(year_info)}")
    
    print("\n" + "-"*70)
    print(f"🎯 총 분석 파일: {total_files:,}개")
    print(f"📂 총 법적 주제: {len(topic_groups)}개")
    print(f"📅 분석 기간: 2015년~현재 ({len(year_stats)}개 년도)")
    print(f"💾 저장 위치: ./topic_grouped_data/")
    
    # 연도별 상세 통계 (생략 없이 모든 연도 표시)
    print(f"\n📅 연도별 상세 통계:")
    for year in sorted(year_stats.keys()):
        count = year_stats[year]
        percentage = (count / total_files * 100) if total_files > 0 else 0
        print(f"  📅 {year}년: {count:,}개 ({percentage:.1f}%)")

if __name__ == "__main__":
    print("🚀 2015년 이후 데이터 법적 주제별 그룹화 시작")
    print("=" * 70)
    group_by_legal_topics()
