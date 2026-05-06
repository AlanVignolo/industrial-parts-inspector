from contextlib import asynccontextmanager
from fastapi import FastAPI
from .camera import open_camera, close_camera

@asynccontextmanager
async def lifespan(app: FastAPI):
    open_camera() # Open the camera when the application starts
    yield
    close_camera() # Close the camera when the application shuts down

app = FastAPI(lifespan=lifespan) # Create the FastAPI application with the lifespan context manager
