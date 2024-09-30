from flask import Blueprint, request, jsonify, current_app
import logging
import json
import requests
from json import JSONEncoder
from utils.azure_config import call_azure_api
from models import get_prompt, get_configuration

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        try:
            return json.JSONEncoder.default(self, obj)
        except TypeError:
            return str(obj)

generate_bp = Blueprint('generate', __name__)

def generate_intro_questions(statements, question_style, use_bolding, config):
    prompt_data = get_prompt("generate_mcqs")
    style_config = get_configuration("question_styles")
    bolding_config = get_configuration("bolding_options")

    style_details = style_config["config_values"][question_style]
    bolding_details = bolding_config["config_values"][str(use_bolding).lower()]

    intro_prompt = prompt_data["intro_prompt"].format(
        statements=json.dumps(statements, indent=2),
        style_example=json.dumps(style_details['example'], indent=2),
        bolding_example=json.dumps(bolding_details['example'], indent=2)
    )

    logging.debug(f"Generated intro prompt: {intro_prompt[:500]}...")
    logging.info(f"Full intro prompt being sent to Azure OpenAI: {intro_prompt}")

    response = call_azure_api(intro_prompt, "question_generation", config)
    raw_questions = process_api_response(response)

    # Process the raw questions to ensure correct formatting
    formatted_questions = []
    for q in raw_questions:
        # Ensure answer choices are in alphabetical order
        answer_choices = sorted(q['answerChoices'], key=lambda x: x['value'].lower())
        
        formatted_question = {
            "question": q['question'],
            "answerChoices": answer_choices,
            "explanation": q['explanation'],
            "concept": q['concept'],
            "is_intro_question": True
        }
        formatted_questions.append(formatted_question)

    return formatted_questions

def generate_mcqs(
    text,
    statements,
    num_questions,
    question_style,
    use_bolding,
    config,
    intro_questions=False
):
    logging.debug(f"Entering generate_mcqs with parameters: intro_questions={intro_questions}")

    all_questions = []

    if intro_questions:
        intro_questions = generate_intro_questions(statements[:10], question_style, use_bolding, config)
        all_questions.extend(intro_questions)
        logging.info(f"Generated {len(intro_questions)} intro questions")

    prompt_data = get_prompt("generate_mcqs")
    style_config = get_configuration("question_styles")
    bolding_config = get_configuration("bolding_options")

    if question_style not in style_config["config_values"]:
        raise ValueError(f"Invalid question style: {question_style}")

    style_details = style_config["config_values"][question_style]
    bolding_details = bolding_config["config_values"][str(use_bolding).lower()]

    prompt_text = prompt_data["regular_prompt"]

    remaining_questions = max(0, num_questions - len(all_questions))
    for i in range(0, len(statements), 10):
        chunk = statements[i:i+10]
        chunk_num_questions = min(remaining_questions - len(all_questions), len(chunk))

        if chunk_num_questions <= 0:
            break

        prompt = prompt_text.format(
            num_questions=chunk_num_questions,
            question_style=f"{question_style} (complexity level: {style_details['complexity_level']})",
            style_example=json.dumps(style_details['example'], indent=2),
            bolding_format=bolding_details['formatting'],
            bolding_example=json.dumps(bolding_details['example'], indent=2),
            text=text,
            statements=json.dumps(chunk, indent=2),
            num_answer_choices=5
        )

        logging.debug(f"Generated prompt for chunk {i//10 + 1}: {prompt[:500]}...")
        logging.info(f"Full prompt being sent to Azure OpenAI for chunk {i//10 + 1}: {prompt}")

        response = call_azure_api(prompt, "question_generation", config)
        chunk_questions = process_api_response(response)
        all_questions.extend(chunk_questions)

        if len(all_questions) >= num_questions:
            break

    final_result = {
        "ID": config["ID"],
        "questions": [
            {
                "question": q.get("question", ""),
                "answerChoices": [
                    {
                        "value": choice.get("value", ""),
                        "correct": choice.get("correct", False)
                    }
                    for choice in q.get("answerChoices", [])
                ],
                "explanation": q.get("explanation", ""),
                "concept": q.get("concept", ""),
                "is_intro_question": q.get("is_intro_question", False)
            }
            for q in all_questions
        ]
    }

    return final_result

def process_api_response(response):
    content = response['choices'][0]['message']['content']
    try:
        questions_data = json.loads(content)
        if 'questions' in questions_data:
            return questions_data['questions']
        elif isinstance(questions_data, list):
            return questions_data
        else:
            return [questions_data]
    except json.JSONDecodeError:
        logging.error(f"Failed to parse API response: {content}")
        return []

@generate_bp.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        logging.debug(f"Received data: {data}")

        # Validate and extract parameters
        required_fields = ['ID', 'text', 'num_questions', 'question_style', 'use_bolding']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        task_id = data['ID']
        text = data['text']
        num_questions = data['num_questions']
        question_style = data['question_style']
        use_bolding = data['use_bolding']
        intro_questions = data.get('intro_questions', False)

        # Validate input types
        style_config = get_configuration("question_styles")
        if question_style not in style_config["config_values"]:
            return jsonify({"error": f"Invalid question style: {question_style}"}), 400
        if not isinstance(use_bolding, bool):
            return jsonify({"error": "Invalid bolding option"}), 400
        if not isinstance(num_questions, int) or num_questions <= 0:
            return jsonify({"error": "Invalid number of questions"}), 400

        config = {
            'AZURE_OPENAI_KEY': current_app.config['AZURE_OPENAI_KEY'],
            'AZURE_OPENAI_ENDPOINT': current_app.config['AZURE_OPENAI_ENDPOINT'],
            'AZURE_OPENAI_VERSION': current_app.config['AZURE_OPENAI_VERSION'],
            'AZURE_OPENAI_DEPLOYMENT': current_app.config['AZURE_OPENAI_DEPLOYMENT'],
            'ID': task_id  # Add this line
        }

        # Condense statements if necessary
        statements = data.get('Statements of information', [])
        condensed_statements = condense_statements(statements, num_questions)

        questions_data = generate_mcqs(
            text,
            condensed_statements,
            num_questions,
            question_style,
            use_bolding,
            config,
            intro_questions=intro_questions
        )

        final_result = {"ID": task_id, "questions": questions_data['questions']}

        # Send generated questions to the webhook
        webhook_url = "https://webhook.site/08537c49-227d-4c6f-bf13-de1fad2c353f"
        json_safe_result = {
            "ID": final_result["ID"],
            "questions": [
                {
                    "question": q.get("question", ""),
                    "answerChoices": [
                        {
                            "value": choice.get("value", ""),
                            "correct": choice.get("correct", False)
                        }
                        for choice in q.get("answerChoices", [])
                    ],
                    "explanation": q.get("explanation", ""),
                    "concept": q.get("concept", "")
                }
                for q in final_result["questions"]
            ]
        }
        
        response = requests.post(webhook_url, json=json_safe_result)
        if response.status_code == 200:
            logging.info(f"Successfully sent questions for task {task_id} to webhook")
        else:
            logging.error(f"Failed to send questions for task {task_id} to webhook. Status code: {response.status_code}")

        return jsonify({"message": "Questions generated and sent successfully"}), 200

    except Exception as e:
        logging.error(f"Error in generate function: {str(e)}", exc_info=True)
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    
    
def condense_statements(statements, num_questions):
    if len(statements) <= num_questions:
        return statements
    
    statements_per_question = len(statements) // num_questions
    remainder = len(statements) % num_questions
    
    condensed = []
    start = 0
    for i in range(num_questions):
        end = start + statements_per_question + (1 if i < remainder else 0)
        condensed.append(" ".join(statements[start:end]))
        start = end
    
    return condensed