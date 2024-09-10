import re
import PyPDF2

patterns = [
    (r"Norma PRO", "PROX"),
    (r"Norma Expert", "EXPERTX"),
    (r"Norma EXPERT", "EXPERTX"),
]

def find_template(pdf_file) -> str:
    #print(f"----{pdf_file.filename}")
    print('Finding template...')
    reader = PyPDF2.PdfReader(pdf_file)

    software_version = check_software_version(reader)

    print(software_version)
    if software_version == "PROX":
        return check_norma_pro_columns_template(reader)
    elif software_version == "EXPERTX":
        return check_norma_expert_columns_template(reader)
    else:
        return software_version

def check_software_version(reader):
    print('Checking version...')
    for page in reader.pages:
        if page.extract_text() is None:
            continue
        template = check_patterns_for_page(page.extract_text())
        if template is not None:
            return template

def check_patterns_for_page(text):
    print("Checking patterns...")
    for pattern, name in patterns:
        if re.search(pattern, text):
            return name
    return None

def check_norma_pro_columns_template(reader):
    print(len(reader.pages))
    for page in reader.pages:
        if page.extract_text() is None:
            continue
        list_of_lines = page.extract_text().split('\n')
        headers = [x for x in list_of_lines if 'Lp.' in x]
        for header in headers:
            if 'Podstawa' in header:
                return 'PRO6'
            elif 'Nr spec' in header:
                return 'PRO7'
    return None

def check_norma_expert_columns_template(reader):
    for index, page in enumerate(reader.pages):
        print(f"Page {index}")
        text = page.extract_text()
        text_normalized = text.replace('\n', '')
        #print(text_normalized)
        if index < 2:
            pass
        else:
            #print(text_normalized)
            #return None
            pass
        
        print(len(text_normalized))
        if index == 1:
            print(text_normalized)


        if 'Lp. PodstawaNrspec.techn.Opis i wyliczenia j.m. Poszcz. Razem' in text_normalized:
            return 'EXPERT7'
        elif 'Razem' in text_normalized and 'Poszcz.' in text_normalized and 'j.m.' in text_normalized and 'Podstawa' in text_normalized and 'Lp' in text_normalized:
            return 'EXPERT6'