import base64
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

OPENAI_TOKEN = os.getenv("OPENAI_TOKEN")
client = OpenAI(api_key=OPENAI_TOKEN)

print(OPENAI_TOKEN)

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
    prompt = """Extract the values from the provided image as defined in the schema below. Return the data in the following JSON format: 
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
        # Getting the base64 string
        base64_image = encode_image(file_path)
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
                        "text": prompt,
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
        print(response.choices[0])
    
    except Exception as e:
        # Handle exceptions (e.g., file not found, OpenAI errors)
        print(f"Error during data extraction: {e}")
        return [None, None]
    

if __name__=='__main__':
   extract_data_with_openai('./test-image.jpg')