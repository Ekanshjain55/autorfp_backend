import os
import markdown
import pdfkit
import re

def add_line_breaks_between_list_items(md_text):
    # Handle main list items
    md_text = re.sub(r'(\n\d+\. .+)(\n\d+\. .+)', r'\1\n\2', md_text)
    
    # Handle sub-list items
    md_text = re.sub(r'(\n  - .+)(\n  - .+)', r'\1\n\2', md_text)
    
    return md_text

def convert_markdown_to_pdf(markdown_file_path, pdf_file_path):
    # Create directories in the output path if they do not exist
    os.makedirs(os.path.dirname(pdf_file_path), exist_ok=True)

    # Read Markdown file
    with open(markdown_file_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    # Add line breaks between list items
    md_text = add_line_breaks_between_list_items(md_text)

    # Convert Markdown to HTML
    html_text = markdown.markdown(md_text)

    # Wrap the HTML content
    wrapped_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
            }}
            ol {{
                list-style-type: decimal;
            }}
            ul {{
                list-style-type: disc;
            }}
        </style>
    </head>
    <body>
        {html_text}
    </body>
    </html>
    """
    
    # Convert HTML to PDF
    pdfkit.from_string(wrapped_html, pdf_file_path)
