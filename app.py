from flask import Flask, render_template, request
import os
import requests
from datetime import datetime

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/run_code', methods=['POST'])
def run_code():
    try:
        OIC_INSTANCE = request.form['instance']
        OIC_USERNAME = request.form['username']
        OIC_PASSWORD = request.form['password']

        # Set up session for persistent connection with authentication
        session = requests.Session()
        session.auth = (OIC_USERNAME, OIC_PASSWORD)

        # Local directory to save exported IAR files
        export_directory = os.path.expanduser('~/Downloads')

        # Generate current date for use in file names
        current_date = datetime.now().strftime('%Y%m%d%H%M')

        # Create a folder with the current date and time
        backup_folder_name = f'OICBACKUP_{current_date}'
        backup_folder_path = os.path.join(export_directory, backup_folder_name)

        # File path for the exported integrations info text file
        exported_info_filename = f'exported_integrations_info_{current_date}.txt'
        exported_info_filepath = os.path.join(backup_folder_path, exported_info_filename)

        try:
            # Make sure the backup folder exists, create it if not
            os.makedirs(backup_folder_path, exist_ok=True)

            # Initialize offset and limit for pagination
            offset = 0
            limit = 100

            while True:
                # Make the request to retrieve integration data with limit and offset
                integrations_url = f'https://{OIC_INSTANCE}/ic/api/integration/v1/integrations?q={{name:/INT_/}}&limit={limit}&offset={offset}'
                response = session.get(integrations_url)
                response.raise_for_status()

                # Parse the response content as JSON
                integration_data = response.json()

                # Open the text file for writing in append mode for subsequent requests
                with open(exported_info_filepath, 'a') as exported_info_file:
                    # Write header to the text file for the first request
                    if offset == 0:
                        exported_info_file.write("Code Name | Integration Version | Status | Last Updated Date\n")

                    # Extract and export integrations with names starting with 'INT_'
                    for integration in integration_data.get('items', []):
                        if integration['name'].startswith('INT_') and not integration['lockedFlag']:
                            # Extract integration code, version, and status
                            integration_code = integration['code']
                            integration_version = integration['version']
                            integration_status = integration['status']

                            # Write information to the text file
                            exported_info_file.write(
                                f"{integration_code} | {integration_version} | {integration_status} | {integration.get('lastUpdated', 'N/A')}\n")

                            # Composite identifier {id} for export API
                            integration_id = f"{integration_code}|{integration_version}"

                            # API endpoint for exporting integration
                            export_url = f'https://{OIC_INSTANCE}/ic/api/integration/v1/integrations/{integration_id}/archive'

                            # Make the request to export the integration
                            export_response = session.get(export_url)
                            export_response.raise_for_status()

                            # Save the exported IAR file to the backup folder
                            iar_filename = f"{integration_code}_{integration_version}.iar"
                            iar_filepath = os.path.join(backup_folder_path, iar_filename)

                            with open(iar_filepath, 'wb') as iar_file:
                                iar_file.write(export_response.content)

                            print(f"Integration {integration_id} exported to {iar_filepath}")

                # Update the offset for the next request
                offset += limit

                # Break the loop if there are no more integrations
                if not integration_data.get('hasMore', False):
                    break

            print(f"Exported integrations info saved to {exported_info_filepath}")

        except requests.exceptions.RequestException as e:
            return f"Error: {e}"

        finally:
            # Close the session
            session.close()

        return render_template('index.html', message=f"Exported integrations info saved to {exported_info_filepath}")

    except requests.exceptions.RequestException as e:
        return render_template('index.html', message=f"Error: {e}")


if __name__ == '__main__':
    app.run(debug=True)
