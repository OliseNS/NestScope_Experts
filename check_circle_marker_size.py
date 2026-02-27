"""
Compare HTML size of Icon markers vs CircleMarkers
"""
import folium
import pandas as pd

def test_icon_markers(num_markers):
    m = folium.Map(location=[27.5, -90.0], zoom_start=6, tiles='OpenStreetMap')
    test_df = pd.DataFrame({
        'Latitude': [25 + (i % 60) * 0.1 for i in range(num_markers)],
        'Longitude': [-97 + (i % 150) * 0.1 for i in range(num_markers)],
        'Name': [f'Colony {i}' for i in range(num_markers)]
    })

    for idx, row in test_df.iterrows():
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            tooltip=row['Name'],
            icon=folium.Icon(color='blue', icon='info-sign', prefix='glyphicon')
        ).add_to(m)

    html = m._repr_html_()
    return len(html.encode('utf-8'))

def test_circle_markers(num_markers):
    m = folium.Map(location=[27.5, -90.0], zoom_start=6, tiles='OpenStreetMap')
    test_df = pd.DataFrame({
        'Latitude': [25 + (i % 60) * 0.1 for i in range(num_markers)],
        'Longitude': [-97 + (i % 150) * 0.1 for i in range(num_markers)],
        'Name': [f'Colony {i}' for i in range(num_markers)]
    })

    for idx, row in test_df.iterrows():
        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=6,
            tooltip=row['Name'],
            color='blue',
            fill=True,
            fillColor='blue',
            fillOpacity=0.7
        ).add_to(m)

    html = m._repr_html_()
    return len(html.encode('utf-8'))

print("Comparing Icon markers vs CircleMarkers:")
print("-" * 70)
print(f"{'Markers':>8} | {'Icon (MB)':>12} | {'Circle (MB)':>12} | {'Reduction':>10}")
print("-" * 70)

for size in [190, 300, 400, 445]:
    icon_size = test_icon_markers(size)
    circle_size = test_circle_markers(size)
    icon_mb = icon_size / (1024 * 1024)
    circle_mb = circle_size / (1024 * 1024)
    reduction = ((icon_size - circle_size) / icon_size) * 100

    print(f"{size:8d} | {icon_mb:11.2f} | {circle_mb:11.2f} | {reduction:9.1f}%")
