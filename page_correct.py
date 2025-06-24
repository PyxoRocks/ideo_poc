import streamlit as st
import pandas as pd
from process_data import get_events, get_locations, add_event, update_event, delete_event
from datetime import datetime

def main():
    st.write("#### Événements de correction de stocks")
    st.write("")

    # Gestion de l'affichage du formulaire
    if 'show_form' not in st.session_state:
        st.session_state.show_form = False
    if 'editing_event' not in st.session_state:
        st.session_state.editing_event = None
    # Ajout de la gestion d'état pour l'heure
    if 'selected_time' not in st.session_state:
        st.session_state.selected_time = datetime.now().time()

    if st.button("Ajouter une correction +"):
        st.session_state.show_form = True
        st.session_state.editing_event = None
        st.session_state.selected_time = datetime.now().time()
    st.write("")

    # Zone formulaire
    if st.session_state.show_form:
        st.write("#### Nouvelle correction de stock" if st.session_state.editing_event is None else "#### Modifier la correction")
        
        with st.form("correction_form"):
            # Liste déroulante pour le lieu
            locations = get_locations()
            selected_location = st.selectbox("Lieu", locations, index=locations.index(st.session_state.editing_event['LOCATION']) if st.session_state.editing_event else 0)
            
            # Zone de sélection de date
            col1, col2 = st.columns(2)
            with col1:
                default_date = st.session_state.editing_event['EVENT_DATE'].date() if st.session_state.editing_event else datetime.now().date()
                event_date = st.date_input("Date", value=default_date)
            with col2:
                # Utiliser l'état pour mémoriser l'heure sélectionnée
                if st.session_state.editing_event:
                    default_time = st.session_state.editing_event['EVENT_DATE'].time()
                else:
                    default_time = st.session_state.selected_time
                
                event_time = st.time_input("Heure", value=default_time)
                # Mettre à jour l'état avec l'heure sélectionnée
                st.session_state.selected_time = event_time
            
            # Combiner date et heure
            event_datetime = datetime.combine(event_date, event_time)
            
            # Zone d'entrée de chiffre avec explication
            default_wagons = st.session_state.editing_event['NB_WAGONS'] if st.session_state.editing_event else 0
            nb_wagons = st.number_input("Nombre de wagons concernés", min_value=None, max_value=None, value=default_wagons, step=1, help="Entrez un nombre positif pour ajouter des wagons, négatif pour en retirer")
            
            # Case à cocher pour le type
            default_inventory = not st.session_state.editing_event['RELATIVE'] if st.session_state.editing_event else False
            is_inventory = st.checkbox("Il s'agit d'un inventaire (valeur absolue)", value=default_inventory,
                                     help="Cochez cette case si la valeur représente un inventaire complet. Décochez si c'est une modification relative (+/- wagons)")
            
            # Case à cocher pour wagons pleins (applicable uniquement pour AMB)
            default_full = st.session_state.editing_event.get('TYPE') == 'full' if st.session_state.editing_event else False
            is_full = st.checkbox("Wagons pleins", value=default_full, 
                                help="Cochez cette case si les wagons sont pleins. Décochez si ce sont des wagons vides. Cette option n'est à considérer que pour AMB.")
            
            # Déterminer le type de wagons (uniquement pour AMB)
            wagon_type = None
            if selected_location == "AMB":
                wagon_type = 'full' if is_full else 'empty'
            
            # Zone de commentaire
            default_comment = st.session_state.editing_event['COMMENT'] if st.session_state.editing_event else ""
            comment = st.text_area("Commentaire", value=default_comment, placeholder="Description de la correction...", height=80)
            
            # Boutons de validation
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.form_submit_button("Valider"):
                    try:
                        # Déterminer si c'est relatif ou absolu
                        relative = not is_inventory
                        
                        if st.session_state.editing_event:
                            # Modifier l'événement existant
                            success = update_event(st.session_state.editing_event['ID'], selected_location, event_datetime, nb_wagons, relative, comment, wagon_type)
                            if success:
                                st.success("Correction modifiée avec succès!")
                        else:
                            # Ajouter un nouvel événement
                            success = add_event(selected_location, event_datetime, nb_wagons, relative, comment, wagon_type)
                            if success:
                                st.success("Correction ajoutée avec succès!")
                        
                        if success:
                            st.session_state.show_form = False
                            st.session_state.editing_event = None
                            st.rerun()
                        else:
                            st.error("Erreur lors de l'opération")
                    except Exception as e:
                        st.error(f"Erreur: {e}")
            
            with col2:
                if st.form_submit_button("Annuler"):
                    st.session_state.show_form = False
                    st.session_state.editing_event = None
                    st.rerun()

    st.write("#### Historique des corrections")
    
    # Récupération et affichage des événements
    events_df = get_events()
    
    if not events_df.empty:
        for _, event in events_df.iterrows():
            # Créer un titre compact pour identifier l'événement
            event_type = "Inventaire" if not event['RELATIVE'] else "Modification"
            sign = "+" if event['NB_WAGONS'] > 0 else ""
            title = f"📅 {event['EVENT_DATE'].strftime('%d/%m/%Y %H:%M')} -📍 {event['LOCATION']}  - {event_type}: {sign}{event['NB_WAGONS']} wagons"
            
            # Ajouter l'information sur le type de wagons si disponible et si c'est AMB
            if event['LOCATION'] == "AMB" and event.get('TYPE'):
                wagon_type_display = "pleins" if event['TYPE'] == 'full' else "vides"
                title += f" ({wagon_type_display})"
            
            if event['COMMENT']:
                title += f" -  💬 {event['COMMENT'][:50]}{'...' if len(event['COMMENT']) > 50 else ''}"
            
            # Créer un expander pour chaque événement
            with st.expander(title, expanded=False):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Lieu:** {event['LOCATION']}")
                    st.write(f"**Date:** {event['EVENT_DATE'].strftime('%d/%m/%Y à %H:%M')}")
                    st.write(f"**Type:** {event_type}")
                    st.write(f"**Wagons:** {sign}{event['NB_WAGONS']}")
                    
                    # Afficher le type de wagons si disponible et si c'est AMB
                    if event['LOCATION'] == "AMB" and event.get('TYPE'):
                        wagon_type_display = "Pleins" if event['TYPE'] == 'full' else "Vides"
                        st.write(f"**Type de wagons:** {wagon_type_display}")
                    
                    if event['COMMENT']:
                        st.write(f"**Commentaire:** {event['COMMENT']}")
                
                with col2:
                    st.write("")  # Espacement
                    st.write("")
                    
                    # Bouton modifier
                    if st.button("✏️", key=f"edit_{event['ID']}", help="Modifier cet événement"):
                        st.session_state.editing_event = event.to_dict()
                        st.session_state.show_form = True
                        st.rerun()
                    
                    # Bouton supprimer
                    if st.button("🗑️", key=f"delete_{event['ID']}", help="Supprimer cet événement"):
                        if delete_event(event['ID']):
                            st.success("Événement supprimé!")
                            st.rerun()
                        else:
                            st.error("Erreur lors de la suppression")
    else:
        st.info("Aucun événement de correction trouvé.")

if __name__ == "__main__":
    main() 