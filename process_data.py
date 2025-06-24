import pandas as pd
import snowflake.connector
import os
from dotenv import load_dotenv


def load_data(file_path = "excel_files/excel_poc.xlsx"):
    """Charge et traite les données du fichier Excel"""
    # Lire les 4 onglets du fichier Excel

    xls = pd.ExcelFile(file_path)  # Remplacez par le nom exact de votre fichier Excel
    df = pd.DataFrame()

    for sheet_name in ["Chargés", "Vides", "Appro", "Evac"]:
        df_temp = pd.read_excel(xls, sheet_name=sheet_name)[[
            "Train Id", "Point départ", "Point arrivée", "Date départ théorique", 
            "Date départ replanifiée", "Date départ réelle", "Date arrivée théorique", 
            "Date arrivée replanifiée", "Date arrivée réelle", "Nb Théo.", "Nb Comm.", "Nb Réel"
        ]].rename(columns={
            "Train Id": "train_id",
            "Point départ": "departure_point", 
            "Point arrivée": "arrival_point",
            "Date départ théorique": "scheduled_departure_date",
            "Date départ replanifiée": "rescheduled_departure_date", 
            "Date départ réelle": "actual_departure_date",
            "Date arrivée théorique": "scheduled_arrival_date",
            "Date arrivée replanifiée": "rescheduled_arrival_date",
            "Date arrivée réelle": "actual_arrival_date",
            "Nb Théo.": "theoretical_nb_wagons",
            "Nb Comm.": "comm_nb_wagons",
            "Nb Réel": "actual_nb_wagons"
        })
        df_temp['type'] = sheet_name
        df = pd.concat([df, df_temp], ignore_index=True)

    # Convertir les colonnes de dates en datetime
    date_columns = ['scheduled_departure_date', 'rescheduled_departure_date', 'actual_departure_date',
                    'scheduled_arrival_date', 'rescheduled_arrival_date', 'actual_arrival_date']

    for col in date_columns:
        df[col] = pd.to_datetime(df[col], format='%d/%m/%Y %H:%M:%S', errors='coerce')

    df['departure_date'] = df['actual_departure_date'].combine_first(df['rescheduled_departure_date']).combine_first(df['scheduled_departure_date'])
    df['arrival_date'] = df['actual_arrival_date'].combine_first(df['rescheduled_arrival_date']).combine_first(df['scheduled_arrival_date'])
    df['nb_wagons'] = df['actual_nb_wagons'].combine_first(df['comm_nb_wagons']).combine_first(df['theoretical_nb_wagons'])
    
    df.drop(columns=["actual_departure_date", "rescheduled_departure_date", "scheduled_departure_date", "actual_arrival_date", "rescheduled_arrival_date", "scheduled_arrival_date", "actual_nb_wagons", "comm_nb_wagons", "theoretical_nb_wagons"], inplace=True)

    # Remplacer VO, GRA et RIO par VO-GRA-RIO dans departure_point et arrival_point
    df['departure_point'] = df['departure_point'].replace(['VO', 'GRA', 'RIO'], 'VO-GRA-RIO')
    df['arrival_point'] = df['arrival_point'].replace(['VO', 'GRA', 'RIO'], 'VO-GRA-RIO')

    return df

def upload_data(df):
    """Upload les données dans la base de données snowflake"""

        # Charger les variables d'environnement
    load_dotenv()

    # Connexion à la base de données Snowflake
    conn = snowflake.connector.connect(
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA')
    )
    
    cursor = conn.cursor()
    
    try:
        # Obtenir les dates couvertes par l'Excel
        min_date = df['departure_date'].min()
        max_date = df['departure_date'].max()
        
        # Formater les dates pour Snowflake
        min_date_str = min_date.strftime('%Y-%m-%d %H:%M:%S')
        max_date_str = max_date.strftime('%Y-%m-%d %H:%M:%S')
        
        # Supprimer les données existantes pour les jours couverts par l'Excel
        delete_query = f"""
        DELETE FROM trains 
        WHERE departure_date >= '{min_date_str}' AND departure_date <= '{max_date_str}'
        """
        cursor.execute(delete_query)
        
        # Insérer les nouvelles données en une seule requête
        insert_query = """
        INSERT INTO trains (
            train_id, departure_point, arrival_point, departure_date, 
            arrival_date, nb_wagons, type
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        # Préparer toutes les données pour l'insertion en lot
        data_to_insert = []
        for _, row in df.iterrows():
            departure_date_str = row['departure_date'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['departure_date']) else None
            arrival_date_str = row['arrival_date'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['arrival_date']) else None
            
            data_to_insert.append((
                row['train_id'], 
                row['departure_point'], 
                row['arrival_point'],
                departure_date_str, 
                arrival_date_str, 
                row['nb_wagons'], 
                row['type']
            ))
        
        # Exécuter l'insertion en lot
        cursor.executemany(insert_query, data_to_insert)

        
        # Valider les changements
        conn.commit()
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Erreur lors de l'import : {e}")
        return False
        
    finally:
        cursor.close()
        conn.close()

def new_excel(file):
    df = load_data(file)
    return upload_data(df)

def get_min_max_dates():

    # Charger les variables d'environnement
    load_dotenv()

    # Connexion à la base de données Snowflake
    conn = snowflake.connector.connect(
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA')
    )

    cursor = conn.cursor()
    
    query = "SELECT MIN(departure_date), MAX(arrival_date) FROM trains"
    cursor.execute(query)

    min_date, max_date = cursor.fetchone()
    cursor.close()
    
    if min_date and max_date:
        return min_date.strftime("%d/%m/%Y"), max_date.strftime("%d/%m/%Y")
    else:
        return None, None
 
def get_trains_data(location=None):
    """Récupère depuis snowflake les données des trains pour une période donnée et retourne un DataFrame pandas"""

    # Charger les variables d'environnement
    load_dotenv()

    # Connexion à la base de données Snowflake
    conn = snowflake.connector.connect(
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA')
    )

    cursor = conn.cursor()

    query = f"SELECT * FROM trains "
    if location:
        query += f"WHERE (departure_point = '{location}' OR arrival_point = '{location}')"
    query += " ORDER BY departure_date DESC"
    # Utiliser pandas pour récupérer les données directement en DataFrame
    df = pd.read_sql(query, conn)
    
    cursor.close()
    conn.close()
    
    return df
    
def get_locations():
    """Récupère les locations des trains depuis snowflake"""
    # Charger les variables d'environnement
    load_dotenv()

    # Connexion à la base de données Snowflake
    conn = snowflake.connector.connect(
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA')
    )

    cursor = conn.cursor()
    
    query = "SELECT DISTINCT departure_point FROM trains"
    cursor.execute(query)

    locations = cursor.fetchall()
    query = "SELECT DISTINCT arrival_point FROM trains"
    cursor.execute(query)
    locations.extend(cursor.fetchall())
    # Supprimer les doublons de la liste
    locations = list(set([loc[0] for loc in locations]))
    cursor.close()
    conn.close()
    
    return locations
    
def get_events(location=None):
    """Récupère les événements depuis snowflake"""
    # Charger les variables d'environnement
    load_dotenv()
    
    # Connexion à la base de données Snowflake
    conn = snowflake.connector.connect(
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA')
    )

    cursor = conn.cursor()
    
    query = "SELECT * FROM events"
    if location:
        query += f" WHERE location = '{location}'"
    query += " ORDER BY event_date DESC"
    df = pd.read_sql(query, conn)
    
    cursor.close()
    conn.close()
    return df

def add_event(location, event_date, nb_wagons, relative, comment, type=None):
    """Ajoute un événement à la base de données snowflake"""
    # Charger les variables d'environnement
    load_dotenv()

    conn = snowflake.connector.connect(
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA')
    )

    cursor = conn.cursor()
    
    query = "INSERT INTO events (location, event_date, nb_wagons, relative, comment, type) VALUES (%s, %s, %s, %s, %s, %s)"
    cursor.execute(query, (location, event_date, nb_wagons, relative, comment, type))
    conn.commit()
    cursor.close()
    conn.close()
    return True

def update_event(event_id, location, event_date, nb_wagons, relative, comment, type=None):
    """Met à jour un événement dans la base de données snowflake"""
    # Charger les variables d'environnement
    load_dotenv()

    conn = snowflake.connector.connect(
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA')
    )

    cursor = conn.cursor()
    
    query = "UPDATE events SET location = %s, event_date = %s, nb_wagons = %s, relative = %s, comment = %s, type = %s WHERE id = %s"
    cursor.execute(query, (location, event_date, nb_wagons, relative, comment, type, event_id))
    conn.commit()
    cursor.close()
    conn.close()
    return True

def delete_event(event_id):
    """Supprime un événement de la base de données snowflake"""
    # Charger les variables d'environnement
    load_dotenv()

    conn = snowflake.connector.connect(
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA')
    )

    cursor = conn.cursor()
    
    query = "DELETE FROM events WHERE id = %s"
    cursor.execute(query, (event_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return True
    
