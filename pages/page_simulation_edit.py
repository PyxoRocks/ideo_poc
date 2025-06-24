import streamlit as st
import pandas as pd
from datetime import datetime
from process_data import get_locations, get_min_max_dates, get_trains_data

def format_date(date_value):
    """Formate une date pour l'affichage"""
    if pd.isna(date_value):
        return "Date inconnue"
    if isinstance(date_value, str):
        try:
            date_value = pd.to_datetime(date_value)
        except:
            return date_value
    return date_value.strftime('%d/%m/%Y à %H:%M')

def main():
    st.title("🎯 Édition de simulation")
    
    # Récupération des paramètres de session
    simulation_id = st.session_state.get('simulation_id', None)
    simulation_name = st.session_state.get('simulation_name', 'Nouvelle simulation')
    
    # Affichage du nom de la simulation
    st.subheader(f"📝 {simulation_name}")
    
    # Obtenir les données pour les sélecteurs
    locations = get_locations()
    locations.insert(0, "tous les lieux")
    min_date_str, max_date_str = get_min_max_dates()
    
    if min_date_str is None:
        st.error("Aucune donnée disponible, veuillez importer des données")
        return
        
    min_date = datetime.strptime(min_date_str, "%d/%m/%Y").date()
    max_date = datetime.strptime(max_date_str, "%d/%m/%Y").date()

    # Les 3 sélecteurs comme dans page_reel
    col1, col2, col3 = st.columns(3)

    with col1:
        selected_location = st.selectbox("Lieu", locations, index=0)  # "tous les lieux" par défaut

    with col2:
        start_date = st.date_input("Date de début", min_value=min_date, max_value=max_date, value=min_date)

    with col3:
        end_date = st.date_input("Date de fin", min_value=min_date, max_value=max_date, value=max_date)
    
    st.markdown("---")
    
    # Section liste des trains
    st.subheader("🚂 Liste des trains")
    
    # Récupérer les données des trains pour la période et le lieu sélectionnés
    location_param = None if selected_location == "tous les lieux" else selected_location
    trains_df = get_trains_data(location_param)
    
    if not trains_df.empty:
        # Filtrer par dates
        start_date_ts = pd.Timestamp(start_date.strftime("%Y-%m-%d") + " 00:00:00")
        end_date_ts = pd.Timestamp(end_date.strftime("%Y-%m-%d") + " 23:59:59")
        
        trains_df_filtered = trains_df[
            ((trains_df['DEPARTURE_DATE'] >= start_date_ts) & (trains_df['DEPARTURE_DATE'] <= end_date_ts)) | 
            ((trains_df['ARRIVAL_DATE'] >= start_date_ts) & (trains_df['ARRIVAL_DATE'] <= end_date_ts))
        ]
        
        if not trains_df_filtered.empty:
            # Affichage compact des trains sur une seule ligne
            for idx, train in trains_df_filtered.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div style="
                        display: flex;
                        align-items: center;
                        border-bottom: 1px solid #eee;
                        padding: 6px 0;
                        font-size: 15px;
                        min-height: 36px;
                    ">
                        <div style="flex: 0 0 110px; font-weight: bold; color: #2c3e50;">Train {train['TRAIN_ID']}</div>
                        <div style="flex: 0 0 220px; margin-left: 10px;">
                            <span style='color:#888;'>Départ:</span> {train['DEPARTURE_POINT']} - {format_date(train['DEPARTURE_DATE'])}
                        </div>
                        <div style="flex: 0 0 220px; margin-left: 10px;">
                            <span style='color:#888;'>Arrivée:</span> {train['ARRIVAL_POINT']} - {format_date(train['ARRIVAL_DATE'])}
                        </div>
                        <div style="flex: 0 0 90px; margin-left: 10px;">
                            <span style='color:#888;'>Wagons:</span> {train['NB_WAGONS']}
                        </div>
                        <div style="flex: 0 0 70px; margin-left: 10px;">
                            <span style='color:#888;'>Type:</span> {train['TYPE']}
                        </div>
                        <div style="flex: 1 1 auto;"></div>
                        <div style="display: flex; gap: 8px;">
                            <form action="#" method="post" style="display:inline;">
                                <button type="button" style="background: #f1f1f1; border: none; border-radius: 4px; padding: 4px 10px; cursor: pointer;">✏️ Modifier</button>
                            </form>
                            <form action="#" method="post" style="display:inline;">
                                <button type="button" style="background: #f1f1f1; border: none; border-radius: 4px; padding: 4px 10px; cursor: pointer;">🗑️ Supprimer</button>
                            </form>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("Aucun train trouvé pour la période et le lieu sélectionnés.")
    else:
        st.warning("Aucune donnée de train disponible.")

if __name__ == "__main__":
    main() 