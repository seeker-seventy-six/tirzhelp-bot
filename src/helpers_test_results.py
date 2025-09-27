import logging
import os
import requests
from uuid import uuid4
from src import create_messages as msgs
from src import helpers_telegram
from src import helpers_openai
from src import helpers_google

def extract_test_results_from_image(image_url, chat_id, message_thread_id):
    """Manually trigger test results extraction for bridged images"""
    try:
        # Download the image
        response = requests.get(image_url)
        response.raise_for_status()
        
        # Save to temp file
        local_path = f"./temp{uuid4()}/bridged_image.jpg"
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(response.content)
        
        # Process with OpenAI
        extracted_test_data = helpers_openai.extract_data_with_openai(local_path, "")
        
        if extracted_test_data:
            # Process same as regular test results
            for sample in extracted_test_data:
                data_row = (
                    [sample.vendor] + [sample.peptide] + [sample.test_date] + [sample.batch] +
                    [sample.expected_mass_mg] + [sample.mass_mg] + [sample.purity_percent] +
                    [sample.tfa_present] + [sample.endotoxin] + [sample.test_lab] +
                    [local_path.split('/')[-1]] + [sample.test_link] + [sample.test_key] + [sample.test_task]
                )
                helpers_google.append_to_sheet(data_row)
            
            # Generate summary message
            if sample.mass_mg:
                grouped_stats = helpers_google.calculate_statistics(sample.vendor, sample.peptide)
                message_text = f"📊 <b>{sample.vendor.upper()} {sample.peptide.upper()} Analysis for the last 3 months:</b>\n\n"
                
                for expected_mass, stats in grouped_stats.items():
                    icon_status_mass = "🟢" if stats['mass_diff_percent'] <= 10 else "🟡" if stats['mass_diff_percent'] <= 15 else "🔴"
                    icon_status_purity = "🟢" if stats['std_purity'] <= 2 else "🟡" if stats['std_purity'] <= 4 else "🔴"
                    message_text += (
                        f"🔹 <b>Expected Mass: {expected_mass} mg</b>\n"
                        f"   • Avg Tested Mass: {stats['average_mass']:.2f} mg\n"
                        f"   • Avg Tested Purity: {stats['average_purity']:.2f}%\n"
                        f"   • # Vials Tested: {stats['test_count']}\n"
                        f"   • Typical Deviation Tested Mass (Std Dev): ±{stats['std_mass']:.1f} mg\n"
                        f"   {icon_status_mass} <b>±{stats['mass_diff_percent']:.1f}% : % Std Dev of Potency</b>\n"
                        f"   {icon_status_purity} <b>±{stats['std_purity']:.1f}% : % Std Dev of Purity</b>\n\n"
                    )
                
                message_text += "<a href='https://docs.google.com/spreadsheets/d/1IbMh3BNqkQP-0ZyI51Dyz8K-msSHRiY_kT0Ue-Uv8qQ'>🌐 You can find the raw data here</a>"
                helpers_telegram.send_message(chat_id, message_text, message_thread_id)
            
            elif sample.endotoxin:
                message_text = (
                    f"📊 <b>{sample.vendor.upper()} {sample.peptide.upper()}</b>\n\n"
                    f"🔹 <b>Endotoxin Level:</b> {sample.endotoxin}\n\n"
                    f"<i>Note:</i> Endotoxin is measured in EU (Endotoxin Units). For tirzepatide, <b>&lt;10 EU/mg</b> is the recommended threshold from FDA-registered API standards.\n"
                    f"<a href='https://www.stairwaytogray.com/posts/testing/testing-101/#endotoxin'>More details in the Testing 101 Guide 🔬</a>\n\n"
                    f"<a href='https://docs.google.com/spreadsheets/d/1IbMh3BNqkQP-0ZyI51Dyz8K-msSHRiY_kT0Ue-Uv8qQ'>🌐 You can find the raw data here</a>"
                )
                helpers_telegram.send_message(chat_id, message_text, message_thread_id)
            
            else:
                message_text = (
                    f"📊 <b>{sample.vendor.upper()} {sample.peptide.upper()}</b>\n\n"
                    f"🔹<a href='https://www.stairwaytogray.com/posts/testing/testing-101/#how-do-i-read-my-test-results'>How Do I Read My Test Results? Check out the Testing 101 Guide 🔬</a>\n\n"
                    f"<a href='https://docs.google.com/spreadsheets/d/1IbMh3BNqkQP-0ZyI51Dyz8K-msSHRiY_kT0Ue-Uv8qQ'>🌐 You can find the raw data here</a>"
                )
                helpers_telegram.send_message(chat_id, message_text, message_thread_id)
            
            logging.info(f"Test results extraction completed for bridged image: {image_url}")
        
        # Clean up
        os.remove(local_path)
        
    except Exception as e:
        logging.error(f"Failed to extract test results from bridged image: {e}")