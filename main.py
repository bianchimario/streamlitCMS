import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
import re
from io import StringIO
import os
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# Ottieni la connection string dal file .env
conn_string = os.getenv('DATABASE_PATH')

# Funzioni di utilità
def create_slug(title):
    """Crea uno slug dal titolo"""
    # Converti in minuscolo e sostituisci spazi con trattini
    slug = title.lower()
    # Rimuovi caratteri speciali
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    # Sostituisci spazi con trattini
    slug = re.sub(r'\s+', '-', slug)
    return slug

def init_db():
    """Inizializza il database se non esiste"""
    if not conn_string:
        st.error("Percorso del database non configurato. Controlla il file .env")
        st.stop()
        
    conn = sqlite3.connect(conn_string)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS articoli (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titolo TEXT NOT NULL,
        slug TEXT NOT NULL UNIQUE,
        data TEXT NOT NULL,
        tags TEXT,
        contenuto TEXT
    )
    ''')
    conn.commit()
    conn.close()

def get_articles():
    """Recupera tutti gli articoli dal database"""
    conn = sqlite3.connect(conn_string)
    df = pd.read_sql('SELECT * FROM articoli ORDER BY data DESC', conn)
    conn.close()
    return df

def add_article(titolo, tags, contenuto):
    """Aggiunge un nuovo articolo al database"""
    slug = create_slug(titolo)
    data_oggi = date.today().strftime('%Y-%m-%d')
    
    conn = sqlite3.connect(conn_string)
    c = conn.cursor()
    try:
        c.execute('''
        INSERT INTO articoli (titolo, slug, data, tags, contenuto)
        VALUES (?, ?, ?, ?, ?)
        ''', (titolo, slug, data_oggi, tags, contenuto))
        conn.commit()
        result = True
    except sqlite3.IntegrityError:
        result = False
    conn.close()
    return result

def update_article(id, titolo, tags, contenuto):
    """Aggiorna un articolo esistente"""
    slug = create_slug(titolo)
    
    # Nota: non aggiorniamo il campo 'data' per mantenere la data di pubblicazione originale
    conn = sqlite3.connect(conn_string)
    c = conn.cursor()
    try:
        c.execute('''
        UPDATE articoli 
        SET titolo=?, slug=?, tags=?, contenuto=?
        WHERE id=?
        ''', (titolo, slug, tags, contenuto, id))
        conn.commit()
        result = True
    except sqlite3.IntegrityError:
        result = False
    conn.close()
    return result

def get_article_by_id(id):
    """Recupera un articolo specifico dal database"""
    conn = sqlite3.connect(conn_string)
    c = conn.cursor()
    c.execute('SELECT * FROM articoli WHERE id=?', (id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        # Creiamo un dizionario dai risultati
        columns = ['id', 'titolo', 'slug', 'data', 'tags', 'contenuto']
        article = {columns[i]: result[i] for i in range(len(columns))}
        return article
    else:
        return None

# Impostazioni della pagina
st.set_page_config(
    page_title="Blog CMS",
    page_icon="📝",
    layout="wide"
)

# Verifica se il file .env è configurato correttamente
if not conn_string:
    st.error("⚠️ Configurazione mancante: Percorso del database non trovato nel file .env")
    st.info("Crea un file .env nella stessa directory di questo script con il seguente contenuto:")
    st.code("DATABASE_PATH=/percorso/al/tuo/database.db")
    st.stop()

# Inizializza il database
init_db()

# Inizializza le variabili di sessione se non esistono
if 'page' not in st.session_state:
    st.session_state['page'] = 'lista'

# Funzione per determinare quale pagina visualizzare
def display_page():
    # Se siamo in modalità modifica, mostro la pagina di modifica
    if 'edit_id' in st.session_state:
        display_edit_page()
    # Altrimenti, mostro la pagina selezionata dalla sidebar
    elif st.session_state['page'] == 'lista':
        display_list_page()
    elif st.session_state['page'] == 'nuovo':
        display_new_page()

# Pagina: Lista Articoli
def display_list_page():
    st.title("Gestione Articoli")
    
    # Recupera gli articoli
    df = get_articles()
    
    if not df.empty:
        # Mostra la tabella degli articoli
        st.write(f"Totale articoli: {len(df)}")
        
        # Usiamo una casella di ricerca per filtrare gli articoli
        search = st.text_input("Cerca articoli per titolo o tag:")
        
        if search:
            filtered_df = df[df['titolo'].str.contains(search, case=False) | 
                             df['tags'].str.contains(search, case=False)]
        else:
            filtered_df = df
        
        # Mostra gli articoli in un layout a griglia con 3 articoli per riga
        col_count = 3
        
        # Aggiungiamo un po' di spazio sopra la griglia
        st.write("")
        
        for i in range(0, len(filtered_df), col_count):
            cols = st.columns(col_count)
            for j in range(col_count):
                if i + j < len(filtered_df):
                    article = filtered_df.iloc[i + j]
                    with cols[j]:
                        # Aggiungiamo un contenitore con bordo e padding
                        with st.container():
                            st.subheader(article['titolo'])
                            st.caption(f"Data: {article['data']}")
                            st.caption(f"Tags: {article['tags']}")
                            
                            # Spazio aggiuntivo prima del pulsante
                            st.write("")
                            
                            # Solo bottone modifica
                            if st.button("✏️ Modifica", key=f"edit_{article['id']}"):
                                st.session_state['edit_id'] = int(article['id'])
                                st.rerun()
                            
                            # Spazio dopo ogni articolo
                            st.write("")
            
            # Spazio tra le righe
            st.write("")
    else:
        st.info("Nessun articolo presente nel database. Crea un nuovo articolo dal menu laterale.")

# Pagina: Nuovo Articolo
def display_new_page():
    st.title("Nuovo Articolo")
    
    # Variabili per memorizzare i valori del form
    form_submitted = False
    titolo = ""
    tags = ""
    contenuto = ""
    
    # Form per l'articolo
    with st.form("new_article_form"):
        titolo = st.text_input("Titolo")
        
        if titolo:
            st.caption(f"Slug: {create_slug(titolo)}")
        
        tags = st.text_input("Tags (separati da virgola)")
        contenuto = st.text_area("Contenuto dell'articolo", height=400)
        
        # Il pulsante di submit restituisce True quando viene premuto
        form_submitted = st.form_submit_button("Salva Articolo")
    
    # Logica di salvataggio FUORI dal form
    if form_submitted:
        if not titolo:
            st.error("Il titolo non può essere vuoto!")
        else:
            if add_article(titolo, tags, contenuto):
                st.success("Articolo creato con successo!")
                # Cambio pagina e forzo il rerun
                st.session_state['page'] = 'lista'
                st.rerun()
            else:
                st.error("Errore durante la creazione dell'articolo. Slug duplicato?")

# Pagina: Modifica Articolo
def display_edit_page():
    st.title("Modifica Articolo")
    
    # Recupera l'articolo dal database
    article_id = st.session_state['edit_id']
    article = get_article_by_id(article_id)
    
    if not article:
        st.error(f"Articolo con ID {article_id} non trovato nel database.")
        if st.button("Torna alla lista"):
            st.session_state.pop('edit_id', None)
            st.rerun()
    else:
        # Variabili per memorizzare i valori del form
        form_submitted = False
        titolo = article['titolo']
        tags = article['tags'] if article['tags'] else ""
        contenuto = article['contenuto'] if article['contenuto'] else ""
        
        # Form per modificare l'articolo
        with st.form("edit_article_form"):
            titolo = st.text_input("Titolo", value=titolo)
            
            if titolo:
                st.caption(f"Slug: {create_slug(titolo)}")
            
            tags = st.text_input("Tags (separati da virgola)", value=tags)
            contenuto = st.text_area("Contenuto dell'articolo", value=contenuto, height=400)
            
            form_submitted = st.form_submit_button("Salva Articolo")
        
        # Logica spostata fuori dal form
        if form_submitted:
            if not titolo:
                st.error("Il titolo non può essere vuoto!")
            else:
                if update_article(article_id, titolo, tags, contenuto):
                    st.success("Articolo aggiornato con successo!")
                    # Rimuovi l'ID di modifica e torna alla lista automaticamente
                    st.session_state.pop('edit_id', None)
                    st.session_state['page'] = 'lista'
                    st.rerun()
                else:
                    st.error("Errore durante l'aggiornamento dell'articolo. Slug duplicato?")
        
        # Bottone per tornare indietro
        if st.button("Torna alla lista"):
            st.session_state.pop('edit_id', None)
            st.rerun()

# Sidebar per la navigazione
st.sidebar.title("Blog CMS")

# Selezione pagina nella sidebar (solo se non stiamo modificando)
if 'edit_id' not in st.session_state:
    page_options = ["Lista Articoli", "Nuovo Articolo"]
    selected_page = st.sidebar.radio("Navigazione", page_options)
    
    # Mappa la selezione alla chiave della pagina
    if selected_page == "Lista Articoli":
        st.session_state['page'] = 'lista'
    elif selected_page == "Nuovo Articolo":
        st.session_state['page'] = 'nuovo'
else:
    # Se siamo in modalità modifica, evidenziamo che stiamo modificando
    st.sidebar.info("✏️ Modalità modifica articolo")
    
    # Pulsante per tornare alla lista dalla sidebar
    if st.sidebar.button("Torna alla lista degli articoli"):
        st.session_state.pop('edit_id', None)
        st.rerun()

# Mostra la pagina corrente
display_page()