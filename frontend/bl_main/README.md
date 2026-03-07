# Black-Litterman Portfolio Dashboard

A production-ready financial dashboard for Black-Litterman portfolio optimization built with Vite, React, and TypeScript.

## 🏗 Architecture

This application follows a feature-based architecture with clear separation of concerns:

```
frontend/bl_main/
├── src/
│   ├── app/                    # Application shell
│   │   ├── App.tsx            # Root component
│   │   ├── AppLayout.tsx      # Main layout with header
│   │   └── providers.tsx      # Context providers
│   │
│   ├── features/              # Feature modules
│   │   └── bl_main/           # Black-Litterman feature
│   │       ├── pages/         # Page components
│   │       ├── components/    # Feature-specific components
│   │       ├── hooks/         # Custom hooks (useBLMain)
│   │       ├── services/      # API service layer
│   │       ├── domain/        # Business logic
│   │       ├── types/         # TypeScript types
│   │       └── mock/          # Mock data (simulates backend)
│   │
│   ├── shared/                # Shared/reusable code
│   │   ├── components/        # Card, Table, Button, ChartWrapper
│   │   ├── hooks/             # Shared hooks
│   │   ├── utils/             # Utility functions
│   │   └── types/             # Shared types
│   │
│   ├── services/              # Global services
│   │   └── apiClient.ts       # HTTP client
│   │
│   ├── styles/                # Global styles
│   └── main.tsx               # Application entry point
│
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## 📁 Directory Overview

### `/src/app`
Application shell containing the root component, layout, and global providers. Houses cross-cutting concerns like routing and theme.

### `/src/features/bl_main`
Complete Black-Litterman feature module with all business logic, UI components, and data management isolated in one place.

- **pages/**: Top-level page components
- **components/**: Feature-specific UI components (charts, tables, controls)
- **hooks/**: Custom React hooks for state and data fetching
- **services/**: Backend communication layer (currently mocked)
- **domain/**: Pure business logic functions
- **types/**: TypeScript interfaces and types
- **mock/**: Mock JSON data simulating API responses

### `/src/shared`
Reusable components, hooks, and utilities used across multiple features. Promotes DRY principles.

### `/src/services`
Global service utilities like API clients that are used application-wide.

## 🎯 Key Features

- **Collapsible Portfolio Context** - Compact portfolio selection that defaults to collapsed state showing summary (portfolio name, asset count, total weight)
- **Natural language view input** - Textarea for analyst views with example inputs (Asset Views and Factor Views) for quick reference
- **Active Views table** - Displays Type, Asset/Factor, Value, Direction, and Confidence columns
- **Two-column responsive layout** - Portfolio context, views, and controls on the left (800px); charts on the right
- **Three interactive charts:**
  - Efficient Frontier with prior and posterior portfolios
  - Grouped bar chart comparing prior vs BL allocations
  - Top-down contribution analysis with return/risk toggle
- **Portfolio management** - Create custom portfolios with weight validation and auto-normalize
- **Model controls** with risk aversion slider and confidence scaling
- **Mock data backend** structured for easy API integration
- **Custom hook** (`useBLMain`) managing data fetching and state
- **Service layer** ready to swap mock data for real API calls
- **Fully typed** with TypeScript for type safety

## 🚀 Getting Started

### Prerequisites

- Node.js 16+ and npm/yarn

### Installation

1. Navigate to the project directory:
```bash
set PATH="C:\Program Files\nodejs\";%PATH%
cd frontend/bl_main
```

2. Install dependencies:
```bash
npm install
```

### Running the Application

Start the development server:
```bash
npm run dev
```

The application will open automatically in your browser at `http://localhost:3000`.

### Build for Production

Create an optimized production build:
```bash
npm run build
```

Preview the production build:
```bash
npm run preview
```

## 🔄 Backend Integration

The application is structured for easy backend integration:

1. **Update `blMainService.ts`** - Replace mock data calls with actual API endpoints:
```typescript
// Before (mock)
return new Promise(resolve => setTimeout(() => resolve(mockData), 500));

// After (real API)
return apiClient.get('/api/bl/data');
```

2. **Set API URL** - Configure `VITE_API_BASE_URL` in `.env`:
```
VITE_API_BASE_URL=https://your-api.com
```

3. **Update types** - Adjust TypeScript types in `types/blMainTypes.ts` to match your API schema

## 🎨 Design System

- **Color Palette:**
  - Primary Blue: `#2563eb`
  - Deep Indigo: `#4338ca` (accent actions)
  - Background: `#f3f4f6`
  - White Cards: `#ffffff`
  - Text: `#1f2937`, `#374151`, `#6b7280`
  
- **Components:** Institutional, clean design with subtle shadows and rounded corners
- **Interactions:** Collapsible sections, hover states, smooth transitions
- **Charts:** Recharts library with consistent color scheme

## 📦 Tech Stack

- **Vite** - Fast build tool and dev server
- **React 18** - UI library
- **TypeScript** - Type safety
- **Recharts** - Data visualization
- **CSS Modules** - Scoped styling

## 🧪 Development

The project uses:
- ESLint for code quality
- TypeScript for type checking
- Vite's hot module replacement for fast development

## 📝 Notes

- All mock data is in `src/features/bl_main/mock/mockBlMainData.json`
- Portfolio Context defaults to collapsed; click header or "Change" button to expand
- Create View component includes example inputs for both Asset and Factor views with copy-to-input functionality
- Active Views displays 4 sample views with Type, Asset/Factor, Value, Direction, and Confidence columns
- Domain logic functions are placeholders - implement actual calculations as needed
- The "Run Black-Litterman" button triggers `refetch()` which currently returns mock data
- Components are prop-typed and ready for real data integration

---

**Built with production-ready architecture and best practices for financial dashboards.**
