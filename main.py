import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- Upload du fichier ---
uploaded_file = st.file_uploader("Choisir un fichier CSV DCS", type=["csv"])

if uploaded_file is not None:
    # Lecture brute avec encodage latin1
    df_raw = pd.read_csv(uploaded_file, sep=";", header=None, encoding="latin1")

    # ---------------------
    # Extraction des noms
    # ---------------------
    tags = df_raw.iloc[4, 5:].astype(str).tolist()      # P_ITEM (tags)
    desc = df_raw.iloc[5, 5:].astype(str).tolist()      # P_CMNT (commentaires)
    units = df_raw.iloc[8, 5:].astype(str).tolist()     # P_EUNT (unités)

    # Noms lisibles = Tag (Description) [Unité]
    var_names = []
    for t, d, u in zip(tags, desc, units):
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
    fixed_cols = ["Type", "Col2", "Date", "Heure"]
    df.columns = fixed_cols + var_names
    df["Datetime"] = pd.to_datetime(
        df["Date"].astype(str) + " " + df["Heure"].astype(str),
        errors="coerce"
    )

    # ---------------------
    # Interface Streamlit
    # ---------------------
    st.subheader("Visualisation des données DCS")

    choix = st.multiselect(
        "Sélectionner les variables à afficher",
        var_names,
        default=var_names[:2]
    )

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

    # Option multi-axes
    multi_axes = st.checkbox("Utiliser plusieurs axes Y", value=True)

    # ---------------------
    # Graphique Plotly
    # ---------------------
    if choix:
        fig = go.Figure()

        if multi_axes and len(choix) > 1:
            # Premier axe Y (gauche)
            fig.add_trace(go.Scatter(
                x=df_filtered["Datetime"], y=df_filtered[choix[0]],
                mode="lines", name=choix[0], yaxis="y1"
            ))

            # Deuxième axe Y (droite)
            fig.add_trace(go.Scatter(
                x=df_filtered["Datetime"], y=df_filtered[choix[1]],
                mode="lines", name=choix[1], yaxis="y2"
            ))

            # Layout avec double axe
            fig.update_layout(
                title="Données process DCS",
                xaxis=dict(title="Temps"),
                yaxis=dict(title=choix[0], side="left"),
                yaxis2=dict(title=choix[1], overlaying="y", side="right"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            # Si plus de 2 variables → les ajouter sur l’axe gauche
            for extra in choix[2:]:
                fig.add_trace(go.Scatter(
                    x=df_filtered["Datetime"], y=df_filtered[extra],
                    mode="lines", name=extra, yaxis="y1"
                ))

        else:
            # Tous sur un seul axe
            for var in choix:
                fig.add_trace(go.Scatter(
                    x=df_filtered["Datetime"], y=df_filtered[var],
                    mode="lines", name=var
                ))
            fig.update_layout(
                title="Données process DCS",
                xaxis=dict(title="Temps"),
                yaxis=dict(title="Valeurs"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

        st.plotly_chart(fig, use_container_width=True)
