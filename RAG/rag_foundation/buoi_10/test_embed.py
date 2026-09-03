import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel

model_name = "thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5"

print(f"Loading model '{model_name}' on CPU...")
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)
model.eval()

# Test embedding function
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0] # First element of model_output contains all token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

def get_embeddings(texts, batch_size=32):
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        encoded_input = tokenizer(batch, padding=True, truncation=True, max_length=512, return_tensors='pt')
        with torch.no_grad():
            model_output = model(**encoded_input)
        sentence_embeddings = mean_pooling(model_output, encoded_input['attention_mask'])
        sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)
        all_embeddings.extend(sentence_embeddings.tolist())
    return all_embeddings

sample_texts = [
    "Điều 1. Phạm vi điều chỉnh",
    "Thông tư này quy định về giao nhận, bảo quản, vận chuyển tiền mặt."
]
emb = get_embeddings(sample_texts)
print(f"Embedding shape: ({len(emb)}, {len(emb[0])})")
print(f"Sample embedding vector preview (first 5 elements): {emb[0][:5]}")
print("SUCCESS: Embeddings generated successfully on CPU!")
