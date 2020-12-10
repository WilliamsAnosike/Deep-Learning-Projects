# -*- coding: utf-8 -*-
"""DATA 690 Practical Deep Learning Final Project.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1TUQAb8hUl0sGWBWfaYhgGp3XN86cT2by
"""

#loading necessary modules...
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision 
from torchvision import transforms
from torch.utils.data import Dataset, DataLoader
import random
import torchtext.data as data
import csv
from tqdm import tqdm
from google.colab import drive
import pandas as pd
import string
import nltk
import torchtext
from nltk.corpus import stopwords
nltk.download('stopwords')
nltk.download('wordnet')
from nltk.stem.wordnet import WordNetLemmatizer
import re
import spacy
nlp = spacy.load('en')
import time
import sys, os

#Mount Google Drive where files are housed.
drive.mount('/content/gdrive')

# Commented out IPython magic to ensure Python compatibility.
# %cd /content/gdrive/My\ Drive/Colab Notebooks

device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")

#For randomization.
seed = 1997
torch.manual_seed(seed)

#Use 1 value to set up new process train/test files.
process_new_data = 1
#Use 1 value to train a new model. Set to 0 to load previously saved model.
train_new_data = 1

#paths for the saved files. Set to a variable for reproducibility on other datasets.
train_dir = "train.csv"
process_train = "process_train.csv"
test_dir = "test.csv"
process_test = "process_test.csv"

traindata = pd.read_csv(train_dir)
traindata.head()

#Inspiration for this function gotten from https://www.kaggle.com/prabhatkumarsahu/toxic-comment-classification-thecaffeinedev
#Used to clean text data into form that can be input into vocabulary.
punctuations = string.punctuation
stopwords_list = stopwords.words("english")
spacy_tokenizer = torchtext.data.utils.get_tokenizer('spacy')
lemmatizer = WordNetLemmatizer()
def processing(text):
  
    def tokenizer(text):
        text = str.split(text)
        return text
    
    def remove_punctuations(sentence):
        result = "".join([i if i not in punctuations and not i.isdigit() else " " for i in sentence])
        return result
    
    def word_lemmatizer(sentence):
        result = lemmatizer.lemmatize(sentence)
        return result
    
    def word_lowercase(sentence):
        return sentence.lower()
    
    def remove_URL(text):
        url = re.compile(r'https?://\S+|www\.\S+')
        html = re.compile(r'<.*?>')
        text = html.sub(r'',text)
        text = url.sub(r'',str(text))
        return text
  
    def remove_newline(text):
        return text.rstrip("\n")
    
    def clean_comment(sentence):
        result = []
        sentence = remove_newline(sentence)
        sentence = remove_URL(sentence)
        sentence = word_lowercase(sentence)
        sentence = word_lemmatizer(sentence)
        sentence = remove_punctuations(sentence)
        sentence = tokenizer(sentence)

        result = " ".join(sentence)
        return result
     
    text = clean_comment(text)
    if text == "":
        text = "None"
    return text

#new file where cleaned comments from test files will be written to.
if process_new_data:
    with open(test_dir, "r", encoding="utf8") as in_csv, open(process_test, "w", newline="", encoding="utf8") as out_csv:
        read = csv.reader(in_csv)
        write = csv.writer(out_csv)
        next(read, None) 
        for i in tqdm(read):
            i[1] = processing(i[1])
            try:
                write.writerow(i)
            except Exception as e:
               print(e)

#new file where cleaned comments from train files will be written to.
if process_new_data:
    with open(train_dir, "r", encoding="utf8") as in_csv, open(process_train, "w", newline="", encoding="utf8") as out_csv:
        read = csv.reader(in_csv)
        write = csv.writer(out_csv)
        next(read, None) # Skip header
        for i in tqdm(read):
            i[1] = processing(i[1])
            try:
                write.writerow(i)
            except Exception as e:
               print(e)

def token_words(sentence):
    tokens = str.split(sentence)
    return tokens

#https://towardsdatascience.com/use-torchtext-to-load-nlp-datasets-part-i-5da6f1c89d84
TEXT = data.Field(batch_first = True,
                  tokenize = token_words,
                  stop_words=stopwords_list)
LABEL = data.LabelField(dtype = torch.float)
ID = data.LabelField()
ID2 = data.Field(sequential=False)

#https://towardsdatascience.com/use-torchtext-to-load-nlp-datasets-part-i-5da6f1c89d84
features = [["id",ID], ["text", TEXT], ["toxic",LABEL],["s_toxic",LABEL],
          ["obscene",LABEL],["threat",LABEL],["insult",LABEL],["id_hate",LABEL]]
test_features = [["id",ID2], ["text", TEXT]]

data_train = data.TabularDataset(process_train,
                              format = "csv",
                              fields=features,
                              skip_header=True)

data_test = data.TabularDataset(process_test,
                              format= "csv",
                              fields=test_features,
                             skip_header=False)

#Randomizing the datasets.
import random

data_train, data_val = data_train.split(split_ratio=0.8, random_state=random.seed(seed))

#Building the corpus vocabulary.
vocab_size = 40000
TEXT.build_vocab(data_train,
                 min_freq = 3,
                 max_size = vocab_size, 
                 vectors = "glove.6B.100d", 
                 unk_init = torch.Tensor.normal_)
LABEL.build_vocab(data_train)
ID.build_vocab(data_train)
ID2.build_vocab(data_test)

#Set up for the Batch iterator.
BATCH_SIZE = 64
train_iterator, val_iterator = data.BucketIterator.splits((data_train, data_val),
                                                  batch_size=BATCH_SIZE,
                                                  device = device)
test_iterator = data.BucketIterator(data_test,
                                batch_size=BATCH_SIZE,
                                shuffle=False,
                                device = device)

data_train

#Set up of Convolutional Model used to solve problem.
class CNN(nn.Module):
    def __init__(self, vocab_size, embedding_dim, n_filters, filter_sizes, output_dim, 
                 dropout, pad_idx):
        
        super().__init__()
                
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx = pad_idx)
        self.convs = nn.ModuleList([
                                    nn.Conv2d(in_channels = 1, 
                                              out_channels = n_filters, 
                                              kernel_size = (i, embedding_dim)) 
                                    for i in filter_sizes
                                    ])
        self.fc = nn.Linear(len(filter_sizes) * n_filters, output_dim)
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, text):
                
        embedded = self.embedding(text)
        embedded = embedded.unsqueeze(1)
        conved = [F.relu(conv(embedded)).squeeze(3) for conv in self.convs]        
        pooled = [F.max_pool1d(conv, conv.shape[2]).squeeze(2) for conv in conved]
        cat = self.dropout(torch.cat(pooled, dim = 1))
            
        return self.fc(cat)

#Hyperparameters for model.
INPUT_DIM = len(TEXT.vocab)
EMBEDDING_DIM = 100
N_FILTERS = 100
FILTER_SIZES = [3,4,5]
OUTPUT_DIM = 6
DROPOUT = 0.5
PAD_IDX = TEXT.vocab.stoi[TEXT.pad_token]
UNK_IDX = TEXT.vocab.stoi[TEXT.unk_token]

model = CNN(INPUT_DIM, EMBEDDING_DIM, N_FILTERS, FILTER_SIZES, OUTPUT_DIM, DROPOUT, PAD_IDX)

model = model.to(device)
optimizer = torch.optim.Adam(model.parameters(), lr = 3e-5,weight_decay=2e-5)
criterion = nn.BCEWithLogitsLoss().to(device)
print(model)

pretrained_embeddings = TEXT.vocab.vectors
model.embedding.weight.data.copy_(pretrained_embeddings)
model.embedding.weight.data[UNK_IDX] = torch.zeros(EMBEDDING_DIM)
model.embedding.weight.data[PAD_IDX] = torch.zeros(EMBEDDING_DIM)

#Function to reach into batch and for each label, return a (batch_size, 1) dimension tensor.
def get_labels(batch):
    toxic = batch.toxic.unsqueeze(1)
    s_toxic = batch.s_toxic.unsqueeze(1)
    obscene = batch.obscene.unsqueeze(1)
    threat = batch.threat.unsqueeze(1)
    insult = batch.insult.unsqueeze(1)
    id_hate = batch.id_hate.unsqueeze(1)
    labels = torch.cat((toxic,s_toxic,obscene,
                        threat,insult,id_hate),dim=1)
    return labels

#training step by step function.
def train_pace(model, optimizer, criterion, batch):
    batch_size = len(batch)
    model.train()
    
    optimizer.zero_grad()
    text = batch.text.view(batch_size, -1)
    labels = get_labels(batch)

    outputs = model(text)
    loss = criterion(outputs,labels)
    loss.backward()
    optimizer.step()

    return loss.item()

#Training function that runs if train_new_data is set to 1. 
if train_new_data:
    epochs = 2
    loss_list = []
    print("Training starting!")
    for epoch in range(epochs):
        for i, batch in enumerate(train_iterator):
            train_loss = train_pace(model,optimizer, criterion, batch)
            loss_list.append(train_loss)
            print(f"Epoch: [{epoch+1}/{epochs}] | Iterations: [{i+1}/{len(train_iterator)}] | Training loss: {train_loss:.3f}")
    torch.save(model.state_dict(), "model.pt")
          
        
    print("Training Done!")

#Change train_new_data value to 0, if you want to load previously saved model.
if not train_new_data:
    model.load_state_dict(torch.load("model.pt"))

#Predicts toxicity level of all test case comments.
def predict_test_cases(model, test_iterator):
    result = []
    model.eval()
    with torch.no_grad():
        for batch in tqdm(test_iterator):
            batch_size = len(batch)
            text = batch.text.view(batch_size,-1).long()
            ids = batch.id.squeeze().cpu()
            output = model(text)
            output = torch.sigmoid(output).cpu()
            for i,j in zip(ids,output):
                result.append([ID2.vocab.itos[i.numpy()],j.numpy()])
    return result

result = predict_test_cases(model, test_iterator)

"""# **Exploration**"""

#Gotten from https://github.com/bentrevett/pytorch-sentiment-analysis/issues/40
#You feed in a text string and the function returns a tensor showing the toxicty level of the comments. Ranging from 0 - 1.
def sentiment_prediction(model, sentence, min_len = 5):
    model.eval()
    tokenized = [i.text for i in nlp.tokenizer(sentence)]
    if len(tokenized) < min_len:
        tokenized += ['<pad>'] * (min_len - len(tokenized))
    indexed = [TEXT.vocab.stoi[w] for w in tokenized]
    tensor = torch.LongTensor(indexed).to(device)
    tensor = tensor.unsqueeze(0)
    prediction = torch.sigmoid(model(tensor))
    return prediction

label_list = ['toxic', 'severe toxic', 'obscene', 'threat', 'insult', 'identity hate']

def output_results(tensor_results, label_list):

  print("Here are the results!")
  print("This comment is ", (tensor_results.tolist()[0][0])*100, "%", label_list[0],'.')
  print("This comment is ", (tensor_results.tolist()[0][1])*100, "%", label_list[1], '.')
  print("This comment is ", (tensor_results.tolist()[0][2])*100, "%", label_list[2], '.')
  print("This comment is ", (tensor_results.tolist()[0][3])*100, "%", label_list[3], '.')
  print("This comment is ", (tensor_results.tolist()[0][4])*100, "%", label_list[4], '.')
  print("This comment is ", (tensor_results.tolist()[0][5])*100, "%", label_list[5], '.')

output_results(sentiment_prediction(model,text2), label_list)

text2 = processing('stupid bitch')
output_results(sentiment_prediction(model,text2), label_list)

text3 = processing('Hello how are you')
output_results(sentiment_prediction(model,text3), label_list)

text4 = processing('Fuck Donald trump')
output_results(sentiment_prediction(model,text4), label_list)

text5 = processing('i love you')
output_results(sentiment_prediction(model,text5), label_list)



