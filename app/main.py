# app/main.py
from fastapi import FastAPI

# VOCÊ PRECISA DESTA LINHA EXATAMENTE ASSIM:
app = FastAPI() 

@app.get("/")
def read_root():
    return {"Hello": "World"}