import streamlit as st
import folium
from streamlit_folium import st_folium
from database import get_all_plants, search_plants, get_plant_by_id, delete_plant, add_plant, get_total_plants, update_plant, get_plant_by_qr

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

import numpy as np
from PIL import Image

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

from urllib.parse import urlparse, parse_qs, unquote
import re

st.set_page_config(
    page_title="FloraAtlas",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .stApp { background-color: #c7d7b8; }
    .stButton > button {
        background-color: #445932 !important;
        color: white !important;
        border-radius: 50px !important;
        padding: 12px 30px !important;
        font-size: 1rem !important;
        border: none !important;
        width: 100% !important;
    }
    .stButton > button:hover { background-color: #354526 !important; }
    .stTextInput input {
        background-color: white !important;
        color: black !important;
        border-radius: 8px !important;
        border: 2px solid #445932 !important;
        padding: 10px !important;
    }
    .stTextInput label { color: black !important; }
    .stTextArea textarea {
        background-color: white !important;
        color: black !important;
        border-radius: 8px !important;
        border: 2px solid #445932 !important;
        padding: 10px !important;
    }
    .stSelectbox > div > div {
        background-color: white !important;
        color: black !important;
        border-radius: 8px !important;
        border: 2px solid #445932 !important;
    }
    .stMarkdown, .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: black !important;
    }
    .stSuccess { color: black !important; }
    .stWarning { color: black !important; }
    .stInfo { color: black !important; }
    .stError { color: black !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 style="color: #445932; text-align: center; font-size: 4rem;">🌿 FloraAtlas</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #000000; font-size: 1.2rem;">Campus Plant Information System</p>', unsafe_allow_html=True)

# ===== LOGIN =====
if not st.session_state.get('logged_in', False):
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            st.markdown('<h3 style="text-align: center; color: #000000;">🔐 Login</h3>', unsafe_allow_html=True)
            username = st.text_input("👤 Username", placeholder="Enter any username")
            password = st.text_input("🔑 Password", type="password", placeholder="Enter any password")
            if st.form_submit_button("🔐 Login", use_container_width=True):
                if username and password:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.rerun()
                else:
                    st.error("⚠️ Please enter both username and password")
        st.caption("🆕 Anyone can login - No restrictions!")

# ===== AI FUNCTION =====
def get_ai_info(plant_name):
    if not OLLAMA_AVAILABLE:
        return "⚠️ AI not available on cloud deployment. Please run locally."
    try:
        response = ollama.chat(
            model='tinyllama',
            options={'num_predict': 512},
            messages=[{'role': 'user', 'content': f"Tell me about {plant_name}. Give short, useful information."}]
        )
        return response['message']['content']
    except:
        return "⚠️ AI service not available."

# ===== READ PLANT NAME FROM IMAGE =====
def read_plant_name_from_image(image):
    if not (CV2_AVAILABLE and PYTESSERACT_AVAILABLE):
        return None
    try:
        if isinstance(image, Image.Image):
            img = np.array(image)
        else:
            img = image
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(thresh, config=custom_config)
        lines = text.split('\n')
        lines = [line.strip() for line in lines if line.strip()]
        common_plants = [
            "Neem", "Tulsi", "Aloe Vera", "Rose", "Mango", "Lavender", "Sunflower",
            "Shankarsivari", "Tagar", "Jaswand", "Supari", "Lakshman Phal",
            "Gulmohar", "Kaju", "Madhumalati", "Nandaruk", "Comfrey"
        ]
        for line in lines:
            for plant in common_plants:
                if plant.lower() in line.lower():
                    return plant
        for line in lines:
            words = line.split()
            for word in words:
                if len(word) > 2 and word[0].isupper():
                    if re.match(r'^[A-Z][a-z]+', word):
                        return word
        return None
    except Exception:
        return None

# ===== EXTRACT PLANT NAME FROM QR DATA =====
def extract_plant_name_from_qr(data):
    plant_name = None
    if "LatinName" in data:
        try:
            parsed = urlparse(data)
            params = parse_qs(parsed.query)
            if "LatinName" in params:
                plant_name = unquote(params["LatinName"][0])
                return plant_name
        except:
            pass
    try:
        cleaned = data.replace('https://', '').replace('http://', '').replace('www.', '')
        parts = cleaned.split('/')
        if parts:
            last = parts[-1]
            if '?' in last:
                last = last.split('?')[0]
            if '.' in last:
                last = last.split('.')[0]
            last = last.replace('-', ' ').replace('_', ' ').replace('%20', ' ')
            plant_name = last.title()
            if plant_name and len(plant_name) > 1:
                return plant_name
    except:
        pass
    return "this plant"

# ===== PROCESS QR (Common Function) =====
def process_qr_image(image):
    if not CV2_AVAILABLE:
        st.error("⚠️ QR scanning not available on cloud. Please run locally.")
        return
    
    img_array = np.array(image)
    qr_detector = cv2.QRCodeDetector()
    data, points, _ = qr_detector.detectAndDecode(img_array)
    
    if data:
        st.success(f"✅ QR Code Data: {data}")
        plant = get_plant_by_qr(data)
        if not plant:
            all_plants = get_all_plants()
            for p in all_plants:
                if p[11] and p[11] in data:
                    plant = p
                    break
        if plant:
            st.success(f"🌿 Plant: {plant[1]}")
            st.write(f"**Scientific Name:** {plant[2]}")
            st.write(f"**Category:** {plant[6]}")
            if plant[12] and plant[13]:
                st.write(f"📍 Location: {plant[12]}, {plant[13]}")
            st.write("---")
            st.write("### 🤖 AI Information")
            with st.spinner("Getting AI information..."):
                ai_info = get_ai_info(plant[1])
                st.write(ai_info)
        else:
            st.warning("⚠️ Plant not found in database. Getting information from AI...")
            plant_name = read_plant_name_from_image(image)
            if not plant_name:
                plant_name = extract_plant_name_from_qr(data)
            st.write(f"### 🤖 AI Information about: {plant_name}")
            with st.spinner("Getting AI information..."):
                ai_info = get_ai_info(plant_name)
                st.write(ai_info)
            st.info(f"💡 Add this plant? QR Code ID: `{data}`")
    else:
        st.warning("⚠️ No QR code detected.")

# ===== AFTER LOGIN =====
if st.session_state.get('logged_in', False):
    st.markdown("---")
    st.markdown(f'<p style="text-align: center; color: #000000; font-size: 1.2rem;">👋 Welcome, <b>{st.session_state["username"]}</b>!</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📱 QR Scanner", key="qr_main", use_container_width=True):
            st.session_state['show_qr'] = True
            st.session_state['show_location'] = False
            st.session_state['show_dashboard'] = False
            st.rerun()
    with col2:
        if st.button("📍 Location Tracker", key="location_main", use_container_width=True):
            st.session_state['show_location'] = True
            st.session_state['show_qr'] = False
            st.session_state['show_dashboard'] = False
            st.rerun()

    st.markdown("---")

    if st.session_state.get("username") == "admin":
        if st.button("📊 Admin Dashboard", key="admin_dashboard_btn", use_container_width=True):
            st.session_state['show_dashboard'] = True
            st.session_state['show_qr'] = False
            st.session_state['show_location'] = False
            st.rerun()
    else:
        st.info("👤 You are logged in as a regular user. Admin features are restricted.")

    # ===== QR SCANNER =====
    if st.session_state.get('show_qr', False):
        st.markdown("---")
        st.markdown('<h2 style="color: #445932;">📱 QR Scanner</h2>', unsafe_allow_html=True)
        
        if not CV2_AVAILABLE:
            st.warning("⚠️ QR scanning not available on cloud. Please run locally for full features.")
        
        tab1, tab2 = st.tabs(["📷 Camera", "📤 Upload"])
        
        with tab1:
            st.write("### 📷 Scan with Camera")
            camera_image = st.camera_input("Point camera at QR code")
            if camera_image:
                try:
                    image = Image.open(camera_image)
                    st.image(image, caption='Captured Image', use_container_width=True)
                    process_qr_image(image)
                except Exception as e:
                    st.error(f"Error: {e}")
        
        with tab2:
            st.write("### 📤 Upload QR Code Image")
            uploaded_file = st.file_uploader("Choose an image", type=['png', 'jpg', 'jpeg'])
            if uploaded_file:
                try:
                    image = Image.open(uploaded_file)
                    st.image(image, caption='Uploaded Image', use_container_width=True)
                    process_qr_image(image)
                except Exception as e:
                    st.error(f"Error: {e}")
        
        if st.button("🔙 Back", key="back_qr"):
            st.session_state['show_qr'] = False
            st.rerun()

    # ===== LOCATION TRACKER =====
    if st.session_state.get('show_location', False):
        st.markdown("---")
        st.markdown('<h2 style="color: #445932;">📍 Location Tracker</h2>', unsafe_allow_html=True)
        
        search_term = st.text_input("🌿 Enter plant name:", placeholder="e.g., Neem")
        
        col1, col2 = st.columns(2)
        with col1:
            search_clicked = st.button("🔍 Search", key="loc_search", use_container_width=True)
        with col2:
            show_all_clicked = st.button("📋 Show All", key="loc_show_all", use_container_width=True)
        
        plants_to_show = []
        if search_clicked and search_term:
            all_plants = get_all_plants()
            for plant in all_plants:
                if search_term.lower() in plant[1].lower():
                    plants_to_show.append(plant)
            if not plants_to_show:
                st.warning("❌ No plants found.")
        elif show_all_clicked:
            plants_to_show = get_all_plants()
        
        if plants_to_show:
            st.success(f"✅ Found {len(plants_to_show)} plant(s):")
            for plant in plants_to_show:
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 2, 1.5, 1])
                    with col1:
                        st.write(f"🌿 **{plant[1]}**")
                    with col2:
                        st.write(f"*{plant[2]}*")
                    with col3:
                        st.write(f"📂 {plant[6]}")
                    with col4:
                        lat = plant[12]
                        lon = plant[13]
                        if lat and lon and lat != 0.0 and lon != 0.0:
                            if st.button("📍 Map", key=f"loc_map_{plant[0]}"):
                                st.session_state['selected_plant'] = plant[0]
                                st.rerun()
                        else:
                            st.write("❌ No location")
                    st.write("---")
        
        if st.session_state.get('selected_plant'):
            plant_id = st.session_state['selected_plant']
            plant = get_plant_by_id(plant_id)
            if plant:
                lat = plant[12]
                lon = plant[13]
                if lat and lon and lat != 0.0 and lon != 0.0:
                    st.write("---")
                    st.write(f"### 📍 Location: **{plant[1]}**")
                    st.write(f"**Latitude:** {lat}")
                    st.write(f"**Longitude:** {lon}")
                    
                    try:
                        m = folium.Map(location=[lat, lon], zoom_start=15)
                        folium.Marker([lat, lon], popup=f"{plant[1]}",
                                     icon=folium.Icon(color="green", icon="leaf")).add_to(m)
                        st_folium(m, width=700, height=450)
                        st.markdown(f"📍 [Open in Google Maps](https://www.google.com/maps?q={lat},{lon})")
                    except Exception as e:
                        st.error(f"Map Error: {e}")
                else:
                    st.warning("📍 No location coordinates available.")
        
        if st.button("🔙 Back", key="back_location"):
            st.session_state['show_location'] = False
            st.session_state['selected_plant'] = None
            st.rerun()

    # ===== ADMIN DASHBOARD =====
    if st.session_state.get('show_dashboard', False) and st.session_state.get("username") == "admin":
        st.markdown("---")
        st.markdown('<h2 style="color: #445932;">📊 Admin Dashboard</h2>', unsafe_allow_html=True)
        
        total = get_total_plants()
        st.markdown(f'<p style="color: black;">🌱 Total Plants: <b>{total}</b></p>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("➕ Add Plant", key="add_plant_btn", use_container_width=True):
                st.session_state['show_add'] = True
                st.session_state['show_manage'] = False
                st.session_state['show_search'] = False
                st.session_state['show_edit'] = False
                st.rerun()
        with col2:
            if st.button("📋 Manage Plants", key="manage_plants_btn", use_container_width=True):
                st.session_state['show_manage'] = True
                st.session_state['show_add'] = False
                st.session_state['show_search'] = False
                st.session_state['show_edit'] = False
                st.rerun()
        with col3:
            if st.button("🔍 Search Plants", key="search_plants_btn", use_container_width=True):
                st.session_state['show_search'] = True
                st.session_state['show_add'] = False
                st.session_state['show_manage'] = False
                st.session_state['show_edit'] = False
                st.rerun()
        with col4:
            if st.button("📱 QR Scanner", key="qr_scanner_dash_btn", use_container_width=True):
                st.session_state['show_qr'] = True
                st.session_state['show_dashboard'] = False
                st.rerun()
        
        st.markdown("---")
        
        if st.session_state.get('show_add', False):
            st.markdown('<h3 style="color: #445932;">➕ Add New Plant</h3>', unsafe_allow_html=True)
            with st.form("add_plant_form"):
                col1, col2 = st.columns(2)
                with col1:
                    plant_id = st.text_input("Plant ID *", placeholder="P001")
                    plant_name = st.text_input("Plant Name *", placeholder="Neem Tree")
                    scientific_name = st.text_input("Scientific Name", placeholder="Azadirachta indica")
                    category = st.selectbox("Category", ["Tree", "Herb", "Flower", "Succulent", "Other"])
                with col2:
                    qr_code_id = st.text_input("QR Code ID", placeholder="QR001")
                    latitude = st.text_input("Latitude", placeholder="28.6139")
                    longitude = st.text_input("Longitude", placeholder="77.2090")
                    description = st.text_area("Description")
                if st.form_submit_button("✅ Add Plant"):
                    if plant_id and plant_name:
                        data = {
                            'plant_id': plant_id, 'plant_name': plant_name,
                            'scientific_name': scientific_name, 'kingdom': '', 'family': '', 'species': '',
                            'category': category, 'description': description,
                            'medicinal_uses': '', 'environmental_benefits': '', 'image_path': '',
                            'qr_code_id': qr_code_id,
                            'latitude': float(latitude) if latitude else None,
                            'longitude': float(longitude) if longitude else None
                        }
                        success, msg = add_plant(data)
                        if success:
                            st.success(f"✅ {msg}")
                            st.session_state['show_add'] = False
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
                    else:
                        st.error("⚠️ Plant ID and Name are required!")
        
        if st.session_state.get('show_manage', False):
            st.markdown('<h3 style="color: #445932;">📋 Manage Plants</h3>', unsafe_allow_html=True)
            plants = get_all_plants()
            if plants:
                for plant in plants:
                    with st.container():
                        cols = st.columns([2, 2, 1.5, 0.7, 0.7])
                        with cols[0]:
                            st.markdown(f"**🌿 {plant[1]}**")
                        with cols[1]:
                            st.markdown(f"*{plant[2]}*")
                        with cols[2]:
                            st.markdown(f"📂 {plant[6]}")
                        with cols[3]:
                            if st.button("✏️", key=f"edit_{plant[0]}"):
                                st.session_state['edit_plant'] = plant[0]
                                st.session_state['show_edit'] = True
                                st.session_state['show_manage'] = False
                                st.rerun()
                        with cols[4]:
                            if st.button("🗑️", key=f"del_{plant[0]}"):
                                success, msg = delete_plant(plant[0])
                                if success:
                                    st.success(f"✅ {msg}")
                                    st.rerun()
                                else:
                                    st.error(f"❌ {msg}")
                        st.markdown("---")
            else:
                st.info("No plants found.")
        
        if st.session_state.get('show_edit', False):
            plant_id = st.session_state.get('edit_plant')
            plant = get_plant_by_id(plant_id)
            if plant:
                st.markdown(f'<h3 style="color: #445932;">✏️ Edit Plant: {plant[1]}</h3>', unsafe_allow_html=True)
                with st.form("edit_plant_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        plant_name = st.text_input("Plant Name", value=plant[1])
                        scientific_name = st.text_input("Scientific Name", value=plant[2] if plant[2] else "")
                        category = st.selectbox("Category", ["Tree", "Herb", "Flower", "Succulent", "Other"], index=0)
                    with col2:
                        qr_code_id = st.text_input("QR Code ID", value=plant[11] if plant[11] else "")
                        latitude = st.text_input("Latitude", value=str(plant[12]) if plant[12] else "")
                        longitude = st.text_input("Longitude", value=str(plant[13]) if plant[13] else "")
                        description = st.text_area("Description", value=plant[7] if plant[7] else "")
                    
                    if st.form_submit_button("💾 Save Changes"):
                        data = {
                            'plant_name': plant_name, 'scientific_name': scientific_name,
                            'kingdom': '', 'family': '', 'species': '', 'category': category,
                            'description': description, 'medicinal_uses': '', 'environmental_benefits': '',
                            'image_path': '', 'qr_code_id': qr_code_id,
                            'latitude': float(latitude) if latitude else None,
                            'longitude': float(longitude) if longitude else None
                        }
                        success, msg = update_plant(plant_id, data)
                        if success:
                            st.success(f"✅ {msg}")
                            st.session_state['show_edit'] = False
                            st.session_state['show_manage'] = True
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
                
                if st.button("❌ Cancel", key="cancel_edit"):
                    st.session_state['show_edit'] = False
                    st.session_state['show_manage'] = True
                    st.rerun()
        
        if st.session_state.get('show_search', False):
            st.markdown('<h3 style="color: #445932;">🔍 Search Plants</h3>', unsafe_allow_html=True)
            search_term = st.text_input("Enter plant name:", placeholder="e.g., Neem", key="search_input")
            if st.button("🔍 Search", key="search_btn"):
                if search_term:
                    results = search_plants(search_term)
                    if results:
                        for plant in results:
                            st.markdown(f"""
                            <div style="background: white; border-radius: 10px; padding: 15px; margin: 10px 0; border: 2px solid #445932;">
                                <strong>🌿 {plant[1]}</strong><br>
                                <i>{plant[2]}</i><br>
                                📂 {plant[6]}
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.warning("No plants found.")
                else:
                    st.warning("Please enter a plant name.")
        
        if st.button("🔒 Hide Dashboard", key="hide_dash_btn", use_container_width=True):
            st.session_state['show_dashboard'] = False
            st.session_state['show_add'] = False
            st.session_state['show_manage'] = False
            st.session_state['show_search'] = False
            st.session_state['show_edit'] = False
            st.rerun()

    st.markdown("---")
    if st.button("🚪 Logout", key="logout_btn_main", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

st.markdown("""
<div style="text-align: center; margin-top: 2rem; padding: 15px 0; color: #000000; border-top: 1px solid rgba(0,0,0,0.1);">
    <p>© 2026 FloraAtlas</p>
</div>
""", unsafe_allow_html=True)