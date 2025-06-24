# azure-ai-work-inspector

## Overview

`azure-ai-work-inspector` is a sample application for analyzing videos and extracting insights using Azure AI services. It combines Azure OpenAI Service and other Azure Services to process video content and generate meaningful insights through AI-driven analysis.

## Azure Resources

You’ll need to create the following Azure resources:

1. **Azure OpenAI Service**
2. **Azure Blob Storage**
3. **Azure Container Registry (ACR)**
4. **Azure App Service (Web App for Containers)**
5. **GitHub repository** (with GitHub Actions configured to build and push Docker images to ACR)

---

## 1. Azure OpenAI Service

### Portal

1. Sign in to the [Azure portal].
2. Click **Create a resource** and search for **Azure OpenAI**.
3. On the **Basics** tab, specify:

   * **Subscription**, **Resource group**, **Region**
   * **Name** (e.g. `MyOpenAIResource`)
   * **Pricing tier**: Standard S0
4. (Optional) Under **Networking**, restrict access to selected networks or configure a private endpoint.
5. Review + create. Once provisioned, navigate to your resource and deploy a model (e.g. `gpt-4.1`).

For full portal instructions, see [Quickstart: Create an Azure OpenAI Service resource]. ([learn.microsoft.com][1])

### Azure CLI

```bash
# Create a resource group (if needed)
az group create \
  --name myResourceGroup \
  --location eastus

# Create the Azure OpenAI resource
az cognitiveservices account create \
  --name MyOpenAIResource \
  --resource-group myResourceGroup \
  --kind OpenAI \
  --sku S0 \
  --location eastus
```

([learn.microsoft.com][1])

---

## 2. Azure Blob Storage

### Portal

1. In the [Azure portal], click **Create a resource** → **Storage account**.
2. Fill in:

   * **Subscription**, **Resource group**, **Storage account name** (globally unique), **Region**
   * **Performance/Replication** settings as needed.
3. After creation, go to **Containers** and add a new container (e.g. `mycontainer`) with **Private** access.

Refer to [Create a storage account using Azure CLI or portal] for full details. ([learn.microsoft.com][2])

### Azure CLI

```bash
# Create a storage account
az storage account create \
  --name mystorageacct \
  --resource-group myResourceGroup \
  --location eastus \
  --sku Standard_LRS \
  --kind StorageV2

# Create a blob container
az storage container create \
  --account-name mystorageacct \
  --name mycontainer \
  --auth-mode login
```

([learn.microsoft.com][2])

---

## 3. Azure Container Registry (ACR)

### Portal

1. In the [Azure portal], click **Create a resource** → **Container Registry**.
2. Specify:

   * **Subscription**, **Resource group**, **Registry name** (5–50 lowercase alphanumeric characters)
   * **SKU**: Standard (or Basic/Premium as needed)
3. Under **Access keys**, enable **Admin user** if you want user/password authentication.

See the [Quickstart: Create a private container registry using the Azure CLI] for more. ([learn.microsoft.com][3])

### Azure CLI

```bash
# Create the registry
az acr create \
  --resource-group myResourceGroup \
  --name myContainerRegistry \
  --sku Standard \
  --admin-enabled true
```

([learn.microsoft.com][3])

---

## 4. Azure App Service (Web App for Containers)

### Portal

1. In the [Azure portal], click **Create a resource** → **App Service**.
2. Under **Publish**, select **Container**.
3. Choose your **Container Registry** (ACR), **Image** and **Tag**.
4. Configure the **App Service Plan** (Linux SKU, e.g. B1).
5. Review + create.

For detailed steps, see [Quickstart: Run a custom container on App Service].

### Azure CLI

```bash
# 1. Create an App Service plan (Linux)
az appservice plan create \
  --name myPlan \
  --resource-group myResourceGroup \
  --is-linux \
  --sku B1

# 2. Create the Web App with a container from ACR
az webapp create \
  --resource-group myResourceGroup \
  --plan myPlan \
  --name myAppName \
  --deployment-container-image-name mycontainerregistry.azurecr.io/myapp:latest
```

([learn.microsoft.com][4])

> **Note:**
>
> * If your registry is private, you may need to configure access credentials via `az webapp config container set`.
> * See the \[az webapp create reference]\[webapp-cli-doc] for additional options (runtime, local git, custom domains, etc.).

---

## 5. GitHub Repository & CI/CD

This repository includes a pre-configured GitHub Actions workflow (`.github/workflows/docker-build-push.yml`) that automatically builds and pushes Docker images to Azure Container Registry when code is pushed to the main branch.

### Required GitHub Secrets

Configure the following secrets in your GitHub repository settings:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Add the following repository secrets:

   * `ACR_USERNAME`: Your ACR admin username
   * `ACR_PASSWORD`: Your ACR admin password

### Automatic Deployment

The workflow will automatically trigger on:
* Push to `main` branch
* Pull requests to `main` branch
* Manual workflow dispatch

When triggered, it will:
1. **Build** the Docker image from your Dockerfile
2. **Log in** to ACR using the configured secrets
3. **Push** the image to ACR with both the commit SHA and `latest` tags
4. Use Docker layer caching for faster builds

---

## Local Development

1. Copy the sample `.env.example` to `.env` and populate:

   ```properties
   AZURE_OPENAI_API_KEY=<your-key>
   AZURE_OPENAI_ENDPOINT=https://<your-openai-resource>.openai.azure.com/
   BLOB_CONNECTION_STRING=<your-storage-conn-string>
   BLOB_CONTAINER_NAME=<your-blob-container-name>
   ```
2. Create and activate a Python virtual environment (Python 3.12+ recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```
4. Run the app:

   ```bash
   streamlit run apps/app.py
   ```

---

By following these steps and using the provided CLI snippets and portal links, you can provision all required Azure resources, deploy the containerized application, and run `azure-ai-work-inspector` both locally and in production.

[Azure portal]: https://portal.azure.com
[Quickstart: Create an Azure OpenAI Service resource]: https://learn.microsoft.com/azure/ai-services/openai/how-to/create-resource
[Create a storage account using Azure CLI or portal]: https://learn.microsoft.com/azure/storage/common/storage-account-create
[Quickstart: Create a private container registry using the Azure CLI]: https://learn.microsoft.com/azure/container-registry/container-registry-get-started-azure-cli
[Quickstart: Run a custom container on App Service]: https://learn.microsoft.com/azure/app-service/quickstart-custom-container

[1]: https://learn.microsoft.com/azure/ai-services/openai/how-to/create-resource
[2]: https://learn.microsoft.com/azure/storage/common/storage-account-create
[3]: https://learn.microsoft.com/azure/container-registry/container-registry-get-started-azure-cli
[4]: https://learn.microsoft.com/cli/azure/webapp?view=azure-cli-latest
