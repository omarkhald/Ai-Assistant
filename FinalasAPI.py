from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from key import api_key
from groq import Groq, GroqError
from firebase_admin import credentials, firestore, initialize_app
import os
import uvicorn
from threading import Thread

# Initialize FastAPI app
app = FastAPI()

# Initialize LLAMA3 client
client = Groq(api_key=api_key)

messages = [
    {"role": "system", "content": "You are a friendly human assistant, you have to remember anything user tell and answer all the questions."}
]

# Initialize Firebase
cred = credentials.Certificate('ai-assistant-33cbf-firebase-adminsdk-s366o-590ff3472e.json')
initialize_app(cred)
db = firestore.client()

# Define request and response models
class QuestionRequest(BaseModel):
    user_id: str
    question: str

class ResponseModel(BaseModel):
    response: str

# Function to query the Llama3 model
def query_llama3(question):
    global messages
    
    # Add user input to messages
    messages.append({"role": "user", "content": question})

    # Generate response from LLAMA3
    chat_completion = client.chat.completions.create(
        messages=messages,
        model="llama3-8b-8192"
    )
    response = chat_completion.choices[0].message.content

    # Add assistant response to messages
    messages.append({"role": "assistant", "content": response})
    
    return response

# Function to store question and response
def store_interaction(user_id, question, response):
    user_ref = db.collection('users').document(user_id)
    doc = user_ref.get()

    interaction = {'question': question, 'response': response}

    if doc.exists:
        user_ref.update({
            'interactions': firestore.ArrayUnion([interaction])
        })
    else:
        user_ref.set({
            'interactions': [interaction]
        })

# Function to retrieve stored interactions
def get_stored_interactions(user_id):
    user_ref = db.collection('users').document(user_id)
    doc = user_ref.get()

    if doc.exists:
        data = doc.to_dict()
        interactions = data.get('interactions', [])
        return interactions
    else:
        return []

# Function to handle user questions with context
def handle_user_question(user_id, question):
    global messages

    # Retrieve stored interactions
    interactions = get_stored_interactions(user_id)

    # Generate the context from previous interactions
    for interaction in interactions:
        if isinstance(interaction, dict):  # Ensure interaction is a dictionary
            messages.append({"role": "user", "content": interaction['question']})
            messages.append({"role": "assistant", "content": interaction['response']})

    # Use context to query the Llama3 model
    response = query_llama3(question)

    # Store the new interaction
    store_interaction(user_id, question, response)

    # Return the response
    return response

# Define API endpoint for asking questions
@app.post("/ask/", response_model=ResponseModel)
async def ask_question(question_request: QuestionRequest):
    try:
        response = handle_user_question(question_request.user_id, question_request.question)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def run_ngrok(ngrok_token):
    os.system(f"ngrok authtoken {ngrok_token}")
    os.system("ngrok http 8000")

if __name__ == "__main__":
    # Start ngrok tunnel in a separate thread
    ngrok_token = "2gT2RHwaagYhWuZ0FiL0HjToAV8_mC5WXUKHViX3Z16b2N8g"  # Replace this with your ngrok authentication token
    Thread(target=run_ngrok, args=(ngrok_token,)).start()

    # Run FastAPI app using uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
