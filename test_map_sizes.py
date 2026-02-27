"""
Test different map sizes to find what works and what doesn't
"""
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import time

st.title("Map Size Testing")

# Generate test data with different sizes
test_sizes = [50, 100, 200, 300, 400, 445]

for size in test_sizes:
    st.header(f"Test: {size} markers")

    # Generate fake colony data
    test_df = pd.DataFrame({
        'ColonyName': [f'Colony {i}' for i in range(size)],
        'Latitude': [25 + (i % 60) * 0.1 for i in range(size)],
        'Longitude': [-97 + (i % 150) * 0.1 for i in range(size)],
        'BirdCount': [100 + i for i in range(size)]
    })

    try:
        start_time = time.time()

        # Test 1: Simple map with all markers
        with st.expander(f"Test 1: Simple map ({size} markers)", expanded=False):
            m1 = folium.Map(
                location=[27.5, -90.0],
                zoom_start=6,
                tiles='OpenStreetMap',
                control_scale=True
            )

            for idx, row in test_df.iterrows():
                folium.Marker(
                    location=[row['Latitude'], row['Longitude']],
                    tooltip=f"{row['ColonyName']}: {row['BirdCount']} birds",
                    icon=folium.Icon(color='blue', icon='info-sign', prefix='glyphicon')
                ).add_to(m1)

            st_folium(m1, width=700, height=400, returned_objects=[], key=f"simple_{size}")
            elapsed = time.time() - start_time
            st.success(f"✅ Rendered in {elapsed:.2f}s")

        # Test 2: Map with MarkerCluster
        with st.expander(f"Test 2: Clustered map ({size} markers)", expanded=False):
            start_time = time.time()
            m2 = folium.Map(
                location=[27.5, -90.0],
                zoom_start=6,
                tiles='OpenStreetMap',
                control_scale=True
            )

            marker_cluster = MarkerCluster().add_to(m2)

            for idx, row in test_df.iterrows():
                folium.Marker(
                    location=[row['Latitude'], row['Longitude']],
                    tooltip=f"{row['ColonyName']}: {row['BirdCount']} birds",
                    icon=folium.Icon(color='red', icon='info-sign', prefix='glyphicon')
                ).add_to(marker_cluster)

            st_folium(m2, width=700, height=400, returned_objects=[], key=f"cluster_{size}")
            elapsed = time.time() - start_time
            st.success(f"✅ Rendered in {elapsed:.2f}s")

        # Test 3: CircleMarkers (lighter weight)
        with st.expander(f"Test 3: Circle markers ({size} markers)", expanded=False):
            start_time = time.time()
            m3 = folium.Map(
                location=[27.5, -90.0],
                zoom_start=6,
                tiles='OpenStreetMap',
                control_scale=True
            )

            for idx, row in test_df.iterrows():
                folium.CircleMarker(
                    location=[row['Latitude'], row['Longitude']],
                    radius=5,
                    popup=f"{row['ColonyName']}: {row['BirdCount']} birds",
                    tooltip=f"{row['ColonyName']}",
                    color='blue',
                    fill=True,
                    fillColor='blue'
                ).add_to(m3)

            st_folium(m3, width=700, height=400, returned_objects=[], key=f"circle_{size}")
            elapsed = time.time() - start_time
            st.success(f"✅ Rendered in {elapsed:.2f}s")

    except Exception as e:
        st.error(f"❌ Failed at {size} markers: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

    st.divider()

st.info("Test complete! Check which map types rendered successfully.")
