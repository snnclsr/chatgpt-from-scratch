# LLMs From Scratch

> Building and training Large Language Models from the ground up

## 🌟 Overview

A full-stack ChatGPT-like application built (almost) from scratch, featuring real-time conversation capabilities, multi-modal support, and a modern web interface. This project demonstrates the implementation of various components of a production-ready LLM application, from model training to deployment. 

## ✨ Features
- 🤖 Multiple LLM Architecture Support
  - Gemma-3-1b-it
  - Qwen2.5-0.5B-Instruct
  - SmolVLM-256M-Instruct (Multi-modal)
- 💬 Real-time Conversation
  - WebSocket-based streaming responses
  - Token-by-token generation
- 🎨 Modern Web Interface (vibe coded)
  - React + TypeScript
  - Tailwind CSS for styling
- 🖼️ Multi-modal Capabilities
  - Image upload and processing
  - Vision-language model integration
- 💾 Persistent Storage
  - SQLite database
  - Message and conversation history
- 🐳 Containerization
  - Docker support for both frontend and backend
  - Easy deployment and scaling

## 🛠️ Technical Stack
### Frontend
- React 18
- TypeScript
- Tailwind CSS
- WebSocket for real-time communication

### Backend
- FastAPI
- SQLAlchemy with SQLite
- PyTorch
- Transformers
- WebSockets
- Docker

## 🚀 Getting Started

### Prerequisites
- Docker and Docker Compose
- Python 3.8+
- Node.js 16+

### Installation
1. Clone the repository
```bash
git clone https://github.com/snnclsr/chatgpt-from-scratch.git
cd chatgpt-from-scratch
```

2. Start the backend
```bash
cd backend
docker build -t chatgpt-backend .
docker run -p 8000:8000 chatgpt-backend
```

3. Start the frontend
```bash
cd frontend
docker build -t chatgpt-frontend .
docker run -p 3000:3000 chatgpt-frontend
```

## 📚 Model Training
This project builds upon Sebastian Raschka's "Build a Large Language Model (From Scratch)" book, implementing:
- Custom GPT model architecture
- Instruction tuning using the Alpaca dataset
- Model conversion techniques (GPT-2 to Llama variants)
- Preference tuning capabilities

## 🏗️ Project Structure

```bash
├── backend
│   ├── ml
│   │   └── providers
│   ├── models
│   │   ├── SmolVLM-256M-Instruct
│   │   │   └── onnx
│   │   ├── gemma-3-1b-it
│   │   └── gemma-3-4b-it
│   ├── my_ml
│   ├── repositories
│   ├── routes
│   │   └── websockets
│   ├── services
│   ├── uploads
│   └── utils
├── frontend
│   ├── public
│   └── src
│       ├── components
│       └── services
├── modelling
```

## 🙏 Acknowledgments
- Sebastian Raschka's "Build a Large Language Model (From Scratch)" book
- Alpaca dataset (CC BY-NC 4.0)
- Open-source model providers (Gemma, Qwen, SmolVLM)

