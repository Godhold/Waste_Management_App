# Waste Management Tracking App

A comprehensive waste management tracking system built with FastAPI and PostgreSQL, featuring real-time driver tracking, route optimization, and performance analytics.

## Features

- **Driver Management**
  - Driver registration and authentication
  - Real-time location tracking
  - Performance dashboard with daily, weekly, and monthly statistics

- **Collection Management**
  - Schedule and track waste collections
  - Photo documentation of collections
  - Status updates and notifications

- **Route Optimization**
  - Intelligent route planning
  - Distance calculation
  - Navigation assistance

- **Analytics Dashboard**
  - Collection completion rates
  - Distance covered metrics
  - Time efficiency analysis

## Tech Stack

- **Backend**: FastAPI, PostgreSQL, SQLAlchemy, Redis
- **Infrastructure**: Docker, Docker Compose
- **Authentication**: JWT
- **File Storage**: Local file system (configurable for cloud storage)

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.8+
- PostgreSQL
- Redis

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/waste-management-tracking-app.git
   cd waste-management-tracking-app
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the Docker containers:
   ```bash
   docker-compose up -d
   ```

5. Run the application:
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8001
   ```

The API will be available at `http://localhost:8001`.

## API Documentation

Once the application is running, you can access:
- Swagger UI documentation at `http://localhost:8001/docs`
- ReDoc documentation at `http://localhost:8001/redoc`

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/waste_management
REDIS_URL=redis://localhost:6379
SECRET_KEY=your_secret_key
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
