# Development Guide

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 14+
- npm or yarn

### Setup

1. **Automated Setup** (Recommended):
   ```bash
   python scripts/setup.py
   ```

2. **Manual Setup**:
   ```bash
   # Backend setup
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your configuration
   python scripts/init_database.py
   
   # Frontend setup
   cd frontend
   npm install
   ```

### Running the Application

**Option 1: Use the start script**
```bash
python start.py
```

**Option 2: Start manually**
```bash
# Terminal 1 - Backend
python backend/app.py

# Terminal 2 - Frontend
cd frontend
npm start
```

### Accessing the Application
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/api/v1/docs

## Project Structure

```
liking-rating-database/
├── backend/                 # Python FastAPI backend
│   ├── models/             # Database models and schemas
│   ├── api/                # API routes
│   ├── services/           # Business logic
│   └── utils/              # Utility functions
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   └── services/       # API client
├── data_processing/        # Data processing utilities
├── scripts/                # Setup and utility scripts
└── docs/                   # Documentation
```

## Database Schema

### Core Models
- **Study**: Research studies
- **Dataset**: Datasets within studies
- **Item**: Food items being rated
- **Rating**: Individual ratings
- **DownloadLog**: Download tracking
- **SearchLog**: Search analytics

### Relationships
- Study → Dataset (1:many)
- Dataset → Rating (1:many)
- Item → Rating (1:many)

## API Endpoints

### Studies
- `GET /api/v1/studies` - List studies
- `GET /api/v1/studies/{id}` - Get study details
- `POST /api/v1/studies` - Create study
- `PUT /api/v1/studies/{id}` - Update study
- `DELETE /api/v1/studies/{id}` - Delete study

### Datasets
- `GET /api/v1/datasets` - List datasets
- `GET /api/v1/datasets/{id}` - Get dataset details
- `POST /api/v1/datasets` - Create dataset

### Items
- `GET /api/v1/items` - List food items
- `GET /api/v1/items/{id}` - Get item details

### Search
- `POST /api/v1/search` - Advanced search
- `GET /api/v1/search/suggestions` - Search suggestions

### Downloads
- `POST /api/v1/download` - Request download
- `GET /api/v1/download/{id}` - Get download file

### Analytics
- `GET /api/v1/statistics` - Database statistics
- `GET /api/v1/ratings/aggregate` - Rating aggregations

## Development Workflow

### Adding New Features

1. **Backend Changes**:
   - Add/modify models in `backend/models/`
   - Update API routes in `backend/api/`
   - Add business logic in `backend/services/`
   - Update schemas in `backend/models/schemas.py`

2. **Frontend Changes**:
   - Add components in `frontend/src/components/`
   - Add pages in `frontend/src/pages/`
   - Update API client in `frontend/src/services/api.js`

3. **Database Changes**:
   - Modify models in `backend/models/database.py`
   - Create migration scripts if needed
   - Update `scripts/init_database.py` for new installations

### Testing

```bash
# Backend tests
python -m pytest tests/

# Frontend tests (when implemented)
cd frontend
npm test
```

### Code Style

- **Backend**: Follow PEP 8, use type hints
- **Frontend**: Use ESLint and Prettier
- **Documentation**: Use docstrings and comments

## Data Processing

### Data Standardization
The `data_processing/data_standardizer.py` module handles:
- Rating scale normalization (0-1)
- Food item name standardization
- Category assignment
- Metadata generation

### Adding New Data Sources
1. Create data cleaning script in `data_processing/`
2. Use `DataStandardizer` class for normalization
3. Import using database models
4. Update metadata

## Configuration

### Environment Variables
Edit `.env` file:
- `DATABASE_URL`: Database connection string
- `OSF_API_TOKEN`: Open Science Framework API token
- `SECRET_KEY`: Application secret key
- `REDIS_URL`: Redis cache URL (optional)

### Database Options
- **Development**: SQLite (default)
- **Production**: PostgreSQL recommended

```bash
# SQLite (default)
DATABASE_URL=sqlite+aiosqlite:///./liking_rating.db

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname
```

## Deployment

### Backend Deployment
1. Set production environment variables
2. Use a production WSGI server (e.g., Gunicorn with Uvicorn workers)
3. Set up PostgreSQL database
4. Configure Redis for caching (optional)

### Frontend Deployment
1. Build the production bundle: `npm run build`
2. Serve static files with a web server
3. Configure API proxy for production backend

### Docker Deployment (TODO)
Docker configuration files are planned for future releases.

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure all dependencies are installed with `pip install -r requirements.txt`

2. **Database Connection**: Check your `DATABASE_URL` in `.env`

3. **Port Conflicts**: Change ports in configuration if 8000 or 3000 are in use

4. **Frontend Build Errors**: Delete `node_modules` and run `npm install` again

### Getting Help
- Check the GitHub Issues page
- Review API documentation at `/api/v1/docs`
- Check application logs for error details
