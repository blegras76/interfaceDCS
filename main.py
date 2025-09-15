import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- Upload du fichier ---
uploaded_file = st.file_uploader("Choisir un fichier CSV DCS", type=["csv"])

if uploaded_file is not None:
    # Lecture brute avec séparateur correct ("," pour ton fichier)
    df_raw = pd.read_csv(uploaded_file, sep=",", header=None, encoding="latin1")

    # ---------------------
    # Extraction des variables
    # ---------------------
    tags  = df_raw.iloc[4, 6:].astype(str).tolist()   # P_ITEM
    desc  = df_raw.iloc[5, 6:].astype(str).tolist()   # P_CMNT
    units = df_raw.iloc[9, 6:].astype(str).tolist()   # P_EUNT

    # Construire noms lisibles et filtrer les vides
    var_names = []
    for t, d, u in zip(tags, desc, units):
        if t == "nan" or t.strip() == "":
            continue
        label = t
        if d and d != "nan":
            label += f" ({d.strip()})"
        if u and u != "nan":
            label += f" [{u.strip()}]"
        var_names.append(label)

    # ---------------------
    # Extraction des données
    # ---------------------
    df = df_raw.iloc[13:].reset_index(drop=True)

    # Colonnes fixes : 5 premières colonnes (Type, Col2, Date, Heure, Timezone)
    fixed_cols = ["Type", "Col2", "Date", "Heure", "Timezone"]

    # Ajuster la taille totale
    all_cols = fixed_cols + var_names
    all_cols = all_cols[:df.shape[1]]

    df.columns = all_cols

    # Création colonne datetime
    df["Datetime"] = pd.to_datetime(
        df["Date"].astype(str) + " " + df["Heure"].astype(str),
        errors="coerce"
    )

    # ---------------------
    # Interface Streamlit
    # ---------------------
    st.subheader("Visualisation des données DCS")

    choix = st.multiselect("Sélectionner les variables à afficher", var_names, default=var_names[:2])

    # Sélection période
    min_date, max_date = df["Datetime"].min(), df["Datetime"].max()
    start, end = st.slider(
        "Sélectionner la période",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD HH:mm"
    )
    df_filtered = df[(df["Datetime"] >= start) & (df["Datetime"] <= end)]

    # ---------------------
    # Graphique Plotly multi-axes
    # ---------------------
    if choix:
        fig = go.Figure()

        # Boucle sur les variables sélectionnées
        for i, var in enumerate(choix):
            axis_id = f"y{i+1}"

            # Créer la trace
            fig.add_trace(go.Scatter(
                x=df_filtered["Datetime"], y=df_filtered[var],
                mode="lines", name=var, yaxis=axis_id
            ))

            # Paramètres de l’axe
            side = "left" if i % 2 == 0 else "right"
            overlay = "y" if i > 0 else None
            fig.update_layout({
                axis_id: dict(
                    title=var,
                    side=side,
                    overlaying=overlay
                )
            })

        # Mise en forme
        fig.update_layout(
            title="Données process DCS",
            xaxis=dict(title="Temps"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig, use_container_width=True)
