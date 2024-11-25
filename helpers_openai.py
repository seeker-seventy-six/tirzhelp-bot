import base64
import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, model_validator, ValidationError

# Load environment variables
load_dotenv('.env-dev')

OPENAI_TOKEN = os.getenv("OPENAI_TOKEN")
client = OpenAI(api_key=OPENAI_TOKEN)


# Function to encode the image
def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')
  

def extract_data_with_openai(file_path):
    """
    Extracts data from a document using GPT-4 model.
    
    Args:
        file_path (str): The local path to the document file.
        
    Returns:
        list: A list containing extracted data (e.g., mass and purity).
    """
    global client

    # Create the schema
    class TestResult(BaseModel):
        vendor: str = Field(alias="vendor", description='vendor name of the tested peptide sometimes called manufacturer')
        test_date: str = Field(alias="test_date", description='date test was performed as MM/DD/YYYY')
        batch: str = Field(alias="batch", description='if present the batch identifier')
        peptide: str = Field(alias="peptide", description='name of the peptide tested')
        expected_mass_mg: int = Field(alias="expected_mass_mg", description='usually 5, 10, 15, 20, 30, 50, or 60 mg')
        mass_mg: float = Field(alias="mass_mg", description='the actual mass in mg found by the test')
        purity_percent: float = Field(alias="purity_percent", description='the actual purity in percent found by the test; a float number between 0 and 100')
        test_lab: str = Field(alias="test_lab", description="the lab name who tested the sample. Pull this from the name in the url")

    # Getting the base64 string
    base64_image = encode_image(file_path)
    # Setup JSON schema and prompt instructions for data extraction
    instructions = generate_parser_instructions(TestResult)
    
    # Send image and instructions to openai gpt model
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=300,
        temperature=0.1,
        messages=[
            {"role": "system", "content": "You are an expert data extraction assistant who is provided data extraction instructions and an image and you return the extracted data as instructed."},
            {
                "role": "user",
                "content": [
                    {
                    "type": "text",
                    "text": instructions,
                    },
                    {
                    "type": "image_url",
                    "image_url": {
                        "url":  f"data:image/jpeg;base64,{base64_image}"
                    },
                    },
                ]
            }
        ]
    )
    # Extract the message content, which should be a JSON string wrapped in markdown
    json_response = response.choices[0].message.content
    match = re.search(r'```json\n(.*?)\n```', json_response, re.DOTALL)
    if not match:
        raise ValueError("JSON content not found in the response")
    json_content = match.group(1)
    
    # Parse the JSON content into a Python dictionary
    try:
        parsed_json = json.loads(json_content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    
    # Return the parsed data as an instance of TestResult
    return TestResult(**parsed_json)
    

def generate_parser_instructions(schema):
    instructions = "Extract the values from the provided image as defined in the schema below. Respond only in JSON. Here is an example schema:\n\n"
    example_data = schema(
        vendor="Vendor A",
        test_date="11-01-2024",
        batch="VA T-60 Mfg 2024-10-22",
        peptide="Tirzepatide",
        expected_mass_mg=60,
        mass_mg=58.43,
        purity_percent=99.892,
        test_lab="Lab B"
    ).model_dump(by_alias=True)
    
    instructions += json.dumps(example_data, indent=2) + "\n\n"
    instructions += "Field Descriptions:\n"
    for _, field_info in schema.model_fields.items():
        instructions += f"- **{field_info.alias}**: {field_info.description}\n"
    return instructions


if __name__=='__main__':
    test_result = extract_data_with_openai('./test-image2.jpg')
    print(test_result)