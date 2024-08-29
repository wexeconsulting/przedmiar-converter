import json
import csv
import re
import PyPDF2
import tabula
import pandas as pd
import io
import csv

debug = True

TEMPLATES = {
    "PRO1": {
        "area": [70.284, 71.697, 785.1, 558.11],
        "columns": [92.8, 144.6, 428.3, 457.2, 507.8],
        "remap_cols": ["lp", "podstawa", "opis", "jm", "poszcz", "razem"],
        "first_col": "Lp.",
        "second_col": "Podstawa",
        "forth_col": "j.m."
    }
}

class SectionTracker:
    def __init__(self):
        self.current_section_id = "0"
        self.current_lp = "0"
        self.next_possible_section_id = None
        self.next_possible_lp = None
        self.last_section = "first"
        self.worktime_calc = False

    def update_current_section_id(self, section_id: str):
        self.current_section_id = section_id
        self.next_possible_section_id = self.calculate_next_possible_section_id(section_id)

    def calculate_next_possible_section_id(self, section_id: str) -> list:
        section_parts = section_id.split('.')
        next_possible_section_id = []

        # Increment the last part
        last_part = section_parts[-1]
        next_part = str(int(last_part) + 1)
        next_possible_section_id.append('.'.join(section_parts[:-1] + [next_part]))

        # Append .1 to the current section ID
        next_possible_section_id.append(section_id + '.1')

        # Increment the preceding part by 1 and remove the last section
        if len(section_parts) > 1:
            preceding_part = section_parts[:-1]
            preceding_part[-1] = str(int(preceding_part[-1]) + 1)
            next_possible_section_id.append('.'.join(preceding_part))

        # Remove duplicates and sort
        next_possible_section_id = sorted(set(next_possible_section_id))

        return next_possible_section_id

    def update_current_lp(self, lp: str):
        self.current_lp = lp
        self.next_possible_lp = str(int(lp) + 1)
    
    def set_last_section(self, section):
        if section is None:
            return
        else:
            self.last_section = section

def extract_dict_from_pdf(template, pdf_path):
    section_tracker = SectionTracker()
    area = TEMPLATES[template]["area"]
    columns = TEMPLATES[template]["columns"]
    remap_cols = TEMPLATES[template]["remap_cols"]
    
    df_list = tabula.read_pdf(pdf_path, area=area, columns=columns, pages='all')
    filtered_dfs = [df for df in df_list if df.columns[0] == TEMPLATES[template]["first_col"] and df.columns[1] == TEMPLATES[template]["second_col"] and df.columns[3] == TEMPLATES[template]["forth_col"]]
    df_main = pd.concat(filtered_dfs, ignore_index=True).fillna("")
    df_main = df_main.rename(columns=dict(zip(df_main.columns, remap_cols)))

    current_section_id = "0"
    current_lp = "0"
    row_type = 'first'
    main_dict = {}

    for index, row in df_main.iterrows():
        section_tracker.set_last_section(row_type)
        row_type = evaluate_row(row, section_tracker)

        if row_type == 'section_title' and current_section_id != row['lp']:
            section_tracker.worktime_calc = False
            current_section_id = row['lp']
            current_section_desc = row['opis'] + row['jm'] + row['poszcz'] + row['razem']

            section_tracker.update_current_section_id(current_section_id)

            main_dict[current_section_id] = {
                'desc': current_section_desc,
                'lp': {}
            }

        if row_type == 'lp' and current_lp != row['lp']:
            section_tracker.worktime_calc = False
            current_lp = row['lp']
            section_tracker.update_current_lp(current_lp)

            if 'czas pracy' in row['opis'].lower():
                section_tracker.worktime_calc = True

            main_dict[current_section_id]['lp'][current_lp] = {
                'podstawa': row['podstawa'],
                'opis': row['opis'],
                'jm': row['jm'],
                'details': {}
            }
            details_no = 0

        if row_type == 'd' and section_tracker.last_section == 'lp':
            main_dict[current_section_id]['code'] = row['lp']
            main_dict[current_section_id]['lp'][current_lp]['podstawa'] += row['podstawa']
            main_dict[current_section_id]['lp'][current_lp]['opis'] += row['opis']
        
        if row_type == 'd' and section_tracker.last_section == 'd':
            main_dict[current_section_id]['code'] += row['lp']
            main_dict[current_section_id]['lp'][current_lp]['podstawa'] += " "+row['podstawa']
            main_dict[current_section_id]['lp'][current_lp]['opis'] += row['opis']
        
        if row_type == 'calculations':
            if row['opis'] == '':
                continue
            if row['jm'] == '':
                try:
                    main_dict[current_section_id]['lp'][current_lp]['details'][details_no]['opis'] += row['opis']
                except Exception as e:
                    raise e
                continue

            details_no += 1
            calculation = {
                "podstawa": row['podstawa'],
                "opis": row['opis'],
                "jm": row['jm'],
                "poszcz": row['poszcz']
            }

            main_dict[current_section_id]['lp'][current_lp]['details'][details_no] = calculation
        
        if row_type == 'total':
            main_dict[current_section_id]['lp'][current_lp]['razem'] = row['razem']

        if index < 10 and debug:
            print('-----------------')
            print(f'Index: {index}')
            print(f'Current section: {current_section_id}')
            print(f'Current lp: {current_lp}')
            print(f'Row type: {row_type}')
            print(row)
            print('---')
            print(json.dumps(main_dict, indent=4))


    return main_dict

def evaluate_row(row, section_tracker):
    lp = row['lp']
    jm = row['jm']
    poszcz = row['poszcz']

    sec_title = re.compile(r'^\d+(\.\d+)*$')
    lp_pattern = re.compile(r'^\d+$')
    d_pattern = re.compile(r'^d\.(\d+\.)*\d*$')

    def is_section_title_match(lp):
        if sec_title.match(lp):
            if section_tracker.next_possible_section_id is None:
                return True
            if lp in section_tracker.next_possible_section_id:
                return True
        return False

    def is_lp_match(lp):
        if lp_pattern.match(lp):
            if section_tracker.next_possible_lp is None:
                return True
            if section_tracker.next_possible_lp == lp:
                return True
        return False 

    if section_tracker.last_section == 'first':
        if sec_title.match(lp):
            return 'section_title'
        else:
            return None
    
    if section_tracker.last_section == 'section_title':
        if is_lp_match(lp):
            return 'lp'
        elif is_section_title_match(lp):
            return 'section_title'
    
    if section_tracker.last_section == 'lp':
        if d_pattern.match(lp):
            return 'd'

    if section_tracker.last_section == 'd':
        if lp != '' and section_tracker.worktime_calc:
            pass
        if jm == '':
            return 'd'
        else:
            return 'calculations'

    if section_tracker.last_section == 'calculations':
        if poszcz == 'RAZEM':
            return 'total'
        else:
            return 'calculations'

    if section_tracker.last_section == 'total' or section_tracker.worktime_calc:
        if is_lp_match(lp):
            return 'lp'
        elif is_section_title_match(lp):
            return 'section_title'

    return None

def convert_dict_to_csv(dict_data):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Lp.', '', 'Opis', '', 'Nazwa', '', '', '', '', 'Obmiar', 'JM'])
    
    try:
        for section_id, section_data in dict_data.items():
            if 'code' not in section_data:
                section_data['code'] = f'd.{section_id}'
            writer.writerow([section_data['code'], section_data['desc'], '', '', '', '', '', '', '', '', ''])
            
            if 'lp' in section_data:
                for lp_id, lp_data in section_data['lp'].items():
                    if 'razem' in lp_data:
                        razem = lp_data['razem']
                    else:
                        razem = 0
                    writer.writerow(['', lp_id, lp_data['podstawa'], '', lp_data['opis'], '', '', '', '', razem, lp_data['jm']])
                    
                    if 'details' in lp_data:
                        for detail_id, detail_data in lp_data['details'].items():
                            writer.writerow(['', '', '', detail_data['opis'], '', '', '', detail_data['poszcz'], '', detail_data['jm']])
    except Exception as e:
        raise e
    
    csv_data = output.getvalue().encode('utf-8')
    output.close()
    
    return csv_data

def convert_dict_to_json(raw_dict):
    result = []
    for section_id, section_data in raw_dict.items():
        section_dict = {
            "id": section_id,
            "opis": section_data["desc"],
            "lp": []
        }

        for lp_id, lp_data in section_data["lp"].items():
            lp_dict = {
                "lp": int(lp_id),
                "podstawa": lp_data["podstawa"],
                "opis": lp_data["opis"],
                "jm": lp_data["jm"],
                "wyliczenia": []
            }
            
            for detail_id, detail_data in lp_data["details"].items():
                detail_dict = {
                    "opis": detail_data["opis"],
                    "jm": detail_data["jm"],
                    "poszcz": detail_data["poszcz"]
                }
                lp_dict["wyliczenia"].append(detail_dict)
            
            section_dict["lp"].append(lp_dict)
        
        result.append(section_dict)
    
    return result

# Example usage
def main(pdf_path):
    pdf_name = pdf_path.split('.')[0]

    dict_content = extract_dict_from_pdf('PRO1', pdf_path)
    with open(f'{pdf_name}_output_raw.json', 'w', encoding='utf-8') as json_file:
        json.dump(dict_content, json_file, ensure_ascii=False, indent=4)

    dict_final = convert_dict_to_json(dict_content)
    with open(f'{pdf_name}_output_final.json', 'w', encoding='utf-8') as json_file:
        json.dump(dict_final, json_file, ensure_ascii=False, indent=4)

    csv_data = convert_dict_to_csv(dict_content)
    with open(f'{pdf_name}_file.csv', 'w', newline='', encoding='utf-8') as file:
        file.write(csv_data.getvalue)

if __name__ == "__main__":
    main('blad1.pdf')
    main('blad2.pdf')
    main('blad3.pdf')
    main('blad4.pdf')
    main('blad6.pdf')