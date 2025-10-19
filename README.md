# AlgoFlow

**Automated DeFi Workflow Orchestration on Algorand**

AlgoFlow is an end-to-end platform that enables users to create, manage, and automate complex DeFi workflows through an intuitive builder interface or natural language chat. It combines visual workflow design, AI-powered intent interpretation, and on-chain execution via smart contracts.

> **🆕 NEW FEATURES**: 
> - **JSON Export/Import**: Save and load strategies as parser-compatible JSON
> - **AI Chat Integration**: Build strategies using natural language
> - **Real-time Updates**: Chat modifies visual flow diagrams instantly
> 
> See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for usage guide.

---

## 📋 Table of Contents

- [Overview](#overview)
- [New Features](#new-features)
- [Architecture](#architecture)
- [Key Features](#key-features)
- [System Components](#system-components)
- [Workflow](#workflow)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

---
## Demo Link
(click the thumbnail)
[![Watch the demo](https://img.youtube.com/vi/l4DMMsyL_Hs/0.jpg)](https://youtu.be/l4DMMsyL_Hs)


## UI Screenshots
<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/4f05c7dc-c98d-4d4d-9125-bea4bd4527f2" />

<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/7b1e3f23-5b11-4936-b164-a95946f4e88c" />
Front-End Visuals

Canvas (defi-strategy-flow.tsx) mirrors a stage-based storyboard: left “markers” define Entry/Manage/Exit lanes, center nodes render action cards (swap/liquidity) with palette colors, right mini-map ensures orientation in large flows.
Execute modal in page.tsx uses tiered cards: readiness badge, Tinyman metadata grid, per-step accordions, wallet panel, and raw payload/txn viewers so builders can audit every detail before signing.
Palette + inspector (component-palette.tsx, scratch-block-node.tsx) keep configuration inline—action presets expose the same fields the backend expects, reducing context switching and mismatched params.
Toasts/spinners and the “Simulate Strategy” affordance match the Algorand purple/orange accent scheme, keeping state transitions obvious while aligning with Tinyman brand cues.

## Smart Contracts
Contract Architecture

Intent storage app (contract.py) owns custodial state: create stores owner/keeper defaults, configure sets keeper + collateral thresholds, register_intent boxes the ABI-encoded workflow and enforces collateral, update_intent_status + withdraw_intent manage lifecycle and payouts, global box numbering via g_next_intent_key.
Execution app (contract.py) reads boxed intent blobs, verifies hashes, validates optional triggers, then streams Tinyman steps through dispatch_workflow_step; helper subs handle swap/liquidity/transfer, on-demand ASA opt-ins, fee-splitting, and slippage guards.
Shared primitives in common/ (ABI structs, constants, events, validation) guarantee consistent encoding: IntentRecord packs owner/collateral/workflow bytes, events.py emits logs, validation.py bounds fees and owners, opcodes.py maps action IDs for the dispatcher.
Intent Lifecycle

UI flow builds Tinyman plan → /api/workflow converts via buildTinymanWorkflow to the contract ABI (no private keys needed) → /api/transactions encodes register/execute groups, fetching g_next_intent from storage.
Register call: collateral payment (if >0) funds storage, register_intent boxes workflow and logs creation, collateral sits custodially.
Execute call: keeper or owner fetches export_intent, recomputes SHA256 plan hash, dispatcher executes Tinyman app calls; balances captured pre/post to infer outputs, optional trigger ensures oracle thresholds before actions.
Completion: execution app logs success; storage update_intent_status flips state to Executing/Success/Failed; withdraw_intent lets owner or keeper reclaim collateral or fees based on final status.
Together, visuals keep builders oriented (stage markers, color-coded actions, comprehensive modal), while the contracts provide a deterministic intent queue with collateral safety, slippage enforcement, and modular Tinyman execution—all wired for Algorand testnet IDs today but structured to swap registries for mainnet when ready.

## 🆕 New Features

### JSON Export/Import
- **Export** visual strategies to parser-compatible JSON
- **Import** JSON to reconstruct visual flow diagrams
- Compatible with backend parser for smart contract deployment
- [Learn more →](AGENT_INTEGRATION.md#json-exportimport)

### AI Agent Integration
- **Chat interface** for building strategies in natural language
- **Real-time updates** to visual flow diagram
- **Context-aware** - modifies existing strategies or creates new ones
- [Learn more →](AGENT_INTEGRATION.md#ai-agent-integration)

### Quick Start
```bash
# 1. Set up environment
echo "OPENAI_API_KEY=your-key" > .env

# 2. Start frontend
cd front && npm run dev

# 3. Open chat and type:
"Swap 100 USDC to ALGO on Tinyman"
```

See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for more examples.

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
