import streamlit as st
import pandas as pd
import plotly.graph_objects as go

uploaded_file = st.file_uploader("Choisir un fichier CSV DCS", type=["csv"])

if uploaded_file is not None:
    # Lecture brute (toujours latin1 pour tes fichiers DCS)
    df_raw = pd.read_csv(uploaded_file, sep=";", header=None, encoding="latin1")

    # Nombre total de colonnes
    ncols = df_raw.shape[1]

    # Variables à partir de la colonne 6 (index 5)
    tags  = df_raw.iloc[4, 5:].astype(str).tolist()   # P_ITEM
    desc  = df_raw.iloc[5, 5:].astype(str).tolist()   # P_CMNT
    units = df_raw.iloc[8, 5:].astype(str).tolist()   # P_EUNT

    var_names = []
    for t, d, u in zip(tags, desc, units):
        label = t
        if d and d != "nan":
            label += f" ({d.strip()})"
        if u and u != "nan":
            label += f" [{u.strip()}]"
        var_names.append(label)

    # Colonnes fixes : 5 premières colonnes
    fixed_cols = ["Type", "Col2", "Date", "Heure", "Timezone"]

    # Construire la liste complète des noms de colonnes
    all_cols = fixed_cols + var_names

    # Ajuster si jamais il y a un décalage
    all_cols = all_cols[:ncols]

    # Données à partir de la ligne 14 (index 13)
    df = df_raw.iloc[13:].reset_index(drop=True)
    df.columns = all_cols

    # Création de la colonne datetime
    df["Datetime"] = pd.to_datetime(
        df["Date"].astype(str) + " " + df["Heure"].astype(str),
        errors="coerce"
    )

    # Liste des variables process
    variables = [c for c in df.columns if c not in fixed_cols]

    # Interface Streamlit
    st.subheader("Visualisation des données DCS")

    choix = st.multiselect("Sélectionner les variables à afficher", variables, default=variables[:2])

    min_date, max_date = df["Datetime"].min(), df["Datetime"].max()
    start, end = st.slider(
        "Sélectionner la période",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD HH:mm"
    )
    df_filtered = df[(df["Datetime"] >= start) & (df["Datetime"] <= end)]

    multi_axes = st.checkbox("Utiliser plusieurs axes Y", value=True)

    if choix:
        fig = go.Figure()
        if multi_axes and len(choix) > 1:
            # Premier axe gauche
            fig.add_trace(go.Scatter(x=df_filtered["Datetime"], y=df_filtered[choix[0]],
                                     mode="lines", name=choix[0], yaxis="y1"))
            # Deuxième axe droite
            fig.add_trace(go.Scatter(x=df_filtered["Datetime"], y=df_filtered[choix[1]],
                                     mode="lines", name=choix[1], yaxis="y2"))
            fig.update_layout(
                xaxis=dict(title="Temps"),
                yaxis=dict(title=choix[0], side="left"),
                yaxis2=dict(title=choix[1], overlaying="y", side="right"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            # Variables supplémentaires → axe gauche
            for extra in choix[2:]:
                fig.add_trace(go.Scatter(x=df_filtered["Datetime"], y=df_filtered[extra],
                                         mode="lines", name=extra, yaxis="y1"))
        else:
            for var in choix:
                fig.add_trace(go.Scatter(x=df_filtered["Datetime"], y=df_filtered[var],
                                         mode="lines", name=var))
            fig.update_layout(
                xaxis=dict(title="Temps"),
                yaxis=dict(title="Valeurs"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

        st.plotly_chart(fig, use_container_width=True)
