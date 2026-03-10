# Cloud-Based EMI Failure Prevention Framework

> A production-grade, cloud-native web application for intelligent EMI monitoring, risk detection, and automated alert generation — built with Python Flask and deployable on AWS.

---

## Project Overview

| Item | Detail |
|------|--------|
| **Backend** | Python 3.11, Flask 3.x, REST API |
| **Database** | MySQL 8.x / AWS RDS |
| **Frontend** | HTML5, Bootstrap 5, Vanilla JS |
| **Deployment** | AWS EC2 + RDS + S3 + CloudWatch |
| **Security** | PBKDF2-SHA256 passwords, session auth, HTTPS |

---

## Folder Structure

```
emi_framework/
│
├── backend/
│   ├── app.py                    # Flask application factory
│   ├── requirements.txt          # Python dependencies
│   ├── gunicorn.conf.py          # Production WSGI config
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── db.py                 # MySQL connection pool
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py               # /api/auth/*
│   │   ├── customers.py          # /api/customers/*
│   │   ├── loans.py              # /api/loans/*
│   │   ├── emi.py                # /api/emi/*
│   │   ├── alerts.py             # /api/alerts/*
│   │   └── frontend.py           # HTML page serving
│   │
│   └── utils/
│       ├── __init__.py
│       ├── emi_engine.py         # EMI formula + risk algorithm
│       ├── alert_system.py       # Alert generation + email
│       └── security.py           # Password hashing + auth decorators
│
├── frontend/
│   └── templates/
│       ├── base.html             # Shared layout + sidebar
│       ├── login.html            # Login & Register page
│       ├── dashboard.html        # Customer dashboard
│       ├── loans.html            # Loan portfolio
│       ├── loan_detail.html      # Single loan view
│       ├── emi_schedule.html     # Amortisation table + pay
│       ├── alerts.html           # Alert centre
│       └── calculator.html       # Standalone EMI calculator
│
├── database/
│   └── schema.sql                # Full MySQL schema + sample data
│
├── deployment/
│   └── AWS_DEPLOYMENT_GUIDE.txt  # Complete AWS setup guide
│
├── tests/
│   └── test_backend.py           # Pytest test suite
│
├── .env.example                  # Environment variable template
└── README.md                     # This file
```

---

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- MySQL 8.x (local or Docker)

### 1 – Clone & Setup

```bash
git clone <your-repo-url>
cd emi_framework

# Copy environment file
cp .env.example .env
# Edit .env with your local DB credentials
```

### 2 – Install Dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3 – Setup Database

```bash
# Create DB and apply schema
mysql -u root -p < ../database/schema.sql

# Create app user
mysql -u root -p -e "
CREATE USER 'emi_user'@'localhost' IDENTIFIED BY 'emi_password';
GRANT ALL PRIVILEGES ON emi_framework.* TO 'emi_user'@'localhost';
FLUSH PRIVILEGES;"
```

### 4 – Run Application

```bash
# Development
python app.py

# Production (local test)
gunicorn -c gunicorn.conf.py app:app
```

Open: http://localhost:5000

### 5 – Register First User

Visit http://localhost:5000/login → Click **Register** tab  
Or use curl:

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"full_name":"John Doe","email":"john@example.com","phone":"9876543210","password":"password123","dob":"1990-05-15","address":"Chennai, TN"}'
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Register new customer |
| POST | /api/auth/login | Login |
| POST | /api/auth/logout | Logout |
| GET | /api/auth/me | Current user profile |
| GET | /api/customers/{id}/dashboard | Dashboard aggregation |
| POST | /api/loans/ | Create loan + generate schedule |
| GET | /api/loans/ | List customer loans |
| GET | /api/loans/{id} | Loan detail + financial summary |
| GET | /api/emi/loan/{id} | Full EMI schedule |
| POST | /api/emi/{id}/pay | Record payment |
| POST | /api/emi/loan/{id}/refresh | Re-evaluate risk levels |
| GET | /api/emi/calculate | Stateless EMI calculator |
| GET | /api/alerts/ | List alerts |
| GET | /api/alerts/summary | Risk count summary |
| POST | /api/alerts/trigger/{loan_id} | Generate alerts for loan |

---

## EMI Formula

```
EMI = [P × R × (1+R)^N] / [(1+R)^N – 1]

P = Principal
R = Monthly Interest Rate (Annual Rate ÷ 12 ÷ 100)
N = Tenure in Months
```

---

## Risk Detection Rules

| Condition | Risk Level |
|-----------|-----------|
| Status = PAID | ✅ SAFE |
| Due date < Today (overdue) | 🔴 CRITICAL |
| Due date within 3 days | 🟡 WARNING |
| All other pending | 🟢 SAFE |

---

## Testing

```bash
cd emi_framework
python3 -c "exec(open('tests/test_backend.py').read())"

# Or with pytest installed:
pytest tests/ -v
```

---

## AWS Deployment

See `deployment/AWS_DEPLOYMENT_GUIDE.txt` for the complete 13-step guide covering:
- EC2 instance setup
- RDS MySQL configuration
- Nginx reverse proxy
- HTTPS with Let's Encrypt
- S3 automated backups
- CloudWatch monitoring
- IAM security configuration

---

## Security Features

- **Password Hashing**: PBKDF2-HMAC-SHA256 with 260,000 iterations and random salt
- **Session Auth**: Flask server-side sessions with HttpOnly cookies
- **CORS**: Configurable allowed origins
- **RDS**: Private subnet, not publicly accessible
- **HTTPS**: Let's Encrypt SSL certificates (production)
- **IAM**: Least-privilege roles for EC2, no hardcoded AWS keys

---

## License

For educational and academic use. Final Year Project – Cloud Computing.
