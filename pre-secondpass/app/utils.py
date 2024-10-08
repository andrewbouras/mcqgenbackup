import pymongo
import os
from pymongo import MongoClient

# Initialize the MongoDB client and database
client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("MONGO_DB_NAME")]

def get_configuration(config_name):
    # Fetch the configuration from the database
    config = db.configurations.find_one({"config_name": config_name})
    if not config:
        raise ValueError(f"Configuration '{config_name}' not found")
    
    # Debugging statement to print the fetched configuration
    print(f"Fetched configuration: {config}")
    
    if "config_values" not in config:
        raise KeyError(f"'config_values' key not found in configuration '{config_name}'")
    
    return config["config_values"]

def get_prompt(prompt_name):
    client = pymongo.MongoClient(os.getenv("MONGODB_URI"))
    db_name = os.getenv("MONGO_DB_NAME")
    if not db_name:
        raise ValueError("MONGO_DB_NAME environment variable is not set")
    print(f"Using database: {db_name}")  # Debug print statement
    db = client[db_name]
    collection = db["prompts"]
    prompt = collection.find_one({"prompt_name": prompt_name})
    if not prompt:
        raise ValueError(f"Prompt '{prompt_name}' not found")
    
    # Return a dictionary with all fields from the prompt document
    return {
        "regular_prompt": prompt.get("prompt_text", ""),
        "intro_prompt": prompt.get("intro_prompt", ""),
        "variables": prompt.get("variables", []),
        "examples": prompt.get("examples", [])
    }