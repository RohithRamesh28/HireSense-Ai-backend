from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router  
from app.metadata_db_sqlite import init_db

init_db() #db will create here if not 


app = FastAPI()

#middleware thingy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# route
app.include_router(router)

