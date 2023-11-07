import PyPDF2

# Function to read PDF file
def read_pdf(file_path):
    pdf_text = []
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        num_pages = len(reader.pages)  
        for page_num in range(num_pages):
            page = reader.pages[page_num]
            pdf_text.append(page.extract_text())
    return '\n'.join(pdf_text)
