# Model Configuration Guide

## Overview

NestScope uses a **centralized model configuration** via the `.env` file. You only need to change the model in **ONE place** - the `.env` file.

## ⚠️ IMPORTANT: Single Source of Truth

The `MODEL_NAME` in `.env` is the **ONLY** place you need to change the model. All components (backend, frontend, API) automatically use this value.

## Configuration

### 1. Edit your `.env` file:

```bash
# Default model
MODEL_NAME=anthropic/claude-sonnet-4.5

# Or use a different model:
# MODEL_NAME=google/gemini-3-flash-preview
# MODEL_NAME=google/gemini-pro-1.5
# MODEL_NAME=anthropic/claude-opus-4.5
# MODEL_NAME=openai/gpt-4-turbo
```

### 2. Restart the server:

```bash
# Stop the current server (Ctrl+C)
# Then restart
./run_app.sh
```

## Available Models

### Recommended Models (via OpenRouter):

**Claude Models (Default):**
- `anthropic/claude-sonnet-4.5` - **Default** - Excellent balance of speed, quality, and cost
- `anthropic/claude-opus-4.5` - Best quality, most accurate (expensive)
- `anthropic/claude-sonnet-4` - Fast, good balance of speed/quality
- `anthropic/claude-3.5-sonnet` - Fast and capable

**Google Models:**
- `google/gemini-3-flash-preview` - Fast, cost-effective, good quality
- `google/gemini-pro-1.5` - Higher quality, more capable

**OpenAI Models:**
- `openai/gpt-4-turbo` - OpenAI's flagship model
- `openai/gpt-4o` - Optimized for speed
- `openai/gpt-3.5-turbo` - Fast and cost-effective

**Other Models:**
- `meta-llama/llama-3-70b-instruct` - Open source alternative

See [OpenRouter Models](https://openrouter.ai/models) for the complete list.

## Cost Considerations

Different models have different costs. Check [OpenRouter Pricing](https://openrouter.ai/models) for current rates.

**Cost Ranking (approximate):**
1. **Most Expensive**: `anthropic/claude-opus-4.5` - Highest quality
2. **Moderate**: `anthropic/claude-sonnet-4.5` (default), `openai/gpt-4-turbo`, `google/gemini-pro-1.5`
3. **Budget**: `google/gemini-3-flash-preview`, `openai/gpt-3.5-turbo`, `anthropic/claude-3.5-sonnet`
4. **Cheapest**: Open source models like Llama

## How It Works

### 1. Default Configuration

If `MODEL_NAME` is set in `.env`:
```bash
MODEL_NAME=anthropic/claude-sonnet-4
```

All queries will use this model by default.

### 2. Per-Request Override (API only)

You can override the model for specific API requests:

```python
import requests

response = requests.post("http://localhost:8000/ask", json={
    "question": "Show brown pelican trends",
    "model": "anthropic/claude-3.5-sonnet"  # Override default
})
```

### 3. Priority Order

1. **Request model** (if provided in API call) - Highest priority
2. **MODEL_NAME** from `.env` - Used if no request model (recommended)
3. **Default fallback** (`anthropic/claude-sonnet-4.5`) - If env not set

### 4. Centralized Configuration

**Backend (`server/main.py`)** and **Frontend (`frontend/services/`)** both read from the same `.env` file automatically. You don't need to change code in multiple places.

## Examples

### Example 1: Use Sonnet 4.5 (Default)

```bash
# .env file
MODEL_NAME=anthropic/claude-sonnet-4.5
```

Restart server. All queries now use Sonnet 4.5 (balanced speed and quality).

### Example 2: Use GPT-4

```bash
# .env file
MODEL_NAME=openai/gpt-4-turbo
```

Restart server. All queries now use GPT-4.

### Example 3: Keep Default

```bash
# .env file
MODEL_NAME=anthropic/claude-sonnet-4.5
# or simply don't set MODEL_NAME at all
```

Uses the default Claude Sonnet 4.5 (balanced speed and quality).

## Troubleshooting

### Model Not Found Error

**Error**: `"Model not found"`

**Solution**: Check the model name is correct. See [OpenRouter Models](https://openrouter.ai/models) for valid names.

### Authentication Error

**Error**: `"Authentication failed"`

**Solution**: Ensure your `OPENROUTER_API_KEY` is valid and has access to the requested model.

### Server Not Using New Model

**Solution**: Make sure you restarted the server after changing `.env`:
```bash
# Kill the old server
pkill -f uvicorn

# Restart
./run_app.sh
```

## Performance Tips

### For Best Quality:
```bash
MODEL_NAME=anthropic/claude-opus-4.5
```
- Most accurate SQL generation
- Best natural language answers
- Highest cost

### For Balanced Performance (Recommended):
```bash
MODEL_NAME=anthropic/claude-sonnet-4.5
```
- Excellent balance of speed and quality (default)
- Fast responses
- Moderate cost

### For Budget:
```bash
MODEL_NAME=google/gemini-3-flash-preview
```
- Fast responses
- Good quality for most queries
- Very cost-effective

### For Higher Quality:
```bash
MODEL_NAME=google/gemini-pro-1.5
```
- Better reasoning than Flash
- Good balance of quality and cost
- Faster than Claude Opus

## Testing

After changing the model, test with a simple query:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How many bird species are in the database?"}'
```

Check the logs to verify which model is being used:
```bash
tail -f logs/server.log
```

## Summary

- ✅ **Centralized Configuration**: Change model in **ONE place only** (`.env` file)
- ✅ **Default Model**: Set in `.env` via `MODEL_NAME`
- ✅ **Easy to Change**: Edit `.env` and restart
- ✅ **Flexible**: Override per-request via API
- ✅ **Cost Control**: Choose models based on budget
- ✅ **Quality Control**: Use Opus for best results, Sonnet 4.5 for balanced performance

**Default if not set**: `anthropic/claude-sonnet-4.5`

## Architecture Notes

The configuration flows as follows:
1. `.env` file contains `MODEL_NAME=anthropic/claude-sonnet-4.5`
2. Backend (`server/main.py`) reads it via `os.getenv("MODEL_NAME")`
3. Frontend (`frontend/services/config.py`) reads it via `os.getenv("MODEL_NAME")`
4. Both use the same value automatically - no duplication needed!
