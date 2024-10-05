import re
import PyPDF2

from logger_cfg import setup_logger

log = setup_logger(__name__)

patterns = [
    (r"Norma PRO", "PROX"),
    (r"Norma Expert", "EXPERTX"),
    (r"Norma EXPERT", "EXPERTX"),
]

def find_template(pdf_file) -> str:
    #print(f"----{pdf_file.filename}")
    log.debug('Begin: find_template')
    log.debug('Finding template...')
    reader = PyPDF2.PdfReader(pdf_file)

    software_version = check_software_version(reader)


    log.debug(f"Software version: {software_version}")
    if software_version == "PROX":
        return check_norma_pro_columns_template(reader)
    elif software_version == "EXPERTX":
        return check_norma_expert_columns_template(reader)
    else:
        return software_version

def check_software_version(reader):
    log.debug("Begin: check_software_version")
    for page in reader.pages:
        if page.extract_text() is None:
            continue
        template = check_patterns_for_page(page.extract_text())
        if template is not None:
            return template

def check_patterns_for_page(text):
    log.debug("Begin: check_patterns_for_page")
    for pattern, name in patterns:
        if re.search(pattern, text):
            return name
    return None

def check_norma_pro_columns_template(reader):
    log.debug("Begin: check_norma_pro_columns_template")
    log.debug(f"Number of pages: {len(reader.pages)}")
    for page in reader.pages:
        text = page.extract_text()
        text_normalized = text.replace('\n', '')
        #print(text_normalized)
        if 'Lp. Podstawa Nr spec. techn. Opis i wyliczenia j.m. Poszcz. Razem' in text_normalized:
            return 'PRO7'
        if 'Lp. Nr spec.techn.Podstawa Opis i wyliczenia j.m. Poszcz. Razem' in text_normalized:
            return 'PRO7'
        if 'Lp. Nr spec. techn. Podstawa Opis i wyliczenia j.m. Poszcz Razem' in text_normalized:
            return 'PRO7'
        if 'Lp. Podstawa Opis i wyliczenia j.m. Poszcz Razem' in text_normalized:
            return 'PRO6'
        elif 'Razem' in text_normalized and 'Poszcz.' in text_normalized and 'j.m.' in text_normalized and 'Podstawa' in text_normalized and 'Lp' in text_normalized:
            return 'PRO6'
            
    return None

def check_norma_expert_columns_template(reader):
    for page in reader.pages:
        text = page.extract_text()
        text_normalized = text.replace('\n', '')
        print(text_normalized)
        if 'Lp. PodstawaNrspec.techn.Opis i wyliczenia j.m. Poszcz. Razem' in text_normalized:
            return 'EXPERT7'
        if 'Lp. Kod pozycji spec. tech Opis i obliczenia liczby j.m. liczba Razem' in text_normalized:
            return 'EXPERT7'
        if 'Lp. Kod pozycji Opis i wyliczenia j.m. Poszcz. Razem' in text_normalized:
            return 'EXPERT6'
        elif 'Razem' in text_normalized and 'Poszcz.' in text_normalized and 'j.m.' in text_normalized and 'Podstawa' in text_normalized and 'Lp' in text_normalized:
            return 'EXPERT6'