import io
import os
from flask import Blueprint, jsonify, request, send_file
#from converter.conv import convert_pdf_wrapper

from converter.pdf import extract_dict_from_pdf, convert_dict_to_csv, convert_dict_to_json

v1_blueprint = Blueprint('v1', __name__)

defined_token = os.getenv('TOKEN')

def check_auth():
    token = request.headers.get('Authorization')
    if token != 'Bearer '+defined_token:
        return False
    return True

@v1_blueprint.route('/converttojson', methods=['POST'])
def convert_to_json():
    if not check_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    pdf_file = request.files['file']
    if pdf_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        dict_raw = extract_dict_from_pdf('PRO1',pdf_file)
        json_content = convert_dict_to_json(dict_raw)
        return jsonify(json_content)
    except Exception as e:
        print(str(e))
        return jsonify({'error': str(e)}), 500

@v1_blueprint.route('/converttocsv', methods=['POST'])
def convert_to_csv():
    if not check_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    pdf_file = request.files['file']
    if pdf_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        dict_raw = extract_dict_from_pdf('PRO1',pdf_file)
        csv_content = convert_dict_to_csv(dict_raw)
        
        csv_file = io.BytesIO(csv_content)
        csv_file.seek(0)
        return send_file(csv_file, mimetype='text/csv', as_attachment=True, download_name='output.csv')
    except Exception as e:
        print(str(e))
        return jsonify({'error': str(e)}), 500

@v1_blueprint.route('/hb', methods=['GET'])
def hello():
    return jsonify({'status': 'ok'})