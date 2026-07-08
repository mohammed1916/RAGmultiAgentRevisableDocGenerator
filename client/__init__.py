"""Client module - Both Python client library and web frontend.

### Python Client Library
```python
from client import create_client

client = create_client("http://localhost:8000")
response = client.generate_document("Create a project plan...")
print(f"Document: {response.document_filename}")
```

### Web Frontend
To run the client:
1. Open index.html in a web browser
2. Ensure the backend server is running on http://localhost:8000
3. Enter a document request and click "Generate Document"

For development with live reload:
    npm install
    npm run dev

For production build:
    npm install
    npm run build
"""

from .python_client import DocumentGenerationClient, create_client

__all__ = ["DocumentGenerationClient", "create_client"]
