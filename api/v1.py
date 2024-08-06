import io
from flask import Blueprint, jsonify, request, send_file
from converter.Table_1 import convert_pdf_wrapper

v1_blueprint = Blueprint('v1', __name__)

@v1_blueprint.route('/converttocsv', methods=['POST'])
def convert_to_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    pdf_file = request.files['file']
    if pdf_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        csv_content = convert_pdf_wrapper(pdf_file)
        csv_file = io.BytesIO()
        csv_file.write(csv_content.encode('utf-8'))
        csv_file.seek(0)
        return send_file(csv_file, mimetype='text/csv', as_attachment=True, download_name='output.csv')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@v1_blueprint.route('/hb', methods=['GET'])
def hello():
    return jsonify({'status': 'ok'})