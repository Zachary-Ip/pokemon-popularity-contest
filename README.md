# Pokémon Popularity Contest

A Streamlit application that ranks Pokémon based on community preferences through head-to-head comparisons.

[Use the app live!](https://pokemon-popularity-contest.streamlit.app/)

## 🌟 Features

- **Head-to-Head Comparisons**: Users choose their preferred Pokémon between two options
- **ELO Rating System**: Sophisticated ranking algorithm adapts based on user selections
- **Live Leaderboard**: View the most popular Pokémon ranked by ELO score
- **Progress Tracking**: Shows remaining comparisons to complete the rankings


## 💻 Technology

- **Frontend**: ![Static Badge](https://img.shields.io/badge/Streamlit-cloud?logo=streamlit&color=grey&link=https%3A%2F%2Fstreamlit.io%2Fcloud)


- **Ranking Algorithm**: Uses ELO rating system (similar to chess rankings)
- **Backend**: ![Static Badge](https://img.shields.io/badge/Supabase-database?logo=supabase&color=grey&link=https%3A%2F%2Fsupabase.com%2F)


## 🛠️ Installation

### Prerequisites

- Python 3.12+
- poetry

### Setup

1. Clone the repository:
```bash
git clone https://github.com/Z/pokemon-popularity-contest.git
cd pokemon-popularity-contest
```

2. Install using poetry:
```bash
poetry install
```

4. Run the application:
```bash
poetry run streamlit run app/main.py
```

## 📊 How It Works

### ELO Rating System

The app uses an ELO rating system where:
- All Pokémon start with a base ELO of 400
- When a user selects their preferred Pokémon, ratings are updated
- Higher-rated Pokémon winning against lower-rated ones gain fewer points
- Upsets (lower-rated beating higher-rated) result in larger point changes
- Formula: `new_rating = old_rating + K * (actual_outcome - expected_outcome)`

### Comparison Process

1. Two Pokémon are presented to the user
2. User selects their favorite
3. ELO ratings are updated based on the selection
4. Process repeats with a new pair
5. User can view current rankings at any time

## 📝 Usage

1. [Navigate to the app in your browser](https://pokemon-popularity-contest.streamlit.app/)
2. Initialize the dataset, including any number of pokemon generations
2. Click on your preferred Pokémon in each matchup
3. Continue voting to help establish accurate community rankings
4. Check the leaderboard to see current standings

## 🤝 Contributing

Contributions are welcome! Please feel free to:
- Report bugs
- Suggest features
- Submit pull requests

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- Pokémon sprites and data from [PokeAPI](https://pokeapi.co/)
