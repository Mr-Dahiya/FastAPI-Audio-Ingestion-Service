# FastAPI Audio Ingestion Service

This project implements a resilient, high-performance microservice designed to ingest real-time audio metadata from a PBX (Private Branch Exchange) system. It features non-blocking ingestion, strict state machine transitions, and a background processing layer that handles "unreliable" external AI dependencies with robust error handling.

## 🚀 Key Features

### 1. Non-Blocking Ingestion (Async/Await)
The system is built on an asynchronous architecture using **FastAPI** and **AsyncPG**.
- **Performance:** Ingestion endpoints return `202 Accepted` immediately (<50ms response time), ensuring the stream is never blocked.
- **Background Processing:** Heavy compute tasks (AI processing) are offloaded to background workers to maintain high throughput.

### 2. Concurrency Control (Race Condition Handling)
To handle simultaneous data packets arriving for the same session ID:
- Implemented **PostgreSQL Row-Level Locking** (`SELECT ... FOR UPDATE`).
- This guarantees **ACID compliance** and data integrity even under heavy concurrent load, preventing "lost update" anomalies.

### 3. Fault Tolerance & Resilience
The system interacts with a simulated "flaky" external AI service (25% failure rate).
- **Exponential Backoff:** Utilizes the `tenacity` library to implement a smart retry strategy.
- **Self-Healing:** If the external service fails (503 Service Unavailable), the system waits (2s, 4s, 8s...) and retries automatically until success, ensuring zero data loss.

---

## 🛠 Methodology

The approach for this project focuses on **responsiveness** and **resilience**. The core problem involves handling high-throughput data streams while interacting with unreliable external services.

* **Non-Blocking Ingestion**: The system leverages **FastAPI's asynchronous capabilities** to separate data ingestion from processing. Incoming metadata packets are acknowledged immediately (`202 Accepted` < 50ms), while heavy compute tasks (AI processing) are offloaded to background workers.
* **Concurrency Control**: To handle the requirement of "Race Conditions," I utilized **Database Row-Level Locking**. This ensures that even if multiple packets for the same call ID arrive simultaneously, they are processed sequentially to maintain data integrity.
* **Fault Tolerance**: The "unreliable" nature of the downstream AI service is managed using an **Exponential Backoff** retry strategy. This prevents the application from crashing or dropping data when external dependencies fail.

---

## 🏗 Technical Details

Specific architectural and logic choices include:

* **State Machine**: A strict Enum-based state machine manages the lifecycle of a call (`IN_PROGRESS` → `COMPLETED` → `PROCESSING_AI` → `ARCHIVED`→ `PROCESSING_AI`(on repeated AI failure) → `FAILED`). This prevents invalid transitions (e.g., trying to process a call that hasn't started).
* **Database Locking**: I chose `PostgreSQL` with `SQLAlchemy Async` specifically to use the `with_for_update()` method. This explicitly locks the row during updates, solving the "Lost Update" problem common in distributed systems.
* **Resilience Library**: Instead of writing a custom retry loop, I utilized the **Tenacity** library. This provides a production-grade implementation of exponential backoff with jitter, ensuring the system recovers gracefully from `503 Service Unavailable` errors.

### 🛠️ Tech Stack

- **Framework:** Python 3.12+, FastAPI
- **Database:** PostgreSQL 15, SQLAlchemy (Async ORM), AsyncPG
- **Resilience:** Tenacity (Retry logic)
- **Testing:** Pytest, HTTPX (Async Client)
- **Infrastructure:** Docker & Docker Compose

---

## 🚀 Setup Instructions

Follow these steps to run the project locally.

### Prerequisites
* **Docker** & **Docker Compose**
* **Python 3.9+**

#### 1. Start the Database
Spin up the PostgreSQL container using Docker Compose:
```bash
docker-compose up -d
```
#### 2. Install requirements
```bash
pip install -r requirements.txt
```
#### 3. Run the server
```bash
uvicorn app.main:app --reload
```
#### 4. Access the API:
Open http://127.0.0.1:8000/docs to use the interactive Swagger UI.

#### 5. Running Tests
To verify the Race Condition logic, run the included integration test:
```bash
python -m pytest tests/test_main.py -v
```
This test spawns concurrent async requests to prove that database locking preserves data integrity.

---

## Project Structure
.
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── database.py
│   ├── services.py
├── tests/
│   ├── __init__.py
│   ├── test_main.py
├── docker-compose.yml
├── requirements.txt
├── .gitignore
└── README.md
