import streamlit as st
import pandas as pd
import plotly.express as px

uploaded_file = st.file_uploader("Choisir un fichier CSV", type=["csv"])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file, sep=";", header=None)

    # Nombre total de colonnes
    ncols = df_raw.shape[1]

    # Colonnes fixes (1-4) + métadonnées (5-13)
    fixed_cols = ["Col1", "Col2", "Date", "Heure"] + [f"Meta{i}" for i in range(5, 14)]

    # Variables process (à partir de la col 14)
    var_names = df_raw.iloc[4, 13:].astype(str) + "_" + df_raw.iloc[5, 13:].astype(str)

    # Construction complète des noms de colonnes
    all_cols = fixed_cols + list(var_names)

    # Vérification : adapter au vrai nombre de colonnes
    all_cols = all_cols[:ncols]

    # Extraction des données (après la ligne 6)
    df = df_raw.iloc[6:].reset_index(drop=True)
    df.columns = all_cols

    # Fusion Date + Heure
    df["Datetime"] = pd.to_datetime(
        df["Date"].astype(str) + " " + df["Heure"].astype(str),
        errors="coerce",
        dayfirst=True
    )

    # Liste des variables process
    variables = [c for c in df.columns if c not in fixed_cols]

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

    df_filtered = df[(df["Datetime"] >= start) & (df["Datetime"] <= end)]

    # Affichage graphique
    if choix:
        fig = px.line(df_filtered, x="Datetime", y=choix, title="Données DCS (Process)")
        st.plotly_chart(fig, use_container_width=True)
