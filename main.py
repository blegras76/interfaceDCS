import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
from io import BytesIO
import plotly.express as px
import numpy as np  # pour la régression linéaire

# Essai d'import du module de capture d'événements
try:
    from streamlit_plotly_events import plotly_events
    has_plotly_events = True
except ModuleNotFoundError:
    has_plotly_events = False
    st.warning("⚠️ Le module `streamlit-plotly-events` n'est pas installé. "
               "Installe-le avec `pip install streamlit-plotly-events` pour activer la sélection de points.")

uploaded_file = st.file_uploader("Choisir un fichier CSV DCS", type=["csv"])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file, sep=",", header=None, encoding="latin1")

    # ---------------------
    # Extraction des variables
    # ---------------------
    tags  = df_raw.iloc[4, 6:].astype(str).tolist()
    desc  = df_raw.iloc[5, 6:].astype(str).tolist()
    units = df_raw.iloc[9, 6:].astype(str).tolist()

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

    fixed_cols = ["Type", "Col2", "Date", "Heure", "Timezone"]
    all_cols = fixed_cols + var_names

    if len(all_cols) < df.shape[1]:
        extra = [f"Col{i}" for i in range(len(all_cols), df.shape[1])]
        all_cols = all_cols + extra
    elif len(all_cols) > df.shape[1]:
        all_cols = all_cols[:df.shape[1]]

    df.columns = all_cols

    df["Datetime"] = pd.to_datetime(
        df["Date"].astype(str) + " " + df["Heure"].astype(str),
        errors="coerce"
    )

    # ---------------------
    # Onglets Streamlit
    # ---------------------
    tab1, tab2 = st.tabs(["Visualisation simple", "Comparaison & Analyse multi-périodes"])

    # --- Visualisation simple ---
    with tab1:
        st.subheader("Visualisation des données DCS")

        choix = st.multiselect("Sélectionner les variables à afficher", var_names, default=var_names[:2])

        min_date = df["Datetime"].min().to_pydatetime()
        max_date = df["Datetime"].max().to_pydatetime()

        start, end = st.slider(
            "Sélectionner la période",
            min_value=min_date,
            max_value=max_date,
            value=(min_date, max_date),
            format="YYYY-MM-DD HH:mm"
        )

        df_filtered = df[(df["Datetime"] >= start) & (df["Datetime"] <= end)]

        if choix:
            fig = go.Figure()
            for i, var in enumerate(choix):
                fig.add_trace(go.Scatter(
                    x=df_filtered["Datetime"], y=df_filtered[var],
                    mode="lines", name=var
                ))
            fig.update_layout(
                title="Données process DCS",
                xaxis=dict(title="Temps"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

            # ✅ Export des données affichées
            export_graph = df_filtered[["Datetime"] + choix]
            csv = export_graph.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Télécharger les données affichées (CSV)", data=csv,
                               file_name="donnees_graph_simple.csv", mime="text/csv")

            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                export_graph.to_excel(writer, sheet_name="Graph", index=False)
            st.download_button("⬇️ Télécharger les données affichées (Excel)", data=buffer.getvalue(),
                               file_name="donnees_graph_simple.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # --- Comparaison multi-périodes + Analyse ---
    with tab2:
        st.subheader("Comparaison et analyse de périodes")

        var = st.selectbox("Variable à comparer", var_names)

        # Choix de la durée
        duree_val = st.number_input("Durée de la fenêtre", min_value=1, value=24)
        unite = st.selectbox("Unité", ["minutes", "heures", "jours"])

        if unite == "minutes":
            delta = pd.Timedelta(minutes=duree_val)
        elif unite == "jours":
            delta = pd.Timedelta(days=duree_val)
        else:
            delta = pd.Timedelta(hours=duree_val)

        # Sélection de dates/heures personnalisées
        col1, col2 = st.columns(2)
        with col1:
            date_sel = st.date_input("Date de début", value=df["Datetime"].min().date())
        with col2:
            time_sel = st.time_input("Heure de début", value=datetime.time(0, 0))

        start_dt = datetime.datetime.combine(date_sel, time_sel)

        # -----------------------------
        # Liste persistante des périodes
        # -----------------------------
        if "debut_list" not in st.session_state:
            st.session_state.debut_list = []

        colA, colB, colC = st.columns([1,1,2])
        with colA:
            if st.button("➕ Ajouter cette période"):
                if start_dt not in st.session_state.debut_list:
                    st.session_state.debut_list.append(start_dt)

        with colB:
            if st.button("♻️ Réinitialiser toutes les périodes"):
                st.session_state.debut_list = []

        with colC:
            if st.session_state.debut_list:
                periode_a_supprimer = st.selectbox(
                    "🗑️ Supprimer une période",
                    options=st.
