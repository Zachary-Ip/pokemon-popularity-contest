import pandas as pd
import requests
import streamlit as st


# Helper function to fetch Pokemon data
def fetch_pokemon_data(gens):

    dataset = []
    gen_bar = st.progress(0, text="Fetching Pokemon data...")
    pk_bar = st.progress(0, text="")
    for i, gen in enumerate(gens):
        gen_bar.progress(i / len(gens), text=f"Fetching generation {gen} data...")
        if gen not in range(1, 10):
            st.error("Invalid generation selected.")
            return []

        url = f"https://pokeapi.co/api/v2/generation/{gen}/"
        response = requests.get(url)
        if response.status_code != 200:
            st.error(
                f"Error fetching data for generation {gen}: {response.status_code}"
            )
            return []
        data = response.json()
        for idx, pokemon in enumerate(data["pokemon_species"]):
            pk_bar.progress(
                idx / len(data["pokemon_species"]),
                text=f"Fetching data for {pokemon['name'].capitalize()}",
            )
            pk_id = pokemon["url"].split("/")[-2]
            pk_response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{pk_id}")
            if response.status_code != 200:
                st.error(
                    f"Error fetching data for generation {gen}: {response.status_code}"
                )
                return []
            else:
                try:
                    pk_data = pk_response.json()
                except json.JSONDecodeError:
                    st.error(
                        f"Error decoding JSON for Pokemon {pokemon['name'].upper()}: {pk_response.status_code}"
                    )
                    continue
                dataset.append(
                    {
                        "id": pk_data["id"],
                        "name": pk_data["name"].capitalize(),
                        "image_url": pk_data["sprites"]["front_default"],
                        "elo": 400,
                        "wins": 0,
                        "losses": 0,
                    }
                )
    return dataset
