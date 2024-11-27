import helpers_google
import helpers_openai



def process_local_test_result(local_path):
    # Process the file using OpenAI
    extracted_test_data = helpers_openai.extract_data_with_openai(local_path)

    if extracted_test_data:
        # Append data to Google Sheets for each sample tested. One Test Result image may have more than one sample
        for sample in extracted_test_data:
            data_row = (
                [sample.vendor]
                + [sample.peptide]
                + [sample.test_date]
                + [sample.batch]
                + [sample.expected_mass_mg]
                + [sample.mass_mg]
                + [sample.purity_percent]
                + [sample.tfa_present]
                + [sample.test_lab]
                + [local_path.split('/')[-1]]
            )
            helpers_google.append_to_sheet(data_row)

        # Calculate statistics
        grouped_stats = helpers_google.calculate_statistics(sample.vendor, sample.peptide)

        # Initialize the message text
        message_text = f"📊 <b>{sample.vendor.upper()} {sample.peptide.upper()} Analysis for the last 3 months:</b>\n\n"

        # Iterate through each group and append stats to the message
        for expected_mass, stats in grouped_stats.items():
            message_text += (
                f"🔹 <b>Expected Mass: {expected_mass} mg</b>\n"
                f"   • Avg Tested Mass: {stats['average_mass']:.2f} mg\n"
                f"   • Avg Tested Purity: {stats['average_purity']:.2f}%\n"
                f"   • Std Dev Mass: +/-{stats['std_mass']:.2f} mg\n"
                f"   • Std Dev Purity: +/-{stats['std_purity']:.2f}%\n"
            )

        # Clean up
        os.remove(local_path)
        return message_text


def list_files_in_dir(directory, extensions=None):
    """
    List all files in a directory with optional filtering by extensions.

    Args:
        directory (str): Path to the directory to list files from.
        extensions (tuple, optional): File extensions to filter by (e.g., ('.pdf', '.jpg')).

    Returns:
        list: List of file paths.
    """
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if extensions is None or filename.lower().endswith(extensions):
                files.append(os.path.join(root, filename))
    return files

if __name__=='__main__':
    import os
    # list all file path in dir
    historic_test_results = list_files_in_dir('./historic_test_results/')
    for test_path in historic_test_results:
        try:
            print(f"Processing {test_path} ...")
            message = process_local_test_result(test_path)
            print(message,'\n')
            os.remove(test_path)
            try:
                os.remove('first_page.png')
            except:
                pass
        except Exception as e:
            print(f"Failed to process: {test_path}\n{e}")