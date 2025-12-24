import base64
import os
import sys
import json
import re
import logging
import random
import yaml
from dotenv import load_dotenv
from pdf2image import convert_from_path
from openai import OpenAI
from pydantic import BaseModel, Field

# Setup basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)

# Load environment variables
load_dotenv('.env-dev')

MODEL_ID = "gpt-4.1-mini"
OPENAI_TOKEN = os.getenv("OPENAI_TOKEN")
client = OpenAI(api_key=OPENAI_TOKEN)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR_CONFIG_PATH = os.path.join(BASE_DIR, "mod_topics", "vendor_disambiguations.yml")


def load_vendor_disambiguations() -> dict:
    """Load vendor disambiguations from YAML config.

    Returns a mapping of vendor abbreviation -> list[str] of known names.
    Falls back to an empty dict if the file is missing or invalid.
    """
    try:
        with open(VENDOR_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        logging.warning("Vendor disambiguation config not found at %s", VENDOR_CONFIG_PATH)
        return {}
    except Exception as e:
        logging.error("Error loading vendor disambiguations from %s: %s", VENDOR_CONFIG_PATH, e)
        return {}

    raw_map = data.get("vendor_disambiguations", {}) or {}
    if not isinstance(raw_map, dict):
        logging.warning("vendor_disambiguations root key is not a mapping in %s", VENDOR_CONFIG_PATH)
        return {}

    cleaned: dict[str, list[str]] = {}
    for abbr, names in raw_map.items():
        if isinstance(names, str):
            cleaned[str(abbr)] = [names]
        elif isinstance(names, list):
            cleaned[str(abbr)] = [str(n) for n in names]
        else:
            logging.warning(
                "Unexpected value type for vendor abbreviation %r in %s: %r",
                abbr,
                VENDOR_CONFIG_PATH,
                type(names),
            )

    return cleaned


def extract_data_with_openai(file_path, text, model_id=MODEL_ID):
    """
    Extracts data from a document using GPT-4 model.
    
    Args:
        file_path (str): The local path to the document file.
        
    Returns:
        list: A list containing extracted data (e.g., mass and purity).
    """
    global client

    vendor_disambiguations = load_vendor_disambiguations()

    # Create the schema
    class TestResult(BaseModel):
        vendor: str = Field(alias="vendor", description="Vendor name of the tested peptide (sometimes called manufacturer). "
        "Match vendor names case-insensitively. Prefer abbreviation keys.\n"
        "Here is a list of the vendor abbreviations with the names each go by for reference:\n"
        + "\n".join([f"{abbr}: {', '.join(names)}" for abbr, names in vendor_disambiguations.items()]) +
        "\nIf no known vendor is found, use UNKNOWN. DO NOT LEAVE BLANK.")
        test_date: str = Field(alias="test_date", description='Date test was performed as MM/DD/YYYY. Sometimes called Analysis conducted. DO NOT LEAVE BLANK')
        batch: str = Field(alias="batch", description="If present, the batch, lot, or client sample identifier. If no batch or lot is called out, use the vendor or manufacturer name and the caption info. Peptide Test puts batch info in the 'Client Sample ID' line. Janoshik puts batch info in the 'Sample' and 'Batch' lines. Often contains a cap color. DO NOT LEAVE BLANK")
        peptide: str = Field(alias="peptide", description='Name of the expected compound tested. DO NOT LEAVE BLANK')
        expected_mass_mg: float = Field(alias="expected_mass_mg", description='The expected sample amount to be present in the vial. Usually reported as whole number milligrams like 5, 10, 12, 15, 20, 30, 40, 50, 60, or 500 mg')
        mass_mg: float | None = Field(alias="mass_mg", description="The actual mass in mg found by the test; a float number. If not tested fill in the JSON value for null")
        purity_percent: float | None = Field(alias="purity_percent", description="The actual purity in percent found by the test; a float number between 0 and 100. If not tested, fill in the JSON value for null")
        tfa_present: float | None = Field(alias='tfa_present', description="The amount of TFA or trifluoroacetic acid found by the test; a float number between 0 and 100. If 'not detected', fill in 0. If not tested, fill in the JSON value for null")
        endotoxin: str | None = Field(alias='endotoxin', description="The amount of endotoxin or EU found by the test; a float number. Extract the value AND the unit; EU or EU/mL. If 'not detected', fill in 0. If not tested, fill in the JSON value for null")
        test_lab: str = Field(alias="test_lab", description="The lab name who tested the sample. Pull the lab name from the name in the url or letterhead logo. DO NOT LEAVE BLANK")
        test_link: str = Field(alias="test_link", description="If test_lab is Peptide Test use https://trustpointelims.com/. If test_lab is Janoshik use https://janoshik.com/verify/. If test_lab is Chromate use https://chromate.org/")
        test_task: str = Field(alias="test_task", description="If present, extract the Task #. If no Task # is present use NA. Janoshik uses Task # at the top left. Chromate uses Report # at the bottom right of the image. Peptide Test uses sample ID that starts with 'SPL-'.")
        test_key: str = Field(alias="test_key", description="If present, extract the Verification Key or Unique Key. If no Key is present use NA. Janoshik puts their Key at the bottom of the image in a gray rectangle. Peptide Test puts their Verification Key at the top right of the image. Chromate puts their Access Code at the bottom right of the image.")


    # if the uploaded doc is a pdf, first convert to image
    if file_path.endswith('.pdf') or file_path.endswith('.PDF'):
        file_path = convert_first_page_to_image(file_path)

    # Getting the base64 string
    base64_image = encode_image(file_path)
    # Setup JSON schema and prompt instructions for data extraction
    instructions = generate_parser_instructions(TestResult, text)

    # Send image and instructions to openai gpt model
    response = client.chat.completions.create(
        model=model_id,
        max_completion_tokens=1000,
        temperature=0,
        messages=[
            {"role": "system", "content": """You are a data extraction engine.\
                Your task:
                - Read text from the provided image (and optional caption text).
                - Extract values exactly as defined by the schema.
                - Output ONLY valid JSON that matches the schema.
                - Never explain, apologize, or include extra text.

                If the image does not contain mass, purity, TFA, or endotoxin test results,
                output exactly: Unsupported Test
                """},
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
    logging.info(f"model response: {json_response}")
    
    if "Unsupported Test" not in json_response:
        # Try to extract JSON from a ```json ... ``` block
        match = re.search(r"```json\n(.*?)\n```", json_response, re.DOTALL)
        
        if match:
            json_content = match.group(1).strip()
        else:
            # Fallback: treat response as direct JSON
            json_content = json_response.strip()

        # Try to parse the content
        try:
            parsed_json = json.loads(json_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}\nContent: {json_content}")

        # Ensure it's a list of dicts (you can adapt this if you allow a single object)
        if not isinstance(parsed_json, list):
            raise ValueError("Expected a list of test result objects")

        # Convert each JSON object into a TestResult instance
        test_results = [TestResult(**result) for result in parsed_json]
        return test_results
    
    else:
        return None
    

def generate_parser_instructions(schema, text):
    instructions = f"""\
        EXTRACT STRUCTURED DATA FROM THE IMAGE.

        Rules:
        - Extract values exactly as they appear in the image.
        - Use the schema fields exactly as named.
        - Do not invent values.
        - Do not leave required fields blank.
        - If a numeric value is not tested, use null.
        - If a value says "Not Detected", use 0.
        - Dates must be formatted MM/DD/YYYY.
        - Vendor must be one of the known abbreviations or UNKNOWN.

        If the image does NOT contain test results for:
        - compound mass
        - purity
        - TFA
        - endotoxin

        Then output exactly:
        Unsupported Test

        If multiple samples are shown:
        - Return a JSON array
        - All shared fields must be identical
        - Only mass_mg, purity_percent, tfa_present, and endotoxin may differ

        Optional caption text (may contain extra clues):
        <image_caption>
        {text}
        </image_caption>

        OUTPUT FORMAT:
        - JSON only
        - No markdown
        - No comments
        - No trailing text

        SCHEMA EXAMPLES:
        """
    example_data = [
        schema(
            vendor="Vendor A",
            test_date="11-01-2024",
            batch="VA T-60 Mfg 2024-10-22",
            peptide="Tirzepatide",
            expected_mass_mg=60,
            mass_mg=58.43,
            purity_percent=98.892,
            tfa_present=None,
            endotoxin=None,
            test_lab="Lab B",
            test_link="janoshik.com/verify",
            test_task="52017",
            test_key="9P6XFTILVPAQ"
        ).model_dump(by_alias=True),
        schema(
            vendor="Vendor A",
            test_date="11-01-2024",
            batch="VA T-60 Mfg 2024-10-22",
            peptide="Tirzepatide",
            expected_mass_mg=60,
            mass_mg=62.98,
            purity_percent=98.723,
            tfa_present=None,
            endotoxin=None,
            test_lab="Lab A",
            test_link="coa.trustpointeanalytics.com",
            test_task="NA",
            test_key="8A2BS2Y9RQ2J"
        ).model_dump(by_alias=True),
    ]
    
    instructions += json.dumps(example_data, indent=2) + "\n\n"
    instructions += "Field Descriptions:\n"
    for _, field_info in schema.model_fields.items():
        instructions += f"- **{field_info.alias}**: {field_info.description}\n"
    return instructions


def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')
  

def convert_first_page_to_image(pdf_path, output_name="first_page.png"):
    """
    Converts the first page of a PDF to an image and saves it as PNG.
    
    Args:
        pdf_path (str): Path to the PDF file.
        output_path (str): Path to save the output image.

    Returns:
        str: Path to the saved image.
    """
    # Convert only the first page of the PDF
    images = convert_from_path(pdf_path, first_page=1, last_page=1)

    # Get the directory of the PDF file
    pdf_dir = os.path.dirname(pdf_path)
    # Create the output path by appending the output_name to the directory
    output_path = os.path.join(pdf_dir, output_name)

    # Save the first page as an image
    images[0].save(output_path, "PNG")
    return output_path


if __name__=='__main__':
    # test_result = extract_data_with_openai('./historic_test_results/4985884030935347022.jpg',"")
    test_result = extract_data_with_openai('./historic_test_results/Test Report #63488.png',"")
    print(test_result)
    # print(generate_ai_conversation())