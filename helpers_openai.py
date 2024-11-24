import openai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPENAI_TOKEN = os.getenv("OPENAI_TOKEN")
openai.api_key = OPENAI_TOKEN


def extract_data_with_openai(file_path):
    """
    Extracts data from a document using GPT-4 model.
    
    Args:
        file_path (str): The local path to the document file.
        
    Returns:
        list: A list containing extracted data (e.g., mass and purity).
    """
    # Define a placeholder prompt for the model
    # You can replace this with a domain-specific prompt as needed
    prompt = """You are a data extraction assistant. Extract the 'mass (mg)' and 'purity (%)' values from the provided document. Return the data in the following JSON format: 
    {
      'Vendor': 'vendor name of the tested peptide sometimes called manufacturer',
      'Test Date': 'MM/DD/YYYY',
      'Batch': 'if present the batch identifier',
      'Peptide': 'name of the peptide tested',
      'Expected Mass mg': 'usually 5, 10, 15, 20, 30, 50, or 60 mg',
      'Mass mg': 'the actual mass in mg found by the test',
      'Purity %': 'the actual purity in percent found by the test',
      'Test Lab': 'the lab name who tested the sample'
    }"""
    
    try:
        # Open the file in binary mode
        with open(file_path, "rb") as file:
            # Send the file to GPT-4 with a low temperature for factual extraction
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an AI expert in data extraction from images and PDFs."},
                    {"role": "user", "content": prompt}
                ],
                file=file.read(),  # Attach the document content
                temperature=0.2  # Low temperature for deterministic results
            )

        # Parse the response to extract mass and purity
        response_text = response['choices'][0]['message']['content']
        
        # Example of simple parsing logic (update this based on your exact output format)
        mass = float(response_text.split("Mass:")[1].split("mg")[0].strip())
        purity = float(response_text.split("Purity:")[1].split("%")[0].strip())
        
        return [mass, purity]
    
    except Exception as e:
        # Handle exceptions (e.g., file not found, OpenAI errors)
        print(f"Error during data extraction: {e}")
        return [None, None]