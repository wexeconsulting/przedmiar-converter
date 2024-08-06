import tabula
import pandas as pd
import numpy as np
import io
import os

os.environ['JAVA_HOME'] = '/usr'

def convert_pdf_wrapper(pdf_file):
    # placeholder for logic to invoke different convert functions based on the PDF content
    # suggested - one function that converts and returns data itself
    # and another function that converts and returns CSV content or json depending on needs
    return convert_pdf_to_csv_1(pdf_file)

def convert_pdf_to_csv_1(pdf_path):
    # Define the area of the table (top-left x, top-left y, bottom-right x, bottom-right y)
    csv_buffer = io.StringIO()
    area = [70.284, 71.697, 761.228, 558.11]
    columns = [92.8, 144.6, 428.3, 457.2, 507.8]

    # Starting page to read from
    start_page = 3

    # Extract the total number of pages in the PDF
    total_pages = tabula.read_pdf(pdf_path, pages='all', area=area, columns=columns, guess=False, multiple_tables=True, silent=True)
    total_pages_count = len(total_pages)

    # List to hold all dataframes
    all_dfs = []

    # Loop through all pages from start_page to the end
    for page in range(start_page, total_pages_count + 1):
        dfs = tabula.read_pdf(pdf_path, pages=page, area=area, columns=columns, guess=False, multiple_tables=True)
        all_dfs.extend(dfs)

    # Concatenate all dataframes into one
    df = pd.concat(all_dfs, ignore_index=True)

    # Porzuć pierwsze dwa wiersze
    df = df.iloc[2:]  # Wybierz wiersze od indeksu 2 (trzeci wiersz) do końca

    # Zresetuj indeksy po porzuceniu wierszy
    df = df.reset_index(drop=True)

    # Przeniesienie wartości 'd.' do nowej kolumny 'Dział'
    df['Dział'] = df['Lp.'].apply(lambda x: x if isinstance(x, str) and x.startswith('d.') else np.nan)

    # Przesunięcie wartości 'd.' w kolumnie 'Dział' o jeden wiersz do góry
    df['Dział'] = df['Dział'].shift(-1, fill_value=np.nan)

    # Ustawienie wartości 'd.' w kolumnie 'Lp.' na NaN
    df['Lp.'] = df['Lp.'].apply(lambda x: np.nan if isinstance(x, str) and x.startswith('d.') else x)

    # Dodanie nowej kolumny 'Nazwa' z początkowymi wartościami NaN
    df['Nazwa'] = ""

    # Nowa kolejność kolumn
    new_order = ['Lp.', 'Dział', 'Podstawa', 'Nazwa','Opis i wyliczenia', 'j.m.', 'Poszcz', 'Razem']

    # Reindeksowanie ramki danych z nową kolejnością kolumn
    df = df.reindex(columns=new_order)

    # # Zajmujemy się wartościami w kolumnie Podstawa
    df['Podstawa'] = df['Podstawa'].replace('analogia', np.nan)

    df['Condition_1'] = False

    # Warunek logiczny do wybrania odpowiednich akapitów takich jak: "ROBOTY MUROWE + NADPROŻA"
    condition = (
        df['Lp.'].notnull() &  # Lp. nie jest puste
        df['Dział'].isnull() & #jest puste
        df['Podstawa'].isnull()
    )

    # Aktualizacja wartości w kolumnie Condition_1
    df.loc[condition, 'Condition_1'] = True

    # Tworzenie nowego DataFrame na podstawie warunku
    df_selected = df.loc[condition].copy()  # Kopiowanie wybranych wierszy do nowego DataFrame

    print(df_selected)

    # Usunięcie wybranych wierszy z oryginalnego DataFrame
    df.drop(df.loc[condition].index, inplace=True)

    # # Usunięcie wierszy, w których kolumny "Opis i wyliczenia j.m.", "Poszcz" i "Razem" są puste
    # df = df.dropna(subset=['Opis i wyliczenia','j.m.', 'Poszcz', 'Razem'], how='all')

    # Warunek logiczny do połączenia opisów ze sobą
    condition = (
        df['j.m.'].isnull() &  #jest puste
        df['Poszcz'].isnull() & #jest puste
        df['Razem'].isnull() #jest puste
    )

    # Za pomocą tego kodu łącze ze sobą opisy i wyliczenia wtedy kiedy były podzielone na kilka wierszy
    df.loc[condition, 'Condition_1'] = True

    df = df.reset_index(drop=True)
    df['Opis i wyliczenia'].fillna(value='', inplace=True)

    # Przetwarzanie danych zgodnie z warunkiem od końca ramki danych
    previous_true_index = None
    for index in reversed(range(len(df))):
        if df.at[index, 'Condition_1'] == True:
            if previous_true_index is not None:
                # Łączenie Opisów i wyliczeń poprzedniego wiersza z obecnym
                df.at[index, 'Opis i wyliczenia'] += ' ' + df.at[previous_true_index, 'Opis i wyliczenia']
                # Ustawienie pustego Opisu i wyliczeń dla poprzedniego wiersza
                df.at[previous_true_index, 'Opis i wyliczenia'] = ''
            # Uaktualnienie poprzedniego indeksu TRUE
            previous_true_index = index
        else:
            # Gdy napotkamy pierwsze FALSE, przerywamy łączenie
            previous_true_index = None

    # Przetwarzanie danych zgodnie z warunkiem
    for index, row in df.iterrows():
        if row['Condition_1'] == True:
            # Łączenie Opisów i wyliczeń poprzedniego wiersza z obecnym
            df.at[index - 1, 'Opis i wyliczenia'] += '' + row['Opis i wyliczenia']
            # Ustawienie pustego Opisu i wyliczeń dla obecnego wiersza
            df.at[index, 'Opis i wyliczenia'] = ''

    # Usunięcie kolumny Condition_1 żeby można było po raz kolejny go użyć
    df = df.drop(axis=1, columns=['Condition_1'])

    df['Condition_1'] = False
    # Warunek logiczny za pomocą którego usuwam puste wiersze
    condition = (
        df['Lp.'].isnull() &  #jest puste
        df['Dział'].isnull() & #jest puste
        df['Podstawa'].isnull() & #jest puste
        df['Poszcz'].isnull() & #jest puste
        df['Razem'].isnull() #jest puste
    )

    # Za pomocą tego kodu łącze ze sobą opisy i wyliczenia wtedy kiedy były podzielone na kilka wierszy
    df.loc[condition, 'Condition_1'] = True
    df = df.drop(df[condition].index).reset_index(drop=True)

    # Wprowadzenie warunku za pomocą którego połączymy Podstawe w 1 ciąg znaków oraz Opisy
    df['Condition_1'] = False

    condition_1 = (
        (df['Opis i wyliczenia'] == '') &
        df['j.m.'].isnull() &  #nie jest puste
        df['Poszcz'].isnull() #nie jest puste
    )

    df.loc[condition_1, 'Condition_1'] = True
    df = df.reset_index(drop=True)

    # # # Znajdź wiersze, gdzie Condition_1 jest PRAWDA
    # mask = df['Condition_1'] == True

    # Przetwarzanie danych zgodnie z warunkiem
    for index, row in df.iterrows():
        if row['Condition_1'] == True and index > 0:  # Upewnij się, że nie próbujemy odwołać się do wiersza o indeksie -1
            # Konwertuj wartość na string, aby uniknąć błędów
            df.at[index - 1, 'Podstawa'] = str(df.at[index - 1, 'Podstawa']) + ' ' + str(row['Podstawa'])
            # Ustawienie pustego Opisu i wyliczeń dla obecnego wiersza
            df.at[index, 'Podstawa'] = ''

    # Porzucenie wierszy, gdzie Condition_1 jest True
    df = df[df['Condition_1'] == False]

    # Usunięcie kolumny Condition_1, bo nie jest już potrzebna
    df = df.drop(columns=['Condition_1'])

    # # Warunek i kopiowanie zawartości
    mask = df['Podstawa'].str.contains('NR', na=False)
    df.loc[mask, 'Nazwa'] = df.loc[mask, 'Opis i wyliczenia']
    df.loc[mask, 'Opis i wyliczenia'] = ""

    # Warunek
    condition = (df['Opis i wyliczenia'] == '') & df['Poszcz'].isna() & df['Razem'].isna()

    # Zmiana wartości w kolumnie 'j.m.' na pustą, jeżeli warunek jest spełniony
    df.loc[condition, 'j.m.'] = ''

    # df['Lp.'] = df['Lp.'].ffill()
    # df['Lp.'] = df['Lp.'].astype(str).astype(int)
    # df['Dział'] = df['Dział'].ffill()
    # df['Podstawa'] = df['Podstawa'].ffill()

    # print('---------------')
    print(df.dtypes)

    # # Wyświetlenie zaktualizowanej ramki danych
    print('---------------')
    # pd.set_option('display.max_rows', None)
    print(df)
    print(df.head(10))

    # # Zapis do pliku CSV
    # df.to_csv(csv_buffer, index=False)


    # Additional debug print statements to inspect dataframe content
    print("Dataframe head after processing:")
    print(df.head())

    # Write to CSV buffer
    df.to_csv(csv_buffer, index=False)

    # Print CSV buffer content for debugging
    csv_content = csv_buffer.getvalue()
    return csv_content
