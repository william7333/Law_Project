from datasets import load_dataset
import pandas as pd
import os

def save_dataset_as_single_csv(dataset_name, subset_name, output_file):
    dataset = load_dataset(dataset_name, subset_name)

    df_list = []
    for split in dataset.keys():  # train, validation, test 등
        df_split = dataset[split].to_pandas()
        df_split["split"] = split
        df_list.append(df_split)

    full_df = pd.concat(df_list, ignore_index=True)

    os.makedirs("data", exist_ok=True)

    path = os.path.join("data", output_file)
    full_df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"{path} 저장 완료 (총 {len(full_df)} 행)")


if __name__ == "__main__":
    save_dataset_as_single_csv("lbox/lbox_open", "casename_classification", "casename_classification.csv") # 사건명 분류
    save_dataset_as_single_csv("lbox/lbox_open", "statute_classification", "statute_classification.csv")  # 법령 조문 분류
    save_dataset_as_single_csv("lbox/lbox_open", "ljp_criminal", "ljp_criminal.csv") # 형사 판결문
    save_dataset_as_single_csv("lbox/lbox_open", "ljp_civil", "ljp_civil.csv") # 민사 판결문
    save_dataset_as_single_csv("lbox/lbox_open", "precedent_corpus", "precedent_corpus.csv") # 판례 코퍼스
    save_dataset_as_single_csv("lbox/lbox_open", "summarization", "summarization.csv") # 판결문 요약
