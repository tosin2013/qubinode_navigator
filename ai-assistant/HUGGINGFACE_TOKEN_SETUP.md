# Hugging Face Token Setup

This document explains how to set up Hugging Face authentication tokens for the AI Assistant to download models.

## Supported Model

**Default Supported Model**: `granite-4.0-micro`
- This is the officially supported and tested model for Qubinode AI Assistant
- Other models are available but may require additional troubleshooting
- For alternative models, users are responsible for their own configuration and troubleshooting

## Why is this needed?

The AI Assistant downloads AI models from Hugging Face Hub. Some models require authentication, and even public models benefit from authentication to avoid rate limits.

## Getting a Hugging Face Token

1. Go to [Hugging Face](https://huggingface.co/) and create an account if you don't have one
2. Navigate to your [Settings → Access Tokens](https://huggingface.co/settings/tokens)
3. Click "New token"
4. Give it a name like "qubinode-ai-assistant"
5. Select "Read" permissions (sufficient for downloading models)
6. Copy the generated token

## Local Development Setup

Set the environment variable in your local environment:

```bash
export HUGGINGFACE_TOKEN="hf_your_token_here"
```

Or add it to your `.env` file:

```bash
echo "HUGGINGFACE_TOKEN=hf_your_token_here" >> .env
```

## GitHub Actions Setup

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `HUGGINGFACE_TOKEN`
5. Value: Your Hugging Face token (e.g., `hf_your_token_here`)
6. Click **Add secret**

## Docker Container Setup

When running the container manually, pass the token as an environment variable:

```bash
docker run -d --name ai-assistant \
  -p 8080:8080 \
  -e HUGGINGFACE_TOKEN="hf_your_token_here" \
  quay.io/takinosh/qubinode-ai-assistant:latest
```

## Verification

You can verify the token is working by checking the container logs. You should see:

```
INFO - Using Hugging Face authentication token
INFO - Model downloaded successfully: /app/models/granite-4.0-micro.gguf
```

Instead of:

```
ERROR - Failed to download model: Client error '401 Unauthorized'
```

## Security Notes

- Never commit tokens to version control
- Use repository secrets for GitHub Actions
- Rotate tokens periodically
- Use read-only tokens when possible
- Consider using fine-grained tokens for production deployments

## Troubleshooting

### 401 Unauthorized Error
- Check that your token is valid and not expired
- Ensure the token has read permissions
- Verify the token is correctly set in the environment

### Rate Limiting
- Authenticated requests have higher rate limits
- Consider using a dedicated token for CI/CD

### Model Access
- Some models require explicit permission from the model owner
- Check the model's page on Hugging Face for access requirements
