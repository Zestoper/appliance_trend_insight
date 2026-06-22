import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("appliance_docs")

total = collection.count()
print(f"저장된 문서 수: {total}개\n")

if total == 0:
    print("아직 저장된 데이터가 없습니다.")
    print("서버 실행 후 제품 검색/분석을 해야 데이터가 쌓입니다.")
else:
    # 최근 저장된 문서 10개 조회
    result = collection.get(limit=10, include=["documents", "metadatas"])

    for i, (doc, meta) in enumerate(zip(result["documents"], result["metadatas"])):
        print(f"[{i+1}] 소스: {meta.get('source', '-')} | 제품: {meta.get('product', '-')}")
        print(f"     내용: {doc[:80]}...")
        print()
