import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import json

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="China Logistics Map",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

  html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
  }
  .stApp {
    background-color: #0d1117;
    color: #e6edf3;
  }
  section[data-testid="stSidebar"] {
    background-color: #161b22;
    border-right: 1px solid #21262d;
  }
  .sidebar-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #58a6ff;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 4px;
    margin-top: 20px;
  }
  .metric-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 12px 16px;
    margin-bottom: 8px;
  }
  .metric-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: #8b949e;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }
  .metric-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 20px;
    font-weight: 600;
    color: #f0f6fc;
    margin-top: 2px;
  }
  .metric-sub {
    font-size: 11px;
    color: #8b949e;
    margin-top: 2px;
  }
  .distance-result {
    background: linear-gradient(135deg, #0d419d22, #58a6ff22);
    border: 1px solid #58a6ff55;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
    margin-top: 12px;
  }
  .distance-km {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 28px;
    font-weight: 600;
    color: #58a6ff;
  }
  .distance-label {
    font-size: 11px;
    color: #8b949e;
    margin-top: 4px;
  }
  .search-result-item {
    background: #1c2128;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 10px 14px;
    margin-bottom: 6px;
    cursor: pointer;
  }
  .city-tag {
    display: inline-block;
    background: #0d419d;
    color: #58a6ff;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 3px;
    margin-right: 6px;
    text-transform: uppercase;
  }
  .port-tag {
    display: inline-block;
    background: #1a3a1a;
    color: #3fb950;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 3px;
    margin-right: 6px;
    text-transform: uppercase;
  }
  h1 {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 22px !important;
    color: #f0f6fc !important;
    letter-spacing: -0.02em;
  }
  .stSelectbox label, .stTextInput label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px !important;
    color: #8b949e !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  div[data-baseweb="select"] > div {
    background-color: #1c2128 !important;
    border-color: #30363d !important;
    color: #e6edf3 !important;
  }
  div[data-baseweb="input"] > div {
    background-color: #1c2128 !important;
    border-color: #30363d !important;
  }
  input {
    color: #e6edf3 !important;
  }
  .stButton > button {
    background-color: #1f6feb;
    color: white;
    border: none;
    border-radius: 6px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    letter-spacing: 0.05em;
    padding: 8px 18px;
    width: 100%;
  }
  .stButton > button:hover {
    background-color: #388bfd;
  }
  hr {
    border-color: #21262d;
  }
  .legend-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-right: 6px;
  }
</style>
""", unsafe_allow_html=True)

# ─── Data ────────────────────────────────────────────────────────────────────
KEY_CITIES = {
    "Qingdao": {
        "lat": 36.0671, "lon": 120.3826,
        "province": "Shandong", "type": "Port / Manufacturing",
        "color": "#f78166", "description": "Major northern port, auto & electronics exports"
    },
    "Shanghai": {
        "lat": 31.2304, "lon": 121.4737,
        "province": "Shanghai Municipality", "type": "Port / Finance / Manufacturing",
        "color": "#58a6ff", "description": "World's busiest container port"
    },
    "Ningbo": {
        "lat": 29.8683, "lon": 121.5440,
        "province": "Zhejiang", "type": "Port / Manufacturing",
        "color": "#3fb950", "description": "Key export hub, paired with Zhoushan"
    },
    "Shenzhen": {
        "lat": 22.5431, "lon": 114.0579,
        "province": "Guangdong", "type": "Port / Tech / SEZ",
        "color": "#d2a8ff", "description": "Special Economic Zone, electronics & tech"
    },
}

ADDITIONAL_CITIES = {
    "Beijing": {"lat": 39.9042, "lon": 116.4074, "province": "Beijing Municipality"},
    "Guangzhou": {"lat": 23.1291, "lon": 113.2644, "province": "Guangdong"},
    "Tianjin": {"lat": 39.3434, "lon": 117.3616, "province": "Tianjin Municipality"},
    "Wuhan": {"lat": 30.5928, "lon": 114.3055, "province": "Hubei"},
    "Chengdu": {"lat": 30.5728, "lon": 104.0668, "province": "Sichuan"},
    "Hangzhou": {"lat": 30.2741, "lon": 120.1551, "province": "Zhejiang"},
    "Nanjing": {"lat": 32.0603, "lon": 118.7969, "province": "Jiangsu"},
    "Suzhou": {"lat": 31.2989, "lon": 120.5853, "province": "Jiangsu"},
    "Dongguan": {"lat": 23.0207, "lon": 113.7518, "province": "Guangdong"},
    "Foshan": {"lat": 23.0218, "lon": 113.1219, "province": "Guangdong"},
    "Xiamen": {"lat": 24.4798, "lon": 118.0894, "province": "Fujian"},
    "Dalian": {"lat": 38.9140, "lon": 121.6147, "province": "Liaoning"},
    "Zhengzhou": {"lat": 34.7466, "lon": 113.6254, "province": "Henan"},
    "Xi'an": {"lat": 34.3416, "lon": 108.9398, "province": "Shaanxi"},
    "Kunming": {"lat": 25.0389, "lon": 102.7183, "province": "Yunnan"},
    "Harbin": {"lat": 45.8038, "lon": 126.5349, "province": "Heilongjiang"},
    "Changsha": {"lat": 28.2278, "lon": 112.9388, "province": "Hunan"},
    "Hefei": {"lat": 31.8206, "lon": 117.2272, "province": "Anhui"},
    "Jinan": {"lat": 36.6512, "lon": 117.1201, "province": "Shandong"},
    "Wenzhou": {"lat": 28.0000, "lon": 120.6667, "province": "Zhejiang"},
    "Zhoushan": {"lat": 30.0361, "lon": 122.1061, "province": "Zhejiang"},
    "Yantai": {"lat": 37.4638, "lon": 121.4479, "province": "Shandong"},
    "Weifang": {"lat": 36.7069, "lon": 119.1616, "province": "Shandong"},
    "Lianyungang": {"lat": 34.5966, "lon": 119.2218, "province": "Jiangsu"},
    "Nantong": {"lat": 31.9798, "lon": 120.8944, "province": "Jiangsu"},
}

ALL_CITIES = {**KEY_CITIES, **{k: {**v, "type": "City", "color": "#8b949e", "description": ""} for k, v in ADDITIONAL_CITIES.items()}}

ALL_CITIES_DF = pd.DataFrame([
    {"name": k, "lat": v["lat"], "lon": v["lon"],
     "province": v["province"], "type": v.get("type", "City")}
    for k, v in ALL_CITIES.items()
])

# ─── Live Geocoding (fallback for any city not in the local dataset) ──────────
@st.cache_resource
def get_geolocator():
    geolocator = Nominatim(user_agent="china_logistics_streamlit_app")
    # Nominatim's usage policy asks for max 1 request/sec
    return RateLimiter(geolocator.geocode, min_delay_seconds=1, swallow_exceptions=True)

@st.cache_data(show_spinner=False, ttl=3600)
def geocode_search(query):
    """Look up any place name in China via OpenStreetMap/Nominatim.
    Returns a list of city-like dicts so cities/towns/districts not in the
    curated ALL_CITIES dataset (e.g. 'Heze City', 'Zhangjiagang') can still
    be found and used."""
    if not query or len(query) < 2:
        return []
    geocode = get_geolocator()
    try:
        locations = geocode(
            query,
            exactly_one=False,
            addressdetails=True,
            country_codes="cn",
            language="en",
            timeout=8,
        )
    except Exception:
        locations = None
    if not locations:
        return []

    results = []
    seen = set()
    for loc in locations[:8]:
        addr = loc.raw.get("address", {}) if hasattr(loc, "raw") else {}
        # Prefer the most specific place-type name available
        name = (
            addr.get("city") or addr.get("town") or addr.get("county")
            or addr.get("village") or addr.get("municipality")
            or loc.address.split(",")[0]
        )
        province = (
            addr.get("state") or addr.get("province")
            or addr.get("region") or "China"
        )
        key = (name.lower(), round(loc.latitude, 2), round(loc.longitude, 2))
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "name": name,
            "lat": loc.latitude,
            "lon": loc.longitude,
            "province": province,
            "type": "City (search)",
            "color": "#e3b341",
            "description": "",
        })
    return results

def get_all_cities():
    """Merged view of the curated dataset plus any cities found via live
    search this session, so they show up in the distance calculator too."""
    custom = st.session_state.get("custom_cities", {})
    return {**ALL_CITIES, **custom}

# ─── Helper Functions ─────────────────────────────────────────────────────────
def calc_distance(city1, city2):
    cities = get_all_cities()
    c1 = (cities[city1]["lat"], cities[city1]["lon"])
    c2 = (cities[city2]["lat"], cities[city2]["lon"])
    return round(geodesic(c1, c2).km, 1)

def search_cities(query):
    if not query or len(query) < 2:
        return []
    q = query.lower()
    results = []
    seen_names = set()

    # 1) Local curated dataset (exact/substring match on name or province)
    for name, data in get_all_cities().items():
        if (q in name.lower() or q in data["province"].lower()):
            results.append({"name": name, **data})
            seen_names.add(name.lower())

    # 2) Live geocoding fallback — catches cities/towns not in the curated
    #    list (e.g. "Heze City", "Zhangjiagang") without requiring an exact
    #    province match.
    if len(results) < 8:
        for r in geocode_search(query):
            if r["name"].lower() not in seen_names:
                results.append(r)
                seen_names.add(r["name"].lower())

    return results[:8]

def make_popup_html(name, data):
    is_key = name in KEY_CITIES
    tag_class = "port-tag" if is_key else "city-tag"
    tag_text = data.get("type", "City")
    desc = data.get("description", "")
    desc_row = f"<div style='color:#8b949e;font-size:11px;margin-top:4px;'>{desc}</div>" if desc else ""
    return f"""
    <div style='font-family:IBM Plex Sans,sans-serif;min-width:200px;padding:4px;'>
      <div style='font-size:15px;font-weight:600;color:#f0f6fc;margin-bottom:6px;'>{name}</div>
      <span class='{tag_class}' style='
        display:inline-block;background:{"#0d419d" if is_key else "#21262d"};
        color:{"#58a6ff" if is_key else "#8b949e"};
        font-size:10px;padding:2px 7px;border-radius:3px;font-family:monospace;
      '>{tag_text}</span>
      <div style='margin-top:8px;'>
        <div style='font-size:11px;color:#8b949e;'>Province / Municipality</div>
        <div style='font-size:13px;color:#e6edf3;'>{data["province"]}</div>
      </div>
      <div style='margin-top:6px;'>
        <div style='font-size:11px;color:#8b949e;'>Coordinates</div>
        <div style='font-size:12px;color:#e6edf3;font-family:monospace;'>{data["lat"]}°N, {data["lon"]}°E</div>
      </div>
      {desc_row}
    </div>
    """

def build_map(center_lat=33.5, center_lon=114.0, zoom=5,
              show_additional=True, highlight=None,
              dist_city1=None, dist_city2=None,
              searched_city=None):

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom,
        tiles=None,
        prefer_canvas=True,
    )

    # Light tile layer
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
        name="Light",
        max_zoom=19,
    ).add_to(m)

    # Additional cities (secondary)
    if show_additional:
        for name, data in ADDITIONAL_CITIES.items():
            folium.CircleMarker(
                location=[data["lat"], data["lon"]],
                radius=4,
                color="#6e7f96",
                fill=True,
                fill_color="#8fa3bc",
                fill_opacity=0.75,
                tooltip=folium.Tooltip(f"<b style='font-family:monospace'>{name}</b><br><small>{data['province']}</small>"),
                popup=folium.Popup(make_popup_html(name, {**data, "type": "City", "description": ""}), max_width=240),
            ).add_to(m)

    # Distance line
    if dist_city1 and dist_city2 and dist_city1 != dist_city2:
        cities = get_all_cities()
        c1 = cities[dist_city1]
        c2 = cities[dist_city2]
        folium.PolyLine(
            locations=[[c1["lat"], c1["lon"]], [c2["lat"], c2["lon"]]],
            color="#f0883e",
            weight=2,
            dash_array="8 4",
            opacity=0.9,
        ).add_to(m)
        mid_lat = (c1["lat"] + c2["lat"]) / 2
        mid_lon = (c1["lon"] + c2["lon"]) / 2
        dist = calc_distance(dist_city1, dist_city2)
        folium.Marker(
            location=[mid_lat, mid_lon],
            icon=folium.DivIcon(
                html=f"""<div style='
                    background:#ffffffee;border:1px solid #f0883e;
                    color:#c05000;font-family:monospace;font-size:11px;
                    padding:3px 8px;border-radius:4px;white-space:nowrap;
                    box-shadow:0 2px 6px rgba(0,0,0,0.15);
                '>{dist} km</div>""",
                icon_size=(90, 24),
                icon_anchor=(45, 12),
            ),
        ).add_to(m)

    # Key cities
    for name, data in KEY_CITIES.items():
        is_highlight = highlight == name
        size = 14 if is_highlight else 10
        pulse_color = data["color"]

        icon_html = f"""
        <div style="position:relative;width:{size*3}px;height:{size*3}px;">
          <div style="
            position:absolute;top:50%;left:50%;
            transform:translate(-50%,-50%);
            width:{size*2}px;height:{size*2}px;
            background:{pulse_color}33;
            border-radius:50%;
            border:1px solid {pulse_color}88;
          "></div>
          <div style="
            position:absolute;top:50%;left:50%;
            transform:translate(-50%,-50%);
            width:{size}px;height:{size}px;
            background:{pulse_color};
            border-radius:50%;
            border:2px solid white;
            box-shadow:0 0 8px {pulse_color};
          "></div>
          <div style="
            position:absolute;top:50%;left:{size*1.2}px;
            transform:translateY(-50%);
            background:#ffffffee;
            color:#1a1a2e;
            font-family:monospace;
            font-size:10px;font-weight:600;
            padding:2px 5px;border-radius:3px;
            white-space:nowrap;
            border:1px solid #c8d0d8;
            box-shadow:0 1px 4px rgba(0,0,0,0.15);
          ">{name}</div>
        </div>
        """

        folium.Marker(
            location=[data["lat"], data["lon"]],
            icon=folium.DivIcon(
                html=icon_html,
                icon_size=(size * 3, size * 3),
                icon_anchor=(size * 1.5, size * 1.5),
            ),
            tooltip=folium.Tooltip(f"<b>{name}</b> — {data['province']}"),
            popup=folium.Popup(make_popup_html(name, data), max_width=260),
        ).add_to(m)

    # Distance endpoint highlights
    _non_key_cities = {**ADDITIONAL_CITIES, **st.session_state.get("custom_cities", {})}
    for dc in [dist_city1, dist_city2]:
        if dc and dc in _non_key_cities:
            d = _non_key_cities[dc]
            folium.CircleMarker(
                location=[d["lat"], d["lon"]],
                radius=7,
                color="#e06c00",
                fill=True, fill_color="#f0883e", fill_opacity=0.8,
            ).add_to(m)

    # ── Search result pin ─────────────────────────────────────────
    if searched_city:
        sc = searched_city
        is_key_city = sc["name"] in KEY_CITIES
        if not is_key_city:
            pin_html = f"""
            <div style="position:relative;width:160px;height:60px;">
              <!-- drop shadow ring -->
              <div style="
                position:absolute;top:8px;left:8px;
                width:28px;height:28px;
                background:#ff4500;
                border-radius:50% 50% 50% 0;
                transform:rotate(-45deg);
                border:3px solid white;
                box-shadow:0 3px 12px rgba(255,69,0,0.6);
              "></div>
              <!-- inner dot -->
              <div style="
                position:absolute;top:16px;left:16px;
                width:12px;height:12px;
                background:white;
                border-radius:50%;
              "></div>
              <!-- label -->
              <div style="
                position:absolute;top:4px;left:44px;
                background:#ff4500;
                color:white;
                font-family:monospace;
                font-size:12px;font-weight:700;
                padding:4px 10px;
                border-radius:5px;
                white-space:nowrap;
                box-shadow:0 2px 8px rgba(255,69,0,0.4);
                border:2px solid white;
              ">{sc["name"]}</div>
              <!-- province sub-label -->
              <div style="
                position:absolute;top:30px;left:44px;
                background:white;
                color:#333;
                font-family:monospace;
                font-size:10px;
                padding:2px 8px;
                border-radius:3px;
                white-space:nowrap;
                box-shadow:0 1px 4px rgba(0,0,0,0.15);
                border:1px solid #ddd;
              ">{sc["province"]}</div>
            </div>
            """
            folium.Marker(
                location=[sc["lat"], sc["lon"]],
                icon=folium.DivIcon(
                    html=pin_html,
                    icon_size=(160, 60),
                    icon_anchor=(22, 38),
                ),
                tooltip=folium.Tooltip(f"<b>🔍 {sc['name']}</b><br>{sc['province']}"),
                popup=folium.Popup(make_popup_html(sc["name"], {
                    **sc, "type": "Search Result", "description": ""}), max_width=250),
                z_index_offset=1000,
            ).add_to(m)
        # If it's a key city, it's already rendered with its own marker above;
        # just add a pulsing ring around it for extra emphasis
        else:
            kc = KEY_CITIES[sc["name"]]
            folium.CircleMarker(
                location=[kc["lat"], kc["lon"]],
                radius=22,
                color="#ff4500",
                fill=False,
                weight=3,
                opacity=0.85,
                tooltip=folium.Tooltip(f"<b>🔍 {sc['name']}</b>"),
            ).add_to(m)

    return m


# ─── Session State ─────────────────────────────────────────────────────────────
if "map_center" not in st.session_state:
    st.session_state.map_center = [33.5, 114.0]
if "map_zoom" not in st.session_state:
    st.session_state.map_zoom = 5
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "dist_city1" not in st.session_state:
    st.session_state.dist_city1 = None
if "dist_city2" not in st.session_state:
    st.session_state.dist_city2 = None
if "searched_city" not in st.session_state:
    st.session_state.searched_city = None
if "custom_cities" not in st.session_state:
    st.session_state.custom_cities = {}


# ─── Layout ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 🗺️ China Logistics")
    st.markdown("<div style='font-family:monospace;font-size:11px;color:#8b949e;'>Manufacturing & Port Regions</div>", unsafe_allow_html=True)
    st.markdown("---")

    # ── Search ────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-header">Search</div>', unsafe_allow_html=True)
    search_input = st.text_input("", placeholder="City, district, province…", label_visibility="collapsed")

    if search_input:
        with st.spinner("Searching…"):
            results = search_cities(search_input)
        if results:
            for i, r in enumerate(results):
                is_key = r["name"] in KEY_CITIES
                is_live = r.get("type") == "City (search)"
                icon = "🔴" if is_key else ("🟡" if is_live else "⚪")
                label = f"{icon} {r['name']} · {r['province']}"
                if st.button(label, key=f"search_{i}_{r['name']}"):
                    st.session_state.map_center = [r["lat"], r["lon"]]
                    st.session_state.map_zoom = 9
                    st.session_state.searched_city = {
                        "name": r["name"],
                        "lat": r["lat"],
                        "lon": r["lon"],
                        "province": r["province"],
                    }
                    # Persist any city found via live geocoding so it also
                    # becomes selectable in the Distance Calculator below.
                    if is_live and r["name"] not in ALL_CITIES:
                        st.session_state.custom_cities[r["name"]] = {
                            "lat": r["lat"], "lon": r["lon"],
                            "province": r["province"], "type": "City",
                            "color": "#e3b341", "description": "",
                        }
        else:
            st.caption("No results found. Try a different spelling, or the English/Pinyin name.")

    if st.session_state.searched_city:
        sc = st.session_state.searched_city
        st.markdown(f"""
        <div style='background:#fff8e6;border:1px solid #f0a030;border-radius:6px;
                    padding:8px 12px;margin-top:8px;'>
          <div style='font-size:10px;color:#a06010;font-family:monospace;
                      text-transform:uppercase;letter-spacing:0.08em;'>Showing on map</div>
          <div style='font-size:13px;font-weight:600;color:#1a1a2e;margin-top:2px;'>📍 {sc["name"]}</div>
          <div style='font-size:11px;color:#666;'>{sc["province"]}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("✕  Clear pin", key="clear_search"):
            st.session_state.searched_city = None

    # ── Key Cities ────────────────────────────────────────────────
    st.markdown('<div class="sidebar-header">Key Cities</div>', unsafe_allow_html=True)
    for name, data in KEY_CITIES.items():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"""
            <div class="metric-card">
              <div style='display:flex;align-items:center;gap:8px;'>
                <div style='width:10px;height:10px;border-radius:50%;background:{data["color"]};flex-shrink:0;'></div>
                <div>
                  <div style='font-size:13px;font-weight:600;color:#f0f6fc;'>{name}</div>
                  <div style='font-size:10px;color:#8b949e;font-family:monospace;'>{data["province"]}</div>
                  <div style='font-size:10px;color:#8b949e;margin-top:2px;font-family:monospace;'>{data["lat"]}°N {data["lon"]}°E</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            if st.button("→", key=f"goto_{name}"):
                st.session_state.map_center = [data["lat"], data["lon"]]
                st.session_state.map_zoom = 9

    # ── Overview ──────────────────────────────────────────────────
    st.markdown("---")
    if st.button("🌏  Reset Overview"):
        st.session_state.map_center = [33.5, 114.0]
        st.session_state.map_zoom = 5

    # ── Distance Calculator ───────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="sidebar-header">Distance Calculator</div>', unsafe_allow_html=True)

    with st.expander("🔎  Can't find a city? Search here", expanded=False):
        dist_search_input = st.text_input(
            "", placeholder="e.g. Heze City, Zhangjiagang…",
            label_visibility="collapsed", key="dist_search_input",
        )
        if dist_search_input:
            with st.spinner("Searching…"):
                dist_results = search_cities(dist_search_input)
            if dist_results:
                for i, r in enumerate(dist_results):
                    label = f"➕ {r['name']} · {r['province']}"
                    if st.button(label, key=f"distsearch_{i}_{r['name']}"):
                        if r["name"] not in ALL_CITIES:
                            st.session_state.custom_cities[r["name"]] = {
                                "lat": r["lat"], "lon": r["lon"],
                                "province": r["province"], "type": "City",
                                "color": "#e3b341", "description": "",
                            }
                        st.rerun()
            else:
                st.caption("No results found. Try the English/Pinyin name.")

    all_city_names = sorted(list(get_all_cities().keys()))
    city_options = ["— Select city —"] + all_city_names

    idx1 = city_options.index(st.session_state.dist_city1) if st.session_state.dist_city1 in city_options else 0
    idx2 = city_options.index(st.session_state.dist_city2) if st.session_state.dist_city2 in city_options else 0

    city1_sel = st.selectbox("From", city_options, index=idx1, key="city1_sel")
    city2_sel = st.selectbox("To",   city_options, index=idx2, key="city2_sel")

    city1 = city1_sel if city1_sel != "— Select city —" else None
    city2 = city2_sel if city2_sel != "— Select city —" else None
    st.session_state.dist_city1 = city1
    st.session_state.dist_city2 = city2

    if city1 and city2 and city1 != city2:
        dist_km = calc_distance(city1, city2)
        dist_mi = round(dist_km * 0.621371, 1)
        st.markdown(f"""
        <div class="distance-result">
          <div class="distance-km">{dist_km:,} km</div>
          <div class="distance-label">straight-line distance · {dist_mi:,} mi</div>
          <div style='margin-top:8px;font-size:11px;color:#8b949e;'>{city1} → {city2}</div>
        </div>
        """, unsafe_allow_html=True)

        col_show, col_clear = st.columns([3, 2])
        with col_show:
            if st.button("📍  Show on Map", key="show_dist"):
                cities = get_all_cities()
                c1 = cities[city1]
                c2 = cities[city2]
                st.session_state.map_center = [(c1["lat"] + c2["lat"]) / 2,
                                               (c1["lon"] + c2["lon"]) / 2]
                st.session_state.map_zoom = 5
        with col_clear:
            if st.button("✕ Clear", key="clear_dist"):
                st.session_state.dist_city1 = None
                st.session_state.dist_city2 = None
                st.rerun()

    elif city1 and city2 and city1 == city2:
        st.caption("Select two different cities.")
    else:
        st.caption("Select two cities to calculate distance.")

    # ── Layer Toggle ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="sidebar-header">Map Layers</div>', unsafe_allow_html=True)
    show_secondary = st.toggle("Show secondary cities", value=True)


# ─── Main Map ──────────────────────────────────────────────────────────────────
col_title, col_coords = st.columns([3, 1])
with col_title:
    st.markdown("### China Manufacturing & Logistics Regions")
with col_coords:
    st.markdown(f"""
    <div style='text-align:right;font-family:monospace;font-size:11px;color:#8b949e;padding-top:8px;'>
      📍 {st.session_state.map_center[0]:.2f}°N, {st.session_state.map_center[1]:.2f}°E
    </div>""", unsafe_allow_html=True)

# Build and display map
active_d1 = st.session_state.dist_city1 if (st.session_state.dist_city1 and st.session_state.dist_city2 and st.session_state.dist_city1 != st.session_state.dist_city2) else None
active_d2 = st.session_state.dist_city2 if (st.session_state.dist_city1 and st.session_state.dist_city2 and st.session_state.dist_city1 != st.session_state.dist_city2) else None

# Map key changes only when markers/content change — NOT on every zoom/pan
# This prevents Streamlit from destroying and recreating the map widget on navigation
_sc_key = st.session_state.searched_city["name"] if st.session_state.searched_city else "none"
_map_key = f"map_{active_d1}_{active_d2}_{_sc_key}_{show_secondary}"

m = build_map(
    center_lat=st.session_state.map_center[0],
    center_lon=st.session_state.map_center[1],
    zoom=st.session_state.map_zoom,
    show_additional=show_secondary,
    dist_city1=active_d1,
    dist_city2=active_d2,
    searched_city=st.session_state.searched_city,
)

map_data = st_folium(
    m,
    width="100%",
    height=650,
    key=_map_key,
    returned_objects=["last_clicked"],  # don't return center/zoom — stops rerun on every pan/zoom
)

# No center/zoom sync needed — Folium/Leaflet handles its own viewport state
# Syncing caused a rerun on every pan/zoom interaction, creating the flicker

# ─── Stats Strip ──────────────────────────────────────────────────────────────
st.markdown("---")
c1, c2, c3, c4 = st.columns(4)

distances = {
    "QD→SH": calc_distance("Qingdao", "Shanghai"),
    "SH→NB": calc_distance("Shanghai", "Ningbo"),
    "NB→SZ": calc_distance("Ningbo", "Shenzhen"),
    "QD→SZ": calc_distance("Qingdao", "Shenzhen"),
}

with c1:
    st.markdown(f"""<div class="metric-card">
      <div class="metric-label">Qingdao → Shanghai</div>
      <div class="metric-value">{distances['QD→SH']:,}</div>
      <div class="metric-sub">km straight-line</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="metric-card">
      <div class="metric-label">Shanghai → Ningbo</div>
      <div class="metric-value">{distances['SH→NB']:,}</div>
      <div class="metric-sub">km straight-line</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="metric-card">
      <div class="metric-label">Ningbo → Shenzhen</div>
      <div class="metric-value">{distances['NB→SZ']:,}</div>
      <div class="metric-sub">km straight-line</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class="metric-card">
      <div class="metric-label">Qingdao → Shenzhen</div>
      <div class="metric-value">{distances['QD→SZ']:,}</div>
      <div class="metric-sub">km straight-line</div>
    </div>""", unsafe_allow_html=True)

# ─── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;font-family:monospace;font-size:10px;color:#444c56;margin-top:12px;'>
  Data for reference only · Coordinates sourced from public geographic databases · Distances are great-circle (straight-line)
</div>
""", unsafe_allow_html=True)
