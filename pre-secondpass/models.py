from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Use the MongoDB URI from the environment variable
client = MongoClient(os.getenv('MONGODB_URI'))
db = client['prompts_db']
prompts_collection = db['prompts']
configurations_collection = db['configurations']

def create_prompt(prompt_name, prompt_text, variables, description):
    prompt = {
        "prompt_name": prompt_name,
        "prompt_text": prompt_text,
        "variables": variables,
        "metadata": {
            "description": description,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    }
    prompts_collection.insert_one(prompt)

def update_prompt(prompt_name, prompt_text=None, variables=None, description=None):
    update_fields = {}
    if prompt_text:
        update_fields["prompt_text"] = prompt_text
    if variables:
        update_fields["variables"] = variables
    if description:
        update_fields["metadata.description"] = description
    update_fields["metadata.updated_at"] = datetime.utcnow()
    
    prompts_collection.update_one({"prompt_name": prompt_name}, {"$set": update_fields})

def get_prompt(prompt_name):
    return prompts_collection.find_one({"prompt_name": prompt_name})

def delete_prompt(prompt_name):
    prompts_collection.delete_one({"prompt_name": prompt_name})

def create_configuration(config_name, config_values, description):
    configuration = {
        "config_name": config_name,
        "config_values": config_values,
        "metadata": {
            "description": description,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    }
    configurations_collection.insert_one(configuration)

def update_configuration(config_name, config_values=None, description=None):
    update_fields = {}
    if config_values:
        update_fields["config_values"] = config_values
    if description:
        update_fields["metadata.description"] = description
    update_fields["metadata.updated_at"] = datetime.utcnow()
    
    configurations_collection.update_one({"config_name": config_name}, {"$set": update_fields})

def get_configuration(config_name):
    return configurations_collection.find_one({"config_name": config_name})

def delete_configuration(config_name):
    configurations_collection.delete_one({"config_name": config_name})