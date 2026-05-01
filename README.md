# ATS CV Builder - Backend

A Django REST API backend for the ATS CV Builder SaaS application. Provides user authentication, CV management, AI suggestions, PDF generation, and Stripe payment integration.

## Features

- **User Authentication** - JWT-based auth with register/login/logout
- **CV Management** - Full CRUD operations for multiple CVs per user
- **AI Suggestions** - OpenAI-powered CV improvement suggestions
- **PDF Export** - Generate professional PDF resumes
- **Stripe Integration** - Subscription payments and webhooks
- **PostgreSQL Database** - Production-ready database
- **REST API** - Full RESTful API with Django REST Framework

## Tech Stack

- Django 5+ (Python web framework)
- Django REST Framework (API)
- Simple JWT (authentication)
- PostgreSQL (database)
- Stripe (payments)
- OpenAI (AI suggestions)
- Gunicorn (WSGI server)
- WhiteNoise (static files)

## Prerequisites

- Python 3.10+
- PostgreSQL 15+ (for production)
- pip or pipenv

## Environment Variables

Create a `.env` file in the backend root:

```env
# Required in production
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,your-subdomain.onrender.com

# Database (PostgreSQL)
DATABASE_URL=postgres://user:password@localhost:5432/dbname

# OpenAI (for AI suggestions)
OPENAI_API_KEY=sk-your-openai-key

# Stripe - Get test keys from https://dashboard.stripe.com/test/apikeys
STRIPE_SECRET_KEY=sk_test_...           # From API Keys page
STRIPE_PUBLISHABLE_KEY=pk_test_...      # From API Keys page
STRIPE_WEBHOOK_SECRET=whsec_...         # From Webhooks page (see below)
STRIPE_PRICE_ID=price_...               # From Products/Prices page (see below)

# To get STRIPE_WEBHOOK_SECRET:
# 1. Go to https://dashboard.stripe.com/test/webhooks
# 2. Click "Add endpoint"
# 3. Enter URL: http://your-domain/api/subscription/webhook/
# 4. Select events: checkout.session.completed, customer.subscription.updated, customer.subscription.deleted
# 5. Click "Add endpoint" and copy the "Signing secret" (whsec_...)

# To get STRIPE_PRICE_ID:
# 1. Go to https://dashboard.stripe.com/test/products
# 2. Click "Add product" - enter name (e.g., "Premium Plan")
# 3. Click "Add price" - set amount (e.g., $9.99/month), click "Save"
# 4. Copy the price ID (starts with price_...) from the product page



# Frontend URL
FRONTEND_URL=http://localhost:5173
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

See `.env.example` for all available variables.

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Local Development

```bash
# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Start development server
python manage.py runserver

# The API will be available at http://localhost:8000
```

## Docker Deployment

Build and run with Docker:

```bash
# Build the image
docker build -t ats-cv-backend .

# Run the container
docker run -p 8000:8000 ats-cv-backend
```

Or use docker-compose to run all services together:

```bash
docker-compose up --build
```

See the main `docker-compose.yml` in the project root for full stack deployment.

## Render Deployment

See [RENDER_DEPLOY.md](../RENDER_DEPLOY.md) for detailed deployment instructions to Render.com.

Quick start:
```bash
# Set environment variables in Render dashboard
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn --bind 0.0.0.0:8000 core.wsgi:application
```

## API Endpoints

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/users/register/` | POST | Register new user |
| `/api/users/login/` | POST | Login user |
| `/api/users/logout/` | POST | Logout user |
| `/api/users/me/` | GET/PUT | Get/Update current user |
| `/api/users/token/` | POST | Get JWT token |
| `/api/users/token/refresh/` | POST | Refresh JWT token |

### CV Management
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/cv/` | GET | List user's CVs |
| `/api/cv/` | POST | Create new CV |
| `/api/cv/{id}/` | GET | Get CV details |
| `/api/cv/{id}/` | PUT | Update CV |
| `/api/cv/{id}/` | DELETE | Delete CV |
| `/api/cv/{id}/duplicate/` | POST | Duplicate CV |
| `/api/cv/{id}/pdf/` | GET | Export as PDF |
| `/api/cv/{id}/suggestions/` | POST | Get AI suggestions |
| `/api/cv/{id}/analyze/` | POST | ATS match analysis |

### Subscription
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/subscription/checkout/` | POST | Create Stripe checkout |
| `/api/subscription/cancel/` | POST | Cancel subscription |
| `/api/subscription/webhook/` | POST | Stripe webhook |
| `/api/subscription/status/` | GET | Get subscription status |

### Social Sharing
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/cv/{id}/share/` | POST | Share CV on platform |

## Project Structure

```
backend/
├── core/                  # Django project settings
│   ├── settings.py       # Main settings
│   ├── urls.py           # URL configuration
│   ├── wsgi.py           # WSGI application
│   └── asgi.py           # ASGI application
├── users/                 # Users app
│   ├── models.py         # User model
│   ├── views.py         # API views
│   ├── urls.py           # URL routes
│   └── admin.py         # Admin configuration
├── cv/                    # CV app
│   ├── models.py         # CV model
│   ├── views.py          # API views
│   ├── urls.py           # URL routes
│   └── admin.py          # Admin configuration
├── manage.py
├── requirements.txt
├── Dockerfile
└── gunicorn.conf.py
```

## Database Models

### User Model
- `id` - Primary key
- `email` - Unique email
- `username` - Unique username
- `first_name` - First name
- `last_name` - Last name
- `password` - Hashed password
- `stripe_customer_id` - Stripe customer ID
- `stripe_subscription_id` - Stripe subscription ID
- `is_subscription_active` - Subscription status
- `referral_code` - Unique referral code
- `referral_count` - Referral count
- `shared_platforms` - JSON of shared platforms

### CV Model
- `id` - Primary key
- `user` - Foreign key to User
- `name` - CV name
- `job_title` - Target job title
- `status` - CV status (draft, optimized, shared)
- `version` - Version number
- `is_template` - Is template flag
- `data` - CV JSON data
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp
- `shared_on` - Share timestamp
- `shared_platforms` - JSON of sharing platforms

## Testing

```bash
# Run tests
python manage.py test

# Check code with pylint
pylint users cv
```

## Security

See [SECURITY_AUDIT.md](../SECURITY_AUDIT.md) for security details.

Key security features:
- JWT authentication
- CORS protection
- CSRF protection
- Secure cookies in production
- SSL/HTTPS required
- X-Frame-Options protection

## License

MIT License
