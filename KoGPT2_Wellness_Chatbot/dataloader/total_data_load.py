import torch
import torch.nn as nn
#데이터 셋 로더 : 파이토치에서 제공하는 데이터셋을 좀 더 쉽게 다룰 수 있도록 해주는 도구
from torch.utils.data import Dataset

from kogpt2_transformers import get_kogpt2_tokenizer

class TotalAutoRegressiveDataset(Dataset): # For AutoRegressive Language Model
    
    def __init__(self, file_path = "/content/drive/My Drive/RogerHeederer/ChatBot/KoGPT2_Wellness/data/total.txt", n_ctx = 1024):
        self.file_path = file_path
        self.data = []
        self.tokenizer = get_kogpt2_tokenizer()

        bos_token_id = [self.tokenizer.bos_token_id] #<s>
        eos_token_id = [self.tokenizer.eos_token_id] #</s>
        pad_token_id = [self.tokenizer.pad_token_id] #<pad>

        file = open(self.file_path, 'r', encoding='utf-8')

        while True:
            line = file.readline()
            if not line:
                break
            datas = line.split("    ") # 질문과 답변을 "    " 단위로 나눈다.
            #index_of_words = <s>질문</s><pad> + <s>답변</s><pad>
            index_of_words = bos_token_id + self.tokenizer.encode(datas[0]) + eos_token_id + bos_token_id + self.tokenizer.encode(datas[1][:-1]) + eos_token_id
            pad_token_len = n_ctx - len(index_of_words) #문장 max 길이에서 현재 길이값 빼기

            index_of_words += pad_token_id * pad_token_len
            self.data.append(index_of_words) # 남은 자리에 패딩처리
        file.close()

    
    def __len__(self):
        return len(self.data)

    def __getitem__(self,index):
        item = self.data[index]
        return item

if __name__ == "__main__":
    dataset = TotalAutoRegressiveDataset()
    print(dataset)