# -*- coding: utf-8 -*-
"""automated_response_generator.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1Dth6BRtnkBBdVszEwepHpvlRGLN-Hxdz
"""

# Mount Google Drive to access the dataset
from google.colab import drive
drive.mount('/content/drive')

# Import necessary libraries
import pandas as pd

# Load the dataset
data_path = "//content/Customer-Support.csv"
df = pd.read_csv(data_path)

# Explore the dataset
print(df.head())
print(df.info())

# Mount Google Drive to access the dataset (if needed)
# from google.colab import drive
# drive.mount('/content/drive')

# Install necessary libraries
!pip install transformers pandas

# Import necessary libraries
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import T5ForConditionalGeneration, T5Tokenizer

# Load the dataset
data_path = "//content/Customer-Support.csv"
df = pd.read_csv(data_path)

# Display the first few rows of the dataset
print("Dataset Head:\n", df.head())
print("\nDataset Info:\n", df.info())

# Check for missing values and handle them
df.dropna(subset=['query', 'response'], inplace=True)

# Define a custom dataset class
class SupportDataset(Dataset):
    def __init__(self, queries, responses, tokenizer, max_length=512):
        self.queries = queries
        self.responses = responses
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.queries)

    def __getitem__(self, idx):
        query = str(self.queries[idx])
        response = str(self.responses[idx])

        input_text = "query: " + query + " </s>"
        target_text = response + " </s>"

        input_ids = self.tokenizer.encode(input_text, max_length=self.max_length, truncation=True, padding="max_length")
        target_ids = self.tokenizer.encode(target_text, max_length=self.max_length, truncation=True, padding="max_length")

        return {"input_ids": torch.tensor(input_ids, dtype=torch.long),
                "attention_mask": torch.tensor([int(i != 0) for i in input_ids], dtype=torch.long),
                "decoder_input_ids": torch.tensor(target_ids, dtype=torch.long),
                "decoder_attention_mask": torch.tensor([int(i != 0) for i in target_ids], dtype=torch.long),
                "labels": torch.tensor(target_ids, dtype=torch.long)}

# Tokenizer and model initialization
tokenizer = T5Tokenizer.from_pretrained('t5-small')
model = T5ForConditionalGeneration.from_pretrained('t5-small')

# Create train and validation datasets
# Adjust the split ratio if needed
train_size = int(0.8 * len(df))
val_size = len(df) - train_size

# Use iloc to ensure correct slicing of the DataFrame
train_dataset = SupportDataset(df.iloc[:train_size]['query'].tolist(), df.iloc[:train_size]['response'].tolist(), tokenizer)
val_dataset = SupportDataset(df.iloc[train_size:]['query'].tolist(), df.iloc[train_size:]['response'].tolist(), tokenizer)

# Check if the validation dataset is empty
if len(val_dataset) == 0:
    print("Warning: Validation dataset is empty. Check your data splitting logic.")

# Define data loaders
train_loader = DataLoader(train_dataset, batch_size=4, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=4, shuffle=False)

# Training function
def train_epoch(model, loader, optimizer, device):
    model.train()
    total_loss = 0.0
    for batch in loader:
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['labels'].to(device)

        optimizer.zero_grad()
        outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
        loss = outputs.loss
        total_loss += loss.item()

        loss.backward()
        optimizer.step()

    return total_loss / len(loader)

# Validation function
def validate_epoch(model, loader, device):
    model.eval()
    total_loss = 0.0
    with torch.no_grad():
        for batch in loader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            total_loss += loss.item()

    return total_loss / len(loader)

# Training loop
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)

for epoch in range(3):
    train_loss = train_epoch(model, train_loader, optimizer, device)
    val_loss = validate_epoch(model, val_loader, device)
    print(f"Epoch {epoch+1}: Train Loss - {train_loss}, Val Loss - {val_loss}")

# Function to generate response
def generate_response(query, model, tokenizer, device):
    input_text = "query: " + query + " </s>"
    input_ids = tokenizer.encode(input_text, return_tensors="pt").to(device)

    with torch.no_grad():
        outputs = model.generate(input_ids=input_ids, max_length=100, num_beams=4, early_stopping=True)

    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response

# Example usage of the generate_response function and updating the dataframe with generated responses
df['generated_response'] = df['query'].apply(lambda query: generate_response(query, model, tokenizer, device))

# Save the updated dataframe to a new CSV file
output_path = "//content/Customer-Support-with-Generated-Responses.csv"
df.to_csv(output_path, index=False)
print(f"Updated dataset saved to {output_path}")

# Display the first few rows of the updated dataframe
print("Updated Dataset Head:\n", df.head())