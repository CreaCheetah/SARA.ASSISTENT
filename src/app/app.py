from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "SARA backend actief"}

@app.get("/healthz")
def health():
    return {"ok": True}
