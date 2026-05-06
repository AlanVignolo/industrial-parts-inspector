import uvicorn # 
from .app import app
from .routes import router

app.include_router(router) # Include the router defined in routes.py, which contains all the API endpoints

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) # Run the FastAPI application using Uvicorn, which is an ASGI server for Python. The application will be accessible at http://localhost:8000/
