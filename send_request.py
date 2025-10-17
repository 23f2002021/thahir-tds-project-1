import requests
import json

url = "http://127.0.0.1:8000/handle_task"  # Your local FastAPI endpoint

data = {
    "email": "student@example.com",
    "secret": "thahir_123_secret",
    "task": "qr-code-generator",
    "round": 1,
    "nonce": "QRGEN-001",
    "brief": (
        "Build a simple QR Code Generator web app. "
        "The app should have a text input and a 'Generate' button. "
        "When the user enters text or a URL and clicks the button, "
        "it should generate a QR code and display it on the page. "
        "Use a free JS library like 'qrcode.js' or 'qrserver API'. "
        "Style the page with Bootstrap."
    ),
    "checks": [
        "Repo has MIT license",
        "README.md includes usage instructions",
        "Page contains an input field and generate button",
        "QR code image updates dynamically when text changes"
    ],
    "evaluation_url": "https://example.com/notify",
    "attachments": []
}

response = requests.post(url, json=data)
print("Status Code:", response.status_code)
print("Response JSON:", json.dumps(response.json(), indent=2))
