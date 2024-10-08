from pymongo import MongoClient
import os
from dotenv import load_dotenv
import logging

load_dotenv()

MONGODB_URI = os.getenv('MONGODB_URI')

client = MongoClient(MONGODB_URI)
db = client['prompts_db']
prompts_collection = db['prompts']

try:
    print("Attempting to connect to MongoDB...")
    all_prompts = list(prompts_collection.find({}))
    print(f"Number of prompts found: {len(all_prompts)}")
    for prompt in all_prompts:
        print(f"Prompt name: {prompt['prompt_name']}")
    if all_prompts:
        print("Successfully connected to MongoDB Atlas!")
    else:
        print("Connected to MongoDB Atlas, but no data found.")
except Exception as e:
    print(f"Error connecting to MongoDB: {str(e)}")