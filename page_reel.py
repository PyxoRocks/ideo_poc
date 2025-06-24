import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from process_data import get_locations, get_min_max_dates, get_trains_data
from compute import apply_corrections
from datetime import datetime
import pandas as pd
import pytz

def main():
    #st.title("Planification réelle")

    # Obtenir l'heure actuelle en heure française
    tz_france = pytz.timezone('Europe/Paris')
    now_france = datetime.now(tz_france)
    now_france = datetime.strptime("2025-05-20 12:00:00", "%Y-%m-%d %H:%M:%S") #fake to test
    # Convertir en datetime naïf pour compatibilité avec plotly
    now_france_naive = now_france.replace(tzinfo=None)

    # Chargement des données de base avec spinner
    with st.spinner("Chargement des données de base..."):
        locations = get_locations()
        locations.insert(0, "tous les lieux")
        min_date_str, max_date_str = get_min_max_dates()
        if min_date_str == None :
            st.error("Aucune donnée disponible, veuillez importer des données")
            return
        min_date = datetime.strptime(min_date_str, "%d/%m/%Y").date()
        max_date = datetime.strptime(max_date_str, "%d/%m/%Y").date()

    col1, col2, col3 = st.columns(3)

    with col1:
        selected_location = st.selectbox("Lieu", locations)

    with col2:
        start_date = st.date_input("Date de début", min_value=min_date, max_value=max_date, value=min_date)

    with col3:
        end_date = st.date_input("Date de fin", min_value=min_date, max_value=max_date, value=max_date)
    
    # Calculer les stocks avec les paramètres sélectionnés
    location_param = None if selected_location == "tous les lieux" else selected_location
    
    # Indicateur de chargement pour le calcul des stocks
    with st.spinner("Calcul des stocks en cours..."):
        stocks_df = apply_corrections(location_param)
    
    st.write("")

    # Créer le graphique
    if not stocks_df.empty:
        if selected_location == "tous les lieux":
            st.write("#### Évolution des stocks de wagons par lieu")
            # Graphique avec toutes les localisations
            fig = px.line(stocks_df, 
                         x='datetime', 
                         y='nombre_wagons', 
                         color='location',
                         labels={'datetime': 'Date et heure', 'nombre_wagons': 'Nombre de wagons', 'location': 'Lieu'},
                         hover_data=['location', 'nombre_wagons'],
                         line_shape='hv')  # Créneaux horizontaux-verticaux
            
        elif selected_location == "AMB":
            st.write("#### Évolution des stocks de wagons - AMB")
            fig = px.line(stocks_df, 
                         x='datetime', 
                         y='nombre_wagons', 
                         color='status',
                         labels={'datetime': 'Date et heure', 'nombre_wagons': 'Nombre de wagons', 'status': 'Statut'},
                         hover_data=['status', 'nombre_wagons'],
                         line_shape='hv')  # Créneaux horizontaux-verticaux
        else:
            st.write(f"#### Évolution des stocks de wagons - {selected_location}")

            # Graphique pour une localisation spécifique
            fig = px.line(stocks_df, 
                         x='datetime', 
                         y='nombre_wagons',
                         labels={'datetime': 'Date et heure', 'nombre_wagons': 'Nombre de wagons'},
                         hover_data=['nombre_wagons'],
                         line_shape='hv')  # Créneaux horizontaux-verticaux
        # Définir les limites de l'axe des abscisses
        fig.update_xaxes(
            range=[
                datetime.combine(start_date, datetime.min.time()),  # Date début à minuit
                datetime.combine(end_date, datetime.max.time().replace(microsecond=0))  # Date fin à 23:59:59
            ]
        )
        
        # Ajouter une ligne verticale pour l'heure actuelle
        fig.add_shape(
            type="line",
            x0=now_france_naive,
            x1=now_france_naive,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(color="red", width=2, dash="dash"),
        )
        
        # Ajouter une annotation pour l'heure actuelle
        fig.add_annotation(
            x=now_france_naive,
            y=1,
            yref="paper",
            text=f"Maintenant ({now_france_naive.strftime('%d/%m/%Y %H:%M')})",
            showarrow=False,
            bgcolor="red",
            bordercolor="red",
            borderwidth=1,
            font=dict(color="white", size=10),
            xanchor="left",
            yanchor="bottom"
        )
        
        # Personnaliser le graphique
        fig.update_layout(
            xaxis_title="Date et heure",
            yaxis_title="Nombre de wagons",
            hovermode='x unified',
            showlegend=(selected_location == "tous les lieux" or selected_location == "AMB")
        )
        
        # Améliorer l'affichage des tooltips pour un hover continu
        fig.update_traces(
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         '%{y} wagons<extra></extra>',
            hoverinfo='y+name'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Aucune donnée disponible pour la période et le lieu sélectionnés.")

    # Section pour afficher la table des données des trains
    st.write("#### Liste des trains")
    
    # Récupérer les données des trains pour la période et le lieu sélectionnés
    with st.spinner("Chargement des données des trains..."):
        trains_df = get_trains_data(location_param)
    
    if not trains_df.empty:
        # Formater les dates pour un affichage plus lisible
        trains_df_display = trains_df.copy()
        start_date = pd.Timestamp(start_date.strftime("%Y-%m-%d") + " 00:00:00")
        end_date = pd.Timestamp(end_date.strftime("%Y-%m-%d") + " 23:59:59")
        trains_df_display = trains_df_display[((trains_df_display['DEPARTURE_DATE'] >= start_date) & (trains_df_display['DEPARTURE_DATE'] <= end_date)) | ((trains_df_display['ARRIVAL_DATE'] >= start_date) & (trains_df_display['ARRIVAL_DATE'] <= end_date))]
        if 'DEPARTURE_DATE' in trains_df_display.columns:
            trains_df_display['DEPARTURE_DATE'] = pd.to_datetime(trains_df_display['DEPARTURE_DATE']).dt.strftime('%d/%m/%Y %H:%M')
        if 'ARRIVAL_DATE' in trains_df_display.columns:
            trains_df_display['ARRIVAL_DATE'] = pd.to_datetime(trains_df_display['ARRIVAL_DATE']).dt.strftime('%d/%m/%Y %H:%M')
        
        # Renommer les colonnes pour un affichage plus clair
        trains_df_display = trains_df_display.rename(columns={
            'train_id': 'ID Train',
            'departure_point': 'Point de départ',
            'arrival_point': 'Point d\'arrivée',
            'departure_date': 'Date de départ',
            'arrival_date': 'Date d\'arrivée',
            'nb_wagons': 'Nombre de wagons',
            'type': 'Type'
        })
        
        # Afficher la table avec pagination
        st.dataframe(
            trains_df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID Train": st.column_config.TextColumn("ID Train", width="medium"),
                "Point de départ": st.column_config.TextColumn("Point de départ", width="medium"),
                "Point d'arrivée": st.column_config.TextColumn("Point d'arrivée", width="medium"),
                "Date de départ": st.column_config.TextColumn("Date de départ", width="medium"),
                "Date d'arrivée": st.column_config.TextColumn("Date d'arrivée", width="medium"),
                "Nombre de wagons": st.column_config.NumberColumn("Nombre de wagons", width="small"),
                "Type": st.column_config.TextColumn("Type", width="small")
            }
        )
    else:
        st.warning("Aucune donnée de train disponible pour la période et le lieu sélectionnés.")

if __name__ == "__main__":
    main() 