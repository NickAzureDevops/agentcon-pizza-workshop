from fastapi import FastAPI
from pydantic import BaseModel
from tools import calculate_pizza_for_people

app = FastAPI()

class PizzaRequest(BaseModel):
    people_count: int
    appetite_level: str = "normal"

@app.post("/calculate_pizza")
def calculate_pizza(req: PizzaRequest):
    result = calculate_pizza_for_people(req.people_count, req.appetite_level)
    return {"recommendation": result}