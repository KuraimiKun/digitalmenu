# Digital Menu SaaS Platform

A professional, scalable digital menu SaaS platform for restaurants and food service businesses built with Django and PostgreSQL.

## 🚀 Features

### Core Features
- **Multi-tenant Architecture**: Support for multiple restaurants with separate data isolation
- **Multi-location Support**: Manage multiple restaurant locations from a single account
- **Role-based Access Control**: Admin, Owner, Manager, Staff, and Customer roles
- **Subscription Management**: Tiered pricing plans with feature limits

### Menu Management
- **Drag-and-Drop Menu Builder**: Intuitive menu creation with categories and items
- **Customizable Themes**: Brand your menus with custom colors, fonts, and layouts
- **Item Variants & Modifiers**: Support for sizes, add-ons, and customizations
- **Multi-language Support**: 10+ languages with automatic translation
- **Multi-currency Support**: Display prices in customer's preferred currency
- **Real-time Updates**: Changes reflect instantly across all platforms

### QR Code System
- **Dynamic QR Codes**: Generate unique QR codes for menus, tables, and locations
- **Custom Designs**: Brand QR codes with logos and custom colors
- **Batch Generation**: Create QR codes for all tables at once
- **Scan Analytics**: Track scans by device, location, and time

### Online Ordering
- **Dine-in Ordering**: Customers order directly from their table
- **Takeout & Delivery**: Support for pickup and delivery orders
- **Cart Management**: Persistent shopping cart with modifiers
- **Order Tracking**: Real-time order status updates
- **Payment Integration**: Stripe payments with tips and fees

### Promotions & Loyalty
- **Discount Codes**: Percentage, fixed amount, BOGO, and free item discounts
- **Loyalty Programs**: Points-based rewards with tiers
- **Referral System**: Customer referral bonuses
- **Time-based Promotions**: Happy hour and scheduled deals

### Analytics Dashboard
- **Sales Reports**: Daily, weekly, and monthly revenue tracking
- **Popular Items**: Track best-selling menu items
- **Customer Insights**: Analyze customer behavior and preferences
- **Performance Metrics**: Monitor order fulfillment and ratings

### Integrations
- **Delivery Platforms**: DoorDash, Uber Eats, Grubhub integration
- **POS Systems**: Connect with existing point-of-sale systems
- **Payment Gateways**: Stripe, Square, and more
- **Webhooks**: Real-time event notifications

## 🛠 Technology Stack

- **Backend**: Django 5.0, Django REST Framework
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7
- **Task Queue**: Celery
- **Authentication**: JWT (Simple JWT), django-allauth
- **API Documentation**: drf-spectacular (OpenAPI/Swagger)
- **Containerization**: Docker, Docker Compose
- **Web Server**: Gunicorn, Nginx
- **Cloud Storage**: AWS S3 (production)

## 📦 Project Structure

```
digitalmenu/
├── apps/
│   ├── core/           # Users, auth, permissions, audit logging
│   ├── restaurants/    # Restaurant and location management
│   ├── menus/          # Menu builder, items, categories, themes
│   ├── orders/         # Order processing, cart, reviews
│   ├── analytics/      # Reports and insights
│   ├── promotions/     # Discounts, loyalty programs
│   ├── integrations/   # Third-party service connections
│   └── qrcodes/        # QR code generation and tracking
├── digitalmenu/        # Project settings
├── docker/             # Docker configuration
├── templates/          # HTML templates
├── static/             # Static assets
└── media/              # User uploads
```

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.12+ (for local development)
- PostgreSQL 16 (for local development)
- Redis 7 (for local development)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/digitalmenu.git
   cd digitalmenu
   ```

2. **Copy environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Start with Docker Compose**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
   ```

4. **Run migrations**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

5. **Create superuser**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

6. **Access the application**
   - API: http://localhost:8000/api/
   - Admin: http://localhost:8000/admin/
   - API Docs: http://localhost:8000/api/docs/
   - pgAdmin: http://localhost:5050
   - Redis Commander: http://localhost:8081

### Local Development (without Docker)

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up database**
   ```bash
   createdb digitalmenu
   python manage.py migrate
   ```

4. **Run development server**
   ```bash
   python manage.py runserver
   ```

5. **Run Celery worker** (in separate terminal)
   ```bash
   celery -A digitalmenu worker -l INFO
   ```

## 🔐 API Authentication

The API uses JWT authentication. To obtain tokens:

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use token
curl http://localhost:8000/api/restaurants/ \
  -H "Authorization: Bearer <access_token>"
```

## 📚 API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- OpenAPI Schema: http://localhost:8000/api/schema/

## 🧪 Testing

```bash
# Run all tests
python manage.py test

# Run with coverage
coverage run manage.py test
coverage report
coverage html
```

## 🚢 Production Deployment

1. **Set production environment variables**
   ```bash
   DEBUG=False
   SECRET_KEY=<secure-random-key>
   ALLOWED_HOSTS=yourdomain.com
   # ... other production settings
   ```

2. **Build and deploy**
   ```bash
   docker-compose -f docker-compose.yml up -d --build
   ```

3. **Run migrations**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

4. **Configure SSL certificates**
   Place your SSL certificates in `docker/nginx/ssl/`:
   - `fullchain.pem`
   - `privkey.pem`

## 📋 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Debug mode | `False` |
| `SECRET_KEY` | Django secret key | Required |
| `DATABASE_URL` | PostgreSQL connection URL | Required |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `STRIPE_SECRET_KEY` | Stripe API key | Optional |
| `AWS_ACCESS_KEY_ID` | AWS access key | Optional |
| `FRONTEND_URL` | Frontend application URL | `http://localhost:3000` |

See `.env.example` for all available variables.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For support, email support@digitalmenu.com or open an issue on GitHub.
