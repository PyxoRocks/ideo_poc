import streamlit as st
import pandas as pd
from datetime import datetime
from process_data import get_simulations, get_cached_locations, get_cached_min_max_dates, get_cached_trains_data, add_simulation, delete_simulation, get_sim_events, add_sim_event, delete_sim_event

# Cache pour les événements de simulation
@st.cache_data(ttl=300)  # Cache pour 5 minutes
def get_cached_sim_events(simulation_id):
    """Version mise en cache de get_sim_events"""
    return get_sim_events(simulation_id)

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

def show_simulation_edit():
    """Affiche l'interface d'édition de simulation"""
    
    # Récupération des paramètres de session
    simulation_id = st.session_state.get('simulation_id', None)
    simulation_name = st.session_state.get('simulation_name', 'Nouvelle simulation')
    
    # Si on ouvre une simulation existante, définir current_simulation_id
    if simulation_id and 'current_simulation_id' not in st.session_state:
        st.session_state.current_simulation_id = simulation_id
    
    # Charger les événements de simulation si on a un simulation_id avec cache
    sim_events_df = pd.DataFrame()
    if simulation_id:
        sim_events_df = get_cached_sim_events(simulation_id)
        # Pour le moment, on ne l'utilise pas mais on l'a chargé
    
    col1, col2, col3 = st.columns(3)

    with col1:
        # Bouton retour
        if st.button("← Retour à la liste des simulations"):
            # Nettoyer les paramètres de session
            if 'simulation_id' in st.session_state:
                del st.session_state.simulation_id
            if 'simulation_name' in st.session_state:
                del st.session_state.simulation_name
            if 'current_simulation_id' in st.session_state:
                del st.session_state.current_simulation_id
            st.rerun()
    
    with col2:
        # Affichage du nom de la simulation
        st.header(simulation_name)

    with col3:
        st.write("futur lanceement de la simulation")

    if len(sim_events_df) != 0:
        st.markdown("---")
        st.subheader("Événements de simulation")
        
        # Affichage de la liste des événements de simulation
        # Titres de colonnes
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1.5, 2, 1.5, 1.5, 1.5, 1.5, 1, 0.5])
        with col1:
            st.write("**Type**")
        with col2:
            st.write("**ID Train**")
        with col3:
            st.write("**Trajet**")
        with col4:
            st.write("**Départ**")
        with col5:
            st.write("**Arrivée**")
        with col6:
            st.write("**Wagons/Type**")
        with col7:
            st.write("**Supprimer**")
        with col8:
            st.write("")  # Espace vide pour aligner

        # Affichage des événements sous forme compacte
        for idx, event in sim_events_df.iterrows():
            with st.container():
                col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1.5, 2, 1.5, 1.5, 1.5, 1.5, 1, 0.5])
                
                with col1:
                    # Afficher le type de modification avec une icône
                    modification_type = event.get('MODIFICATION_TYPE', 'unknown')
                    if modification_type == 'added':
                        st.write("➕ Ajouté")
                    elif modification_type == 'modified':
                        st.write("✏️ Modifié")
                    elif modification_type == 'deleted':
                        st.write("🗑️ Supprimé")
                    else:
                        st.write(modification_type)
                
                with col2:
                    train_id = event.get('TRAIN_ID', None)
                    st.write(f"{train_id if pd.notna(train_id) else 'N/A'}")
                
                with col3:
                    departure_point = event.get('DEPARTURE_POINT', None)
                    arrival_point = event.get('ARRIVAL_POINT', None)
                    if pd.notna(departure_point) and pd.notna(arrival_point):
                        st.write(f"{departure_point} → {arrival_point}")
                    else:
                        st.write("N/A")
                
                with col4:
                    departure_time = event.get('DEPARTURE_TIME', None)
                    if pd.notna(departure_time):
                        st.write(f"{format_date(departure_time)}")
                    else:
                        st.write("N/A")
                
                with col5:
                    arrival_time = event.get('ARRIVAL_TIME', None)
                    if pd.notna(arrival_time):
                        st.write(f"{format_date(arrival_time)}")
                    else:
                        st.write("N/A")
                
                with col6:
                    nb_wagons = event.get('NB_WAGONS', None)
                    if pd.notna(nb_wagons):
                        nb_wagons = int(nb_wagons)
                    is_empty = event.get('IS_EMPTY', None)
                    if pd.notna(nb_wagons):
                        wagon_type = "Vides" if is_empty else "Chargés"
                        st.write(f"{nb_wagons} - {wagon_type}")
                    else:
                        st.write("N/A")
                
                with col7:
                    if st.button(f"🗑️", key=f"delete_event_{idx}", help="Retirer cet événement de la simulation"):
                        # Supprimer l'événement de la base de données en utilisant tous les critères
                        with st.spinner("Suppression de l'événement..."):
                            success = delete_sim_event(
                                simulation_id=simulation_id,
                                modification_type=event.get('MODIFICATION_TYPE'),
                                train_id=event.get('TRAIN_ID'),
                                departure_time=event.get('DEPARTURE_TIME'),
                                arrival_time=event.get('ARRIVAL_TIME'),
                                departure_point=event.get('DEPARTURE_POINT'),
                                arrival_point=event.get('ARRIVAL_POINT'),
                                nb_wagons=event.get('NB_WAGONS'),
                                is_empty=event.get('IS_EMPTY')
                            )
                        
                        if success:
                            st.rerun()
                        else:
                            st.error(f"❌ Erreur lors de la suppression de l'événement")
                
                with col8:
                    st.write("")  # Espace vide
    
    # Obtenir les données pour les sélecteurs avec cache
    locations = get_cached_locations()
    locations.insert(0, "tous les lieux")
    min_date_str, max_date_str = get_cached_min_max_dates()
    
    if min_date_str is None:
        st.error("Aucune donnée disponible, veuillez importer des données")
        return
        
    min_date = datetime.strptime(min_date_str, "%d/%m/%Y").date()
    max_date = datetime.strptime(max_date_str, "%d/%m/%Y").date()

    st.markdown("---")
    
    # Section liste des trains
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("🚂 Liste des trains")
    with col2:
        if st.button("➕ Ajouter un train", use_container_width=True):
            st.session_state.show_add_train_form = True
            st.rerun()
    
    # Formulaire d'ajout de train (modal-like)
    if st.session_state.get('show_add_train_form', False):
        st.markdown("---")
        
        # Utiliser un conteneur avec style pour un formulaire compact
        with st.container():
            st.markdown("##### Ajout d'un train à la simulation")
            
            # Obtenir les lieux disponibles (sans "tous les lieux")
            with st.spinner("Chargement des lieux..."):
                train_locations = get_cached_locations()
            
            # Formulaire compact en 4 colonnes
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                departure_point = st.selectbox("Départ", train_locations, key="form_departure")
                arrival_point = st.selectbox("Arrivée", train_locations, key="form_arrival")
            
            with col2:
                departure_date = st.date_input("Date départ", min_value=min_date, max_value=max_date, value=min_date, key="form_departure_date")
                arrival_date = st.date_input("Date arrivée", min_value=min_date, max_value=max_date, value=min_date, key="form_arrival_date")
            
            with col3:
                # Heures avec input text pour plus de précision
                departure_time_str = st.text_input("Heure départ (HH:MM)", value="08:00", key="form_departure_time", help="Format HH:MM (ex: 08:30)")
                arrival_time_str = st.text_input("Heure arrivée (HH:MM)", value="10:00", key="form_arrival_time", help="Format HH:MM (ex: 10:15)")
            
            with col4:
                nb_wagons = st.number_input("Wagons", min_value=1, max_value=50, value=10, key="form_wagons")
                st.write("")
                is_empty = st.checkbox("Wagons vides", key="form_empty")
            
            # Boutons d'action en ligne
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button("✅ Confirmer", key="confirm_add_train", use_container_width=True):
                    # Valider le format des heures
                    try:
                        departure_time = datetime.strptime(departure_time_str, "%H:%M").time()
                        arrival_time = datetime.strptime(arrival_time_str, "%H:%M").time()
                    except ValueError:
                        st.error("❌ Format d'heure invalide. Utilisez HH:MM (ex: 08:30)")
                        return
                    
                    # Combiner date et heure pour les timestamps
                    departure_datetime = datetime.combine(departure_date, departure_time)
                    arrival_datetime = datetime.combine(arrival_date, arrival_time)
                    
                    # Appeler add_sim_event
                    success = add_sim_event(
                        simulation_id=simulation_id,
                        modification_type="added",
                        train_id=None,
                        departure_time=departure_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                        arrival_time=arrival_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                        departure_point=departure_point,
                        arrival_point=arrival_point,
                        nb_wagons=nb_wagons,
                        is_empty=is_empty
                    )
                    
                    if success:
                        st.success("✅ Train ajouté avec succès à la simulation")
                        # Nettoyer le formulaire
                        del st.session_state.show_add_train_form
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de l'ajout du train")
            
            with col2:
                if st.button("❌ Annuler", key="cancel_add_train", use_container_width=True):
                    del st.session_state.show_add_train_form
                    st.rerun()
            
            with col3:
                st.write("")  # Espace vide
            
            with col4:
                st.write("")  # Espace vide
        
        st.markdown("---")
    
    # Affichage de la liste des trains (APRÈS le formulaire)

        # Les 3 sélecteurs comme dans page_reel
    col1, col2, col3 = st.columns(3)

    with col1:
        selected_location = st.selectbox("Lieu", locations, index=0)  # "tous les lieux" par défaut

    with col2:
        start_date = st.date_input("Date de début", min_value=min_date, max_value=max_date, value=min_date)

    with col3:
        end_date = st.date_input("Date de fin", min_value=min_date, max_value=max_date, value=max_date)
    
    
    # Récupérer les données des trains pour la période et le lieu sélectionnés (AVANT le formulaire)
    location_param = None if selected_location == "tous les lieux" else selected_location
    trains_df = get_cached_trains_data(location_param)


    if not trains_df.empty:
        # Filtrer par dates
        start_date_ts = pd.Timestamp(start_date.strftime("%Y-%m-%d") + " 00:00:00")
        end_date_ts = pd.Timestamp(end_date.strftime("%Y-%m-%d") + " 23:59:59")
        
        trains_df_filtered = trains_df[
            ((trains_df['DEPARTURE_DATE'] >= start_date_ts) & (trains_df['DEPARTURE_DATE'] <= end_date_ts)) | 
            ((trains_df['ARRIVAL_DATE'] >= start_date_ts) & (trains_df['ARRIVAL_DATE'] <= end_date_ts))
        ]
        
        if not trains_df_filtered.empty:
            # Titres de colonnes
            col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 2, 1.5, 1.5, 1.5, 1, 1])
            with col1:
                st.write("**ID Train**")
            with col2:
                st.write("**Trajet**")
            with col3:
                st.write("**Départ**")
            with col4:
                st.write("**Arrivée**")
            with col5:
                st.write("**Wagons/Type**")
            with col6:
                st.write("**Modifier**")
            with col7:
                st.write("**Supprimer**")

            # Affichage des trains sous forme compacte sur une seule ligne
            for idx, train in trains_df_filtered.iterrows():
                # Création d'un conteneur compact pour chaque train
                with st.container():
                    # Utiliser des colonnes pour un affichage horizontal compact
                    col1, col2, col3, col4, col5, col6, col7= st.columns([2, 2, 1.5, 1.5, 1.5, 1, 1])
                    
                    with col1:
                        st.write(f"{train['TRAIN_ID']}")
                    with col2:
                        st.write(f"{train['DEPARTURE_POINT']} → {train['ARRIVAL_POINT']}")
                    with col3:
                        st.write(f"{format_date(train['DEPARTURE_DATE'])}")
                    with col4:
                        st.write(f"{format_date(train['ARRIVAL_DATE'])}")
                    with col5:
                        st.write(f"{train['NB_WAGONS']} - {train['TYPE']}")
                    with col6:
                        if st.button(f"✏️", key=f"edit_train_{idx}", help="Modifier"):
                            # Stocker les informations du train à modifier
                            st.session_state.edit_train_id = train['TRAIN_ID']
                            st.session_state.edit_departure_point = train['DEPARTURE_POINT']
                            st.session_state.edit_arrival_point = train['ARRIVAL_POINT']
                            st.session_state.edit_departure_date = train['DEPARTURE_DATE'].date() if pd.notna(train['DEPARTURE_DATE']) else min_date
                            st.session_state.edit_arrival_date = train['ARRIVAL_DATE'].date() if pd.notna(train['ARRIVAL_DATE']) else min_date
                            st.session_state.edit_departure_time = train['DEPARTURE_DATE'].strftime('%H:%M') if pd.notna(train['DEPARTURE_DATE']) else "08:00"
                            st.session_state.edit_arrival_time = train['ARRIVAL_DATE'].strftime('%H:%M') if pd.notna(train['ARRIVAL_DATE']) else "10:00"
                            st.session_state.edit_nb_wagons = train['NB_WAGONS']
                            st.session_state.edit_is_empty = train['TYPE'] in ['Vides', 'Evac']  # Wagons vides si type est Vides ou Evac
                            st.session_state.show_edit_train_form = True
                            st.session_state.edit_train_index = idx  # Stocker l'index du train modifié
                            st.rerun()
                    with col7:
                        if st.button(f"🗑️", key=f"delete_train_{idx}", help="Supprimer"):
                            # Ajouter directement un événement de suppression avec les informations du train
                            success = add_sim_event(
                                simulation_id=simulation_id,
                                modification_type="deleted",
                                train_id=train['TRAIN_ID'],
                                departure_time=train['DEPARTURE_DATE'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(train['DEPARTURE_DATE']) else None,
                                arrival_time=train['ARRIVAL_DATE'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(train['ARRIVAL_DATE']) else None,
                                departure_point=train['DEPARTURE_POINT'],
                                arrival_point=train['ARRIVAL_POINT'],
                                nb_wagons=train['NB_WAGONS'],
                                is_empty=train['TYPE'] in ['Vides', 'Evac']  # Wagons vides si type est Vides ou Evac
                            )
                            
                            if success:
                                st.success(f"✅ Train {train['TRAIN_ID']} supprimé de la simulation")
                                st.rerun()
                            else:
                                st.error(f"❌ Erreur lors de la suppression du train {train['TRAIN_ID']}")
                
                # Formulaire de modification sous le train sélectionné
                if (st.session_state.get('show_edit_train_form', False) and 
                    st.session_state.get('edit_train_index') == idx):
                    
                    st.markdown("---")
                    
                    # Utiliser un conteneur avec style pour un formulaire compact
                    with st.container():
                        st.markdown("##### Modification du train")
                        
                        # Obtenir les lieux disponibles (sans "tous les lieux")
                        train_locations = get_cached_locations()
                        
                        # Formulaire compact en 4 colonnes
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            departure_point = st.selectbox(
                                "Départ", 
                                train_locations, 
                                index=train_locations.index(st.session_state.edit_departure_point) if st.session_state.edit_departure_point in train_locations else 0,
                                key="edit_form_departure"
                            )
                            arrival_point = st.selectbox(
                                "Arrivée", 
                                train_locations, 
                                index=train_locations.index(st.session_state.edit_arrival_point) if st.session_state.edit_arrival_point in train_locations else 0,
                                key="edit_form_arrival"
                            )
                        
                        with col2:
                            departure_date = st.date_input(
                                "Date départ", 
                                min_value=min_date, 
                                max_value=max_date, 
                                value=st.session_state.edit_departure_date,
                                key="edit_form_departure_date"
                            )
                            arrival_date = st.date_input(
                                "Date arrivée", 
                                min_value=min_date, 
                                max_value=max_date, 
                                value=st.session_state.edit_arrival_date,
                                key="edit_form_arrival_date"
                            )
                        
                        with col3:
                            # Heures avec input text pour plus de précision
                            departure_time_str = st.text_input(
                                "Heure départ (HH:MM)", 
                                value=st.session_state.edit_departure_time, 
                                key="edit_form_departure_time", 
                                help="Format HH:MM (ex: 08:30)"
                            )
                            arrival_time_str = st.text_input(
                                "Heure arrivée (HH:MM)", 
                                value=st.session_state.edit_arrival_time, 
                                key="edit_form_arrival_time", 
                                help="Format HH:MM (ex: 10:15)"
                            )
                        
                        with col4:
                            nb_wagons = st.number_input(
                                "Wagons", 
                                min_value=1, 
                                max_value=50, 
                                value=st.session_state.edit_nb_wagons,
                                key="edit_form_wagons"
                            )
                            st.write("")
                            is_empty = st.checkbox(
                                "Wagons vides", 
                                value=st.session_state.edit_is_empty,
                                key="edit_form_empty"
                            )
                        
                        # Boutons d'action en ligne
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            if st.button("✅ Confirmer", key="confirm_edit_train", use_container_width=True):
                                # Valider le format des heures
                                try:
                                    departure_time = datetime.strptime(departure_time_str, "%H:%M").time()
                                    arrival_time = datetime.strptime(arrival_time_str, "%H:%M").time()
                                except ValueError:
                                    st.error("❌ Format d'heure invalide. Utilisez HH:MM (ex: 08:30)")
                                    return
                                
                                # Combiner date et heure pour les timestamps
                                departure_datetime = datetime.combine(departure_date, departure_time)
                                arrival_datetime = datetime.combine(arrival_date, arrival_time)
                                
                                # Appeler add_sim_event avec modification_type="modified"
                                success = add_sim_event(
                                    simulation_id=simulation_id,
                                    modification_type="modified",
                                    train_id=st.session_state.edit_train_id,
                                    departure_time=departure_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                                    arrival_time=arrival_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                                    departure_point=departure_point,
                                    arrival_point=arrival_point,
                                    nb_wagons=nb_wagons,
                                    is_empty=is_empty
                                )
                                
                                if success:
                                    st.success("✅ Train modifié avec succès dans la simulation")
                                    # Nettoyer le formulaire
                                    del st.session_state.show_edit_train_form
                                    # Nettoyer les variables de modification
                                    for key in ['edit_train_id', 'edit_departure_point', 'edit_arrival_point', 
                                               'edit_departure_date', 'edit_arrival_date', 'edit_departure_time', 
                                               'edit_arrival_time', 'edit_nb_wagons', 'edit_is_empty', 'edit_train_index']:
                                        if key in st.session_state:
                                            del st.session_state[key]
                                    st.rerun()
                                else:
                                    st.error("❌ Erreur lors de la modification du train")
                        
                        with col2:
                            if st.button("❌ Annuler", key="cancel_edit_train", use_container_width=True):
                                del st.session_state.show_edit_train_form
                                # Nettoyer les variables de modification
                                for key in ['edit_train_id', 'edit_departure_point', 'edit_arrival_point', 
                                           'edit_departure_date', 'edit_arrival_date', 'edit_departure_time', 
                                           'edit_arrival_time', 'edit_nb_wagons', 'edit_is_empty', 'edit_train_index']:
                                    if key in st.session_state:
                                        del st.session_state[key]
                                st.rerun()
                        
                        with col3:
                            st.write("")  # Espace vide
                        
                        with col4:
                            st.write("")  # Espace vide
                    
                    st.markdown("---")
                    
                    # Ligne de séparation fine
                    #st.markdown("<hr style='margin: 5px 0; border: 0.5px solid #ddd;'>", unsafe_allow_html=True)
        else:
            st.info("Aucun train trouvé pour la période et le lieu sélectionnés.")
    else:
        st.warning("Aucune donnée de train disponible.")

def show_simulation_list():
    """Affiche la liste des simulations"""
    st.title("🎯 Simulations")
    
    # Bouton pour créer une nouvelle simulation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("➕ Créer une nouvelle simulation", use_container_width=True):
            # Définir les paramètres de session pour une nouvelle simulation
            st.session_state.simulation_id = None
            st.session_state.simulation_name = "Nouvelle simulation"
            st.session_state.show_name_input = True
            st.rerun()
    
    # Zone de saisie du nom de simulation (simple, sous le bouton)
    if st.session_state.get('show_name_input', False):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            simulation_name = st.text_input(
                "Nom de la simulation :",
                value="Nouvelle simulation",
                key="new_simulation_name"
            )
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("✅ Confirmer", use_container_width=True):
                    # Créer la simulation dans la base de données
                    simulation_id = add_simulation(simulation_name)
                    if simulation_id:
                        st.session_state.simulation_id = simulation_id
                        st.session_state.simulation_name = simulation_name
                        st.session_state.current_simulation_id = simulation_id
                        del st.session_state.show_name_input
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la création de la simulation")
            with col_btn2:
                if st.button("❌ Annuler", use_container_width=True):
                    del st.session_state.show_name_input
                    if 'simulation_id' in st.session_state:
                        del st.session_state.simulation_id
                    if 'simulation_name' in st.session_state:
                        del st.session_state.simulation_name
                    st.rerun()
    
    st.markdown("---")
    
    # Section historique des simulations
    st.subheader("📚 Historique des simulations")
    
    # Récupération des simulations
    simulations_df = get_simulations()
    
    if simulations_df.empty:
        st.info("Aucune simulation trouvée. Créez votre première simulation !")
    else:
        # Affichage des simulations sous forme de cartes compactes
        for _, sim in simulations_df.iterrows():
            # Utiliser les statistiques directement depuis le DataFrame
            added_count = sim.get('added_count', 0)
            modified_count = sim.get('modified_count', 0)
            deleted_count = sim.get('deleted_count', 0)
            
            with st.container():
                # Création d'une carte compacte pour chaque simulation avec boutons intégrés
                col_info, col_buttons = st.columns([4, 1])
                
                with col_info:
                    st.markdown(f"""
                    <div style="
                        border: 1px solid #ddd;
                        border-radius: 8px;
                        padding: 15px;
                        margin: 8px 0;
                        background-color: #f8f9fa;
                        transition: all 0.3s ease;
                    " onmouseover="this.style.backgroundColor='#e9ecef'" onmouseout="this.style.backgroundColor='#f8f9fa'">
                        <h4 style="margin: 0 0 8px 0; color: #2c3e50;">{sim['name']}</h4>
                        <p style="margin: 4px 0; color: #6c757d; font-size: 0.9em;">
                            <strong>Créée:</strong> {format_date(sim['created_at'])} | 
                            <strong>Modifiée:</strong> {format_date(sim['last_modified_at'])}
                        </p>
                        <p style="margin: 4px 0; color: #6c757d; font-size: 0.9em;">
                            <strong>Trains ajoutés:</strong> {added_count} | 
                            <strong>Trains modifiés:</strong> {modified_count} | 
                            <strong>Trains supprimés:</strong> {deleted_count}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_buttons:
                    st.write("")  # Espace pour aligner avec le conteneur
                    if st.button(f"✏️", key=f"edit_sim_{sim['id']}", help="Modifier la simulation"):
                        # Définir les paramètres de session pour la simulation existante
                        st.session_state.simulation_id = sim['id']
                        st.session_state.simulation_name = sim['name']
                        st.rerun()
                    if st.button(f"🗑️", key=f"delete_sim_{sim['id']}", help="Supprimer la simulation"):
                        # Supprimer la simulation et ses événements
                        if delete_simulation(sim['id']):
                            st.success(f"✅ Simulation '{sim['name']}' supprimée avec succès")
                            st.rerun()
                        else:
                            st.error(f"❌ Erreur lors de la suppression de la simulation '{sim['name']}'")

def main():
    # Vérifier si on est en mode édition
    if 'simulation_id' in st.session_state:
        # Si on est en train de saisir le nom, ne pas aller à l'édition
        if st.session_state.get('show_name_input', False):
            show_simulation_list()
        else:
            show_simulation_edit()
    else:
        show_simulation_list()

if __name__ == "__main__":
    main() 