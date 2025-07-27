# Liking Rating Database

A comprehensive user-facing database system for food liking ratings from 30 studies with 700k+ data entries. This system provides researchers with easy access to standardized food preference data for analysis and research purposes.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 14+
- npm or yarn

### Automated Setup (Recommended)
```bash
# Clone the repository
git clone https://github.com/yourusername/liking-rating-database.git
cd liking-rating-database

# Run the automated setup
python scripts/setup.py

# Start both backend and frontend
python start.py
```

### Manual Setup
```bash
# Backend setup
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
python scripts/init_database.py

# Frontend setup
cd frontend
npm install

# Start backend (Terminal 1)
python backend/app.py

# Start frontend (Terminal 2)
cd frontend && npm start
```

### Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/v1/docs

## ✨ Features

- **Comprehensive Data Access**: 700k+ food liking ratings from 30 studies
- **Advanced Search**: Filter by study, food items, rating scales, and more
- **Data Standardization**: Normalized rating scales for cross-study comparisons
- **Multiple Export Formats**: CSV, JSON, SPSS, R-compatible formats
- **Interactive Visualizations**: Rating distributions and cross-study comparisons
- **OSF Integration**: Direct access to Open Science Framework data storage
- **Citation Generator**: Automatic citation generation for used datasets

## 📊 Current Implementation Status

### ✅ Completed Features
- **Backend API**: FastAPI with comprehensive models and routes
- **Database Models**: Studies, datasets, items, ratings with relationships
- **Search System**: Advanced filtering and search functionality
- **Download System**: Multi-format data export (CSV, JSON, Excel, SPSS)
- **Frontend Interface**: React app with Ant Design components
- **Data Standardization**: Rating normalization and food categorization
- **Documentation**: API docs and development guides

### 🚧 In Development
- Data visualization components
- User authentication system
- Advanced analytics dashboard
- OSF API integration
- Bulk data import tools

### 📋 Planned Features
- Interactive charts and graphs
- User accounts and saved searches
- Data quality metrics
- Citation management
- Email notifications
- Mobile-responsive design improvements

## 🏗️ Architecture

### Backend (Python/FastAPI)
- **Database**: SQLAlchemy with async support (SQLite/PostgreSQL)
- **API**: RESTful API with automatic OpenAPI documentation
- **Services**: Modular business logic for search, downloads, and data processing
- **Data Processing**: Standardization and normalization utilities

### Frontend (React/JavaScript)
- **UI Framework**: Ant Design for consistent, professional interface
- **State Management**: React Query for server state management
- **Routing**: React Router for navigation
- **Styling**: CSS-in-JS with styled-components

### Data Layer
- **Studies**: Research study metadata
- **Datasets**: Individual datasets within studies  
- **Items**: Standardized food items with categories
- **Ratings**: Individual preference ratings (normalized 0-1 scale)

## 📖 Documentation

- **[Development Guide](docs/DEVELOPMENT.md)**: Complete setup and development instructions
- **[API Documentation](http://localhost:8000/api/v1/docs)**: Interactive API documentation (when running)
- **[Data Dictionary](docs/DATA_DICTIONARY.md)**: Detailed field descriptions (planned)

## 🔧 Configuration

The application uses environment variables for configuration. Copy `.env.example` to `.env` and modify as needed:

```bash
# Database (SQLite for development, PostgreSQL for production)
DATABASE_URL=sqlite+aiosqlite:///./liking_rating.db

# API Configuration  
SECRET_KEY=your-secret-key-here
API_HOST=localhost
API_PORT=8000

# Optional: OSF Integration
OSF_API_TOKEN=your-osf-token
OSF_PROJECT_ID=your-project-id

# Optional: Redis for caching
REDIS_URL=redis://localhost:6379
```

## 🧪 Sample Data

The setup script can create sample data for testing:

```bash
python scripts/create_sample_data.py
```

This creates:
- 3 sample studies with realistic metadata
- 6 datasets with varying characteristics  
- 10 common food items across categories
- Thousands of realistic preference ratings

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📬 Contact & Support

- **Email**: support@likingdatabase.org
- **GitHub Issues**: [Project Issues](https://github.com/yourusername/liking-rating-database/issues)
- **Documentation**: [Development Guide](docs/DEVELOPMENT.md)

## 🙏 Citation

If you use this database in your research, please cite:

```
[Citation format will be provided upon publication]
```

## 🔮 Roadmap

- **Phase 1** (Current): Core functionality and data access
- **Phase 2**: Advanced visualizations and analytics  
- **Phase 3**: User accounts and collaboration features
- **Phase 4**: Machine learning insights and recommendations
- **Phase 5**: Mobile app and API ecosystem

