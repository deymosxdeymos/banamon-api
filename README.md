# Banamon API

Banamon API is a FastAPI-based web service designed to predict banana leaf diseases. It leverages machine learning models for prediction, integrates with Google Cloud Storage for image uploads, and uses Firestore for storing prediction history.

---

## Features
- **User Authentication**: Token-based authentication with JWT.
- **Disease Prediction**: Upload banana leaf images for disease prediction.
- **Cloud Storage Integration**: Securely stores images in Google Cloud Storage.
- **Prediction History**: Tracks user predictions in Firestore.
- **Health Check**: Ensures service readiness and availability.

---

## Requirements
### Prerequisites
- Python 3.10+
- Docker (for containerization)
- Google Cloud Platform account

### Environment Variables
Ensure the following environment variables are set:

| Variable               | Description                                      |
|------------------------|--------------------------------------------------|
| `MODEL_PATH`           | Path to the trained ML model file               |
| `IMAGES_BUCKET`        | Name of the Google Cloud Storage bucket         |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID                                  |
| `MODEL_VERSION`        | Version of the deployed model                   |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to GCP service account credentials |

---

## Installation
### Local Development
1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/banamon-api.git
   cd banamon-api
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

### Docker
1. Build the Docker image:
   ```bash
   docker build -t banamon-api .
   ```

2. Run the Docker container:
   ```bash
   docker run -p 8080:8080 -e MODEL_PATH=/app/model/banana_disease_model_vgg_v3.keras -e IMAGES_BUCKET=banamon-images -e GOOGLE_CLOUD_PROJECT=capstone-project-banamon banamon-api
   ```

---

## API Endpoints

### Authentication
#### **POST** `/auth/register`
Register a new user.
```json
{
  "email": "user@example.com",
  "password": "string"
}
```

#### **POST** `/auth/login`
Log in and retrieve access and refresh tokens.
```json
{
  "email": "user@example.com",
  "password": "string"
}
```

### Prediction
#### **POST** `/predict`
Upload a banana leaf image for disease prediction.
- **Headers**:
  ```json
  {
    "Authorization": "Bearer <access_token>"
  }
  ```
- **Body**:
  Form-data with key `file` containing the image file.

### History
#### **GET** `/history/predict`
Retrieve user prediction history.

### Health Check
#### **GET** `/health`
Check API health and readiness.

---

## Deployment
### Google Cloud Run
1. Build and push the Docker image:
   ```bash
   gcloud builds submit --tag gcr.io/<project-id>/banamon-api
   ```

2. Deploy to Cloud Run:
   ```bash
   gcloud run deploy banamon-api \
     --image gcr.io/<project-id>/banamon-api \
     --region asia-southeast2 \
     --memory 8Gi \
     --cpu 4 \
     --timeout 600 \
     --service-account <service-account-email> \
     --allow-unauthenticated
   ```

---

## Monitoring and Logging
### Logs
Monitor logs using GCP:
```bash
gcloud run services logs read banamon-api --region asia-southeast2
```

### Budget Monitoring
Set up budgets and alerts in the GCP Billing dashboard to monitor service usage and costs.

---

## Contributing
Contributions are welcome! Please submit a pull request with detailed information about your changes.

---

## License
This project is licensed under the MIT License. See the LICENSE file for details.

---

## Support
For questions or support, contact [your-email@example.com].

