#-----이 파일은 데이터를 불러오고 가공하는 기능들이 구현되어 있음-------#

import os #운영체제 기능 사용 위한 모듈
import re
import json

import numpy as np
import pandas as pd
from tqdm import tqdm

from konlpy.tag import Okt #한글 형태소 활용 모듈

FILTERS = "([~.,!?\"':;)(])"
PAD = "<PAD>"
STD = "<SOS>"
END = "<END>"
UNK = "<UNK>"

PAD_INDEX = 0
STD_INDEX = 1
END_INDEX = 2
UNK_INDEX = 3

MARKER = [PAD, STD, END, UNK]
CHANGE_FILTER = re.compile(FILTERS)

MAX_SEQUENCE = 25

def load_data(path):
    #판다스를 통해 데이터를 불러온다
    data_df = pd.read_csv(path, header=0)
    #질문과 답변 열을 가져와서 question, answer에 넣는다.
    question, answer = list(data_df['Q']), list(data_df['A'])
    return question, answer

def data_tokenizer(data):
    words = [] #토크나이징해서 담을 배열 / 단어리스트를 만든다
    for sentence in data:
        sentence = re.sub(CHANGE_FILTER, "", sentence) # 전처리하고
        for word in sentence.split(): #공백 문자를 기준으로 단어 나누고
            words.append(word)

    return [word for word in words if word]

def prepro_like_morphlized(data):
    #Okt 형태소 분리기를 사용해 형태소 기준으로 텍스트 토크나이징
    morph_analyzer = Okt()
    result_data = list()
    for seq in tqdm(data):
        morphlized_seq = " ".join(morph_analyzer.morphs(seq.replace(' ', '')))
        result_data.append(morphlized_seq)

    return result_data

def load_vocabulary(path, vocab_path, tokenize_as_morph=False):
    vocabulary_list = [] # 사전에 담을 배열 준비

    if not os.path.exists(vocab_path): #이미 생성된 사전은 없는 경우
        if (os.path.exists(path)): #사전으로 만들 데이터는 존재
            data_df = pd.read_csv(path, encoding='utf-8')
            question, answer = list(data_df['Q']), list(data_df['A'])
            if tokenize_as_morph: #형태소에 따른 토크나이져 처리
                question = prepro_like_morphlized(question)
                answer = prepro_like_morphlized(answer)
            data = [] #extend는 하나의 배열. 1차원 배열에 [] 여기 속에 다 합친다.
            data.extend(question)
            data.extend(answer)
            words = data_tokenizer(data)
            words = list(set(words)) #공통 단어 제거
            words[:0] = MARKER # MARKER값을 순서대로 넣기 위해 인덱스 0에 추가

        #리스트로 만들어진 사전을 파일에 만들어 넣는다.
        with open(vocab_path, 'w', encoding='utf-8') as vocabulary_file:
            for word in words:
                vocabulary_file.write(word + '\n')

    #사전 파일이 이미 존재하는 경우
    with open(vocab_path, 'r', encoding='utf-8') as vocabulary_file:
        for line in vocabulary_file:
            vocabulary_list.append(line.strip()) #배열에 넣어준다

    char2idx, idx2char = make_vocabulary(vocabulary_list)
    return char2idx, idx2char, len(char2idx)

def make_vocabulary(vocabulary_list):
    # Key: 단어 Value: 인덱스
    char2idx = {char: idx for idx, char in enumerate(vocabulary_list)}
    
    # Key: 인덱스 Value : 단어
    idx2char = {idx: char for idx, char in enumerate(vocabulary_list)}
    
    return char2idx, idx2char

# 인코더 부분에 들어가기 알맞게 전처리 하는 과정
def enc_processing(value, dictionary, tokenize_as_morph=False):

    sequences_input_index = [] #인덱스 값들을 가지고 있는 배열
    sequences_length = [] #하나의 인코딩 되는 문장의 길이를 가지고 있음
    
    if tokenize_as_morph: #형태소 토크나이징 사용 유무 체크
        value = prepro_like_morphlized(value)

    for sequence in value: 
        sequence = re.sub(CHANGE_FILTER, "", sequence)
        sequence_index = []
        for word in sequence.split():
            if dictionary.get(word) is not None:
                sequence_index.extend([dictionary[word]])
            else: #단어가 사전에 없는 경우
                sequence_index.extend([dictionary[UNK]])
        
        #문장 제한 길이보다 길어질 경우 뒤의 토큰을 잘라내기
        if len(sequence_index) > MAX_SEQUENCE:
            sequence_index = sequence_index[:MAX_SEQUENCE]

        sequences_length.append(len(sequence_index)) #하나의 문장에 대한 길이를 준다.
        #max_sequence_length보다 작은 경우에 PAD 작업 해준다.
        sequence_index += (MAX_SEQUENCE - len(sequence_index)) * [dictionary[PAD]]
        sequences_input_index.append(sequence_index)
    return np.asarray(sequences_input_index), sequences_length #reload되나 안되나
    #인덱스화 되어 있는 일반 배열을 넘파이 배열로 변경 : 텐서플로의 Dataset에 넣어주기 위한 사전 작업


#------ 디코더의 입력값 : "<SOS>, 그래, 오랜만이야, <PAD>"
#------ 디코더의 타깃값 : "그래, 오랜만이야, <END>, <PAD>"

def dec_output_processing(value, dictionary, tokenize_as_morph=False):
    
    sequences_output_index = []
    sequences_length = []

    if tokenize_as_morph:
        value = prepro_like_morphlized(value)

    for sequence in value:
        sequence = re.sub(CHANGE_FILTER, "", sequence)
        sequence_index = []
        #디코딩 입력의 처음에는 START 토큰이 와야 한다. 
        sequence_index = [ dictionary[STD]] + [dictionary[word] if word in dictionary else dictionary[UNK] for word in sequence.split() ]
        if len(sequence_index) > MAX_SEQUENCE:
            sequence_index = sequence_index[:MAX_SEQUENCE]
        
        sequences_length.append(len(sequence_index))
        sequence_index += (MAX_SEQUENCE - len(sequence_index)) * [dictionary[PAD]]

        sequences_output_index.append(sequence_index)

    return np.asarray(sequences_output_index), sequences_length

def dec_target_processing(value, dictionary, tokenize_as_morph=False):

    sequences_target_index = []
    
    if tokenize_as_morph:

        value = prepro_like_morphlized(value)
    
    for sequence in value: #한줄씩 불러온다
        sequence = re.sub(CHANGE_FILTER, "", sequence)
        sequence_index = [ dictionary[word] if word in dictionary else dictionary[UNK] for word in sequence.split() ]
        
        if len(sequence_index) >= MAX_SEQUENCE:
            sequence_index = sequence_index[:MAX_SEQUENCE - 1] + [dictionary[END]] #문장의 마지막에 END 토큰을 넣어준다.
        else:
            sequence_index += [dictionary[END]]
        
        sequence_index += (MAX_SEQUENCE - len(sequence_index)) * [dictionary[PAD]]
        sequences_target_index.append(sequence_index)
    
    return np.asarray(sequences_target_index) #디코드 타겟 함수에서는 길이를 담는 리스트를 만들지 않았다.