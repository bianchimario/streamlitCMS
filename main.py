import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
import re
from io import StringIO
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the connection string from the .env file
conn_string = os.getenv('DATABASE_PATH')

# Utility functions
def create_slug(title):
    """Create a slug from the title"""
    # Convert to lowercase and replace spaces with hyphens
    slug = title.lower()
    # Remove special characters
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    # Replace spaces with hyphens
    slug = re.sub(r'\s+', '-', slug)
    return slug

def init_db():
    """Initialize the database if it doesn't exist"""
    if not conn_string:
        st.error("Database path not configured. Check the .env file")
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
    """Retrieve all articles from the database"""
    conn = sqlite3.connect(conn_string)
    df = pd.read_sql('SELECT * FROM articoli ORDER BY data DESC', conn)
    conn.close()
    return df

def add_article(titolo, tags, contenuto):
    """Add a new article to the database"""
    slug = create_slug(titolo)
    today_date = date.today().strftime('%Y-%m-%d')
    
    conn = sqlite3.connect(conn_string)
    c = conn.cursor()
    try:
        c.execute('''
        INSERT INTO articoli (titolo, slug, data, tags, contenuto)
        VALUES (?, ?, ?, ?, ?)
        ''', (titolo, slug, today_date, tags, contenuto))
        conn.commit()
        result = True
    except sqlite3.IntegrityError:
        result = False
    conn.close()
    return result

def update_article(id, titolo, tags, contenuto):
    """Update an existing article"""
    slug = create_slug(titolo)
    
    # Note: we don't update the 'data' field to maintain the original publication date
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
    """Retrieve a specific article from the database"""
    conn = sqlite3.connect(conn_string)
    c = conn.cursor()
    c.execute('SELECT * FROM articoli WHERE id=?', (id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        # Create a dictionary from the results
        columns = ['id', 'titolo', 'slug', 'data', 'tags', 'contenuto']
        article = {columns[i]: result[i] for i in range(len(columns))}
        return article
    else:
        return None

# Page settings
st.set_page_config(
    page_title="Blog CMS",
    page_icon="📝",
    layout="wide"
)

# Check if the .env file is configured correctly
if not conn_string:
    st.error("⚠️ Missing configuration: Database path not found in .env file")
    st.info("Create an .env file in the same directory as this script with the following content:")
    st.code("DATABASE_PATH=/path/to/your/database.db")
    st.stop()

# Initialize the database
init_db()

# Initialize session variables if they don't exist
if 'page' not in st.session_state:
    st.session_state['page'] = 'list'

# Function to determine which page to display
def display_page():
    # If we're in edit mode, show the edit page
    if 'edit_id' in st.session_state:
        display_edit_page()
    # Otherwise, show the page selected from the sidebar
    elif st.session_state['page'] == 'list':
        display_list_page()
    elif st.session_state['page'] == 'new':
        display_new_page()

# Page: Article List
def display_list_page():
    st.title("Article Management")
    
    # Retrieve articles
    df = get_articles()
    
    if not df.empty:
        # Show the table of articles
        st.write(f"Total articles: {len(df)}")
        
        # Use a search box to filter articles
        search = st.text_input("Search articles by title or tag:")
        
        if search:
            filtered_df = df[df['titolo'].str.contains(search, case=False) | 
                             df['tags'].str.contains(search, case=False)]
        else:
            filtered_df = df
        
        # Show articles in a grid layout with 3 articles per row
        col_count = 3
        
        # Add some space above the grid
        st.write("")
        
        for i in range(0, len(filtered_df), col_count):
            cols = st.columns(col_count)
            for j in range(col_count):
                if i + j < len(filtered_df):
                    article = filtered_df.iloc[i + j]
                    with cols[j]:
                        # Add a container with border and padding
                        with st.container():
                            st.subheader(article['titolo'])
                            st.caption(f"Date: {article['data']}")
                            st.caption(f"Tags: {article['tags']}")
                            
                            # Additional space before the button
                            st.write("")
                            
                            # Only edit button
                            if st.button("✏️ Edit", key=f"edit_{article['id']}"):
                                st.session_state['edit_id'] = int(article['id'])
                                st.rerun()
                            
                            # Space after each article
                            st.write("")
            
            # Space between rows
            st.write("")
    else:
        st.info("No articles in the database. Create a new article from the side menu.")

# Page: New Article
def display_new_page():
    st.title("New Article")
    
    # Variables to store form values
    form_submitted = False
    titolo = ""
    tags = ""
    contenuto = ""
    
    # Form for the article
    with st.form("new_article_form"):
        titolo = st.text_input("Title")
        
        if titolo:
            st.caption(f"Slug: {create_slug(titolo)}")
        
        tags = st.text_input("Tags (comma separated)")
        contenuto = st.text_area("Article content", height=400)
        
        # The submit button returns True when pressed
        form_submitted = st.form_submit_button("Save Article")
    
    # Save logic OUTSIDE the form
    if form_submitted:
        if not titolo:
            st.error("Title cannot be empty!")
        else:
            if add_article(titolo, tags, contenuto):
                st.success("Article created successfully!")
                # Change page and force rerun
                st.session_state['page'] = 'list'
                st.rerun()
            else:
                st.error("Error creating the article. Duplicate slug?")

# Page: Edit Article
def display_edit_page():
    st.title("Edit Article")
    
    # Retrieve the article from the database
    article_id = st.session_state['edit_id']
    article = get_article_by_id(article_id)
    
    if not article:
        st.error(f"Article with ID {article_id} not found in the database.")
        if st.button("Back to list"):
            st.session_state.pop('edit_id', None)
            st.rerun()
    else:
        # Variables to store form values
        form_submitted = False
        titolo = article['titolo']
        tags = article['tags'] if article['tags'] else ""
        contenuto = article['contenuto'] if article['contenuto'] else ""
        
        # Form to edit the article
        with st.form("edit_article_form"):
            titolo = st.text_input("Title", value=titolo)
            
            if titolo:
                st.caption(f"Slug: {create_slug(titolo)}")
            
            tags = st.text_input("Tags (comma separated)", value=tags)
            contenuto = st.text_area("Article content", value=contenuto, height=400)
            
            form_submitted = st.form_submit_button("Save Article")
        
        # Logic moved outside the form
        if form_submitted:
            if not titolo:
                st.error("Title cannot be empty!")
            else:
                if update_article(article_id, titolo, tags, contenuto):
                    st.success("Article updated successfully!")
                    # Remove the edit ID and return to the list automatically
                    st.session_state.pop('edit_id', None)
                    st.session_state['page'] = 'list'
                    st.rerun()
                else:
                    st.error("Error updating the article. Duplicate slug?")
        
        # Button to go back
        if st.button("Back to list"):
            st.session_state.pop('edit_id', None)
            st.rerun()

# Sidebar for navigation
st.sidebar.title("Blog CMS")

# Page selection in the sidebar (only if we're not editing)
if 'edit_id' not in st.session_state:
    page_options = ["Article List", "New Article"]
    selected_page = st.sidebar.radio("Navigation", page_options)
    
    # Map the selection to the page key
    if selected_page == "Article List":
        st.session_state['page'] = 'list'
    elif selected_page == "New Article":
        st.session_state['page'] = 'new'
else:
    # If we're in edit mode, highlight that we're editing
    st.sidebar.info("✏️ Article edit mode")
    
    # Button to return to the list from the sidebar
    if st.sidebar.button("Back to article list"):
        st.session_state.pop('edit_id', None)
        st.rerun()

# Show the current page
display_page()