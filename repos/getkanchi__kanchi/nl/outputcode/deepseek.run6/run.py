import uvicorn
from kanchi.config import settings
from kanchi.main import app

if __name__ == "__main__":
    uvicorn.run(app, host=settings.APP_HOST, port=settings.APP_PORT)

