import os
import random
import traceback

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


def get_setting(key):
    # First try to get from streamlit secrets (for cloud deployment)
    try:
        if key in st.secrets:
            return st.secrets[key]
    # Otherwise try environment variables (for local development)
    except st.errors.StreamlitSecretNotFoundError:
        return os.environ.get(key)


if "pokemon_a" not in st.session_state or "pokemon_b" not in st.session_state:
    # Initialize session state variables for Pokemon A and B
    st.session_state.pokemon_a = None
    st.session_state.pokemon_b = None

# Initialize Supabase client
SUPABASE_URL = get_setting("SUPABASE_URL")
SUPABASE_KEY = get_setting("SUPABASE_KEY")
SERVICE_EMAIL = get_setting("SERVICE_EMAIL")
SERVICE_PASSWORD = get_setting("SERVICE_PASSWORD")


if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Missing Supabase credentials. Check your .env file or Streamlit secrets.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# Authenticate as service account
def authenticate_service_account():
    try:
        response = supabase.auth.sign_in_with_password(
            {"email": SERVICE_EMAIL, "password": SERVICE_PASSWORD}
        )
        return response
    except Exception as e:
        st.error(f"Authentication failed: {str(e)}")
        return None


def ensure_authenticated():
    # Check if session exists and is valid
    if "supabase_auth" not in st.session_state:
        auth_response = authenticate_service_account()
        if auth_response and hasattr(auth_response, "session"):
            st.session_state.supabase_auth = auth_response.session
            # Update client with session
            supabase.auth.set_session(
                auth_response.session.access_token, auth_response.session.refresh_token
            )
            return True
        return False

    # If session exists but might be expired, refresh it
    try:
        # Auto-refresh happens through the client
        return True
    except:
        # If refresh fails, try authenticating again
        auth_response = authenticate_service_account()
        if auth_response and hasattr(auth_response, "session"):
            st.session_state.supabase_auth = auth_response.session
            supabase.auth.set_session(
                auth_response.session.access_token, auth_response.session.refresh_token
            )
            return True
        return False


def load_pokemon_data(gens=None):
    """
    Load all Pokemon data from Supabase database for the given list of generations.
    """
    if gens:
        try:
            if not isinstance(gens, list):
                gens = [gens]

            response = (
                supabase.table("Community Pokemon Rankings")
                .select("*")
                .in_("gen", gens)
                .execute()
            )
            return response.data

        except Exception as e:
            st.error(f"Failed to load Pokemon data: {e}")
            return None
    else:
        response = supabase.table("Community Pokemon Rankings").select("*").execute()
        return response.data


def generation_module(key, label="Filter by Pokémon generation:"):
    """
    Display a multi-select pills UI for choosing Pokémon generations (1-9).
    Returns a list of selected generation numbers.
    """
    return st.pills(
        label,
        list(range(1, 10)),
        default=[],
        selection_mode="multi",
        key=key,
    )


def type_module(label="Filter by pokemon type"):
    """
    Display a multi-select pills UI for choosing Pokémon types.
    Returns a list of selected types.
    """
    types = [
        "Normal",
        "Fire",
        "Water",
        "Grass",
        "Electric",
        "Ice",
        "Fighting",
        "Poison",
        "Ground",
        "Flying",
        "Psychic",
        "Bug",
        "Rock",
        "Ghost",
        "Dragon",
        "Dark",
        "Steel",
        "Fairy",
    ]
    return st.pills(label, types, default=[], selection_mode="multi")


def select_pokemon(pokemon_data):
    # Check if there are any pokemon who have not been compared yet using total wins + losses
    not_compared = [
        pokemon
        for pokemon in pokemon_data
        if pokemon.get("wins", 0) + pokemon.get("losses", 0) == 0
    ]
    if len(not_compared) > 1:
        return random.sample(not_compared, 2)
    else:
        # If all Pokemon have been compared, get a random number to determine selection behavior
        behavior = random.random()

        if behavior < 0.25:
            # Find the pokemon with the fewest wins and losses
            fewest_wins_losses = min(
                pokemon_data,
                key=lambda x: x.get("wins", 0) + x.get("losses", 0),
            )
            # get the pokemon with the fewest wins and losses
            fewest_wins_losses = [
                pokemon
                for pokemon in pokemon_data
                if pokemon.get("wins", 0) + pokemon.get("losses", 0)
                == fewest_wins_losses.get("wins", 0)
                + fewest_wins_losses.get("losses", 0)
            ]
            if len(fewest_wins_losses) > 1:
                return random.sample(fewest_wins_losses, 2)

        elif behavior < 0.75:
            # Break the dataset into quartiles and
            # select two pokemon from a random quartile to keep comparisons competitive
            sorted_pokemon = sorted(pokemon_data, key=lambda x: x.get("elo", 0))
            quartile_size = len(sorted_pokemon) // 4
            quartile = random.randint(0, 3)
            start_index = quartile * quartile_size
            end_index = start_index + quartile_size
            quartile_pokemon = sorted_pokemon[start_index:end_index]
            if len(quartile_pokemon) > 1:
                return random.sample(quartile_pokemon, 2)

    return random.sample(pokemon_data, 2)


def update_pokemon_ratings(pokemon_list):
    """
    Update the Elo ratings and win/loss counts of Pokemon in the Supabase database.

    Args:
        pokemon_list: List of dictionaries with Pokemon updates
    """
    if not ensure_authenticated():
        st.error("Failed to authenticate with Supabase.")
        st.stop()
    try:
        for pokemon_to_update in pokemon_list:
            pokemon_id = pokemon_to_update["id"]

            fetch_response = (
                supabase.table("Community Pokemon Rankings")
                .select("elo", "wins", "losses")
                .eq("id", pokemon_id)
                .single()
                .execute()
            )

            current = fetch_response.data

            # Build update payload
            new_wins = current["wins"]
            new_losses = current["losses"]
            if pokemon_to_update["result"] == 1:
                new_wins += 1
            else:
                new_losses += 1

            update_payload = {
                "elo": pokemon_to_update["new_rating"],
                "wins": new_wins,
                "losses": new_losses,
            }

            update_response = (
                supabase.table("Community Pokemon Rankings")
                .update(update_payload)
                .eq("id", pokemon_id)
                .execute()
            )

            if not update_response.data:
                st.warning(f"No rows updated for Pokemon ID {pokemon_id}.")
                st.stop()

    except Exception as e:
        st.error(f"Failed to update Pokemon ratings: {str(e)}")
        st.error(traceback.format_exc())
        st.stop()


@st.cache_data(show_spinner=False)
def split_frame(input_df, rows):
    df = [input_df.loc[i : i + rows - 1, :] for i in range(0, len(input_df), rows)]
    return df


# ELO rating calculation function
def calculate_elo(rating_a, rating_b, result, k_factor=32):
    """
    Calculate new Elo ratings based on match result

    Parameters:
    rating_a (float): Rating of player A
    rating_b (float): Rating of player B
    result (float): 1 if A wins, 0 if B wins, 0.5 for draw
    k_factor (int): K-factor for Elo calculation (determines rating volatility)

    Returns:
    tuple: New ratings for A and B
    """
    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    expected_b = 1 / (1 + 10 ** ((rating_a - rating_b) / 400))

    new_rating_a = rating_a + k_factor * (result - expected_a)
    new_rating_b = rating_b + k_factor * ((1 - result) - expected_b)

    return new_rating_a, new_rating_b


def display_tier(tier, quartile_size, sorted_pokemon, header):
    start_index = tier * quartile_size
    end_index = start_index + quartile_size
    quartile_pokemon = sorted_pokemon[start_index:end_index]

    im_size = 250

    with st.container(border=True):
        st.subheader(header)
        st.write(
            f"**Elo range:** {quartile_pokemon[0]['elo']:0.2f} - {quartile_pokemon[-1]['elo']:0.2f}"
        )

        left, right = st.columns(2)
        with left:
            st.write("**Top Pokémon**")
            st.image(
                quartile_pokemon[0]["image_url"],
                width=im_size,
                caption=quartile_pokemon[0]["name"],
            )
        with right:
            st.write("**Bottom Pokémon**")
            st.image(
                quartile_pokemon[-1]["image_url"],
                width=im_size,
                caption=quartile_pokemon[-1]["name"],
            )


# Main app
def main():
    st.set_page_config(
        page_title="Pokémon Popularity Contest", page_icon="🗳️", layout="wide"
    )
    st.markdown(
        """
        <style>
            .reportview-container {
                margin-top: -2em;
            }
            #MainMenu {visibility: hidden;}
            .stDeployButton {display:none;}
            footer {visibility: hidden;}
            #stDecoration {display:none;}
        </style>
    """,
        unsafe_allow_html=True,
    )
    # App title and navigation
    st.title("🗳️ Pokémon 1v1 Popularity Contest")

    st.write(
        """
    🤜🤛 Determine the best Pokémon by comparing them head-to-head! 

    📈 As we vote, Pokémon will develop competitive Elo ratings based on the results of the matches

    🌏 The **Summary** tab shows quick highlights

    📊 The **Leaderboard** shows all the current standings sorted by Elo or Win %

    🗂️ Use the buttons below to filter selected generations of Pokémon to include in consideration
        """
    )
    gens = generation_module(key="choose_gens")
    data = load_pokemon_data(gens)

    tab_compare, tab_summary, tab_results, tab_exp = st.tabs(
        ["🗳️ Vote", "🌏 Summary", "📊 Leaderboard", "🎛️ Under the hood"]
    )
    with tab_compare:

        st.header("Pick Your Favorite Pokemon!")
        im_size = 250
        if not data:
            st.error(
                "Failed to load Pokemon data. Please check your Supabase connection."
            )
            st.stop()

        pokemon_a, pokemon_b = select_pokemon(data)

        A_col, B_col = st.columns(2)

        with A_col:
            st.subheader(pokemon_a["name"])
            st.image(pokemon_a["image_url"], width=im_size)

            if st.button("Choose this Pokémon", key="winner_A"):
                new_rating_a, new_rating_b = calculate_elo(
                    st.session_state.pokemon_a["elo"],
                    st.session_state.pokemon_b["elo"],
                    1,
                )
                pokemon_to_update_a = [
                    {
                        "id": st.session_state.pokemon_a["id"],
                        "new_rating": new_rating_a,
                        "result": 1,
                    },
                    {
                        "id": st.session_state.pokemon_b["id"],
                        "new_rating": new_rating_b,
                        "result": -1,
                    },
                ]
                update_pokemon_ratings(pokemon_to_update_a)

        with B_col:

            st.subheader(pokemon_b["name"])
            st.image(pokemon_b["image_url"], width=im_size)
            if st.button("Choose this Pokémon", key="winner_B"):
                new_rating_a, new_rating_b = calculate_elo(
                    st.session_state.pokemon_a["elo"],
                    st.session_state.pokemon_b["elo"],
                    0,
                )
                pokemon_to_update_b = [
                    {
                        "id": st.session_state.pokemon_a["id"],
                        "new_rating": new_rating_a,
                        "result": -1,
                    },
                    {
                        "id": st.session_state.pokemon_b["id"],
                        "new_rating": new_rating_b,
                        "result": 1,
                    },
                ]
                update_pokemon_ratings(pokemon_to_update_b)

    # Summary tab
    with tab_summary:

        df = pd.DataFrame(data)
        num_votes = df["wins"].sum()
        im_size = 250
        st.header(f"📈 Together we've voted {num_votes} times! ")

        left, center, right = st.columns(3)

        with left:
            st.subheader("✨ Most popular")
            most_popular = df.loc[
                df["elo"] == df["elo"].max(),
                ["name", "image_url", "elo", "wins", "losses"],
            ]
            st.image(
                most_popular["image_url"].values[0],
                width=im_size,
                caption=most_popular["name"].values[0],
            )
            st.write(
                f"**Elo:** {most_popular['elo'].values[0]:0.2f} | **Wins:** {most_popular['wins'].values[0]} | **Losses:** {most_popular['losses'].values[0]}"
            )
        with center:
            st.subheader("😐 Average")
            # Find the central pokemon when sorting by elo
            sorted_pokemon = df.sort_values(by="elo")
            mid_index = len(sorted_pokemon) // 2
            most_average = sorted_pokemon.iloc[mid_index]
            st.image(
                most_average["image_url"],
                width=im_size,
                caption=most_average["name"],
            )
            st.write(
                f"**Elo:** {most_average['elo']:0.2f} | **Wins:** {most_average['wins']} | **Losses:** {most_average['losses']}"
            )
        with right:
            st.subheader("🪦 Least popular")
            least_popular = df.loc[
                df["elo"] == df["elo"].min(),
                ["name", "image_url", "elo", "wins", "losses"],
            ]
            st.image(
                least_popular["image_url"].values[0],
                width=im_size,
                caption=least_popular["name"].values[0],
            )
            st.write(
                f"**Elo:** {least_popular['elo'].values[0]:0.2f} | **Wins:** {least_popular['wins'].values[0]} | **Losses:** {least_popular['losses'].values[0]}"
            )

        st.header("📊 Pokémon Distributions")
        # create a histogram of the Elo ratings
        elo_fig, elo_ax = plt.subplots()
        elo_ax.hist(df["elo"], bins=30, color="blue", alpha=0.7, density=True)
        elo_ax.set_xlabel("Elo rating")
        elo_ax.set_ylabel("Frequency")
        elo_ax.spines["top"].set_visible(False)
        elo_ax.spines["right"].set_visible(False)
        elo_ax.spines["left"].set_visible(False)
        elo_ax.axvline(
            df["elo"].median(), color="black", linestyle="--", label="Median"
        )

        left, right = st.columns(2)

        comp_fig, comp_ax = plt.subplots()
        comp_ax.hist(
            (df["wins"] + df["losses"]), bins=30, color="blue", alpha=0.7, density=True
        )
        comp_ax.set_xlabel("Number of times compared")
        comp_ax.set_ylabel("Frequency")
        comp_ax.spines["top"].set_visible(False)
        comp_ax.spines["right"].set_visible(False)
        comp_ax.spines["left"].set_visible(False)
        comp_ax.spines["bottom"].set_visible(False)
        comp_ax.axvline(
            (df["wins"] + df["losses"]).median(),
            color="black",
            linestyle="--",
            label="Median",
        )
        with left:
            # Distribution of Elo ratings
            st.subheader("Elo ratings")
            st.pyplot(elo_fig, use_container_width=True)
        with right:
            # Distribution of number of times compared (wins + losses)
            st.subheader("Comparisons")
            st.pyplot(comp_fig, use_container_width=True)

        st.header("Competitive match making tiers")
        sorted_pokemon = sorted(data, key=lambda x: x.get("elo", 0), reverse=True)
        quartile_size = len(sorted_pokemon) // 4
        # Champion tier
        display_tier(0, quartile_size, sorted_pokemon, "🏆 Champion Tier")
        # Gold tier
        display_tier(1, quartile_size, sorted_pokemon, "🥇 Gold Tier")
        # Silver tier
        display_tier(2, quartile_size, sorted_pokemon, "🥈 Silver Tier")
        # Bronze tier
        display_tier(3, quartile_size, sorted_pokemon, "🥉 Bronze Tier")

    # Results tab
    with tab_results:
        st.header("📊 Leaderboard")

        if not data:
            st.error(
                "Failed to load Pokemon data. Please check your Supabase connection."
            )
            st.stop()

        tabled_data = pd.DataFrame(
            [
                {
                    "Image": f"![]({pokemon['image_url']})",
                    "Name": pokemon["name"],
                    "Win %": (
                        pokemon["wins"] / (pokemon["wins"] + pokemon["losses"])
                        if (pokemon["wins"] + pokemon["losses"]) > 0
                        else 0
                    ),
                    "Record": f"{pokemon['wins']} - {pokemon['losses']}",
                    "Elo": pokemon["elo"],
                }
                for pokemon in data
            ]
        )
        # Sort the data based on the selected criteria
        top_menu = st.columns(2)
        with top_menu[0]:
            sort_field = st.selectbox("Sort By", options=["Elo", "Win %"])
        # Add a radio button for ascending/descending order
        with top_menu[1]:
            sort_direction = st.radio(
                "Direction",
                options=[
                    "⬇️",
                    "⬆️",
                ],
                horizontal=True,
            )
        tabled_data = tabled_data.sort_values(
            by=sort_field, ascending=sort_direction == "⬆️", ignore_index=True
        )
        pagination = st.container()

        bottom_menu = st.columns((1, 3, 1))
        with bottom_menu[2]:
            batch_size = st.selectbox("Page Size", options=[25, 50, 100])
        with bottom_menu[1]:
            total_pages = (
                int(len(tabled_data) / batch_size)
                if int(len(tabled_data) / batch_size) > 0
                else 1
            )
            current_page = st.number_input(
                "Page", min_value=1, max_value=total_pages, step=1
            )
        with bottom_menu[0]:
            st.markdown(f"Page **{current_page}** of **{total_pages}** ")

        pages = split_frame(tabled_data, batch_size)
        pagination.table(data=pages[current_page - 1])

    with tab_exp:
        st.header("🎛️ Under the hood")
        st.subheader("Match making")
        st.write(
            "When generating a comparison, the app selects between the following strategies:"
        )
        st.write(
            """
**🤼 Ranked Matchmaking (50%)**: 

Ranked match making is selected 50% of the time, and is done by breaking the dataset into quartiles and selecting two Pokémon from a random quartile. This is to keep comparisons competitive.

**🎲 Select two Pokémon at random (25%)**: 

Pure random selection is selected 25% of the time to ensure all Pokémon have the chance to be compared against any other, allowing for potential upsets.

**⚖️ Select two Pokémon with the fewest comparisons (25%)**: 

Two Pokémon with the fewest comparisons is choosen 25% of the time to ensure that underrepresented Pokémon are given a higher chance to be compared.
"""
        )
        st.subheader("🌐 Universal Pokémon Elo rating")
        st.write(
            "Regardless of which generation you filter by, all Pokémon are compared using a universal Elo rating system. This means that the Elo rating is not generation-specific, allowing for a fair comparison across generations."
        )
        st.subheader("🧮 PokémonElo rating calculation")
        st.write(
            "The Elo rating system is used to calculate the new ratings of Pokémon after each match. The formula is as follows:"
        )
        st.latex(
            r"""
            R_{new} = R_{old} + K \cdot (S - E)
            """
        )
        st.write(
            """
Where:
- $R_{new}$ is the new rating
- $R_{old}$ is the old rating
- $K$ is the K-factor (default is 32)
- $S$ is the score (1 for a win, 0 for a loss)
- $E$ is the expected score, calculated as:
            """
        )
        st.latex(
            r"""
            E = \frac{1}{1 + 10^{\frac{(R_{opponent} - R_{player})}{400}}}
            """
        )
        st.write(
            """
Where:
- $R_{opponent}$ is the rating of the opponent
- $R_{player}$ is the rating of the player
The K-factor determines how much the ratings change after each match. A higher K-factor means more volatility in the ratings, while a lower K-factor means more stability.
        """
        )
        st.subheader("📦 Data source")
        st.write(
            "The Pokémon data is fetched from the [PokéAPI](https://pokeapi.co/) and stored in a Supabase database. The app uses the Supabase client to interact with the database."
        )
        st.subheader("🤝 Contributing")
        st.write(
            "If you want to contribute to this project, feel free to fork [the repository](https://github.com/Zachary-Ip/pokemon-elo-ranking) and submit a pull request!"
        )

    # Store the selected Pokemon in session state
    st.session_state.pokemon_a = pokemon_a
    st.session_state.pokemon_b = pokemon_b


if __name__ == "__main__":
    main()
