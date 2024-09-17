from converter.pdf_evaluator import find_template
import pdfplumber
import json
import csv
import re
import tabula
import pandas as pd
import io
import csv

from logger_cfg import setup_logger

log = setup_logger(__name__)

debug = True

FORMATS = {
    "PRO7": {
        "columns": 7,
        "remap_cols": ["lp", "nr_spec", "podstawa", "opis", "jm", "poszcz", "razem"],
        "first_col": "Lp.",
        "seventh_col": "Razem"
    },
    "PRO6": {
        "columns": 6,
        "remap_cols": ["lp", "podstawa", "opis", "jm", "poszcz", "razem"],
        "first_col": "Lp.",
        "sixth_col": "Razem"
    },
    "EXPERT6": {
        "columns": 6,
        "remap_cols": ["lp", "podstawa", "opis", "jm", "poszcz", "razem"],
        "first_col": "Lp.",
        "sixth_col": "Razem"
    },
    "EXPERT7": {
        "columns": 7,
        "remap_cols": ["lp", "podstawa", "nr_spec", "opis", "jm", "poszcz", "razem"],
        "first_col": "Lp.",
        "seventh_col": "Razem"
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


def check_format_and_extract_dict(pdf_path):
    log.debug("Begin: check_format_and_extract_dict")
    format = find_template(pdf_path)
    log.debug(f"Found template: {format}")
    return extract_dict_from_pdf(format, pdf_path)

def get_df_from_pdf(pdf_path, template):
    log.debug("Begin: get_df_from_pdf")
    tpl_params = FORMATS[template]
    print(tpl_params)
    list_of_dfs = []

    #extract dataframes from file - page by page, table by table as separate dataframe
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            if page is None:
                continue
            tables = page.extract_tables()
            for tab in tables:
                first_row = [element.replace('\n', ' ') if element else element for element in tab[0]]
                df = pd.DataFrame(tab[1:], columns=first_row).fillna("")
                list_of_dfs.append(df)
    log.debug(f"Found total dataframes: {len(list_of_dfs)}")

    #for x in list_of_dfs:
        #print(x.columns)
        #print(x.head(5))


    # todo temporary solution
    filtered_dfs = [df for df in list_of_dfs if df.columns[0] == tpl_params["first_col"]]
    log.debug(f"After filtering: {len(list_of_dfs)}")
    for i in filtered_dfs:
        log.debug(len(i.columns))

    #process the tables - merge columns if necessary
    for i, df in enumerate(filtered_dfs):
        columns = df.columns.tolist()
        j = 0
        while j < len(columns) - 1:
            if columns[j + 1] is None:
                df[columns[j]] = df[columns[j]].astype(str) + df.iloc[:, j + 1].astype(str)
                df.drop(columns=[columns[j + 1]], inplace=True)
                columns = df.columns.tolist()  # Update columns list after dropping
            else:
                j += 1
        filtered_dfs[i] = df
    
    log.debug(f"After merging columns: {len(filtered_dfs)}")
    #for df in filtered_dfs:
    #    print(df.columns)

    for df in filtered_dfs:
        print(df.head(10))

    if 'sixth_col' in tpl_params:
        filtered_dfs = [df for df in filtered_dfs if len(df.columns) >= tpl_params["columns"] and tpl_params["sixth_col"] in df.columns[5]]
    elif 'seventh_col' in tpl_params:
        filtered_dfs = [df for df in filtered_dfs if len(df.columns) >= tpl_params["columns"] and tpl_params["seventh_col"] in df.columns[6]]
        
    else:
        filtered_dfs = [df for df in filtered_dfs if len(df.columns) >= tpl_params["columns"]]
    
    

    df_main = pd.concat(filtered_dfs, ignore_index=True)
    df_main = df_main.rename(columns=dict(zip(df_main.columns, tpl_params["remap_cols"])))
    #print(df_main.head(10))
    return split_rows(df_main)

def extract_dict_from_pdf(template, pdf_path):
    log.debug("Begin: extract_dict_from_pdf")
    section_tracker = SectionTracker()
    
    df_main = get_df_from_pdf(pdf_path, template)

    current_section_id = "0"
    current_lp = "0"
    row_type = 'first'
    main_dict = {}

    #if template in ("EXPERT6", "PRO6", "EXPERT7"):
    evaluate_function = evaluate_row_pro6
    #elif template == "PRO7":
    #    evaluate_function = evaluate_row_pro7
    #else:
    #    evaluate_function = evaluate_row_pro6

    for index, row in df_main.iterrows():
        section_tracker.set_last_section(row_type)
        row_type = evaluate_function(row, section_tracker)

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
            main_dict[current_section_id]['lp'][current_lp]['podstawa'] += " "+row['podstawa']
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

        if index > 550 and debug:
            print('-----------------')
            print(f'Index: {index}')
            print(f'Current section: {current_section_id}')
            print(f'Current lp: {current_lp}')
            print(f'Row type: {row_type}')
            print(row)
            print('---')
            #if index == 9:
            #    print(json.dumps(main_dict, indent=4))


    return main_dict

def evaluate_row_pro6(row, section_tracker):
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

def evaluate_row_pro6(row, section_tracker):
    lp = row['lp']
    jm = row['jm']
    poszcz = row['poszcz']
    podstawa = row['podstawa']

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
        if section_tracker.worktime_calc and jm == '' and podstawa == '':
            if is_section_title_match(lp):
                return 'section_title'
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
                            writer.writerow(['', '', '', detail_data['opis'], '', '', '', detail_data['poszcz'], '', '', detail_data['jm']])
    except Exception as e:
        raise e
    
    csv_data = output.getvalue().encode('utf-8')
    output.close()
    
    return csv_data

def convert_dict_to_json(raw_dict):
    result = []
    for section_id, section_data in raw_dict.items():
        section_dict = {
            "lp": section_id,
            "opis": section_data["desc"],
            "pozycje": []
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
            
            section_dict["pozycje"].append(lp_dict)
        
        result.append(section_dict)
    
    return result

def split_rows(df):
    new_rows = []
    for index, row in df.iterrows():
        split_needed = False
        new_row_data = {col: [] for col in df.columns}
        
        for col in df.columns:
            if '\n' in str(row[col]):
                split_needed = True
                split_values = str(row[col]).split('\n')
                new_row_data[col] = split_values
            else:
                new_row_data[col] = [row[col]]
        
        if split_needed:
            max_splits = max(len(values) for values in new_row_data.values())
            for i in range(max_splits):
                new_row = {col: (new_row_data[col][i] if i < len(new_row_data[col]) else '') for col in df.columns}
                new_rows.append(new_row)
        else:
            new_rows.append(row.to_dict())
    
    new_df = pd.DataFrame(new_rows)
    return new_df.reset_index(drop=True)

# Example usage
def main(pdf_path):
    pdf_name = pdf_path.split('.')[0]

    template = check_format_and_extract_dict(pdf_path)

    dict_content = extract_dict_from_pdf(template, pdf_path)
    with open(f'{pdf_name}_output_raw.json', 'w', encoding='utf-8') as json_file:
        json.dump(dict_content, json_file, ensure_ascii=False, indent=4)

    dict_final = convert_dict_to_json(dict_content)
    with open(f'{pdf_name}_output_final.json', 'w', encoding='utf-8') as json_file:
        json.dump(dict_final, json_file, ensure_ascii=False, indent=4)

    csv_data = convert_dict_to_csv(dict_content)
    with open(f'{pdf_name}_file.csv', 'w', newline='', encoding='utf-8') as file:
        file.write(csv_data.getvalue)

if __name__ == "__main__":
    pass
    #check_file_format('test_data/blad1.pdf')
    main('test_data/pro7.pdf')
    #main('blad3.pdf')
    #main('blad4.pdf')
    #main('blad6.pdf')