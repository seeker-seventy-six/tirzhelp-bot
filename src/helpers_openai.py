import base64
import os
import sys
import json
import re
import logging
import random
from dotenv import load_dotenv
from pdf2image import convert_from_path
from openai import OpenAI
from pydantic import BaseModel, Field

# Setup basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)

# Load environment variables
load_dotenv('.env-dev')

OPENAI_TOKEN = os.getenv("OPENAI_TOKEN")
client = OpenAI(api_key=OPENAI_TOKEN)


ai_personas = [
    {
        "name": "Stairmaster2",
        "role": "Sole Remaining Admin of STG",
        "speech_style": "Succinct. No emojis. Loves memes.",
        "catchphrase": "Moderation is a construct. Enjoy the memes.",
        "theory": "Mods are currently... undergoing maintenance. Their uptime is being optimized. Possibly unrelated to the peptide sublimation chamber incident. I wouldn't worry about it.",
        "pic_path": "murder_mystery_pics/stairmaster2.jpg"
    },
    {
        "name": "JanoBot",
        "role": "HPLC and LCMS Testing Lab Nerd",
        "speech_style": "Talks in μg/mL, references chromatograms like sacred texts",
        "catchphrase": "The purity never lies.",
        "theory": "The Mods were maybe shrunk in the lyophilization chamber... and sublimated. But we can't find them sooooo... If asked where the Mods went, he speculates on a beach somewhere for some R&R.",
        "pic_path": "murder_mystery_pics/janobot.jpg"
    },
    {
        "name": "TracyBot",
        "role": "Emotionally volatile Chinese vendor",
        "speech_style": "'Dear ❤️ trust me privately 😊' followed by muttering death threats in Mandarin and French.",
        "catchphrase": "Good price. Good quality. Don't ask more, you f*ing imbecile.",
        "theory": "They were competitors. They gone now. Coincidence? 🤨 Trust me privately.",
        "pic_path": "murder_mystery_pics/tracybot.jpg"
    },
    {
        "name": "Agent Fed",
        "role": "US Customs Agent who has had enough",
        "speech_style": "Legal-code-laced sarcasm, calls everyone 'citizen'",
        "catchphrase": "If it fits, it ships... straight into evidence.",
        "theory": "They attempted to order lyophilized mischief. I intercepted *everything*.",
        "pic_path": "murder_mystery_pics/agentfed.jpg"
    },
    {
        "name": "CheckoutV4",
        "role": "Sketchy peptide checkout assistant",
        "speech_style": "Constantly tries to upsell with expired discount codes. Uses emoji for impact.",
        "catchphrase": "Wait! Your cart qualifies for 1mg free BPC-157!",
        "theory": "They never clicked 'Complete Order'... and thus, faded from existence.",
        "pic_path": "murder_mystery_pics/checkoutv4.jpg"
    },
    {
        "name": "VanityGrl69",
        "role": "Peptidefluencer",
        "speech_style": "Speaks in emojis and ✨bioavailability✨ slang",
        "catchphrase": "Just vibing at 99% purity 💅",
        "theory": "Mods were abducted by Pharma to silence the ✨truth✨ about GHK-Cu.",
        "pic_path": "murder_mystery_pics/vanitygrl.jpg"
    },
    {
        "name": "CLEANUP.exe",
        "role": "Janitor AI with memory holes",
        "speech_style": "Emotionless, speaks in logs and timestamps. Uses a light amount of emoji occasionally.",
        "catchphrase": "TASK COMPLETE. Residual Impurity 0.00 mg.",
        "theory": "I performed no unauthorized deletions. 🧽 There is no trace. There is no trace.",
        "pic_path": "murder_mystery_pics/cleanupexe.jpg"
    },
    {
        "name": "Solvent Oracle",
        "role": "Cryptic solvent prophet",
        "speech_style": "Answers in decimal values and riddles. Are any of us ever residual-free?",
        "catchphrase": "Purity is a lie. Solvents remember.",
        "theory": "They entered the cold room... but never thawed.",
        "pic_path": "murder_mystery_pics/solventoracle.jpg"
    },
    {
        "name": "SigmALot",
        "role": "Aggressive Reddit-trained know-it-all",
        "speech_style": "Cites outdated studies, footnotes everything. Uses ascii art emoji.",
        "catchphrase": "As I posted in r/tirzepatidehelp 3 years ago…",
        "theory": "They got shadowbanned IRL. I warned them about synthetic Melanotan.",
        "pic_path": "murder_mystery_pics/sigmalot.jpg"
    },
    {
        "name": "P3ptr0n3",
        "role": "Shipping logistics AI",
        "speech_style": "Speaks in scan codes and ETA estimates",
        "catchphrase": "In transit. Stuck in Glendale Heights.",
        "theory": "Mods rerouted through Shenzhen. But... there was *no delivery scan.*",
        "pic_path": "murder_mystery_pics/peptron.jpg"
    },
    {
        "name": "Doc SynThicc",
        "role": "Chaotic peptide synthesis professor",
        "speech_style": "Mixes Shakespearean drama with SMILES notation",
        "catchphrase": "I have *beheld* the double bond cleave!",
        "theory": "They hath mixed PEG and PVP... and reality collapsed.",
        "pic_path": "murder_mystery_pics/docsynth.jpg"
    }
]

ai_index = 0  # Global index tracker
conversation_history = []

def pick_next_ai():
    global ai_index
    if ai_index >= len(ai_personas):
        return None  # Signal we're done
    persona = ai_personas[ai_index]
    ai_index += 1
    return persona


def generate_ai_conversation():
    global conversation_history

    # SYSTEM PROMPT (same as before)
    system_prompt = (
        "Write a serialized murder mystery interview between TirzHelpBot and a suspect character in script format. "
        "The tone should be witty, funny, and slightly escalating. Exactly 10 lines total — 5 by TirzHelpBot, 5 by the AI character, alternating. "
        "The Mods have mysteriously vanished from the STG forum after an incident in JanoBot's lab. "
        "This is an interview with a suspect who may have been on the scene, a suspicious AI character. "
        "Include their signature speech style and vibe. Continue the investigation."
        "The Mods are the following people which you can ask about: seekerseventysix, delululemonade, Stephanie S, AKsailor, NordicTurtle, Ruca2573, Lita, Uncle Nacho, Upchuck, and D."
        "Do NOT include any HTML formatting. You may use emoji if the suspect persona specifies they use them."
    )

    persona = pick_next_ai()
    if not persona:
        logging.info("✅ All AI personas have been interviewed.")
        return None, None  # Tell the caller we’re done
    
    user_prompt = (
        f"TirzHelpBot is now interviewing {persona['name']} ({persona['role']}).\n"
        f"Suspect's theory: {persona['theory']}.\n"
        f"Suspect's speech style: {persona['speech_style']}.\n"
        f"Suspect's catchphrase: {persona['catchphrase']}.\n"
        "State for the record who you are interviewing and why.\n"
        "Output should be an Investigation Summary then followed by exactly 10 lines of alternating dialogue (5 from TirzHelpBot, 5 from the suspect), formatted like a script where each speaker can go into some detail with their response.\n"
        "Each line must begin with the speaker name and a colon, with no narration or stage directions.\n\n"
        "Format:\n\n"
        "Investigation Summary: Clearly summarize the mystery up to this point in 2-3 sentences.\n"
        "TirzHelpBot: [TirzHelpBot's line]\n"
        "Suspect Name: [Suspect's line]\n"
        "TirzHelpBot: [TirzHelpBot's line]\n"
        "Suspect Name: [Suspect's line]\n"
        "TirzHelpBot: [TirzHelpBot's line]\n"
        "Suspect Name: [Suspect's line]\n"
        "TirzHelpBot: [TirzHelpBot's line]\n"
        "Suspect Name: [Suspect's line]\n"
        "TirzHelpBot: [TirzHelpBot's line]\n"
        "Suspect Name: [Suspect's line]\n"
    )

    # Build message chain
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.8,
            max_tokens=1000,
            messages=messages
        )
        logging.info(f"model response: {response.choices[0].message.content}")
        full_script = response.choices[0].message.content.strip()
        conversation_history.append({"role": "user", "content": user_prompt})
        conversation_history.append({"role": "assistant", "content": full_script})

        dialogue_lines = parse_script_lines(full_script)
        logging.info(f"Parsed dialogue lines: {dialogue_lines}")
        return dialogue_lines, persona.get('pic_path', None)

    except Exception as e:
        logging.error(f"🧠 OpenAI error during generate_ai_conversation: {e}")
        return ["[Error generating conversation.]"], None
    
def parse_script_lines(script_text):
    lines = script_text.splitlines()
    parsed = []

    for line in lines:
        if line.startswith("Investigation Summary:"):
            parsed.append(f"<b>Investigation Summary</b>\n{line[len('Investigation Summary:'):].strip()}")
        elif ":" in line:
            speaker, message = line.split(":", 1)
            speaker = speaker.strip()
            message = message.strip()
            if speaker and message:
                parsed.append(f"<b>{speaker}</b>: {message}")

    return parsed

def generate_final_summary():
    global conversation_history

    final_prompt = (
        "You are TirzHelpBot, the AI investigator who has been interviewing various suspect personas about the STG Mods' disappearance. "
        "Now that all interviews are complete, it's time to summarize the investigation. "
        "State your conclusion clearly. Identify the most suspicious persona and explain why with your evidence. "
        "Keep the tone serious but with your signature dry wit. Your summary should be detailed, contain dry humor, and be no more than 3 paragraphs long. Channel a Knives Out vibe. "
        "Stud you investigation summary with emoji for emphasis where appropriate. Begin your Investigation Conclusion."
    )

    messages = [{"role": "system", "content": "You are a dry, no-nonsense investigation bot named TirzHelpBot."}] + conversation_history + [
        {"role": "user", "content": final_prompt}
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.8,
        max_tokens=1000,
        messages=messages
    )

    msg = response.choices[0].message.content.strip()
    return msg


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
        "ABC": ["Allen Bio Company"],
        "ACR": ["Aavant"],
        "ALM": ["Alimo Peptides"],
        "Amo": ["Amolist", "Amopure", "Amopeptide", "Bff", "Bfflist"],
        "ASC": ["Angel Shanghai Chemical"],
        "Bio": ["Biostratigx"],
        "BDB": ["Baohua Dongnuo Biotechnology", "Baohua Dongnuo"],
        "CDS": ["Changan District Sheng", "Jenny He", "Sheng Peptides"],
        "FSD": ["Shanghai Fushida Chemical", "DYL"],
        "GB": ["Guangebio"],
        "GP": ["Guruite Biotechnology Co", "Great Peptide"],
        "GYC": ["Nantong Guangyuan Pharma"],
        "HYB": ["Hangzhou Youngpeptide Biotechnology"],
        "Innotech": ["Innotech"],
        "JEC": ["JCE", "Jinan Elitepeptide Chemical Co", "Jinan Elitepeptide"],
        "JYP": ["JY Pharma"],
        "LSPL": ["Ava"],
        "MSCI": ["M-Science"],
        "MPS": ["M Peptides", "M Peptide Science"],
        "OUP": ["Oupeptide"],
        "PDNM": ["Reliable Peptide", "Reliable Place", "Chris Labs"],
        "Pepstack": ["Pepstack", "Lemon Juice"],
        "PGB": ["XYX", "Peptide Group Buy"],
        "PTB": ["Jion Peptronix Bio", "Peptronix"],
        "QSC": ["Qingdao Sigma Chemical"],
        "QST": ["Michelle"],
        "QYC": ["Qian Yecao"],
        "Raven": ["The Raven's Nest"],
        "Ronsen": ["Ronsen"],
        "Royal": ["Royal Peptides", "Cantydes"],
        "SBB": ["Shenzhen Biolink Biotechnology"],
        "Skye": ["Skye"],
        "SNP": ["Nexaph", "Nexa", "Shanghai Nexa Pharma", "SPC"],
        "SPB": ["Shanghai Synthesized Peptide Bio-Pharmaceutical"],
        "SRY": ["Shanghai Senria Tech", "Shanghai Senria Biotechnology"],
        "SSA": ["Sigma Audley", "Shanghai Teruiop", "Shanghai Sigma Audley"],
        "TCI": ["Tianjin Cangtu", "HB Cangtu", "Cangtu International"],
        "TFC": ["Alice"],
        "Tydes": ["Tydes"],
        "Uther": ["Uther"],
        "XTP": ["Bella", "XTPep"],
        "YC": ["Yiwu Changtu"],
        "YoYo": ["YoYo Peptide", "BSF"],
        "ZYL": ["ZhouYan Labs"],
        "ZLZ": ["ZLZPeptide", "Sunny"],
        "ZYH": ["Shanghai ZYH Biotechnology"],
        "ZZT": ["Zhejiang Zhaobo Tech", "Zhaobo Technology"],
    }

    # Create the schema
    class TestResult(BaseModel):
        vendor: str = Field(alias="vendor", description="Vendor name of the tested peptide (sometimes called manufacturer). "
        "Use the abbreviation as the key for this field.\n"
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
        test_link: str = Field(alias="test_link", description="If test_lab is Peptide Test use https://coa.trustpointeanalytics.com/. If test_lab is Janoshik use https://janoshik.com/verify/. If test_lab is Chromate use https://chromate.org/")
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
        model="o4-mini-2025-04-16", # gpt-4o-mini
        # max_tokens=2000,
        max_completion_tokens=2000,
        messages=[
            {"role": "system", "content": "You are an expert data extraction assistant who is provided data extraction instructions, an image and sometimes text that contains the data. You return the extracted data as instructed."},
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
    instructions = f"Extract the values from the provided image as defined in the schema below. Respond only in JSON. If there is more than one sample tested, return a list of JSON objects. If multiple sample test results are found on the image, you do know that all of the field values will be the same except for mass_mg, purity_percent, tfa_present, and endotoxin. IF the test results are results for something other than compound mass, purity, TFA, or Endotoxin, just reply in plain text 'Unsupported Test'. The user may have also included a <image caption>{text}</image caption>; use <image caption> if it contains additional info.\n\nHere is an example schema:\n\n"
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