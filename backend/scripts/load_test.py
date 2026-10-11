"""Load testing script using Locust."""

import os
from locust import HttpUser, task, between, events
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get base URL and API key from environment
BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000')
API_KEY = os.getenv('API_KEY', 'test-key')


class RAGDocQAUser(HttpUser):
    """Simulated user for load testing."""

    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks

    def on_start(self):
        """Setup: Register and login user."""
        self.token = None
        self.documents = []
        self.register_and_login()

    def register_and_login(self):
        """Register a new user and get auth token."""
        import uuid
        email = f"user_{uuid.uuid4().hex[:8]}@loadtest.com"

        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "username": f"user_{uuid.uuid4().hex[:8]}",
                "password": "LoadTestPass123"
            }
        )

        if response.status_code == 201:
            self.token = response.json()["access_token"]
            logger.info(f"Registered user: {email}")

    def get_headers(self):
        """Get request headers with auth token."""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    @task(1)
    def get_stats(self):
        """Load test: Get user statistics."""
        self.client.get(
            "/api/v1/analytics/user/stats",
            headers=self.get_headers()
        )

    @task(2)
    def ask_question(self):
        """Load test: Ask a question (RAG)."""
        self.client.post(
            "/api/v1/ask",
            json={
                "question": "What is artificial intelligence?",
                "top_k": 5
            },
            headers=self.get_headers()
        )

    @task(1)
    def list_documents(self):
        """Load test: List documents."""
        self.client.get(
            "/api/v1/documents",
            headers=self.get_headers()
        )

    @task(1)
    def health_check(self):
        """Load test: Health check."""
        self.client.get("/api/v1/health")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print summary statistics when test stops."""
    print("\n=== Load Test Summary ===")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    print(f"Average response time: {environment.stats.total.avg_response_time:.2f}ms")
    print(f"Min response time: {environment.stats.total.min_response_time:.2f}ms")
    print(f"Max response time: {environment.stats.total.max_response_time:.2f}ms")
    print(f"Requests/sec: {environment.stats.total.total_rps:.2f}")


if __name__ == "__main__":
    print("Run with: locust -f scripts/load_test.py --host=" + BASE_URL)
