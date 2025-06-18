FROM python:3.12-slim

# ネイティブライブラリなどが必要な場合はここでインストール
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
		libglib2.0-0 \
        libgl1-mesa-glx \
        libsm6 \
        libxext6 \
        libxrender1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Python 依存をインストール
RUN pip install --no-cache-dir -r requirements.txt

# コンテナ外部に開放するポート
EXPOSE 8000

# Streamlit 起動コマンドに合わせて CMD を指定
CMD ["python", "-m", "streamlit", "run", "apps/app.py", "--server.port", "8000", "--server.address", "0.0.0.0"]
