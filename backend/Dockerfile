FROM python:3.12-slim

# 다나와 HTML 파싱을 스레드(asyncio.to_thread)에서 돌리는데 glibc는 스레드마다 메모리 영역(arena)을 따로 만들어
# 반납이 잘 안 된다 → 512MB 무료 서버에서 메모리가 계속 불어나다 죽는 원인이 된다. 영역 수를 2개로 제한
ENV MALLOC_ARENA_MAX=2

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
