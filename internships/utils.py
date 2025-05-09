from sentence_transformers import SentenceTransformer
import numpy as np

model = None

# To reduce memory usage in production:
def get_embedding_model():
    global model
    if model is None:
        model = SentenceTransformer(
            'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
            device='cpu'
        )
        # Lightweight mode
        # model.max_seq_length = 128  # Reduce from default 256
    return model

def generate_embedding(text: str) -> np.array:
    return get_embedding_model().encode(text)