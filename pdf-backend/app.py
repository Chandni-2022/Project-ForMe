# from flask import Flask, request, jsonify, send_file, url_for
# from flask_cors import CORS
# from PyPDF2 import PdfReader, PdfWriter
# import os
# import json
# from PIL import Image
# import io
# from datetime import datetime

# app = Flask(__name__)
# CORS(app)

# # Create necessary directories
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# INPUT_DIR = os.path.join(BASE_DIR, 'public', 'input')
# OUTPUT_DIR = os.path.join(BASE_DIR, 'public', 'output')
# UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')

# for directory in [INPUT_DIR, OUTPUT_DIR, UPLOAD_DIR]:
#     if not os.path.exists(directory):
#         os.makedirs(directory)

# def extract_form_fields(pdf_path):
#     """Extract form fields and their positions from a PDF file."""
#     reader = PdfReader(pdf_path)
#     fields = {}
    
#     for page_num in range(len(reader.pages)):
#         page = reader.pages[page_num]
#         if '/Annots' in page:
#             annotations = page['/Annots']
#             if annotations:
#                 for annotation in annotations:
#                     if annotation.get_object()['/Subtype'] == '/Widget':
#                         field_name = annotation.get_object().get('/T', '')
#                         rect = annotation.get_object()['/Rect']
#                         fields[field_name] = {
#                             'page': page_num,
#                             'position': rect,
#                             'type': annotation.get_object().get('/FT', ''),
#                             'value': ''
#                         }
#     return fields

# @app.route('/forms', methods=['GET'])
# def list_forms():
#     """List all available forms in the input directory."""
#     try:
#         forms = []
#         for filename in os.listdir(INPUT_DIR):
#             if filename.endswith('.pdf'):
#                 form_id = os.path.splitext(filename)[0]
#                 forms.append({
#                     'id': form_id,
#                     'name': filename,
#                     'url': f'/public/input/{filename}'
#                 })
#         return jsonify({'forms': forms})
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @app.route('/completed-forms', methods=['GET'])
# def list_completed_forms():
#     """List all completed forms in the output directory."""
#     try:
#         forms = []
#         for filename in os.listdir(OUTPUT_DIR):
#             if filename.endswith('.pdf'):
#                 file_path = os.path.join(OUTPUT_DIR, filename)
#                 forms.append({
#                     'id': os.path.splitext(filename)[0],
#                     'name': filename,
#                     'url': f'/public/output/{filename}',
#                     'date': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
#                 })
#         return jsonify({'forms': forms})
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @app.route('/upload', methods=['POST'])
# def upload_pdf():
#     """Handle PDF file upload and extract form fields."""
#     if 'file' not in request.files:
#         return jsonify({'error': 'No file part'}), 400
    
#     file = request.files['file']
#     if file.filename == '':
#         return jsonify({'error': 'No selected file'}), 400

#     if not file.filename.lower().endswith('.pdf'):
#         return jsonify({'error': 'File must be a PDF'}), 400

#     try:
#         filename = os.path.join(UPLOAD_DIR, file.filename)
#         file.save(filename)
        
#         fields = extract_form_fields(filename)
        
#         return jsonify({
#             'message': 'File uploaded successfully',
#             'fields': fields,
#             'filename': file.filename
#         })
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @app.route('/fill-pdf', methods=['POST'])
# def fill_pdf():
#     """Fill PDF form with provided data and save to output directory."""
#     try:
#         data = request.json
#         filename = data.get('filename')
#         field_data = data.get('fields', {})
        
#         if not filename:
#             return jsonify({'error': 'No filename provided'}), 400
        
#         input_pdf_path = os.path.join(UPLOAD_DIR, filename)
#         if not os.path.exists(input_pdf_path):
#             return jsonify({'error': 'PDF file not found'}), 404
        
#         timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#         output_filename = f'filled_{os.path.splitext(filename)[0]}_{timestamp}.pdf'
#         output_pdf_path = os.path.join(OUTPUT_DIR, output_filename)
        
#         reader = PdfReader(input_pdf_path)
#         writer = PdfWriter()
        
#         for page in reader.pages:
#             writer.add_page(page)
        
#         writer.update_page_form_field_values(writer.pages[0], field_data)
        
#         with open(output_pdf_path, 'wb') as output_file:
#             writer.write(output_file)
        
#         return send_file(
#             output_pdf_path,
#             as_attachment=True,
#             download_name=output_filename
#         )
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @app.route('/public/<path:filename>')
# def serve_file(filename):
#     """Serve files from public directory."""
#     try:
#         directory = INPUT_DIR if 'input' in filename else OUTPUT_DIR
#         return send_file(os.path.join(directory, os.path.basename(filename)))
#     except Exception as e:
#         return jsonify({'error': str(e)}), 404

# if __name__ == '__main__':
#     app.run(debug=True, port=5000)




from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import NameObject, BooleanObject
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Directory setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, 'public', 'input')
OUTPUT_DIR = os.path.join(BASE_DIR, 'public', 'output')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')

for directory in [INPUT_DIR, OUTPUT_DIR, UPLOAD_DIR]:
    os.makedirs(directory, exist_ok=True)


def extract_form_fields(pdf_path):
    """Extract all form fields and their types from a PDF."""
    reader = PdfReader(pdf_path)
    fields = {}

    for page_num, page in enumerate(reader.pages):
        if '/Annots' in page:
            for annot_ref in page['/Annots']:
                annot = annot_ref.get_object()
                if annot.get('/Subtype') == '/Widget':
                    field_name = annot.get('/T', '').strip('()')
                    field_type = annot.get('/FT')
                    rect = annot.get('/Rect', [])
                    value = annot.get('/V', '')

                    # Identify field type
                    if field_type == '/Btn':
                        field_flag = annot.get('/Ff', 0)
                        is_radio = (field_flag & 32768) != 0
                        field_type_readable = 'radio' if is_radio else 'checkbox'
                    elif field_type == '/Tx':
                        field_type_readable = 'text'
                    elif field_type == '/Ch':
                        field_type_readable = 'dropdown'
                    else:
                        field_type_readable = 'unknown'

                    fields[field_name] = {
                        'page': page_num,
                        'position': rect,
                        'type': field_type_readable,
                        'value': value
                    }
    return fields


@app.route('/forms', methods=['GET'])
def list_forms():
    """List all available forms in the input directory."""
    try:
        forms = [
            {
                'id': os.path.splitext(filename)[0],
                'name': filename,
                'url': f'/public/input/{filename}'
            }
            for filename in os.listdir(INPUT_DIR) if filename.endswith('.pdf')
        ]
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
                path = os.path.join(OUTPUT_DIR, filename)
                forms.append({
                    'id': os.path.splitext(filename)[0],
                    'name': filename,
                    'url': f'/public/output/{filename}',
                    'date': datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
                })
        return jsonify({'forms': forms})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/upload', methods=['POST'])
def upload_pdf():
    """Handle PDF upload and extract form fields."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'File must be a PDF'}), 400

    try:
        filepath = os.path.join(UPLOAD_DIR, file.filename)
        file.save(filepath)

        fields = extract_form_fields(filepath)

        return jsonify({
            'message': 'File uploaded successfully',
            'fields': fields,
            'filename': file.filename
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/fill-pdf', methods=['POST'])
def fill_pdf():
    """Fill the PDF form fields with data and save the result."""
    try:
        data = request.json
        filename = data.get('filename')
        field_data = data.get('fields', {})

        if not filename:
            return jsonify({'error': 'No filename provided'}), 400

        input_path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.exists(input_path):
            return jsonify({'error': 'PDF file not found'}), 404

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f'filled_{os.path.splitext(filename)[0]}_{timestamp}.pdf'
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        reader = PdfReader(input_path)
        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        # Prepare form data with proper values
        filled_fields = {}
        for key, val in field_data.items():
            if isinstance(val, bool):
                filled_fields[key] = '/Yes' if val else '/Off'
            else:
                filled_fields[key] = val

        writer.update_page_form_field_values(writer.pages[0], filled_fields)

        # Ensure appearance updates
        if "/AcroForm" in reader.trailer["/Root"]:
            writer._root_object.update({
                NameObject("/AcroForm"): reader.trailer["/Root"]["/AcroForm"]
            })
            writer._root_object["/AcroForm"].update({
                NameObject("/NeedAppearances"): BooleanObject(True)
            })

        with open(output_path, 'wb') as out_file:
            writer.write(out_file)

        return send_file(output_path, as_attachment=True, download_name=output_filename)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/public/<path:filename>')
def serve_file(filename):
    """Serve static PDF files from input or output directories."""
    try:
        directory = INPUT_DIR if 'input' in filename else OUTPUT_DIR
        return send_file(os.path.join(directory, os.path.basename(filename)))
    except Exception as e:
        return jsonify({'error': str(e)}), 404


if __name__ == '__main__':
    app.run(debug=True, port=5000)
