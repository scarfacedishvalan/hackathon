# Frontend - Portfolio Optimization Dashboard

Production-ready financial dashboard for Black-Litterman portfolio optimization, backtesting, and AI-powered portfolio analysis built with Vite, React, and TypeScript.

## Overview

This frontend integrates with the FastAPI backend to provide a comprehensive portfolio management platform with:
- **Black-Litterman Optimization**: Natural language view input, efficient frontier visualization, and allocation analysis
- **Portfolio Backtesting**: Historical strategy testing with performance metrics and equity curves
- **AI Agent Analysis**: Agentic BL analysis with stress testing and sensitivity exploration
- **News Integration**: Analyst news with pre-structured BL views ready to add to portfolio recipes
- **Admin Console**: LLM usage tracking and cost monitoring across all services

## 🏗 Architecture

Feature-based architecture with clear separation of concerns and fully integrated with backend API:

```
frontend/port_optim/
├── src/
│   ├── app/                    # Application shell
│   │   ├── App.tsx            # Root component with routing
│   │   ├── AppLayout.tsx      # Main layout with navigation
│   │   └── providers.tsx      # Context providers
│   │
│   ├── features/              # Feature modules (each with pages, components, services, types)
│   │   ├── bl_main/           # Black-Litterman optimization
│   │   │   ├── pages/BLMainPage.tsx
│   │   │   ├── components/    # AssetSelection, ActiveViews, ModelControls, Charts, BLCalculationSteps, PortfolioStats
│   │   │   ├── context/BLMainContext.tsx
│   │   │   ├── hooks/useBLMain.ts
│   │   │   ├── services/blMainService.ts
│   │   │   ├── domain/        # Business logic (contribution calculations)
│   │   │   └── types/blMainTypes.ts
│   │   │
│   │   ├── backtest/          # Portfolio backtesting
│   │   │   ├── pages/BacktestPage.tsx
│   │   │   ├── components/RecipeDisplay.tsx
│   │   │   ├── context/BacktestContext.tsx
│   │   │   ├── hooks/useBacktest.ts
│   │   │   ├── services/backtestService.ts
│   │   │   └── types/backtestTypes.ts
│   │   │
│   │   ├── agent/             # AI agent analysis
│   │   │   ├── pages/AgentPage.tsx
│   │   │   ├── components/    # AuditDisplay, StepTimeline
│   │   │   ├── services/agentService.ts
│   │   │   └── types/agentTypes.ts
│   │   │
│   │   ├── admin/             # LLM usage and cost tracking
│   │   │   ├── pages/AdminPage.tsx
│   │   │   ├── services/adminService.ts
│   │   │   └── types/adminTypes.ts
│   │   │
│   │   └── about/             # About / project info page
│   │       ├── pages/AboutPage.tsx
│   │       ├── components/AboutSection.tsx
│   │       └── index.ts
│   │
│   ├── shared/                # Reusable components
│   │   └── components/        # Card, Table, Button, ChartWrapper
│   │
│   ├── services/              # Global services
│   │   └── apiClient.ts       # HTTP client with backend integration
│   │
│   └── main.tsx               # Application entry point
│
├── public/
├── index.html
├── package.json
└── vite.config.ts
```

## Feature Modules

### **bl_main/** - Black-Litterman Optimization
Complete BL workflow with asset selection, view management, and portfolio analysis.
- **AnalystSuggestions.tsx**: News table with search/filter and "+ Active Views" button to add BL-formatted views
- **AssetSelection.tsx**: Asset picker with weight allocation and validation
- **ActiveViews.tsx**: Display and manage bottom-up and top-down views
- **CreateView.tsx**: Natural language view input with example templates
- **ModelControls.tsx**: Risk aversion, tau, and confidence scaling controls
- **BLAllocationChart.tsx**: Bar chart comparing prior vs posterior allocations
- **EfficientFrontierChart.tsx**: Scatter plot with prior and posterior portfolios
- **TopDownContribution.tsx**: Factor contribution analysis with return/risk toggle
- **BLCalculationSteps.tsx**: Step-by-step display of BL matrix construction and calculations
- **PortfolioStats.tsx**: Portfolio performance statistics summary panel
- **domain/**: Pure functions for contribution calculations (return, risk, top-down aggregation)

### **backtest/** - Portfolio Backtesting
Historical strategy testing with recipe management and performance visualization.
- **BacktestPage.tsx**: Main backtesting interface with recipe input and results display
- **RecipeDisplay.tsx**: Portfolio strategy recipe viewer with parameters and metrics
- **backtestService.ts**: API client for backtest execution and data fetching

### **agent/** - AI Agent Analysis
Agentic workflow for stress testing and scenario exploration.
- **AgentPage.tsx**: Agent orchestration interface with goal input and audit display
- **AuditDisplay.tsx**: Execution log viewer with step-by-step breakdown
- **StepTimeline.tsx**: Visual timeline of agent tool calls and decisions

### **admin/** - Admin Console
LLM usage tracking and cost monitoring dashboard.
- **AdminPage.tsx**: Aggregated view of token usage, costs, and service breakdowns
- **adminService.ts**: API client for admin console data

### **about/** - About Page
Project information and attribution page.
- **AboutPage.tsx**: Main about page composing multiple AboutSection panels
- **AboutSection.tsx**: Reusable panel component with title, optional image, and content body

## 🎯 Key Features

### Black-Litterman Optimization
- **Asset Selection**: Custom portfolio builder with weight validation and auto-normalize
- **Analyst News**: Search and filter news articles with fuzzy matching, add structured BL views to recipe
- **Natural Language Views**: Textarea input with example templates for asset and factor views
- **Active Views Table**: Display bottom-up (asset) and top-down (factor) views with confidence levels
- **Model Controls**: Risk aversion slider (0.5-5.0), tau parameter, confidence scaling
- **Three Interactive Charts**:
  - Efficient Frontier with prior/posterior portfolios and Sharpe ratio annotations
  - Grouped bar chart comparing prior vs BL-optimized allocations
  - Top-down contribution analysis with return/risk decomposition toggle
- **BL Calculations Display**: Step-by-step view construction and matrix operations

### Portfolio Backtesting
- **Strategy Recipe Input**: Natural language or JSON-based strategy definitions
- **Historical Testing**: Execute strategies on historical price data
- **Performance Metrics**: CAGR, Sharpe ratio, max drawdown, volatility
- **Equity Curves**: Visual representation of strategy performance over time

### AI Agent Analysis
- **Goal-Based Exploration**: Define analysis goals in natural language
- **Tool Calling**: Agent autonomously calls BL tools for stress testing and analysis
- **Execution Audit**: Step-by-step log of agent decisions and tool calls
- **Cost Tracking**: Token usage and LLM costs per agent run

### Admin Console
- **LLM Usage Dashboard**: Token counts and costs by service/operation
- **Agent Audit Logs**: Historical agent runs with performance metrics
- **Cost Breakdown**: Detailed view of API costs across all features

## 🚀 Getting Started

### Prerequisites
- Node.js 16+ and npm

### Installation

1. Navigate to the project directory:
```bash
cd frontend/port_optim
```

2. Install dependencies:
```bash
npm install
```

3. Configure environment (optional):
```bash
# Create .env file
echo VITE_API_BASE_URL=http://localhost:8000 > .env
```

### Running the Application

**Development mode** (with backend running on port 8000):
```bash
npm run dev
```

Application opens at `http://localhost:5173`

**Production build**:
```bash
npm run build
```

**Preview production build**:
```bash
npm run preview
```

## 🧪 Development

### Backend Connection
Ensure backend is running before starting frontend:
```bash
# In backend directory
uvicorn app.main:app --reload --port 8000
```

### Project Structure
- Each feature is self-contained with pages, components, services, and types
- Shared components in `shared/components/` for reusability
- API client in `services/apiClient.ts` handles all HTTP requests
- TypeScript types ensure type safety across the application

### Code Quality
- ESLint for code quality
- TypeScript for static type checking
- Vite's HMR for fast development iteration

## � Backend Integration

The frontend is fully integrated with the FastAPI backend:

**API Configuration** (`services/apiClient.ts`):
```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
```

**Key API Endpoints Used**:
- `GET /api/news?keyword={keyword}&limit={limit}` - Fetch news with BL views
- `POST /api/news/{id}/add-to-recipe` - Add news view to current recipe
- `POST /api/bl/parse-views` - Parse natural language to BL views
- `GET /api/bl/calculate` - Execute Black-Litterman optimization
- `POST /api/agent/run` - Execute agentic analysis
- `GET /api/admin/stats` - Fetch LLM usage and cost data

**Environment Variables** (`.env`):
```bash
VITE_API_BASE_URL=http://localhost:8000  # Development
# VITE_API_BASE_URL=http://167.172.198.36  # Production
```

**Service Layer Structure**:
```typescript
// Each feature has its own service file
bl_main/services/blMainService.ts
backtest/services/backtestService.ts
agent/services/agentService.ts
admin/services/adminService.ts
```

## 🎨 Design System

**Professional financial UI** with consistent styling:
- **Colors**: Blue/Indigo accents (#2563eb, #4338ca), light backgrounds (#f3f4f6), dark text hierarchy
- **Components**: Clean cards with subtle shadows and rounded corners, institutional design
- **Charts**: Recharts library for line, bar, pie, scatter plots with consistent color scheme
- **Tables**: Custom DataTable with sorting, filtering, inline editing
- **Forms**: LabeledInput, ButtonGroup, Slider for user inputs

## 📦 Tech Stack

**Core**:
- React 18.3 with TypeScript 5.6
- Vite 6.0 (build tool with HMR)
- React Router 7.1

**UI & Visualization**:
- Recharts 2.15 (charts)
- Lucide React (icons)
- CSS Modules (scoped styling)

**HTTP & Data**:
- Axios (API client)
- TypeScript interfaces for type safety

## 📝 Notes

- Backend API must be running on port 8000 for full functionality
- Environment variable `VITE_API_BASE_URL` configures API endpoint
- Each feature module has its own service layer for API communication
- LLM usage tracking in Admin Console provides cost monitoring
- The "Run Black-Litterman" button triggers `refetch()` which currently returns mock data
- Components are prop-typed and ready for real data integration

---

**Built with production-ready architecture and best practices for financial dashboards.**
