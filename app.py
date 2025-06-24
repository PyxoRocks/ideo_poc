import streamlit as st
from process_data import new_excel, get_min_max_dates
import hashlib
import os

# Configuration du code d'accès depuis st.secrets
def get_access_code_hash():
    """Récupère le hash du code d'accès depuis st.secrets"""
    try:
        return st.secrets["ACCESS_CODE_HASH"]
    except KeyError:
        st.error("❌ Configuration manquante : ACCESS_CODE_HASH non défini dans st.secrets")
        st.stop()

def check_access_code():
    """Vérifie si l'utilisateur a fourni le bon code d'accès"""
    if 'access_granted' not in st.session_state:
        st.session_state.access_granted = False
    
    if not st.session_state.access_granted:
        # Interface de connexion
        st.markdown("""
        <div style="text-align: center; padding: 50px;">
            <h1>🔐 Accès Restreint</h1>
            <p>Veuillez entrer le code d'accès pour continuer</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Centrer le formulaire de connexion
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("access_form"):
                access_code = st.text_input("Code d'accès", type="password", placeholder="Entrez votre code")
                submit_button = st.form_submit_button("🔓 Accéder à l'application")
                
                if submit_button:
                    if access_code:
                        # Vérification du code avec hash SHA-256
                        input_hash = hashlib.sha256(access_code.encode()).hexdigest()
                        if input_hash == get_access_code_hash():
                            st.session_state.access_granted = True
                            st.success("✅ Accès autorisé !")
                            st.rerun()
                        else:
                            st.error("❌ Code d'accès incorrect")
                    else:
                        st.error("❌ Veuillez entrer un code d'accès")
        
        # Empêcher l'accès au reste de l'application
        st.stop()
    
    return True

def main():
    st.set_page_config(
        page_title="IDEO stocks & simulations",
        page_icon="🚂",
        layout="wide"
    )
    
    # Vérification du code d'accès AVANT tout
    if not check_access_code():
        return
    
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

    with st.spinner("Vérification des données existantes..."):
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
        with st.spinner("Import des données en cours..."):
            if new_excel(uploaded_file):
                st.sidebar.success("Données importées avec succès")
            else:
                st.sidebar.error("Erreur lors de l'import")
    
    # Exécution de la page sélectionnée
    selected_page.run()

if __name__ == "__main__":
    main() 