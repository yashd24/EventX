# EventX

EventX is a Django-based event management platform with support for accounts, bookings, analytics, inventory, and more.
It is fully containerized with Docker for easy setup and deployment, and is deployed on Kubernetes for scalability and high availability.
---
Live URL:  http://34.60.239.163 

## 🚀 Features
- User authentication & account management
- Event creation and bookings
- Inventory tracking
- Analytics dashboard
- Production-ready with **Gunicorn** + **Docker**

---

## 📦 Prerequisites
Make sure you have the following installed on your system:
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/)

---

## 🛠️ Setup & Run

### 1. Clone the repository
```bash
git clone https://github.com/yashd24/EventX.git
cd EventX
```

### 2. Build and start containers
```bash
docker-compose up --build

```
This will:

- Build the Django app container

- Run database and dependencies

- Start the application with Gunicorn

## 🐳 Common Commands
### Start the containers
```bash
docker-compose up
```
### Stop containers
```bash
docker-compose down
```
### View Logs
```bash
docker-compose logs -f
```

## 📂 Project Structure
```bash
EventX-main/
└── EventX-main/
    ├── accounts/          # User authentication and profiles
    ├── analytics/         # Reporting and analytics
    ├── bookings/          # Booking system
    ├── events/            # Event management
    ├── inventory/         # Inventory tracking
    ├── Dockerfile
    ├── docker-compose.yaml
    ├── entrypoint.sh
    ├── gunicorn_config.py
    ├── manage.py
    └── requirements.txt
```

