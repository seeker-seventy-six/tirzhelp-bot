import base64
import os
import sys
import json
import re
import logging
from dotenv import load_dotenv
from pdf2image import convert_from_path
from openai import OpenAI
from pydantic import BaseModel, Field

# Setup basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)

# Load environment variables
load_dotenv()

OPENAI_TOKEN = os.getenv("OPENAI_TOKEN")
client = OpenAI(api_key=OPENAI_TOKEN)


def extract_data_with_openai(file_path, text):
    """
    Extracts data from a document using GPT-4 model.
    
    Args:
        file_path (str): The local path to the document file.
        
    Returns:
        list: A list containing extracted data (e.g., mass and purity).
    """
    global client

    vendor_disambiguations = {
        "ALM": ["Alimo Peptides"],
        "ACR": ["Aavant"],
        "Amo": ["Amolist", "Amopure", "Amopeptide", "Bfflist"],
        "ASC": ["Angel Shanghai Chemical"],
        "CDS": ["Changan District Sheng", "Jenny He"],
        "GB": ["Guangebio"],
        "GYC": ["Nantong Guangyuan Pharma"],
        "HYB": ["Hangzhou Youngpeptide Biotechnology"],
        "Innotech": ["Innotech"],
        "QSC": ["Qingdao Sigma Chemical"],
        "QYC": ["Qian Yecao"],
        "Raven": ["The Raven's Nest"],
        "Royal": ["Royal Peptides", "Cantydes"],
        "SBB": ["Shenzhen Biolink Biotechnology"],
        "Skye": ["Skye"],
        "SNP": ["Nexaph", "Shanghai Nexa Pharma", "SPC", "Cain"],
        "SPB": ["Shanghai Synthetic Peptide Biopharmaceutical", "Yuna"],
        "SRY": ["Shanghai Senria Tech", "Shanghai Senria Biotechnology"],
        "SSA": ["Sigma Audley", "Shanghai Teruiop", "Shanghai Sigma Audley"],
        "TCI": ["Tianjin Cangtu", "HB Cangtu", "Cangtu International", "Cangtu"],
        "Tydes": ["Tydes"],
        "Uther": ["Uther", "Enzo"],
        "YC": ["Yiwu Changtu", "Changtu"],
        "ZLZ": ["ZLZPeptide"],
        "ZYH": ["Shanghai ZYH Biotech"],
        "ZZT": ["Zhejiang Zhaobo Tech", "Zhaobo Technology"]
    }

    # Create the schema
    class TestResult(BaseModel):
        vendor: str = Field(alias="vendor", description=f"Vendor name of the tested peptide sometimes called manufacturer. Here is a list of most common vendors and their abbreviation. Use the abbreviation key value for this field:\n{vendor_disambiguations}. If no known vendor is found, put UNKNOWN. DO NOT LEAVE BLANK")
        test_date: str = Field(alias="test_date", description='Date test was performed as MM/DD/YYYY. DO NOT LEAVE BLANK')
        batch: str = Field(alias="batch", description="If present, the batch, lot, or client sample identifier. If no batch or lot is called out, use the vendor or manufacturer name and the caption info. Peptide Test puts batch info in the 'Client Sample ID' line. Janoshik puts batch info in the 'Sample' and 'Batch' lines. DO NOT LEAVE BLANK")
        peptide: str = Field(alias="peptide", description='Name of the expected compound tested.  DO NOT LEAVE BLANK')
        expected_mass_mg: float = Field(alias="expected_mass_mg", description='The expected sample amount to be present in the vial. Usually 5, 10, 12, 15, 20, 30, 50, or 60 mg')
        mass_mg: float | None = Field(alias="mass_mg", description="The actual mass in mg found by the test; a float number. If not tested fill in the JSON value for null")
        purity_percent: float | None = Field(alias="purity_percent", description="The actual purity in percent found by the test; a float number between 0 and 100. If not tested, fill in the JSON value for null")
        tfa_present: float | None = Field(alias='tfa_present', description="The amount of TFA or trifluoroacetic acid found by the test; a float number between 0 and 100. If 'not detected', fill in 0. If not tested, fill in the JSON value for null")
        test_lab: str = Field(alias="test_lab", description="The lab name who tested the sample. Pull the lab name from the name in the url or letterhead logo. DO NOT LEAVE BLANK")
        test_link: str = Field(alias="test_link", description="If test_lab is Peptide Test use https://coa.trustpointeanalytics.com/. If test_lab is Janoshik use https://janoshik.com/verify/. If test_lab is Chromate use https://chromate.org/.")
        test_task: str = Field(alias="test_task", description="If present, extract the Task#. If no Task# is present use NA. Janoshik uses Task # at the top left. Chromate uses Report# at the bottom right of the image. Peptide Test does NOT use Task #.")
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
        model="gpt-4o-mini",
        max_tokens=2000,
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
    logging.info(f"model response: {json_response}")
    
    if "Unsupported Test" not in json_response:
        match = re.search(r'```json\n(.*?)\n```', json_response, re.DOTALL)
        if not match:
            raise ValueError("JSON content not found in the response")
        json_content = match.group(1)
    
        # Parse the JSON content into a Python dictionary
        try:
            parsed_json = json.loads(json_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
        
        # Convert each JSON object into a TestResult instance
        test_results = [TestResult(**result) for result in parsed_json]
        return test_results
    
    else:
        return None
    

def generate_parser_instructions(schema, text):
    instructions = f"Extract the values from the provided image as defined in the schema below. Respond only in JSON. If there is more than one sample tested, return a list of JSON objects. If multiple sample test results are found on the image, you do know that all of the field values will be the same except for mass_mg, purity_percent, and tfa_present. IF the test results are results for something other than compound mass, purity, or TFA, just reply in plain text 'Unsupported Test'. The user may have also included a <image caption>{text}</image caption>; use <image caption> if it contains additional info.\n\nHere is an example schema:\n\n"
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
    test_result = extract_data_with_openai('./historic_test_results/5042221709662466859.jpg',"")
    print(test_result)