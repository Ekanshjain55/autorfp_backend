from fastapi import FastAPI, File, Query, Body,HTTPException, UploadFile
from utilities.docx_reader import read_docx
from utilities.pdf_reader import read_pdf
from utilities.markdown_to_pdf_converter import convert_markdown_to_pdf
from utilities.md2pdfdoc import convert_markdown_to_pdf_and_word
from api.openai_wrapper import get_chatgpt_response
import os
import pymysql
import uuid
from tempfile import NamedTemporaryFile


app = FastAPI()

async def create_connection_pool():
    pool = await aiopg.create_pool(
        host="127.0.0.1",
        user="root",
        password="password",
        database="auto_rfp"
    )
    return pool

@app.post("/generate_rfp/")
async def generate_rfp(file: UploadFile = File(..., description="Path to the SoW file")):
    with NamedTemporaryFile('wb', prefix=str(file.filename).split(".", 1)[0], suffix=f'.{str(file.filename).split(".")[-1]}') as f:
        f.write(file.file.read())
        print(f.name)
        sow = read_docx(f.name) if f.name.endswith('.docx') else read_pdf(f.name)
    
    prompt = f"""
    As a seasoned Senior Software Architect, you are tasked with formulating a project proposal for a potential client based on their `Statement of Work (SoW)`. You must create a comprehensive and robust markdown document that naturally segregates into sections and sub-sections and lists in these sections should always be numbered. Make sure to thoroughly review the `sow` variable holding all the client's project specifications, targets, and constraints. Every detail is crucial, and demonstrating a firm grasp of the project is imperative. Structure the proposal relative to the `sow` insights as follows:
    Using the following Statement of Work, carve out the proposal sections for Project:
    Statement of Work:
    {sow}

    Desired Output: 
    ---
        
    ## Project Proposal Document

    ### PROJECT NAME 
    (Create a suitable project name here. If the Client's name is mentioned in the SoW specification, also refer to it when generating the project name. The project name can contain a maximum of one line.)

    ### TABLE OF CONTENT
    (Design a thorough table of contents involving sections and sub-sections here)

    ### EXECUTIVE SUMMARY 
    (Formulate an executive summary for the project here)

    ### INTRODUCTION
    (Describe the nature of the project, why it is important, and how it addresses the client needs expressed in the SoW, statement of work.)

    ### OBJECTIVES
    (Frame the project's objectives here. Keep it organized, easily comprehensible, and in line with the `sow`)

    ### SCOPE OF WORK
    (Expound on the project's scope of work here)

    ### TECHNOLOGY STACK 
    (Specify the technology stack applicable for the project' practical completion. Remember to only highlight the necessary technologies that emphasize our technical expertise. Arrange them according to their associated domain such as Database, Front-End, Back-End, Deployment, etc. All necessary technology should be methodically detailed here)

    ### RISKS AND MITIGATION
    (Identify potential risks linked to the project's implementation and the corresponding solution strategies here) 

    ### CONCLUSION  
    (Conclude the proposal here)

    ### APPENDIX
    (Create an appendix for the proposal document here)
    ---
    General Formatting Instructions:
    - For any lists and sublist in the proposal, use numbered list ALWAYS.
    - Use `##` for subsection headers and `###` for sub-subsection headers.
    - Enclose code snippets within triple backticks (\`\`\`).
    - Use **bold** for important terms and *italics* for emphasis.
    - To include hyperlinks, use the Markdown format `[text](URL)`.
    - To include images, use the Markdown format `![alt text](URL)`.
    - Format tables using Markdown's table syntax.
    - Use `>` for block quotes.
    - If footnotes are needed, place them at the end of the document and link to them within the text.
    - For line breaks, start the text from a new line. 
    """
    generated_rfp_sections = get_chatgpt_response(prompt)
    
    db_connection = pymysql.connect(
        host="127.0.0.1",
        user="root",
        password="password",
        database="auto_rfp"
    )
#create a cursor object to interact with the database
    cursor = db_connection.cursor()

    # Create a table to store the Markdown content with a UUID primary key
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS markdown_content (
            id CHAR(36) PRIMARY KEY,
            content TEXT
        )
    """)
    new_uuid= str(uuid.uuid4())
    shared_data=new_uuid
    # Insert the generated Markdown content into the database
    cursor.execute("""
        INSERT INTO markdown_content (id, content)
        VALUES (%s, %s)
    """, (new_uuid, generated_rfp_sections))
    # Commit the changes to the database
    db_connection.commit()
    print("Markdown content added to the database with UUID:", new_uuid)
    return new_uuid
    # Ensure the directory exists
   
@app.post("/edit_rfp/")
async def edit_rfp(uuid: str = Body(..., embed=True),
    section: str = Body(..., embed=True),
    edit_instruction: str = Body(..., embed=True)
):
    # Connect to the database
    db_connection = pymysql.connect(
        host="127.0.0.1",
        user="root",
        password="password",
        database="auto_rfp"
    )

    with db_connection.cursor() as db_cursor:
        # Retrieve content from the database using UUID
        db_cursor.execute("SELECT content FROM markdown_content WHERE id = %s", (uuid,))
        result = db_cursor.fetchone()

        if result is None:
            raise HTTPException(status_code=404, detail="Document not found in the database")

        # Extract the existing content
        existing_content = result[0]

        # Find the section in the existing content
        start_idx, end_idx = None, None
        section_level = section.count("#")
        content_lines = existing_content.split('\n')
        for i, line in enumerate(content_lines):
            line_level = line.count("#")
            if line.strip() == section:
                start_idx = i
            elif start_idx is not None and line.startswith("#") and line_level <= section_level:
                end_idx = i
                break

        if start_idx is None:
            return {"error": "Section not found"}

        # Extract the previous content
        previous_content = "\n".join(content_lines[start_idx+1:end_idx]).strip()

        # Create a prompt for editing
        prompt = f"""
        You are tasked with editing a specific section in a project proposal. You are given the section, editing instructions, and the previous content of the section.
        1. Section: {section} - This pinpoints the exact section within the document that requires editing. Note: Do not include this header in your response.
        2. Instructions: {edit_instruction} - These directions offer insights into the kind of amendments or additions needed.
        3. Previous Content: {previous_content} - This encapsulates what was originally drafted in this section.

        Produce a stand-alone, revised version of the section's content. Do not reference the previous content or indicate that the section has been edited. Also do not generate section Heading. 
        """

        # Generate the new content based on the prompt
        generated_new_content = get_chatgpt_response(prompt).strip()

        # Replace the section in the existing content with the new content
        content_lines[start_idx+1:end_idx] = generated_new_content.split('\n')

        # Update the content in the database
        updated_content = "\n".join(content_lines)
        
        db_cursor.execute("UPDATE markdown_content SET content = %s WHERE id = %s", (updated_content, uuid))
        db_connection.commit()

        return updated_content


@app.post("/generate_rfp_from_verbal/")
async def generate_rfp_from_verbal(verbal_requirements: str = Body(..., description="Verbal requirements for the project")):
    
    prompt = f"""
    As an experienced Senior Software Architect, you have received verbal requirements for a potential project. Your task is to convert these verbal specifications into a formal project proposal. Ensure that your proposal is comprehensive, professionally structured, and addresses all the verbal requirements as follows:
    
    Verbal Requirements:
    {verbal_requirements}
    
    Desired Output: 
    ---
    ## Project Proposal Document

    ### PROJECT NAME 
    (Craft a fitting project name here. If the Client's Name mentioned in the SoW, reference that while generating the Project name as well. project Name should be at max a line long.)

    ### Table Of Content
    (Design a thorough table of contents involving sections and sub-sections here)

    ### EXECUTIVE SUMMARY 
    (Formulate an executive summary for the project here)

    ### INTRODUCTION
    (Describe the project's essence, why it matters, and its adherence to the client's needs as expressed in the SoW.)

    ### OBJECTIVES
    (Frame the project's objectives here. Keep it organized, easily comprehensible, and in line with the verbal requirements)

    ### SCOPE OF WORK
    (Expound on the project’s scope of work here)

    ### TECHNOLOGY STACK 
    (Specify the technology stack applicable for the project’s practical completion. Remember to only highlight the necessary technologies that emphasize our technical expertise. Arrange them according to their associated domain such as Database, Front-End, Back-End, Deployment, etc. All necessary technology should be methodically detailed here)

    ### RISKS AND MITIGATION
    (Identify potential risks linked to the project’s implementation and the corresponding solution strategies here) 

    ### CONCLUSION
    (Conclude the proposal here)

    ### APPENDIX
    (Create an appendix for the proposal document here)
    ---
    General Formatting Instructions:
    - For any lists and sublist in the proposal, use numbered list ALWAYS.
    - Use `##` for subsection headers and `###` for sub-subsection headers.
    - Enclose code snippets within triple backticks (\`\`\`).
    - Use **bold** for important terms and *italics* for emphasis.
    - To include hyperlinks, use the Markdown format `[text](URL)`.
    - To include images, use the Markdown format `![alt text](URL)`.
    - Format tables using Markdown's table syntax.
    - Use `>` for block quotes.
    - If footnotes are needed, place them at the end of the document and link to them within the text.
    - For line breaks, start the text from a new line. 
    """
    
    generated_rfp_sections = get_chatgpt_response(prompt)
    
    db_connection = pymysql.connect(
        host="127.0.0.1",
        user="root",
        password="password",
        database="auto_rfp"
    )
#create a cursor object to interact with the database
    cursor = db_connection.cursor()

    # Create a table to store the Markdown content with a UUID primary key
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS markdown_content (
            id CHAR(36) PRIMARY KEY,
            content TEXT
        )
    """)
    new_uuid= str(uuid.uuid4())

    shared_data=new_uuid
    # Insert the generated Markdown content into the database
    cursor.execute("""
        INSERT INTO markdown_content (id, content)
        VALUES (%s, %s)
    """, (new_uuid, generated_rfp_sections))

    # Commit the changes to the database
    db_connection.commit()
    print("Markdown content added to the database with UUID:", new_uuid)

    return new_uuid