python graph_rag/cleanup.py
python graph_rag/builder.py
python graph_rag/create_vector_index.py
python graph_rag/populate_vector_index.py

rm -rf rag/.rag_store.json
python rag/ingest.py
