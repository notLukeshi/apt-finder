# APT-Finder - Web Dashboard Integration

You are tasked with integrating an **adorable, kawaii-themed web dashboard** into the existing apartment scraper project. This dashboard will visualize apartment search results from the SQLite database.

## 🎨 **CRITICAL: AESTHETIC IS THE #1 PRIORITY**

This dashboard MUST embody authentic Japanese **kawaii culture**:
- Soft pastel colors throughout
- Smooth, delightful animations on every interaction
- Playful, friendly UI elements
- Every pixel should spark joy! ✨

## 📁 Updated Project Structure

Integrate the web panel into the existing project as follows:

```
apt-finder/
├── config.yaml                    # Scraper configuration
├── .env                           # Optional Google Maps API key + other secrets
├── main.py                        # Scraper entry point
├── requirements.txt               # Python dependencies
├── README.md
│
├── src/                           # Backend (scraper + API)
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── loader.py
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── tokyo_monthly.py
│   │   └── registry.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── apartment.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── schema.py
│   │   └── repository.py
│   ├── distance/
│   │   ├── __init__.py
│   │   └── calculator.py
│   ├── filters/
│   │   ├── __init__.py
│   │   └── price_filter.py
│   │
│   └── api/                       # NEW: FastAPI backend
│       ├── __init__.py
│       ├── app.py                 # FastAPI application
│       ├── routes.py              # API endpoints
│       └── schemas.py             # Pydantic response models
│
└── web/                           # NEW: React frontend
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── index.html
    ├── public/
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── components/
        │   ├── Dashboard.jsx
        │   ├── ApartmentMap.jsx
        │   ├── ApartmentCard.jsx
        │   ├── FilterBar.jsx
        │   └── StatsCards.jsx
        ├── hooks/
        │   └── useApartments.js
        ├── utils/
        │   └── api.js             # API client
        └── styles/
            └── kawaii.css         # Custom animations
```

## 🛠️ Technology Stack (MANDATORY)

### Backend API
**FastAPI** (Python)
- Serve data from existing SQLite database
- Use existing `src/database/repository.py` for DB operations
- Reuse existing `src/models/apartment.py` dataclasses

### Frontend
```
React 18+ (with Vite)
├── UI Components: DaisyUI (Tailwind CSS component library)
├── Themes: DaisyUI built-in themes ("cupcake", "pastel", "valentine")
│   └── OR: Catppuccin for DaisyUI (soothing pastel theme)
├── Maps: react-leaflet (interactive apartment maps)
├── Animations: framer-motion (smooth, fluid animations)
├── Icons: lucide-react
└── HTTP Client: axios or fetch
```

**Catppuccin for DaisyUI**: Optional plugin that provides even more soothing pastel themes (latte, frappe, macchiato, mocha)

## 🎯 Core Features

### FastAPI Backend Requirements

Create RESTful API with these endpoints:

```python
GET  /api/apartments              # List all apartments (with filters)
     ?min_price=50000
     &max_price=150000
     &website=TokyoMonthly
     &target_id=1
     &max_time=30

GET  /api/apartments/{id}         # Get single apartment details

GET  /api/websites                # List scraped websites

GET  /api/targets                 # List configured targets

GET  /api/stats                   # Dashboard statistics
     Returns: { total_apartments, avg_price, best_commute, websites_count }
```

**Important:**
- Use existing `src/database/repository.py` for all DB queries
- Return JSON responses with proper Pydantic schemas
- Enable CORS for local development
- Use existing dataclasses from `src/models/apartment.py`

### React Dashboard Requirements

Build a kawaii-themed dashboard with:

1. **Interactive Map** (using react-leaflet)
   - Display apartment locations as cute markers
   - Color-code markers by commute time (green < 20min, yellow 20-40min, etc.)
   - Show route on marker click
   - Smooth animations when flying to locations

2. **Apartment Cards**
   - Card-based layout (NOT boring tables)
   - Each card shows: name, price, address, commute time
   - Pastel gradient backgrounds
   - Hover effects with smooth transitions
   - Click to focus on map

3. **Filtering & Sorting**
   - Price range slider
   - Website filter (multi-select)
   - Target location selector
   - Sort by: Price | Distance | Best Value
   - "Best Value" = normalized score of (low price + short distance)

4. **Stats Cards**
   - Total apartments found
   - Average price
   - Best commute time
   - Websites scraped
   - Animated count-up on load

## 🌸 Design Requirements

### Color Palette (Choose ONE approach)

**Option 1: DaisyUI "cupcake" theme** (recommended for speed)
```javascript
// tailwind.config.js
module.exports = {
  plugins: [require("daisyui")],
  daisyui: {
    themes: ["cupcake"] // or "pastel", "valentine"
  }
}
```

**Option 2: Custom kawaii theme**
```javascript
daisyui: {
  themes: [{
    kawaii: {
      "primary": "#fda7dc",      // Pink
      "secondary": "#d879c9",     // Purple  
      "accent": "#7068bd",        // Blue
      "neutral": "#f3f4f6",       // Light gray
      "base-100": "#fefefe",      // White
      "info": "#e2eeff",          // Soft blue
      "success": "#e5ffe4",       // Soft green
      "warning": "#ffffe3",       // Soft yellow
      "error": "#ffe2e2",         // Soft red
    }
  }]
}
```

**Option 3: Catppuccin DaisyUI**
```bash
npm install @catppuccin/daisyui
```

### Animation Guidelines

- **Page load**: Stagger fade-in for elements (100ms delay between each)
- **Hover**: Scale(1.05) with 200ms transition
- **Click**: Brief scale(0.95) feedback
- **Map interactions**: Smooth flyTo animations (1s duration)
- **Loading states**: Use cute spinners (NOT default boring ones)

### Typography
- **Headers**: Rounded, friendly fonts (e.g., "Quicksand", "Nunito")
- **Body**: Soft, readable (e.g., "Inter", "DM Sans")
- Use Google Fonts import in `index.html`

### Component Design
- **Rounded corners**: Everything should have `border-radius: 12px+`
- **Soft shadows**: Use subtle drop shadows, never harsh
- **Generous spacing**: Padding and margins for breathing room
- **Emojis**: Use liberally in UI text (🏠, 💰, 🚇, etc.)

## 🚀 Implementation Priorities

### Phase 1: Backend Setup
1. Create FastAPI app in `src/api/app.py`
2. Implement API routes using existing repository
3. Add CORS middleware
4. Test endpoints with existing SQLite DB

### Phase 2: Frontend Foundation
1. Set up Vite + React project in `web/`
2. Install DaisyUI + dependencies
3. Configure Tailwind with kawaii theme
4. Create basic layout structure

### Phase 3: Core Features
1. Implement apartment list/cards
2. Add filtering and sorting logic
3. Integrate API calls
4. Build interactive map with react-leaflet

### Phase 4: Polish & Kawaii Transformation
1. Apply DaisyUI theme throughout
2. Add framer-motion animations
3. Implement micro-interactions
4. Custom loading states
5. Responsive design tweaks

## 📦 Dependencies

### Backend (`requirements.txt` additions)
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.4.0
python-multipart>=0.0.6
```

### Frontend (`web/package.json`)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-leaflet": "^4.2.1",
    "leaflet": "^1.9.4",
    "framer-motion": "^10.16.4",
    "lucide-react": "^0.294.0",
    "axios": "^1.6.2",
    "daisyui": "^4.4.24"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.3.6",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32"
  }
}
```

**Optional:** `@catppuccin/daisyui` for Catppuccin pastel themes

## ✅ Success Criteria

1. **Integration**: Backend API cleanly uses existing scraper codebase
2. **Aesthetic**: Immediately feels kawaii and delightful
3. **Smooth**: 60 FPS animations, no performance issues
4. **Functional**: All data from SQLite displayed correctly
5. **Interactive**: Map and filters work intuitively
6. **Responsive**: Works on desktop, tablet, mobile

## 💝 Final Notes

- The dashboard should make apartment hunting **FUN** instead of stressful
- Use DaisyUI's built-in themes for fast, consistent kawaii aesthetics
- Leverage existing scraper code (don't duplicate database logic)
- Keep code simple and Pythonic in backend
- Keep components modular and reusable in frontend
- Every interaction should feel smooth and delightful