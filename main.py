import streamlit as st
import pandas as pd
import plotly.express as px

# Upload du fichier
uploaded_file = st.file_uploader("Choisir un fichier CSV", type=["csv"])

if uploaded_file is not None:
    # Lecture brute sans header
    df_raw = pd.read_csv(uploaded_file, sep=";", header=None)

    # Extraction des noms des variables à partir de la ligne 5 et 6, colonnes 14 → fin
    var_names = df_raw.iloc[4, 13:].astype(str) + "_" + df_raw.iloc[5, 13:].astype(str)

    # Construction du DataFrame (vraies données : à partir de la ligne 7)
    df = df_raw.iloc[6:].reset_index(drop=True)

    # Attribution des noms de colonnes
    fixed_cols = ["Col1", "Col2", "Date", "Heure"] + [f"Meta{i}" for i in range(5, 14)]
    df.columns = fixed_cols + list(var_names)

    # Fusion Date + Heure
    df["Datetime"] = pd.to_datetime(
        df["Date"].astype(str) + " " + df["Heure"].astype(str),
        errors="coerce",
        dayfirst=True
    )

    # Liste des variables process
    variables = list(var_names)

    # Sélection interactive
    choix = st.multiselect("Sélectionner les variables à afficher", variables)

    # Slider période
    min_date, max_date = df["Datetime"].min(), df["Datetime"].max()
    start, end = st.slider(
        "Sélectionner la période",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD HH:mm"
    )

    # Filtrage temporel
    df_filtered = df[(df["Datetime"] >= start) & (df["Datetime"] <= end)]

    # Affichage graphique
    if choix:
        fig = px.line(df_filtered, x="Datetime", y=choix, title="Données DCS (Process)")
        st.plotly_chart(fig, use_container_width=True)
