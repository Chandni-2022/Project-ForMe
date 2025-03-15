from flask import Flask, request, jsonify, send_file, url_for
from flask_cors import CORS
from PyPDF2 import PdfReader, PdfWriter
import os
import json
from PIL import Image
import io

app = Flask(__name__)
CORS(app)

# Create uploads folder if it doesn't exist
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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
        # Save the uploaded file
        filename = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filename)
        
        # Extract form fields
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
    """Fill PDF form with provided data and return the filled PDF."""
    try:
        data = request.json
        filename = data.get('filename')
        field_data = data.get('fields', {})
        
        if not filename:
            return jsonify({'error': 'No filename provided'}), 400
        
        input_pdf_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(input_pdf_path):
            return jsonify({'error': 'PDF file not found'}), 404
        
        output_filename = f'filled_{filename}'
        output_pdf_path = os.path.join(UPLOAD_FOLDER, output_filename)
        
        # Fill the PDF form
        reader = PdfReader(input_pdf_path)
        writer = PdfWriter()
        
        # Copy all pages
        for page in reader.pages:
            writer.add_page(page)
        
        # Update form fields
        writer.update_page_form_field_values(writer.pages[0], field_data)
        
        # Save the filled PDF
        with open(output_pdf_path, 'wb') as output_file:
            writer.write(output_file)
        
        return send_file(
            output_pdf_path,
            as_attachment=True,
            download_name=output_filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Clean up temporary files."""
    try:
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        return jsonify({'message': 'Cleanup successful'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
