# FastAPI Project

This repository contains a FastAPI application with MongoDB Atlas integration.

## Prerequisites

-   Python 3.8+
-   MongoDB Atlas account (free tier works fine)
-   Git

## MongoDB Atlas Setup

1. Create a free MongoDB Atlas account at [https://www.mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)
2. Create a new cluster (the free tier is sufficient)
3. In the Security tab, create a database user with read/write permissions
4. In Network Access, add your IP address or allow access from anywhere (0.0.0.0/0)
5. Copy your connection string from the Connect button
6. Create a `.env` file from the example:

```bash
cp .env.example .env
```

7. Update the `.env` file with your MongoDB connection string:

```
MONGODB_URL=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/<database>?retryWrites=true&w=majority
```

## MongoDB Azure Setup

### Prerequisites

-   Azure account with active subscription
-   Azure Cosmos DB account with MongoDB API

### Setup Steps

1. **Create Azure Cosmos DB Account**:

    - Go to the Azure Portal
    - Create a new Cosmos DB account
    - Select MongoDB API as the API type
    - Configure other settings as needed

2. **Get Connection String**:

    - After creating the account, go to "Connection String" in the left menu
    - Copy the Primary Connection String

3. **Configure Environment Variables**:
   Add the following to your `.env` file:

    ```
    MONGODB_CONNECTION_STRING=your_connection_string_here
    MONGODB_DATABASE_NAME=your_database_name
    ```

4. **Install Required Packages**:
    ```
    pip install pymongo python-dotenv
    ```

### API Endpoints for Projects

-   `POST /api/projects` - Create a new project
-   `GET /api/projects` - List all projects
-   `GET /api/projects/{project_id}` - Get a specific project by ID

## Setup

1. Create a virtual environment (recommended):

```bash
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Application

Start the FastAPI server:

```bash
python -m uvicorn main:app --reload
```

The application will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:

-   Interactive API documentation (Swagger UI) at `http://localhost:8000/docs`
-   Alternative API documentation (ReDoc) at `http://localhost:8000/redoc`

## Development

The `--reload` flag enables hot reloading, which automatically restarts the server when you make changes to the code.

### Troubleshooting

If you encounter permission issues when activating the virtual environment, try running PowerShell as administrator or use the following command:

```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

az acr build --resource-group rg-veervs19-7627_ai --registry flowaiacr --image flowaiapi .
