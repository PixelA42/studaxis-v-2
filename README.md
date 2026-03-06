# Studaxis - Offline-First AI Tutor

> AWS Hackathon 2026 Submission | Dual-Brain Architecture for Low-Connectivity Learning

## Quick Start

### Prerequisites
- Python 3.9+
- Ollama installed
- 4GB RAM minimum
- 2GB free disk space

### Installation (5 minutes)

```bash
# 1. Clone repository
git clone <your-repo-url>
cd studaxis-vtwo

# 2. Activate virtual environment
studaxis-vtwo-env\Scripts\activate  # Windows
source studaxis-vtwo-env/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Pull Llama model
ollama pull llama3:3b

# 5. Copy environment file
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac

# 6. Test hardware
python local-app/hardware_validator.py

# 7. Launch app
streamlit run local-app/streamlit_app.py
```

## Project Structure

```
studaxis-vtwo/
├── local-app/              # Student-facing application
│   ├── streamlit_app.py    # Main UI
│   ├── quiz_engine.py      # Quiz logic
│   ├── rag_engine.py       # ChromaDB RAG
│   ├── sync_manager.py     # Cloud sync
│   └── utils/              # Helper modules
├── aws-infra/              # Cloud infrastructure
│   ├── lambda/             # Serverless functions
│   └── teacher-dashboard/  # Teacher UI
├── data/                   # Local storage
│   ├── chromadb/           # Vector store
│   └── user_stats.json     # Progress data
└── shared/                 # Common schemas
```

## Architecture

### Dual-Brain System
- **Brain 1 (Cloud)**: Amazon Bedrock - Quiz generation, content creation
- **Brain 2 (Edge)**: Llama 3.2 3B - Tutoring, grading, RAG (100% offline)

### Key Features
✅ 100% offline AI tutoring  
✅ Semantic grading with Red Pen feedback  
✅ RAG-powered curriculum grounding  
✅ Adaptive difficulty (Beginner/Intermediate/Expert)  
✅ Hinglish support  
✅ Panic Mode exam simulator  
✅ Delta sync (<5KB payloads)  
✅ Dark/Light theme (default: light)  

## Development Workflow

### Day 1: Core Setup
- [x] Project structure
- [x] Hardware validator
- [x] Ollama client
- [x] Local storage
- [ ] Streamlit UI skeleton
- [ ] AWS resources (S3, AppSync)

### Day 2: Features
- [ ] Quiz engine
- [ ] RAG pipeline
- [ ] Flashcard system
- [ ] Sync manager
- [ ] Teacher dashboard

### Day 3: Integration
- [ ] End-to-end sync
- [ ] Bedrock integration
- [ ] Panic Mode
- [ ] Accessibility

### Day 4: Polish
- [ ] UI refinement
- [ ] Testing
- [ ] Demo prep
- [ ] Documentation

## Testing Components

```bash
# Test hardware validation
python local-app/hardware_validator.py

# Test Ollama connection
python local-app/utils/ollama_client.py

# Test local storage
python local-app/utils/local_storage.py

# Run full app
streamlit run local-app/streamlit_app.py
```

## AWS Resources (Member 2)

### Required Services
- Amazon Bedrock (quiz generation)
- AWS AppSync (GraphQL sync)
- AWS S3 (content storage)
- AWS Lambda (sync resolvers)

### Setup Commands
```bash
# Configure AWS CLI
aws configure

# Create S3 buckets
aws s3 mb s3://studaxis-student-stats --region ap-south-1
aws s3 mb s3://studaxis-content --region ap-south-1

# Deploy AppSync API (via CloudFormation or Console)
# See aws-infra/cloudformation/template.yaml
```

## Environment Variables

### Local App (.env)
```
OLLAMA_MODEL=llama3:3b
CHROMA_DB_PATH=./data/chromadb
USER_STATS_PATH=./data/user_stats.json
AWS_APPSYNC_ENDPOINT=<your-endpoint>
```

### AWS Infra (.env.aws)
```
AWS_REGION=ap-south-1
S3_BUCKET_STUDENT=studaxis-student-stats
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
```

## Memory Optimization

### For 4GB RAM Devices
- Uses Q2_K quantization (~1.1GB model)
- Lazy-loads ChromaDB embeddings
- Limits context window to 4096 tokens
- Unloads model after inference

### Monitoring
```python
from local-app.hardware_validator import HardwareValidator

validator = HardwareValidator()
memory = validator.monitor_runtime_memory()
print(f"RAM Usage: {memory['used_gb']}GB / {memory['percent']}%")
```

## Troubleshooting

### Ollama Not Found
```bash
# Verify Ollama is running
ollama list

# If not installed, download from:
# https://ollama.com/download
```

### Model Not Available
```bash
# Pull the model
ollama pull llama3:3b

# Verify
ollama list
```

### Low RAM Warning
- Close other applications
- System will auto-select Q2_K quantization
- Reduce context window in settings

### Sync Failures
- Check internet connectivity
- Verify AWS credentials
- Check AppSync endpoint in .env

## Documentation

- [Design Document](design.md) - Architecture and technical decisions
- [Requirements](requirements.md) - Detailed specifications
- [Project Init](PROJECT_INIT.md) - Setup checklist

## Team Workflow

### Member 1 (Local App)
- Focus: Streamlit UI, Ollama integration, ChromaDB, local features
- Test: `python local-app/streamlit_app.py`

### Member 2 (AWS Infra)
- Focus: S3, AppSync, Lambda, Bedrock, teacher dashboard
- Test: AWS Console + `python aws-infra/teacher-dashboard/dashboard_app.py`

### Integration Points
- JSON schemas in `shared/schemas/`
- Sync via AppSync GraphQL
- Content distribution via S3

## License

MIT License - AWS Hackathon 2026

## Contact

[Your Team Name]  
[GitHub Repository]  
[Demo Video]
