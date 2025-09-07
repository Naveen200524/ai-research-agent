# 🔍 AI Research Agent

A powerful, free, and open-source AI research assistant that automatically searches the web, extracts key insights, and generates comprehensive summaries with citations.

## ✨ Features

- **Multi-Engine Search**: Enhanced DuckDuckGo (free) + optional Brave Search
- **Smart Search Detection**: Automatically uses news backend for news-related queries
- **Advanced Filtering**: Time-based search (past day/week/month/year)
- **Rich Results**: Snippets, timestamps, and enhanced metadata
- **Smart Caching**: Semantic similarity + exact match caching
- **Multiple AI Models**: Gemini 2.0 Flash, Mixtral, Llama 3.2, DeepSeek
- **Automatic Fallback**: Switches between models if one fails
- **Export Options**: PDF, Markdown, JSON
- **100% Free**: Uses free tiers of all services
- **Docker Ready**: One-command deployment

## 🚀 Quick Start

### Prerequisites

1. Get your free API keys:
   - **Google AI** (Required): [Get key](https://makersuite.google.com/app/apikey)
   - **Hugging Face** (Recommended): [Get key](https://huggingface.co/settings/tokens)
   - **Brave Search** (Optional): [Get 2000 free searches/month](https://brave.com/search/api/)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/ai-research-agent.git
cd ai-research-agent
```

2. **Set up environment**
```bash
cp .env.example .env
# Edit .env and add your API keys
```

3. **Run with Docker** (Recommended)
```bash
docker-compose up -d
```

Or **run locally**:
```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Start backend
cd backend
python -m uvicorn api.main:app --reload

# Start frontend (new terminal)
cd frontend
streamlit run streamlit_app.py
```

4. **Access the app**
- Frontend: http://localhost:8501
- API Docs: http://localhost:8000/docs

## 📋 Usage

1. Enter your research query
2. Select search engines and time range
3. Choose summary style (comprehensive, brief, technical)
4. Click "Start Research"
5. Export results as PDF, Markdown, or JSON

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Streamlit  │────▶│   FastAPI   │────▶│   Search    │
│   Frontend  │     │   Backend   │     │   Engines   │
└─────────────┘     └─────────────┘     └─────────────┘
                            │
                    ┌───────┴───────┐
                    │               │
              ┌─────▼─────┐   ┌────▼────┐
              │    LLM    │   │  Cache  │
              │  Manager  │   │ SQLite  │
              └───────────┘   └─────────┘
```

## 🔍 Enhanced Search Capabilities

### DuckDuckGo Integration (FREE - No API Key Required)

The system uses advanced DuckDuckGo search with the following features:

- **Smart Backend Selection**:
  - Regular web search for general queries
  - News backend for news-related queries (detects keywords like "news", "latest", "breaking")
  - Enhanced result formatting with snippets and metadata

- **Time Filtering**:
  - Past day (`pd`)
  - Past week (`pw`)
  - Past month (`pm`)
  - Past year (`py`)

- **Result Enrichment**:
  - Title, URL, and description
  - Relevance scoring
  - Source attribution
  - Timestamps and age information
  - Snippet extraction for better context

### Example Queries with Smart Detection

```json
// Regular search
{"query": "quantum computing basics"}

// News search (auto-detected)
{"query": "latest quantum computing news"}

// Time-filtered search
{"query": "AI developments", "freshness": "pw"}
```

## 🤖 AI Models

The system automatically selects the best available model:

1. **Gemini 2.0 Flash** (Primary) - 2M free tokens/day
2. **Mixtral 8x7B** (Backup) - Via Hugging Face

## 💰 Cost Analysis

| Usage | Cost |
|-------|------|
| 100 queries/day | $0 (free tier) |
| 1000 queries/day | ~$0.50 (paid models) |
| Unlimited | ~$2-3/day (paid models) |

## 🔧 Configuration

Edit `.env` file to customize:

- `MAX_SEARCH_RESULTS`: Number of sources to analyze
- `CACHE_TTL`: Cache duration in seconds
- `MAX_CONCURRENT_EXTRACTIONS`: Parallel content extraction

## 📚 API Documentation

### Create Research
```bash
POST /api/v1/research
{
  "query": "Your research question",
  "max_results": 10,
  "style": "comprehensive",
  "search_engines": ["duckduckgo"]
}
```

### Get Results
```bash
GET /api/v1/research/{job_id}
```

### Export
```bash
GET /api/v1/export/{job_id}?format=pdf
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "No API key" | Add keys to `.env` file |
| Slow extraction | Increase `MAX_CONCURRENT_EXTRACTIONS` |
| Model timeout | Try different model or increase timeout |
| Docker issues | Run `docker-compose down` and rebuild |

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file

## 🙏 Acknowledgments

- DuckDuckGo for free search API
- Google for Gemini Flash free tier
- Hugging Face for model hosting
- All open-source contributors

## 📧 Support

- Issues: [GitHub Issues](https://github.com/yourusername/ai-research-agent/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/ai-research-agent/discussions)

---

Built with ❤️ for the research community