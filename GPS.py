import spacy
import openrouteservice
import folium
import webbrowser
import os
import sys

# Load SpaCy model
nlp = spacy.load('en_core_web_lg')

def process_location(location):
    # Function to get coordinates from a location string using OpenRouteService geocoding
    def get_coordinates(api_key, location):
        client = openrouteservice.Client(key=api_key)
        geocode = client.pelias_search(text=location)
        if geocode and 'features' in geocode and len(geocode['features']) > 0:
            coords = geocode['features'][0]['geometry']['coordinates']
            return (coords[0], coords[1])
        else:
            raise ValueError(f"Could not find coordinates for location: {location}")

    # Function to get directions using OpenRouteService
    def get_directions(api_key, start_coords, end_coords):
        client = openrouteservice.Client(key=api_key)
        coords = [start_coords, end_coords]
        routes = client.directions(coords, profile='driving-car', format='geojson')
        return routes

    # Function to create a map with the route
    def create_map_with_route(maptiler_key, start_coords, end_coords, route):
        # Create a folium map centered at the midpoint of the route
        midpoint = [(start_coords[1] + end_coords[1]) / 2, (start_coords[0] + end_coords[0]) / 2]
        m = folium.Map(
            location=midpoint,
            zoom_start=13,
            tiles=f'https://api.maptiler.com/maps/streets/{{z}}/{{x}}/{{y}}.png?key={maptiler_key}',
            attr='MapTiler'
        )

        # Add the start and end points to the map
        folium.Marker(location=[start_coords[1], start_coords[0]], popup='Start', icon=folium.Icon(color='green')).add_to(m)
        folium.Marker(location=[end_coords[1], end_coords[0]], popup='End', icon=folium.Icon(color='red')).add_to(m)

        # Extract the route geometry and add it to the map
        route_coords = [(coord[1], coord[0]) for coord in route['features'][0]['geometry']['coordinates']]
        folium.PolyLine(route_coords, color='blue', weight=5).add_to(m)

        return m

    # Function to extract duration from route
    def get_duration(route):
        # Extracting duration in seconds from the first segment of the route
        duration = route['features'][0]['properties']['segments'][0]['duration']
        return duration

    # Define the API keys
    openrouteservice_api_key = '5b3ce3597851110001cf6248bd1580dcedcd4fb1937a60063427037d'
    maptiler_api_key = 'hcGsEThHi4W8qibt9KAm'

    # Input locations
    start_location = input("Enter your location to estimate the time: ")
    end_location = location

    # Get coordinates for the input locations
    try:
        start_coords = get_coordinates(openrouteservice_api_key, start_location)
        end_coords = get_coordinates(openrouteservice_api_key, end_location)
    except ValueError as e:
        print(e)
        sys.exit(1)

    # Get directions
    route = get_directions(openrouteservice_api_key, start_coords, end_coords)

    # Get duration
    duration_seconds = get_duration(route)
    duration_minutes = duration_seconds / 60

    # Create map with route
    route_map = create_map_with_route(maptiler_api_key, start_coords, end_coords, route)

    # Save the map to an HTML file
    file_path = 'route_map.html'
    route_map.save(file_path)

    # Print the path to the HTML file
    print(f"Map with route saved as {file_path}")

    # Print the duration
    print(f"Duration: {duration_minutes:.2f} minutes")

    # Open the map in the default web browser
    try:
        webbrowser.open_new_tab(f'file://{os.path.abspath(file_path)}')
    except Exception as e:
        print(f"Failed to open the map automatically. Please open the file manually at: {os.path.abspath(file_path)}")
        print(e)
    else:
        print("The map has been opened in your default web browser.")


def analyze_text(text):
    # Use SpaCy to process the text
    doc = nlp(text)

    # Iterate over the named entities in the text
    for ent in doc.ents:
        if ent.label_ == 'GPE':  # 'GPE' stands for Geo-Political Entity, often a location
            process_location(ent.text)

