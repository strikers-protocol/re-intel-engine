# ?? API Reference 
 
The platform provides a RESTful API built on FastAPI. All endpoints require JWT authentication except for user registration and login. 
 
## Authentication Endpoints 
 
| Method | Endpoint | Description | Auth Required | 
| :--- | :--- | :--- | :--- | 
| `POST` | `/api/auth/register` | Register a new operator account | No | 
| `POST` | `/api/auth/login` | Authenticate and retrieve JWT token | No | 
| `GET`  | `/api/auth/me` | Retrieve current authenticated session info | **Yes** | 
 
## Analysis Operations 
 
| Method | Endpoint | Description | Auth Required | 
| :--- | :--- | :--- | :--- | 
| `POST` | `/api/analysis/run` | Submit a payload for multi-vector analysis | **Yes** | 
| `GET`  | `/api/analysis/history` | Retrieve full analysis history for the user | **Yes** | 
| `GET`  | `/api/analysis/{id}` | Fetch detailed intelligence for a specific scan | **Yes** | 
| `GET`  | `/api/analysis/{id}/pdf` | Generate and download a PDF threat report | **Yes** | 
| `DELETE` | `/api/analysis/{id}` | Purge an analysis record from the database | **Yes** | 
 
> **Note:** For interactive endpoint testing, run the server locally and navigate to `http://localhost:8000/api/docs` to access the auto-generated Swagger UI. 
