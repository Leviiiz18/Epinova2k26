import uvicorn
from server import app

if __name__ == '__main__':
    print("Starting StudyBuddy Main Entrypoint on http://127.0.0.1:8000...")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)