from dotenv import load_dotenv
import os, torch, pickle
from transformers import GPT2Tokenizer, GPT2LMHeadModel, AutoTokenizer, AutoModelWithLMHead

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

load_dotenv(verbose=True)
# paths and configs
# 원래 소스와는 다르게, 내 경로에 맞춰 수정함
base_path = "/content/drive/MyDrive/RogerHeederer/ChatBot/personaGPT_Michigan"
save_path = f"{base_path}/save_path"
tokenizer_path = os.path.join(save_path, 'checkpoint/tokenizer/')
model_path = os.path.join(save_path, 'checkpoint/model/')
data_path = f"{base_path}/data"
# learning
lr = 5e-5
gradient_accumulation_steps = 8
bs = 8
epochs = 3
weight_decay = 0.0
logging_steps = 10
save_steps = 250

def create_dir(directory):
    """create directory if not exists
    """
    if not os.path.exists(directory):
        os.makedirs(directory)

# initialize save folder
create_dir(save_path)

class Configs():
    def __init__(self):
        # saving and loading paths
        self.raw_data_path = os.path.join(save_path, 'train_convai_gpt')
        self.val_data_path = os.path.join(save_path, 'valid_convai_gpt')
        self.output_dir = os.path.join(save_path, 'checkpoint/model/')
        self.model_name_or_path = os.path.join(save_path,'checkpoint/model/')
        self.plot_path = os.path.join(save_path,'samples/')
        self.download_name = 'microsoft/DialoGPT-medium'
        self.i2p_path = os.path.join(save_path, 'i2p')
        # eval
        self.do_eval = True
        self.evaluate_during_training = False
        # batching
        self.batch_size = int(bs)
        self.eval_batch_size = 1
        # optimization
        self.gradient_accumulation_steps = int(gradient_accumulation_steps)
        self.lr = float(lr)
        self.weight_decay = float(weight_decay)
        self.eps = float(1e-8)
        self.max_grad_norm = 1.0
        self.num_train_epochs = int(epochs)
        self.max_steps = -1
        self.warmup_steps = 0
        # logging
        self.logging_steps = int(logging_steps)
        self.save_steps = int(save_steps)
        # fp16
        self.use_token_ids = False
        self.seed = 42
        self.fp16 = False
        self.fp16_opt_level = 'O1'
        
opts = Configs()

# global pretrained model and tokenizer
def load_from_pretrained():
    try: 
        print("*"*50)
        print("Load from checkpoint")
        tokenizer = GPT2Tokenizer.from_pretrained(opts.model_name_or_path, 
                                                pad_token='<|endoftext|>', cls_token='<|cls|>',
                                                sep_token='<|sep|>')
        model = GPT2LMHeadModel.from_pretrained(opts.model_name_or_path)
        try:
            with open(os.path.join(opts.output_dir, 'stats.pkl'), 'rb') as f:
                stats = pickle.load(f)
        except: 
            print("Can't find training stats...")
            stats = None
        print("*"*50)
    except Exception as e:
        print(e)
        try:
            # from dialogpt pretrained
            print("*"*50)
            print("Load from pretrained")
            print("*"*50)
            tokenizer = GPT2Tokenizer.from_pretrained(tokenizer_path, 
                                                pad_token='<|endoftext|>', cls_token='<|cls|>',
                                                sep_token='<|sep|>')
            model =  GPT2LMHeadModel.from_pretrained(model_path)
        except:
            print("*"*50)
            print("Downloading ... ")
            print("*"*50)
            # download dialogpt
            tokenizer = AutoTokenizer.from_pretrained(opts.download_name, 
                                                pad_token='<|endoftext|>', cls_token='<|cls|>',
                                                sep_token='<|sep|>')
            model = AutoModelWithLMHead.from_pretrained(opts.download_name)
            # save to dialogpt
            tokenizer.save_pretrained(tokenizer_path)
            model.save_pretrained(model_path)
        stats = None
    tokenizer.add_special_tokens({'additional_special_tokens': ['<|start|>', '<|p1|>', '<|p2|>']})
    model.resize_token_embeddings(len(tokenizer))
    return model.to(device), tokenizer, stats
    
model, tokenizer, stats = load_from_pretrained()
p1_tok, p2_tok, start_tok = tokenizer.encode('<|p1|>')[0], tokenizer.encode('<|p2|>')[0], tokenizer.encode('<|start|>')[0]
