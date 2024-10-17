import folium

# List of coordinates (latitude, longitude)
coordinates = [
    (16.45664856720629, 107.58525431345238),
    (16.457299736740776, 107.58509879158913),
    (16.457481627281574, 107.58601674990393),
    (16.45797306356558, 107.58917522823675),
    (16.46313270098462, 107.59494022071998),
    (16.46733402941242, 107.59058748283674),
    (16.46733402941242, 107.59058748283674),
    (16.4686224126527, 107.59207573031551),
    (16.468226297807906, 107.59242978188783)
    # Add more coordinates as needed
]

# Create a map centered around the first coordinate
my_map = folium.Map(location=coordinates[0], zoom_start=13)

# Add points to the map
# for coordinate in coordinates:
#     folium.Marker(location=coordinate).add_to(my_map)
folium.Marker(location=(16.45664856720629, 107.58525431345238)).add_to(my_map)

# Add a line connecting the points
folium.PolyLine(locations=coordinates, color="blue").add_to(my_map)

# Save the map as an HTML file
my_map.save("route_map.html")
