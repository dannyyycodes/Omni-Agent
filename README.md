# 🌐 OMNI v6 - Lovable-Style AI Agent

**Your AI that builds, learns, and evolves.**

OMNI is like having a developer friend who can build anything you describe, import your existing workflows, and upgrade itself when you need new features.

## ✨ What's New in v6

- **📁 File Upload Support** - Upload JSON, code, or documents and OMNI works with them
- **🔄 n8n Workflow Import** - Upload your n8n workflow JSON and OMNI converts it
- **🔍 Smart Web Search** - Automatically searches for current info when needed
- **💬 Natural Conversation** - Talks like a helpful friend, not a robot
- **🛠️ Self-Updating** - Ask OMNI to add features and it deploys them

## 🚀 Quick Start

1. Deploy to Railway
2. Set environment variables:
   ```
   OPENROUTER_API_KEY=sk-or-v1-xxx
   GITHUB_TOKEN=ghp_xxx
   GITHUB_OWNER=yourusername
   GITHUB_REPO=omni-ai-agent
   ```
3. Start chatting!

## 💬 Example Conversations

**Import n8n workflow:**
> Upload your workflow JSON
> "Set this up as a project"

**Search for info:**
> "What's the latest Google AI model?"

**Add features:**
> "Add support for DALL-E image generation"
> "deploy it"

**Create projects:**
> "Create a project called Video Empire"

## 🏗️ Architecture

```
omni/
├── app.py              # Flask web UI
├── core/
│   ├── brain.py        # AI + file handling + self-update
│   ├── memory.py       # PostgreSQL storage
│   └── self_update.py  # GitHub integration
├── api/
│   └── model_router.py # Claude 3.5 Sonnet via OpenRouter
└── workflows/
    └── engine.py       # Automation
```

## 📄 License

MIT
