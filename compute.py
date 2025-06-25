import pandas as pd
import streamlit as st
from process_data import get_cached_trains_data, get_cached_events

# Cache pour les calculs lourds
@st.cache_data(ttl=600)  # Cache pour 10 minutes
def get_cached_trains_data_for_compute(location=None):
    """Version mise en cache de get_trains_data pour les calculs"""
    return get_cached_trains_data(location)

@st.cache_data(ttl=600)  # Cache pour 10 minutes
def get_cached_events_for_compute(location=None):
    """Version mise en cache de get_events pour les calculs"""
    return get_cached_events(location)

@st.cache_data(ttl=300)  # Cache pour 5 minutes
def compute_stocks_cached(location=None):
    """Version mise en cache de compute_stocks"""
    return compute_stocks(location)

def apply_corrections(location=None):
    """Applique les corrections aux stocks avec cache"""
    # Récupérer les événements de correction avec cache
    corrections = get_cached_events_for_compute(location)
    wagons_count_df = compute_stocks_cached(location)
    
    if corrections.empty:
        return wagons_count_df
    
    # Créer une copie du dataframe pour éviter de modifier l'original
    wagons_count_df1 = wagons_count_df.copy()
    
    # Trier les corrections par date
    corrections = corrections.sort_values('EVENT_DATE').reset_index(drop=True)
    
    # Liste pour stocker toutes les nouvelles lignes de correction
    nouvelles_lignes = []
    
    # Pour chaque lieu dans les données de wagons
    for loc in wagons_count_df1['location'].unique():
        # Filtrer les corrections pour ce lieu
        loc_corrections = corrections[corrections['LOCATION'] == loc]
        
        if loc_corrections.empty:
            continue
            
        # Filtrer les données de wagons pour ce lieu
        loc_mask = wagons_count_df1['location'] == loc
        loc_data = wagons_count_df1[loc_mask].copy()

        # Pour AMB, traiter séparément les wagons vides et pleins
        if location == "AMB" and 'status' in loc_data.columns:
            # Appliquer les corrections pour chaque statut (vides/pleins)
            for status in ['vides', 'pleins']:
                status_data = loc_data[loc_data['status'] == status].copy()
                status_corrections = loc_corrections[loc_corrections['TYPE'] == ('empty' if status == 'vides' else 'full')]
                
                if status_corrections.empty:
                    continue
                
                # Appliquer les corrections chronologiquement pour ce statut
                for _, correction in status_corrections.iterrows():
                    correction_date = correction['EVENT_DATE']
                    nb_wagons = correction['NB_WAGONS']
                    is_relative = correction['RELATIVE']

                    # Trouver les indices des lignes avant et après cette date pour ce statut
                    past_mask = status_data['datetime'] < correction_date
                    future_mask = status_data['datetime'] >= correction_date

                    # Calculer la valeur avant correction
                    if past_mask.any():
                        valeur_avant = status_data[past_mask]['nombre_wagons'].iloc[-1]
                    else:
                        valeur_avant = 0

                    # Calculer la nouvelle valeur selon le type de correction
                    if is_relative:
                        # Correction relative : ajouter/soustraire le nombre de wagons
                        nouvelle_valeur = valeur_avant + nb_wagons
                        # Appliquer la correction aux données futures
                        if future_mask.any():
                            status_data.loc[future_mask, 'nombre_wagons'] += nb_wagons
                    else:
                        # Correction absolue : définir directement le nombre de wagons
                        nouvelle_valeur = nb_wagons
                        # Calculer la différence à appliquer
                        difference = nb_wagons - valeur_avant
                        # Appliquer la différence aux données futures
                        if future_mask.any():
                            status_data.loc[future_mask, 'nombre_wagons'] += difference

                    # Créer une nouvelle ligne avec la correction
                    nouvelle_ligne = {
                        'datetime': correction_date,
                        'location': loc,
                        'status': status,
                        'nombre_wagons': nouvelle_valeur
                    }
                    
                    nouvelles_lignes.append(nouvelle_ligne)
                
                # Mettre à jour les données pour ce statut
                status_mask = (loc_data['location'] == loc) & (loc_data['status'] == status)
                wagons_count_df1.loc[status_mask, 'nombre_wagons'] = status_data['nombre_wagons']
        else:
            # Pour les autres lieux, traiter toutes les corrections normalement
            # Appliquer les corrections chronologiquement
            for _, correction in loc_corrections.iterrows():
                correction_date = correction['EVENT_DATE']
                nb_wagons = correction['NB_WAGONS']
                is_relative = correction['RELATIVE']

                # Trouver les indices des lignes avant et après cette date
                past_mask = loc_data['datetime'] < correction_date
                future_mask = loc_data['datetime'] >= correction_date

                # Calculer la valeur avant correction
                if past_mask.any():
                    valeur_avant = loc_data[past_mask]['nombre_wagons'].iloc[-1]
                else:
                    valeur_avant = 0

                # Calculer la nouvelle valeur selon le type de correction
                if is_relative:
                    # Correction relative : ajouter/soustraire le nombre de wagons
                    nouvelle_valeur = valeur_avant + nb_wagons
                    # Appliquer la correction aux données futures
                    if future_mask.any():
                        loc_data.loc[future_mask, 'nombre_wagons'] += nb_wagons
                else:
                    # Correction absolue : définir directement le nombre de wagons
                    nouvelle_valeur = nb_wagons
                    # Calculer la différence à appliquer
                    difference = nb_wagons - valeur_avant
                    # Appliquer la différence aux données futures
                    if future_mask.any():
                        loc_data.loc[future_mask, 'nombre_wagons'] += difference

                # Créer une nouvelle ligne avec la correction
                nouvelle_ligne = {
                    'datetime': correction_date,
                    'location': loc,
                    'nombre_wagons': nouvelle_valeur
                }
                
                # Ajouter les colonnes supplémentaires si elles existent
                if 'status' in wagons_count_df1.columns:
                    if not loc_data.empty:
                        # S'assurer que c'est une valeur scalaire, pas une Series
                        status_values = loc_data['status'].values
                        status_value = status_values[0] if len(status_values) > 0 else None
                    else:
                        status_value = None
                    nouvelle_ligne['status'] = status_value
                
                nouvelles_lignes.append(nouvelle_ligne)
            
            # Mettre à jour le dataframe principal
            wagons_count_df1.loc[loc_mask, 'nombre_wagons'] = loc_data['nombre_wagons']
    
    # Ajouter toutes les nouvelles lignes de correction en une seule fois
    if nouvelles_lignes:
        nouvelles_lignes_df = pd.DataFrame(nouvelles_lignes)
        wagons_count_df1 = pd.concat([wagons_count_df1, nouvelles_lignes_df], ignore_index=True)
    
    # Trier le dataframe final par datetime et location
    wagons_count_df1 = wagons_count_df1.sort_values(['location', 'datetime']).reset_index(drop=True)
    
    return wagons_count_df1


def compute_stocks(location=None):
    """Calcule les stocks de wagons pour une période donnée et une localisation donnée avec optimisation"""

    # Récupérer les données des trains avec cache
    trains_data = get_cached_trains_data_for_compute(location)
    
    # Vérifier si les données sont vides
    if trains_data.empty:
        # Retourner un DataFrame vide avec les bonnes colonnes
        if location == "AMB":
            return pd.DataFrame(columns=['datetime', 'location', 'status', 'nombre_wagons'])
        else:
            return pd.DataFrame(columns=['datetime', 'location', 'nombre_wagons'])
    
    # Créer une liste pour stocker tous les événements (arrivées et départs)
    events = []

    # Optimisation : traiter les données par chunks pour éviter la surcharge mémoire
    chunk_size = 1000
    total_trains = len(trains_data)
    
    for start_idx in range(0, total_trains, chunk_size):
        end_idx = min(start_idx + chunk_size, total_trains)
        chunk_data = trains_data.iloc[start_idx:end_idx]
        
        for _, row in chunk_data.iterrows():
            departure_date = row['DEPARTURE_DATE']
            arrival_date = row['ARRIVAL_DATE']
            nb_wagons = row['NB_WAGONS']

            if pd.notna(departure_date):
                to_append = {
                    'datetime': departure_date,
                    'location': row['DEPARTURE_POINT'],
                    'train_id': row['TRAIN_ID'],
                    'event_type': 'departure',
                    'change': -nb_wagons,  # Le train quitte ce lieu
                }
                if location == "AMB":
                    to_append['status'] = "pleins" if row['TYPE'] == "Chargés" else "vides"
                events.append(to_append)

            if pd.notna(arrival_date):
                to_append = {
                    'datetime': arrival_date,
                    'location': row['ARRIVAL_POINT'],
                    'train_id': row['TRAIN_ID'],
                    'event_type': 'arrival',
                    'change': nb_wagons,  # Le train arrive dans ce lieu
                }
                if location == "AMB":
                    to_append['status'] = "pleins" if row['TYPE'] == "Evac" else "vides"
                events.append(to_append)

    # Vérifier si des événements ont été créés
    if not events:
        # Retourner un DataFrame vide avec les bonnes colonnes
        if location == "AMB":
            return pd.DataFrame(columns=['datetime', 'location', 'status', 'nombre_wagons'])
        else:
            return pd.DataFrame(columns=['datetime', 'location', 'nombre_wagons'])

    # Convertir en DataFrame et trier par datetime
    events_df = pd.DataFrame(events)
    
    # Supprimer les doublons exacts (même train, même lieu, même datetime, même type)
    if location == "AMB":
        events_df = events_df.drop_duplicates(subset=['datetime', 'location', 'train_id', 'event_type', 'status']).reset_index(drop=True)
    else:
        events_df = events_df.drop_duplicates(subset=['datetime', 'location', 'train_id', 'event_type']).reset_index(drop=True)
    
    # Vérifier si le DataFrame n'est pas vide après suppression des doublons
    if events_df.empty:
        if location == "AMB":
            return pd.DataFrame(columns=['datetime', 'location', 'status', 'nombre_wagons'])
        else:
            return pd.DataFrame(columns=['datetime', 'location', 'nombre_wagons'])
    
    events_df = events_df.sort_values(['location', 'datetime']).reset_index(drop=True)

    # Calculer le nombre cumulé de trains par lieu et datetime
    if location == "AMB":
        events_df['cumulative_wagons'] = events_df.groupby(['location', 'status'])['change'].cumsum()
    else:
        events_df['cumulative_wagons'] = events_df.groupby('location')['change'].cumsum()

    # Créer le dataframe final avec le nombre de trains à chaque moment et lieu
    if location == "AMB":
        train_count_df = events_df[['datetime', 'location', 'status', 'cumulative_wagons']].copy()
        train_count_df = train_count_df.rename(columns={'cumulative_wagons': 'nombre_wagons'})
    else:
        train_count_df = events_df[['datetime', 'location', 'cumulative_wagons']].copy()
        train_count_df = train_count_df.rename(columns={'cumulative_wagons': 'nombre_wagons'})

    if location:
        train_count_df = train_count_df[train_count_df['location'] == location]
    
    return train_count_df