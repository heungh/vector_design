# Vector Knowledge Base Streamlit App with AI Chat

A Streamlit web application that allows you to search in a vector knowledge base, chat with Claude AI, and upload new documents.

## Features

- 🔍 **Vector Search**: Search for relevant documents in the Knowledge Base using natural language
- 💬 **AI Chat**: Real-time interactive conversation with Claude 4/3.7
- 🤖 **Integrated Answers**: Claude's customized answers based on vector search results
- 📤 **Document Upload**: Add new knowledge by uploading text files or direct input
- 💾 **Auto Save**: Automatic synchronization to local directory, S3 bucket, and Knowledge Base

## New AI Chat Features

### Claude Model Support
- **Claude Sonnet 4**: Latest model used as priority
- **Claude 3.7 Sonnet**: Fallback model to ensure stability

### Interactive Features
- Real-time chat interface
- Chat history management
- Answers based on vector search results
- Context-aware conversation

## Installation and Running

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure AWS credentials (AWS CLI or environment variables)

3. Run the application:
```bash
streamlit run vector_knowledge_app.py
```

4. Test Claude integration:
```bash
python test_claude.py
```

## Configuration

Check/modify the following settings in the `vector_knowledge_app.py` file:

- `KNOWLEDGE_BASE_ID`: Knowledge Base ID
- `S3_BUCKET_NAME`: S3 bucket name
- `VECTOR_DIR`: Local storage directory

## Usage

### Search Mode
- Enter search terms and set maximum number of results
- Ask in natural language (e.g., "database performance optimization methods")

### AI Chat Mode (New)
- Real-time conversation with Claude AI
- Option to include vector search results
- Chat history management
- Automatic reference document display

### Upload Mode
- File upload or direct text input
- Set topic, category, and tags
- Automatically syncs to local/S3/Knowledge Base upon saving

## Tech Stack

- **Frontend**: Streamlit
- **AI Models**: Claude Sonnet 4, Claude 3.7 Sonnet
- **Vector Store**: Amazon Bedrock Knowledge Base
- **Storage**: Amazon S3
- **Runtime**: AWS Bedrock Runtime
