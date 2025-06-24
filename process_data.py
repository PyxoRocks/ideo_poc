import pandas as pd
import snowflake.connector
import os
from dotenv import load_dotenv # Gardez ceci pour le développement local
import streamlit as st # Importez streamlit
from snowflake.snowpark.context import get_active_session # Importez pour la session Snowflake
from snowflake.snowpark.session import Session
from snowflake.snowpark.types import StructType, StructField, StringType, TimestampType, IntegerType

# --- Nouvelle fonction utilitaire pour la connexion à Snowflake ---
def get_snowflake_connection_or_session():
    """
    Établit et retourne une connexion à Snowflake.
    Utilise la session active si l'application tourne dans Snowflake,
    sinon utilise les variables d'environnement pour une exécution locale.
    """
    try:
        # Tente d'obtenir la session active de Snowpark (indique que nous sommes dans Snowflake)
        session = get_active_session()
        return session
        
    except Exception as e:
        # Si l'exception est levée, nous ne sommes probablement pas dans l'environnement Snowflake.
        # On suppose une exécution locale, donc on charge les variables d'environnement.
        load_dotenv()
        try:
            conn = snowflake.connector.connect(
                user=os.getenv('SNOWFLAKE_USER'),
                password=os.getenv('SNOWFLAKE_PASSWORD'),
                account=os.getenv('SNOWFLAKE_ACCOUNT'),
                warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
                database=os.getenv('SNOWFLAKE_DATABASE'),
                schema=os.getenv('SNOWFLAKE_SCHEMA')
            )
            return conn
        except Exception as local_e:
            st.error(f"Erreur de connexion locale à Snowflake : {local_e}")
            raise local_e

# --- Votre code existant, modifié pour utiliser get_snowflake_connection_or_session ---

def load_data(file_path="excel_files/excel_poc.xlsx"):
    """Charge et traite les données du fichier Excel"""
    # Lire les 4 onglets du fichier Excel

    xls = pd.ExcelFile(file_path)
    df = pd.DataFrame()

    for sheet_name in ["Chargés", "Vides", "Appro", "Evac"]:
        df_temp = pd.read_excel(xls, sheet_name=sheet_name)[[
            "Train Id", "Point départ", "Point arrivée", "Date départ théorique",
            "Date départ replanifiée", "Date départ réelle", "Date arrivée théorique",
            "Date arrivée replanifiée", "Date arrivée réelle", "Nb Théo.", "Nb Comm.", "Nb Réel"
        ]]
        df_temp = df_temp.rename(mapper={
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
        }, axis='columns')
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
    db_handle = get_snowflake_connection_or_session()

    try:
        # Obtenir les dates couvertes par l'Excel
        min_date = df['departure_date'].min()
        max_date = df['departure_date'].max()

        # Formater les dates pour Snowflake
        min_date_str = min_date.strftime('%Y-%m-%d %H:%M:%S')
        max_date_str = max_date.strftime('%Y-%m-%d %H:%M:%S')

        if isinstance(db_handle, Session):
            # Environnement Snowflake - utiliser Snowpark
            # Supprimer les données existantes pour les jours couverts par l'Excel
            delete_query = f"""
            DELETE FROM trains
            WHERE departure_date >= '{min_date_str}' AND departure_date <= '{max_date_str}'
            """
            db_handle.sql(delete_query).collect()

            # Insérer les nouvelles données en utilisant write_pandas
            db_handle.write_pandas(
                df, 
                table_name='trains', 
                table_type='table', 
                overwrite=False,
                auto_create_table=False
            )
            
        else:
            # Environnement local - utiliser snowflake.connector
            cursor = db_handle.cursor()

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
            db_handle.commit()

        return True

    except Exception as e:
        if not isinstance(db_handle, Session):
            db_handle.rollback()
        print(f"Erreur lors de l'import : {e}")
        return False

    finally:
        if not isinstance(db_handle, Session):
            cursor.close()
            db_handle.close()

def new_excel(file):
    df = load_data(file)
    return upload_data(df)

def get_min_max_dates():
    db_handle = get_snowflake_connection_or_session()

    try:
        query = "SELECT MIN(departure_date), MAX(arrival_date) FROM trains"
        
        if isinstance(db_handle, Session):
            # Environnement Snowflake - utiliser Snowpark
            result = db_handle.sql(query).collect()
            min_date, max_date = result[0]
        else:
            # Environnement local - utiliser snowflake.connector
            cursor = db_handle.cursor()
            cursor.execute(query)
            min_date, max_date = cursor.fetchone()
            cursor.close()
            db_handle.close()
        
        if min_date and max_date:
            return min_date.strftime("%d/%m/%Y"), max_date.strftime("%d/%m/%Y")
        else:
            return None, None
            
    except Exception as e:
        if not isinstance(db_handle, Session):
            db_handle.close()
        print(f"Erreur lors de la récupération des dates : {e}")
        return None, None

def get_trains_data(location=None):
    """Récupère depuis snowflake les données des trains pour une période donnée et retourne un DataFrame pandas"""
    db_handle = get_snowflake_connection_or_session()

    try:
        query = f"SELECT * FROM trains "
        if location:
            query += f"WHERE (departure_point = '{location}' OR arrival_point = '{location}')"
        query += " ORDER BY departure_date DESC"
        
        if isinstance(db_handle, Session):
            # Environnement Snowflake - utiliser Snowpark
            df = db_handle.sql(query).to_pandas()
        else:
            # Environnement local - utiliser pandas read_sql
            df = pd.read_sql(query, db_handle)
            db_handle.close()
        
        return df
        
    except Exception as e:
        if not isinstance(db_handle, Session):
            db_handle.close()
        print(f"Erreur lors de la récupération des données trains : {e}")
        return pd.DataFrame()

def get_locations():
    """Récupère les locations des trains depuis snowflake"""
    db_handle = get_snowflake_connection_or_session()

    try:
        if isinstance(db_handle, Session):
            # Environnement Snowflake - utiliser Snowpark
            query_departure = "SELECT DISTINCT departure_point FROM trains"
            query_arrival = "SELECT DISTINCT arrival_point FROM trains"
            
            departure_locations = db_handle.sql(query_departure).collect()
            arrival_locations = db_handle.sql(query_arrival).collect()
            
            locations = [loc[0] for loc in departure_locations] + [loc[0] for loc in arrival_locations]
        else:
            # Environnement local - utiliser snowflake.connector
            cursor = db_handle.cursor()
            
            query = "SELECT DISTINCT departure_point FROM trains"
            cursor.execute(query)
            locations = cursor.fetchall()
            
            query = "SELECT DISTINCT arrival_point FROM trains"
            cursor.execute(query)
            locations.extend(cursor.fetchall())
            
            locations = [loc[0] for loc in locations]
            cursor.close()
            db_handle.close()
        
        # Supprimer les doublons de la liste
        locations = list(set(locations))
        return locations
        
    except Exception as e:
        if not isinstance(db_handle, Session):
            db_handle.close()
        print(f"Erreur lors de la récupération des locations : {e}")
        return []

def get_events(location=None):
    """Récupère les événements depuis snowflake"""
    db_handle = get_snowflake_connection_or_session()

    try:
        query = "SELECT * FROM events"
        if location:
            query += f" WHERE location = '{location}'"
        query += " ORDER BY event_date DESC"
        
        if isinstance(db_handle, Session):
            # Environnement Snowflake - utiliser Snowpark
            df = db_handle.sql(query).to_pandas()
        else:
            # Environnement local - utiliser pandas read_sql
            df = pd.read_sql(query, db_handle)
            db_handle.close()
        
        return df
        
    except Exception as e:
        if not isinstance(db_handle, Session):
            db_handle.close()
        print(f"Erreur lors de la récupération des événements : {e}")
        return pd.DataFrame()

def add_event(location, event_date, nb_wagons, relative, comment, type=None):
    """Ajoute un événement à la base de données snowflake"""
    db_handle = get_snowflake_connection_or_session()

    try:
        if isinstance(db_handle, Session):
            # Environnement Snowflake - utiliser Snowpark
            query = "INSERT INTO events (location, event_date, nb_wagons, relative, comment, type) VALUES (?, ?, ?, ?, ?, ?)"
            db_handle.sql(query, params=[location, event_date, nb_wagons, relative, comment, type]).collect()
        else:
            # Environnement local - utiliser snowflake.connector
            cursor = db_handle.cursor()
            query = "INSERT INTO events (location, event_date, nb_wagons, relative, comment, type) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(query, (location, event_date, nb_wagons, relative, comment, type))
            db_handle.commit()
            cursor.close()
            db_handle.close()
        
        return True
        
    except Exception as e:
        if not isinstance(db_handle, Session):
            db_handle.rollback()
            db_handle.close()
        print(f"Erreur lors de l'ajout de l'événement : {e}")
        return False

def update_event(event_id, location, event_date, nb_wagons, relative, comment, type=None):
    """Met à jour un événement dans la base de données snowflake"""
    db_handle = get_snowflake_connection_or_session()

    try:
        if isinstance(db_handle, Session):
            # Environnement Snowflake - utiliser Snowpark
            query = "UPDATE events SET location = ?, event_date = ?, nb_wagons = ?, relative = ?, comment = ?, type = ? WHERE id = ?"
            db_handle.sql(query, params=[location, event_date, nb_wagons, relative, comment, type, event_id]).collect()
        else:
            # Environnement local - utiliser snowflake.connector
            cursor = db_handle.cursor()
            query = "UPDATE events SET location = %s, event_date = %s, nb_wagons = %s, relative = %s, comment = %s, type = %s WHERE id = %s"
            cursor.execute(query, (location, event_date, nb_wagons, relative, comment, type, event_id))
            db_handle.commit()
            cursor.close()
            db_handle.close()
        
        return True
        
    except Exception as e:
        if not isinstance(db_handle, Session):
            db_handle.rollback()
            db_handle.close()
        print(f"Erreur lors de la mise à jour de l'événement : {e}")
        return False

def delete_event(event_id):
    """Supprime un événement de la base de données snowflake"""
    db_handle = get_snowflake_connection_or_session()

    try:
        if isinstance(db_handle, Session):
            # Environnement Snowflake - utiliser Snowpark
            query = "DELETE FROM events WHERE id = ?"
            db_handle.sql(query, params=[event_id]).collect()
        else:
            # Environnement local - utiliser snowflake.connector
            cursor = db_handle.cursor()
            query = "DELETE FROM events WHERE id = %s"
            cursor.execute(query, (event_id,))
            db_handle.commit()
            cursor.close()
            db_handle.close()
        
        return True
        
    except Exception as e:
        if not isinstance(db_handle, Session):
            db_handle.rollback()
            db_handle.close()
        print(f"Erreur lors de la suppression de l'événement : {e}")
        return False