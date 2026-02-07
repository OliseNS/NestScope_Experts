# Bird Colony SQL Chatbot API Server

A FastAPI-based REST API server that converts natural language questions into SQL queries and provides answers based on bird colony observation data from 2010-2021.

## Features

- **Natural Language to SQL**: Converts user questions to SQL queries using LLM
- **Query Execution**: Executes SQL queries against SQLite database
- **Natural Language Answers**: Generates human-readable answers from query results
- **RESTful API**: Clean REST endpoints for integration with any client
- **CORS Enabled**: Can be accessed from web browsers
- **Health Monitoring**: Health check endpoint for monitoring

## Installation

### Prerequisites

- Python 3.8+
- SQLite database (`bird_data.db`) in parent directory
- OpenRouter API key

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
Create a `.env` file in the parent directory (or set environment variables):
```env
OPENROUTER_API_KEY=your_api_key_here
DB_PATH=../bird_data.db  # Optional, defaults to ../bird_data.db
```

## Running the Server

### Development Mode

```bash
python main.py
```

The server will start on `http://localhost:8000`

### Production Mode with Uvicorn

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### With Auto-Reload (for development)

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### GET `/`
Root endpoint that returns API information and available endpoints.

**Response:**
```json
{
  "message": "Bird Colony SQL Chatbot API",
  "version": "1.0.0",
  "endpoints": {
    "/ask": "POST - Ask a question in natural language",
    "/schema": "GET - Get database schema",
    "/stats": "GET - Get database statistics",
    "/health": "GET - Health check"
  }
}
```

### GET `/health`
Health check endpoint to verify server and database connectivity.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### GET `/schema`
Returns the complete database schema including table structures and sample data.

**Response:**
```json
{
  "tables": {
    "observations": {
      "columns": [
        {
          "name": "year",
          "type": "INTEGER",
          "notnull": 0,
          "pk": 0
        },
        ...
      ],
      "sample_data": [...]
    },
    ...
  }
}
```

### GET `/stats`
Returns database statistics including observation counts, year ranges, and more.

**Response:**
```json
{
  "total_observations": 15234,
  "year_range": "2010-2021",
  "total_colonies": 156,
  "total_species": 42,
  "states": ["AL", "FL", "LA", "MS", "TX"],
  "observations_by_year": {
    "2010": 1234,
    "2011": 1456,
    ...
  }
}
```

### POST `/ask`
Ask a question in natural language. The API will convert it to SQL, execute the query, and return results with a natural language answer.

**Request Body:**
```json
{
  "question": "What colonies had oil present in 2010?",
  "model": "anthropic/claude-3.5-sonnet"  // Optional, defaults to claude-3.5-sonnet
}
```

**Response:**
```json
{
  "sql_query": "SELECT colony_name, COUNT(*) as observations FROM observations WHERE year = 2010 AND oil_present = 'Y' GROUP BY colony_name ORDER BY observations DESC LIMIT 50",
  "results": [
    {
      "colony_name": "Breton Island",
      "observations": 45
    },
    ...
  ],
  "results_count": 12,
  "answer": "In 2010, there were 12 colonies that had oil present from the Deepwater Horizon spill. The most affected colony was Breton Island with 45 observations...",
  "error": null
}
```

**Error Response:**
```json
{
  "sql_query": "ERROR: Not relevant to this dataset",
  "results": null,
  "results_count": 0,
  "answer": "",
  "error": "ERROR: Not relevant to this dataset"
}
```

## Example Usage

### Using cURL

```bash
# Health check
curl http://localhost:8000/health

# Get database stats
curl http://localhost:8000/stats

# Ask a question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the top 5 most observed species?"}'
```

### Using Python `requests`

```python
import requests

# Ask a question
response = requests.post(
    "http://localhost:8000/ask",
    json={
        "question": "What colonies had oil present in 2010?",
        "model": "anthropic/claude-3.5-sonnet"
    }
)

data = response.json()
print(f"SQL Query: {data['sql_query']}")
print(f"Results: {data['results_count']} rows")
print(f"Answer: {data['answer']}")
```

### Using JavaScript/Fetch

```javascript
const response = await fetch('http://localhost:8000/ask', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    question: 'What colonies had oil present in 2010?',
    model: 'anthropic/claude-3.5-sonnet'
  })
});

const data = await response.json();
console.log('SQL Query:', data.sql_query);
console.log('Results:', data.results);
console.log('Answer:', data.answer);
```

## Interactive API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: Visit `http://localhost:8000/docs`
- **ReDoc**: Visit `http://localhost:8000/redoc`

These interfaces allow you to test all endpoints directly from your browser.

## Architecture

The server uses a three-step process for each question:

1. **SQL Generation**: Uses an LLM to convert natural language to SQL
   - Includes database schema in prompt
   - Validates question relevance
   - Cleans and formats SQL output

2. **Query Execution**: Executes the SQL query against SQLite database
   - Returns results as pandas DataFrame
   - Handles errors gracefully

3. **Answer Generation**: Uses an LLM to create natural language answer
   - Includes query results in prompt
   - Provides contextual, informative responses

## Database Schema

The API works with four main tables:

- **observations**: Individual bird observation records (year, colony, species, habitat, notes)
- **colony_profiles**: Aggregated data per colony
- **colony_inventory**: Master list of colonies with geographic data
- **species**: Species code to name lookup

## Configuration

### Environment Variables

- `OPENROUTER_API_KEY`: Your OpenRouter API key (required)
- `DB_PATH`: Path to SQLite database (default: `../bird_data.db`)

### Modifying the Model

You can specify different models per request or change the default in the code:

```python
# In main.py, modify the default:
chatbot = SQLChatbot(model="anthropic/claude-3.5-sonnet")

# Or specify per request:
POST /ask
{
  "question": "...",
  "model": "openai/gpt-4"
}
```

## Error Handling

The API returns appropriate HTTP status codes:

- `200`: Success
- `500`: Internal server error (database, LLM, or processing error)
- `503`: Service unavailable (database connection failed)

Error responses include detailed error messages in the response body.

## Performance Considerations

- Database connections are created per request (no connection pooling)
- Query results are limited to 50 rows by default (configurable in SQL generation prompt)
- Schema is cached after first load
- CORS is enabled for all origins (configure for production)

## Security Notes

For production deployment:

1. **Restrict CORS**: Update `allow_origins` to specific domains
2. **Add Authentication**: Implement API key or OAuth
3. **Rate Limiting**: Add rate limiting middleware
4. **Input Validation**: Additional validation for malicious inputs
5. **Database Access**: Use read-only database connection
6. **Environment Variables**: Secure storage for API keys

## Troubleshooting

### Database Connection Error

Ensure `bird_data.db` exists in the parent directory or set `DB_PATH` environment variable:

```bash
export DB_PATH=/path/to/bird_data.db
```

### OpenRouter API Error

Verify your API key is set correctly:

```bash
export OPENROUTER_API_KEY=your_key_here
```

### Port Already in Use

Change the port:

```bash
uvicorn main:app --port 8001
```

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest httpx

# Run tests
pytest
```

### Code Structure

```
server/
├── main.py              # FastAPI application and endpoints
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## License

[Your License Here]

## Support

For issues or questions, please open an issue in the repository.
