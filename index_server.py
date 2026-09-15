import os
from multiprocessing import Lock
from multiprocessing.managers import BaseManager
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext, load_index_from_storage, Document
from llama_index.core.agent.workflow import AgentWorkflow, FunctionAgent
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.workflow import Context
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding

persist_dir = "storage"
data_dir = "data"
index = None
lock = Lock()

Settings.node_parser = SentenceSplitter(
    chunk_size=850,
    chunk_overlap=220,
    paragraph_separator="\n\n",
    secondary_chunking_regex=r'[^。！？;\n]+[。！？;\n]?',
)

Settings.embed_model = OllamaEmbedding(
    model_name="embeddinggemma:latest",
    base_url="http://192.168.100.57:11434",
)
Settings.llm = Ollama(
    model="qwen2.5:32b",
    base_url="http://192.168.100.57:11434",
    request_timeout=360.0,
    context_window=8000,
)

def initialize_index():
    global index
    with lock:
        if os.path.exists(persist_dir):
            storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
            index = load_index_from_storage(
                storage_context,
                # embed_model=Settings.embed_model,
            )
        else:
            all_files = os.listdir(data_dir)
            real_files = [
                f for f in all_files
                if not f.startswith(".")
            ]
            
            # 加载文档
            if len(real_files) == 0:
                documents = []
            else:
                documents = SimpleDirectoryReader(data_dir).load_data()
            
            # 创建索引
            index = VectorStoreIndex.from_documents(
                documents,
                # embed_model=Settings.embed_model,  # 默认使用 Settings 中的配置
            )
            index.storage_context.persist(persist_dir)
        print(f"doc数量:{len(index.docstore.docs)}")

def query_index(query_text):
    query_engine = index.as_query_engine(
        similarity_top_k=3,
        # llm=Settings.llm,  # 默认使用 Settings 中的配置
    )
    response = query_engine.query(query_text)
    print(f"retrieve hit nodes: {len(response.source_nodes)}")
    for idx, node in enumerate(response.source_nodes):
        print(f"node{idx} score={node.score:.4f}, text={node.text[:200]}")
    
    return str(response)

def insert_into_index(filepath, doc_id=None):
    global index
    document = SimpleDirectoryReader(input_files=[filepath]).load_data()[0]
    if doc_id is not None:
        document.doc_id = doc_id

    with lock:
        index.insert(document)
        index.storage_context.persist(persist_dir)
        print(f"doc数量:{len(index.docstore.docs)}")

if __name__ == "__main__":
    # init the global index
    print("initializing index...")
    initialize_index()

    # setup server
    # NOTE: you might want to handle the password in a less hardcoded way
    manager = BaseManager(('', 5602), b'password')
    manager.register('query_index', query_index)
    manager.register('insert_into_index', insert_into_index)
    server = manager.get_server()

    print("starting server...")
    server.serve_forever()