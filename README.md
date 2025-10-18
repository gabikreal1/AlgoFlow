# AlgoFlow

**Automated DeFi Workflow Orchestration on Algorand**

AlgoFlow is an end-to-end platform that enables users to create, manage, and automate complex DeFi workflows through an intuitive builder interface or natural language chat. It combines visual workflow design, AI-powered intent interpretation, and on-chain execution via smart contracts.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Key Features](#key-features)
- [System Components](#system-components)
- [Workflow](#workflow)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

AlgoFlow bridges the gap between user intent and blockchain execution by:

1. **Visual & Natural Language Interface**: Build workflows via drag-and-drop canvas or conversational AI
2. **Intelligent Parsing**: Transform user input into executable workflow specifications
3. **Risk & Feasibility Analysis**: AI agent analyzes DeFi protocols and calculates risks
4. **Atomic Execution**: Group complex transactions into atomic operations on Algorand
5. **Automated Monitoring**: Keeper system monitors conditions and triggers execution
6. **Real-time Tracking**: Monitor positions, P&L, and execution status

---

## 🏗️ Architecture

### High-Level Component Map

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Layer (Web)                      │
│  Canvas | Chat UI | Wallet Manager | Position Monitor       │
└──────────────────┬──────────────────────────────┬───────────┘
                   │                              │
┌──────────────────▼──────────────────────────────▼─────────┐
│                    DSL Layer                               │
│  Parser (Block→JSON) | Serializer (JSON→Executable)       │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                 AI Agent System                              │
│  LangChain Core | Agent Tools | MCP Services                │
│  • Protocol Query • Token Lookup • Risk Analysis             │
│  • Gas Estimation • DeFi Protocol Data • Token Registry      │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                Backend Services                              │
│  API Gateway | Intent Manager | Chat Service                │
│  Transaction Composer | Status Tracking                      │
└──────────────────┬──────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────▼────────┐   ┌────────▼─────────────────┐
│  Keeper System │   │ Smart Contracts (Algo)  │
│  • Scheduler   │   │  • Intent Storage       │
│  • Checker     │   │  • Execution Contract   │
│  • Executor    │   │  • Deployer Service     │
│  • Oracle      │   └────────────┬────────────┘
└────────────────┘                │
                                  │ (Direct Interaction)
                                  ├──────────────────────┐
                                  │                      │
                          ┌───────▼──────────┐   ┌──────▼─────┐
                          │  Frontend        │   │   Keeper   │
                          │  Wallet Manager  │   │   System   │
                          │  (Sign & Submit) │   │ (Monitor & │
                          └──────────────────┘   │  Execute)  │
                                                 └────────────┘
```

---

## ✨ Key Features

### User-Facing
- 🎨 **Visual Builder**: Drag-and-drop workflow composition with block library
- 💬 **AI Chat Interface**: Natural language workflow creation and refinement
- 🔐 **Wallet Integration**: Secure transaction signing and balance management
- 📊 **Position Monitor**: Real-time status, P&L tracking, and alerts
- ✅ **Transaction Preview**: ABI encoding, fee calculation, and validation

### Technical
- 🤖 **LangChain Integration**: Sophisticated prompt management and chain orchestration
- 🔌 **MCP Services**: Extensible model context protocol for DeFi data
- ⛓️ **Atomic Transactions**: Multi-step operations as single blockchain transaction
- ⏲️ **Automated Execution**: Cron-based scheduler with condition checking
- 🏛️ **On-Chain Storage**: Smart contracts for intent registration and execution
- 💾 **Full History**: Chat and transaction history with search/filter

---

## 🔧 System Components

### Frontend (`frontend/`)
| Component | Purpose |
|-----------|---------|
| **canvas** | Visual workflow builder with block library and connection logic |
| **chat-interface** | Message history, streaming responses, context management |
| **wallet-manager** | Connect/disconnect, transaction signing, balance display |
| **position-monitor** | Real-time status, P&L tracking, alerts |
| **transaction-builder** | Atomic group composition, ABI encoding, fee calculation |

### DSL Layer (`dsl/`)
| Component | Purpose |
|-----------|---------|
| **parser** | Converts visual blocks or prompts to validated JSON |
| **serializer** | Transforms JSON to executable format with parameter binding |

### AI Agent System (`ai-agent/`)
| Component | Purpose |
|-----------|---------|
| **langchain-core** | Prompt management, chain orchestration, memory |
| **tools/** | Protocol queries, token lookups, risk analysis, gas estimation |
| **mcp-mocks/** | DeFi protocol ABIs, token registry, metadata |

### Backend Services (`backend/`)
| Component | Purpose |
|-----------|---------|
| **gateway** | API routing, authentication, rate limiting, validation |
| **intent-manager** | Intent CRUD, status tracking, event emission |
| **chat-service** | History storage, context retrieval, search |
| **transaction-composer** | Atomic group building, fee calculation, encoding |

### Keeper System (`keeper-system/`)
| Component | Purpose |
|-----------|---------|
| **cron-scheduler** | Configurable intervals, priority queue, retry logic |
| **condition-checker** | Price comparisons, time triggers, state validation |
| **oracle-client** | Price feeds, aggregation, fallback sources |
| **execution-engine** | Transaction building, nonce management, error handling |

### Smart Contracts (`smart-contracts/`)
| Component | Purpose |
|-----------|---------|
| **intent-storage** | Store intents, handle deposits, access control, events |
| **execution** | Validate conditions, orchestrate inner txns, manage state |
| **deployer-service** | Compile, deploy, version tracking, upgrades |

---

## 📈 Workflow

### User Interaction Flow

```
1. CREATE WORKFLOW
   User (drag-drop canvas) → DSL Parser → LangChain Agent
           OR (chat)

2. ANALYZE & VALIDATE
   Agent queries DeFi protocols & token data (MCP)
   → Calculates risks & feasibility
   → Returns structured JSON + explanation

3. APPROVE & SIGN
   User reviews workflow + risks
   → Approves in UI
   → Signs transaction with wallet

4. STORE ON-CHAIN (Frontend → Smart Contract)
   Frontend builds atomic transaction group
   → Frontend directly submits to Intent Storage contract
   → User signs & sends from wallet
   → Contract registers intent + stores deposit

5. MONITOR & EXECUTE (Keeper ↔ Smart Contract)
   Keeper system polls conditions:
   → Checks price feeds via Oracle
   → Reads from Intent Storage contract
   → Validates on-chain conditions
   → Triggers execution when ready

6. EXECUTE WORKFLOW (Smart Contract)
   Smart contract validates conditions
   → Executes series of inner transactions:
      • Swap tokens
      • Supply to lending
      • Stake rewards
   → Returns results

7. TRACK & MANAGE (Frontend ↔ Smart Contract)
   User monitors position in UI (Frontend queries Smart Contract)
   → Reads holdings from chain state
   → Views real-time P&L calculations
   → Can submit withdrawal requests directly to contract
   → Receives funds back to wallet
```

---

## 🚀 Getting Started

### Prerequisites
- Node.js 18+
- Python 3.9+
- Algorand SDK
- Git

### Installation

```bash
# Clone repository
git clone https://github.com/gabikreal1/AlgoFlow.git
cd AlgoFlow

# Install frontend dependencies
cd frontend
npm install

# Install backend dependencies
cd ../backend
npm install

# Install Python dependencies for AI agent
cd ../ai-agent
pip install -r requirements.txt

# Install smart contract tools
cd ../smart-contracts
pip install pyteal
```

### Configuration

Create a `.env` file in each service directory:

**Backend (`backend/.env`)**
```
API_PORT=3000
DATABASE_URL=postgresql://...
ALGORAND_NODE_URL=https://...
ALGORAND_INDEXER_URL=https://...
JWT_SECRET=your_secret_key
```

**Frontend (`frontend/.env`)**
```
REACT_APP_API_URL=http://localhost:3000
REACT_APP_WALLET_CONNECT_ID=your_project_id
```

**AI Agent (`ai-agent/.env`)**
```
OPENAI_API_KEY=your_api_key
ALGORAND_NODE_URL=https://...
```

### Running Services

```bash
# Terminal 1: Backend
cd backend && npm start

# Terminal 2: Frontend
cd frontend && npm start

# Terminal 3: Keeper System
cd keeper-system && npm start

# Terminal 4: AI Agent (for chat workflows)
cd ai-agent && python main.py
```

Access the application at `http://localhost:3000`

---

## 📁 Project Structure

```
AlgoFlow/
├── frontend/                 # Web UI & Builder
│   ├── canvas/              # Visual workflow builder
│   ├── chat-interface/      # AI chat component
│   ├── wallet-manager/      # Web3 wallet integration
│   ├── position-monitor/    # Position tracking UI
│   └── transaction-builder/ # Atomic txn composer
│
├── backend/                 # API & Services
│   ├── gateway/             # API gateway & routing
│   ├── intent-manager/      # Intent management
│   ├── chat-service/        # Chat history & context
│   └── transaction-composer/# Txn composition
│
├── ai-agent/                # AI & Orchestration
│   ├── langchain-core/      # LangChain setup
│   ├── tools/               # Agent tools
│   │   ├── gas-estimator/
│   │   ├── protocol-query/
│   │   ├── risk-analyzer/
│   │   └── token-lookup/
│   └── mcp-mocks/           # MCP services
│       ├── defi-protocol/
│       └── token-address/
│
├── dsl/                     # Domain-Specific Language
│   ├── parser/              # Block → JSON parser
│   └── serializer/          # JSON → Executable
│
├── keeper-system/           # Automation & Monitoring
│   ├── cron-scheduler/      # Job scheduling
│   ├── condition-checker/   # Trigger validation
│   ├── oracle-client/       # Price feeds
│   └── execution-engine/    # Txn execution
│
└── smart-contracts/         # Algorand Smart Contracts
    ├── intent-storage/      # Intent storage contract
    ├── execution/           # Execution contract
    └── deployer-service/    # Contract deployment
```

---

## 🔄 Data Flow Example

### Simple Swap → Stake Workflow

```
User Input: "Swap 100 ALGO for USDC, then stake in governance"
    ↓
DSL Parser: Converts to workflow JSON
    ↓
LangChain Agent:
  • Queries DeFi protocols → Gets swap ABIs
  • Queries token registry → Gets ALGO/USDC decimals
  • Analyzes risk & feasibility
  • Calculates gas fees
    ↓
Backend: Stores intent, creates transaction composer job
    ↓
Frontend: Displays preview + risks, user approves & signs
    ↓
Smart Contract: Stores intent + receives deposit
    ↓
Keeper System:
  • Monitors price conditions (if any)
  • Executes atomic transaction group:
    1. Swap 100 ALGO for USDC
    2. Stake USDC in governance program
    ↓
Position Monitor: Shows new holdings + pending rewards
```

---

## 🧪 Testing

```bash
# Run frontend tests
cd frontend && npm test

# Run backend tests
cd backend && npm test

# Run contract tests
cd smart-contracts && pytest

# Run AI agent tests
cd ai-agent && pytest
```

---

## 📚 Documentation

- [Frontend Development Guide](frontend/README.md)
- [Backend API Reference](backend/README.md)
- [AI Agent Architecture](ai-agent/README.md)
- [Smart Contract Specification](smart-contracts/README.md)
- [DSL Specification](dsl/README.md)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Workflow

- Follow the architectural guidelines in each service's README
- Write tests for new features
- Ensure all tests pass before submitting PR
- Update documentation as needed

---

## 🐛 Reporting Issues

Please report issues on [GitHub Issues](https://github.com/gabikreal1/AlgoFlow/issues) with:
- Clear title and description
- Steps to reproduce
- Expected vs. actual behavior
- Environment details (OS, Node version, etc.)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Team

**AlgoFlow** is built and maintained by the community. Special thanks to all contributors.

---

## 🔗 Links

- **GitHub**: https://github.com/gabikreal1/AlgoFlow
- **Issues**: https://github.com/gabikreal1/AlgoFlow/issues
- **Discussions**: https://github.com/gabikreal1/AlgoFlow/discussions

---

## 📞 Support

For questions or support:
- Open an issue on GitHub
- Check existing documentation
- Join our community discussions

---

**Built with ❤️ for the Algorand ecosystem**
