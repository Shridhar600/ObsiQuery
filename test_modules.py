from sympy import im
from src.utils import config
from src.embedding import embedding_model_instance,test_embedding_model
from src.llm import llm_instance, test_llm_instance
from src.vector_store import vector_store_instance, test_vector_store

if __name__ == "__main__":
   test_embedding_model(embedding_model_instance)
   # test_llm_instance(llm_instance)
   test_vector_store(vector_store_instance)