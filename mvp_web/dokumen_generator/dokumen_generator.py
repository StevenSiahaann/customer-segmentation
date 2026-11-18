import sys
from docxtpl import DocxTemplate, InlineImage

from docx import Document
import re
def create_document(template_file,fileNames,replacements):
    output_dir=f"./mvp_web/dokumen_results/{fileNames}.docx"
    tpl =DocxTemplate(f"./mvp_web/template_dokumen/{template_file}.docx")
    tpl.render(replacements)
    tpl.save(output_dir)
    return output_dir



def find_placeholders_in_docx(file_path):
    doc = Document(f"./mvp_web/template_dokumen/{file_path}.docx")
    placeholders = []
    placeholder_pattern = re.compile(r'\{\{ \w+ \}\}')
    for paragraph in doc.paragraphs:
        found = placeholder_pattern.findall(paragraph.text)
        placeholders.extend(found)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    found = placeholder_pattern.findall(paragraph.text)
                    placeholders.extend(found)
    return list(set(placeholders))

