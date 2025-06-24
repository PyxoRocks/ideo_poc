import streamlit as st
from process_data import new_excel, get_min_max_dates
def main():
    st.set_page_config(
        page_title="Mon Application Streamlit",
        page_icon="🚀",
        layout="wide"
    )
    
    # Configuration de la navigation multi-pages
    pages = [
        st.Page("page_reel.py", title="Planification réelle", icon="📊"),
        st.Page("page_correct.py", title="Correction du stock", icon="🔄"),
        st.Page("page_simu.py", title="Simulations", icon="🎯"),
    ]
    
    # Création du menu de navigation dans la sidebar
    selected_page = st.navigation(pages, position="sidebar")
    
    # Zone de dépôt de fichier Excel dans la sidebar
    st.sidebar.subheader("📁 Import de données")

    max_date = get_min_max_dates()[1]
    if max_date:
        txt = f"Dernières données datent du {max_date}"
    else:
        txt = "Aucune donnée disponible"
    
    uploaded_file = st.sidebar.file_uploader(
        txt,
        type=['xlsx', 'xls'],
        help="⚠️ Les données du fichier écrasent celles déjà présentes pour les mêmes jours."
    )
    
    if uploaded_file is not None:
        if new_excel(uploaded_file):
            st.sidebar.success("Données importées avec succès")
        else:
            st.sidebar.error("Erreur lors de l'import")
    
    # Exécution de la page sélectionnée
    selected_page.run()

if __name__ == "__main__":
    main() 