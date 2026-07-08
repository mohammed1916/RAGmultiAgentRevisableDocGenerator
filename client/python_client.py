"""Python client library for the Document Generation API."""

import requests
from typing import Optional, Dict, Any
from models import DocumentResponse


class DocumentGenerationClient:
    """Client for interacting with the Document Generation API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the client.

        Args:
            base_url: Base URL of the API server
        """
        self.base_url = base_url
        self.session = requests.Session()

    def generate_document(self, request: str, **kwargs) -> DocumentResponse:
        """Generate a document from a natural language request.

        Args:
            request: Natural language request for the document
            **kwargs: Additional parameters (e.g., metadata)

        Returns:
            DocumentResponse instance

        Raises:
            requests.RequestException: If API call fails
        """
        payload = {"request": request}
        if kwargs:
            payload.update(kwargs)

        response = self.session.post(
            f"{self.base_url}/agent",
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        return DocumentResponse(**data)

    def health_check(self) -> Dict[str, Any]:
        """Check API server health.

        Returns:
            Health check response

        Raises:
            requests.RequestException: If API call fails
        """
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics from the API.

        Returns:
            Metrics data

        Raises:
            requests.RequestException: If API call fails
        """
        response = self.session.get(f"{self.base_url}/metrics")
        response.raise_for_status()
        return response.json()

    def close(self):
        """Close the client session."""
        self.session.close()


def create_client(base_url: str = "http://localhost:8000") -> DocumentGenerationClient:
    """Factory function to create a client instance.

    Args:
        base_url: Base URL of the API server

    Returns:
        DocumentGenerationClient instance
    """
    return DocumentGenerationClient(base_url)
