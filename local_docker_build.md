GitHub Actionsパイプラインをローカルで実行する手順を詳しく説明します。

## Windowsローカルで Docker Build を実行する手順

### 事前準備

#### 1. Docker Desktop のインストール

1. **Docker Desktop for Windows をダウンロード**
   - [Docker Desktop公式サイト](https://www.docker.com/products/docker-desktop/)からダウンロード
   - WSL2を使用することを推奨

2. **インストール後の設定**
   - Docker Desktopを起動
   - PowerShellで動作確認:
   ```powershell
   docker --version
   ```

#### 2. Azure Container Registry (ACR) の認証情報

ACRの管理者ユーザーが有効化されているため、以下の認証情報を使用:
- **ユーザー名**: ACRの管理者ユーザ名（Azure Portal > Container Registry > アクセスキーで確認）
- **パスワード**: ACRの管理者パスワード（Azure Portal > Container Registry > アクセスキーで確認）

### ローカル実行手順

#### Step 1: リポジトリの準備

```powershell
# プロジェクトのルートディレクトリに移動
cd c:\Users\<USER NAME>\repo\<YOUR REGISTRY NAME>

# 最新のコードを取得（必要に応じて）
git pull origin main
```

#### Step 2: Docker イメージのビルド

```powershell
# 現在のGitコミットハッシュを取得
$IMAGE_TAG = git rev-parse HEAD

# 環境変数を設定
$REGISTRY_NAME = "<YOUR REGISTRY NAME>"
$REPOSITORY_NAME = "<YOUR REPOSITORY NAME>"

# Dockerイメージをビルド
docker build -t "${REGISTRY_NAME}.azurecr.io/${REPOSITORY_NAME}:${IMAGE_TAG}" .
docker build -t "${REGISTRY_NAME}.azurecr.io/${REPOSITORY_NAME}:latest" .
```

#### Step 3: ACR へのログイン

```powershell
# ACRにログイン（管理者ユーザーの認証情報を使用）
docker login "${REGISTRY_NAME}.azurecr.io"
# Username: <YOUR REGISTRY NAME>
# Password: [ACRの管理者パスワード]
```

#### Step 4: Docker イメージのプッシュ

```powershell
# イメージをACRにプッシュ
docker push "${REGISTRY_NAME}.azurecr.io/${REPOSITORY_NAME}:${IMAGE_TAG}"
docker push "${REGISTRY_NAME}.azurecr.io/${REPOSITORY_NAME}:latest"
```

#### Step 5: ローカルでの動作確認

```powershell
# ローカルでアプリケーションを実行してテスト
docker run -p 8000:8000 "${REGISTRY_NAME}.azurecr.io/${REPOSITORY_NAME}:latest"
```

ブラウザで `http://localhost:8000` にアクセスしてアプリケーションが正常に動作することを確認

### 【自動化する場合のオプション】完全な実行スクリプト

以下のPowerShellスクリプトを作成して、一連の作業を自動化できます：

````powershell
# Azure AI Work Inspector - ローカルビルド・プッシュスクリプト

# 環境変数の設定
$REGISTRY_NAME = "<YOUR REGISTRY NAME>"
$REPOSITORY_NAME = "azure-ai-work-inspector"
$IMAGE_TAG = git rev-parse HEAD

Write-Host "=== Azure AI Work Inspector - ローカルビルド・プッシュ ===" -ForegroundColor Green

# Step 1: Dockerイメージのビルド
Write-Host "Step 1: Dockerイメージをビルドしています..." -ForegroundColor Yellow
docker build -t "${REGISTRY_NAME}.azurecr.io/${REPOSITORY_NAME}:${IMAGE_TAG}" .
docker build -t "${REGISTRY_NAME}.azurecr.io/${REPOSITORY_NAME}:latest" .

if ($LASTEXITCODE -ne 0) {
    Write-Host "エラー: Dockerビルドに失敗しました" -ForegroundColor Red
    exit 1
}

# Step 2: ACRにログイン
Write-Host "Step 2: ACRにログインしています..." -ForegroundColor Yellow
Write-Host "ACRの認証情報を入力してください:" -ForegroundColor Cyan
Write-Host "Username: <YOUR REGISTRY NAME>" -ForegroundColor Cyan
docker login "${REGISTRY_NAME}.azurecr.io"

if ($LASTEXITCODE -ne 0) {
    Write-Host "エラー: ACRログインに失敗しました" -ForegroundColor Red
    exit 1
}

# Step 3: イメージをプッシュ
Write-Host "Step 3: イメージをプッシュしています..." -ForegroundColor Yellow
docker push "${REGISTRY_NAME}.azurecr.io/${REPOSITORY_NAME}:${IMAGE_TAG}"
docker push "${REGISTRY_NAME}.azurecr.io/${REPOSITORY_NAME}:latest"

if ($LASTEXITCODE -ne 0) {
    Write-Host "エラー: イメージのプッシュに失敗しました" -ForegroundColor Red
    exit 1
}

Write-Host "=== 完了 ===" -ForegroundColor Green
Write-Host "イメージが正常にプッシュされました:" -ForegroundColor Green
Write-Host "  - ${REGISTRY_NAME}.azurecr.io/${REPOSITORY_NAME}:${IMAGE_TAG}" -ForegroundColor Cyan
Write-Host "  - ${REGISTRY_NAME}.azurecr.io/${REPOSITORY_NAME}:latest" -ForegroundColor Cyan

# Step 4: ローカルテスト（オプション）
$test = Read-Host "ローカルでテストしますか？ (y/n)"
if ($test -eq "y" -or $test -eq "Y") {
    Write-Host "ローカルテストを開始します..." -ForegroundColor Yellow
    Write-Host "http://localhost:8000 でアプリケーションにアクセスできます" -ForegroundColor Cyan
    Write-Host "終了するには Ctrl+C を押してください" -ForegroundColor Cyan
    docker run -p 8000:8000 "${REGISTRY_NAME}.azurecr.io/${REPOSITORY_NAME}:latest"
}
````

### スクリプトの実行

```powershell
# 実行権限を設定
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# スクリプトを実行
.\local-build-push.ps1
```

### トラブルシューティング

1. **Docker Desktop が起動していない場合**
   - Docker Desktopを起動してから実行

2. **ACR認証エラーが発生する場合**
   - Azure Portal > Container Registry > アクセスキーでパスワードを確認
   - ユーザー名が `<YOUR REGISTRY NAME>` であることを確認

3. **ビルドエラーが発生する場合**
   ```powershell
   # Dockerキャッシュをクリア
   docker system prune -a
   ```