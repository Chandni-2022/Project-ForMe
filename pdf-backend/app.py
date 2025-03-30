from flask import Flask, request, jsonify, send_file, url_for
from flask_cors import CORS
from PyPDF2 import PdfReader, PdfWriter
import os
import json
from PIL import Image
import io
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Create necessary directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, 'public', 'input')
OUTPUT_DIR = os.path.join(BASE_DIR, 'public', 'output')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')

for directory in [INPUT_DIR, OUTPUT_DIR, UPLOAD_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

def extract_form_fields(pdf_path):
    """Extract form fields and their positions from a PDF file."""
    reader = PdfReader(pdf_path)
    fields = {}
    
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        if '/Annots' in page:
            annotations = page['/Annots']
            if annotations:
                for annotation in annotations:
                    if annotation.get_object()['/Subtype'] == '/Widget':
                        field_name = annotation.get_object().get('/T', '')
                        rect = annotation.get_object()['/Rect']
                        fields[field_name] = {
                            'page': page_num,
                            'position': rect,
                            'type': annotation.get_object().get('/FT', ''),
                            'value': ''
                        }
    return fields

@app.route('/forms', methods=['GET'])
def list_forms():
    """List all available forms in the input directory."""
    try:
        forms = []
        for filename in os.listdir(INPUT_DIR):
            if filename.endswith('.pdf'):
                form_id = os.path.splitext(filename)[0]
                forms.append({
                    'id': form_id,
                    'name': filename,
                    'url': f'/public/input/{filename}'
                })
        return jsonify({'forms': forms})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/completed-forms', methods=['GET'])
def list_completed_forms():
    """List all completed forms in the output directory."""
    try:
        forms = []
        for filename in os.listdir(OUTPUT_DIR):
            if filename.endswith('.pdf'):
                file_path = os.path.join(OUTPUT_DIR, filename)
                forms.append({
                    'id': os.path.splitext(filename)[0],
                    'name': filename,
                    'url': f'/public/output/{filename}',
                    'date': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                })
        return jsonify({'forms': forms})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_pdf():
    """Handle PDF file upload and extract form fields."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'File must be a PDF'}), 400

    try:
        filename = os.path.join(UPLOAD_DIR, file.filename)
        file.save(filename)
        
        fields = extract_form_fields(filename)
        
        return jsonify({
            'message': 'File uploaded successfully',
            'fields': fields,
            'filename': file.filename
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/fill-pdf', methods=['POST'])
def fill_pdf():
    """Fill PDF form with provided data and save to output directory."""
    try:
        data = request.json
        filename = data.get('filename')
        field_data = data.get('fields', {})
        
        if not filename:
            return jsonify({'error': 'No filename provided'}), 400
        
        input_pdf_path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.exists(input_pdf_path):
            return jsonify({'error': 'PDF file not found'}), 404
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f'filled_{os.path.splitext(filename)[0]}_{timestamp}.pdf'
        output_pdf_path = os.path.join(OUTPUT_DIR, output_filename)
        
        reader = PdfReader(input_pdf_path)
        writer = PdfWriter()
        
        for page in reader.pages:
            writer.add_page(page)
        
        writer.update_page_form_field_values(writer.pages[0], field_data)
        
        with open(output_pdf_path, 'wb') as output_file:
            writer.write(output_file)
        
        return send_file(
            output_pdf_path,
            as_attachment=True,
            download_name=output_filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/public/<path:filename>')
def serve_file(filename):
    """Serve files from public directory."""
    try:
        directory = INPUT_DIR if 'input' in filename else OUTPUT_DIR
        return send_file(os.path.join(directory, os.path.basename(filename)))
    except Exception as e:
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
