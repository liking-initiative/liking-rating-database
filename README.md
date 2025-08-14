# Liking Rating Database

A comprehensive user-facing database system for food liking ratings from 35+ research studies with 500k+ data entries. This system provides researchers with easy access to standardized food preference data for analysis and research purposes.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Automated Setup (Recommended)
```bash
# Clone the repository
git clone https://github.com/kiante-fernandez/liking-rating-database.git
cd liking-rating-database

# Start both backend and frontend
python start.py
```

The database comes pre-loaded with real research data from 35+ studies.

### Manual Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env
# Edit .env with your configuration if needed

# Frontend setup
cd frontend
npm install

# Start both servers using the automated script
python ../start.py
```

**Note**: The database (`backend/liking_rating_db.db`) comes pre-populated with real research data.

### Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## ✨ Features

- **Comprehensive Data Access**: 500k+ food liking ratings from 35+ research studies
- **Advanced Search**: Filter by study, food items, rating scales, and more
- **Data Standardization**: Normalized rating scales for cross-study comparisons
- **Multiple Export Formats**: CSV, JSON, Excel, SPSS-compatible formats
- **Interactive Interface**: Clean, professional UI built with React and Ant Design
- **Real Research Data**: Pre-loaded with actual academic research datasets
- **Clean Study Names**: User-friendly study titles for easy browsing

## 📊 Current Implementation Status

### ✅ Completed Features
- **Backend API**: FastAPI with comprehensive endpoints and data models
- **Database**: SQLite database pre-loaded with 35+ research studies
- **Search System**: Advanced filtering and search functionality
- **Download System**: Multi-format data export (CSV, JSON, Excel, SPSS)
- **Frontend Interface**: React app with Ant Design components
- **Data Import**: Real academic research data with clean study names
- **Documentation**: API documentation and development guides

### � Future Enhancements
- Interactive data visualizations
- User authentication system
- Advanced analytics dashboard
- Citation management
- Additional export formats

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
- **Studies**: 35+ research studies with clean, descriptive titles
- **Datasets**: 43 individual datasets within studies  
- **Items**: 2,248 standardized food items
- **Ratings**: 500k+ individual preference ratings across multiple scales

## 📖 Documentation

- **[Development Guide](docs/DEVELOPMENT.md)**: Complete setup and development instructions
- **[API Documentation](http://localhost:8000/docs)**: Interactive API documentation (when running)
- **[Data Dictionary](docs/DATA_DICTIONARY.md)**: Detailed field descriptions

## 🔧 Configuration

The application uses environment variables for configuration. Copy `.env.example` to `.env` and modify as needed:

```bash
# Database (SQLite with pre-loaded data)
DATABASE_URL=sqlite+aiosqlite:///./backend/liking_rating_db.db

# API Configuration  
SECRET_KEY=liking-rating-db-secure-key-2025
API_HOST=localhost
API_PORT=8000

# Development settings
DEBUG=True
```

## 📊 Data Overview

The database contains real research data from academic studies:

- **35+ Research Studies** with clean, descriptive titles
- **500k+ Individual Ratings** across multiple rating scales  
- **2,248 Food Items** standardized across studies
- **43 Datasets** with comprehensive metadata

All data has been validated and is ready for research use.

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

- **GitHub**: [kiante-fernandez/liking-rating-database](https://github.com/kiante-fernandez/liking-rating-database)
- **Issues**: [Project Issues](https://github.com/kiante-fernandez/liking-rating-database/issues)
- **Documentation**: [Development Guide](docs/DEVELOPMENT.md)

## 🙏 Citation

If you use this database in your research, please cite:

```
[Citation format will be provided upon publication]
```

## 🔮 Roadmap

- **Phase 1** ✅ **Complete**: Core functionality and real data integration
- **Phase 2**: Advanced visualizations and analytics  
- **Phase 3**: User accounts and collaboration features
- **Phase 4**: Machine learning insights and recommendations
- **Phase 5**: Mobile app and API ecosystem

