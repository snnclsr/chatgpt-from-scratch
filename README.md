## 🌟 Overview

A full-stack ChatGPT-like application built (almost) from scratch, featuring real-time conversation capabilities, multi-modal support, and a modern web interface. This project demonstrates the implementation of various components of a production-ready LLM application, from model training to deployment. 

![](assets/ui.png)

## ✨ Features
- 🤖 Multiple LLM Architecture Support
  - MyGPT (Instruction-tuned GPT2, details below)
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

### Installation
1. Clone the repository
```bash
git clone https://github.com/snnclsr/chatgpt-from-scratch.git
cd chatgpt-from-scratch
```

2. With `docker-compose`
  ```bash
  cd chatgpt-from-scratch
  docker-compose up --build
  ```

3. or separately without the docker

  **Backend:**
  ```bash
  uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
  ```

  **Frontend:**
  ```bash
  cd frontend
  npm start
  ```

<!-- 2. Start the backend
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
``` -->

## 📚 Model Training
The training procedure is under `modelling` directory building upon Sebastian Raschka's ["Build a Large Language Model (From Scratch)" book](https://github.com/rasbt/LLMs-from-scratch), adapted from [here](https://github.com/rasbt/LLMs-from-scratch/tree/main/ch07/01_main-chapter-code) and implementing:
- GPT2 model architecture
- Instruction tuning using the Alpaca dataset (from the pretrained weights)

To run the training:

```bash
python -m modelling.train
```

I also applied following changes to the training code/model to make training/inference faster (https://github.com/rasbt/LLMs-from-scratch/tree/main/ch05/10_llm-training-speed)

1. Create causal mask on the fly
2. Use tensor cores
3. Fused AdamW optimizer
4. Replacing from-scratch code by PyTorch classes
5. Using FlashAttention
6. Using pytorch.compile
7. Increasing the batch size

As outlined by Sebastian as well, these updates make everything go faster, 6-7 times. 

## 🙏 Acknowledgments
- [Sebastian Raschka's "Build a Large Language Model (From Scratch)" book](https://www.amazon.com/Build-Large-Language-Model-Scratch/dp/1633437167)
- [Alpaca dataset (CC BY-NC 4.0)](https://github.com/tatsu-lab/stanford_alpaca)
- Open-source model providers ([Gemma-3-1b-it](https://huggingface.co/google/gemma-3-1b-it), [Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct), [SmolVLM-256M-Instruct](https://huggingface.co/HuggingFaceTB/SmolVLM-256M-Instruct))

## Future Enhancements
- Markdown support