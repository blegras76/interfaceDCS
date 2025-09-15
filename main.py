import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
from io import StringIO

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
    tab1, tab2 = st.tabs(["Visualisation simple", "Comparaison multi-périodes"])

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
                yaxis_ref = "y" if i == 0 else f"y{i+1}"
                layout_key = "yaxis" if i == 0 else f"yaxis{i+1}"

                side = "left" if i % 2 == 0 else "right"
                overlay = "y" if i > 0 else None

                fig.add_trace(go.Scatter(
                    x=df_filtered["Datetime"], y=df_filtered[var],
                    mode="lines", name=var, yaxis=yaxis_ref
                ))

                fig.update_layout({
                    layout_key: dict(
                        title=var,
                        side=side,
                        overlaying=overlay
                    )
                })

            fig.update_layout(
                title="Données process DCS",
                xaxis=dict(title="Temps"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

    # --- Comparaison multi-périodes ---
    with tab2:
        st.subheader("Comparaison d'une variable sur plusieurs périodes")

        var = st.selectbox("Variable à comparer", var_names)

        # Choix de la durée
        duree_val = st.number_input("Durée de la fenêtre", min_value=1, value=24)
        unite = st.selectbox("Unité", ["minutes", "heures", "jours"])

        if unite == "minutes":
            delta = pd.Timedelta(minutes=duree_val)
            unite_label = "min"
        elif unite == "jours":
            delta = pd.Timedelta(days=duree_val)
            unite_label = "j"
        else:
            delta = pd.Timedelta(hours=duree_val)
            unite_label = "h"

        # Sélection de dates/heures personnalisées
        col1, col2 = st.columns(2)
        with col1:
            date_sel = st.date_input("Date de début", value=df["Datetime"].min().date())
        with col2:
            time_sel = st.time_input("Heure de début", value=datetime.time(0, 0))

        start_dt = datetime.datetime.combine(date_sel, time_sel)

        # Liste persistante des périodes
        if "debut_list" not in st.session_state:
            st.session_state.debut_list = []

        if st.button("➕ Ajouter cette période"):
            st.session_state.debut_list.append(start_dt)

        if st.button("♻️ Réinitialiser la sélection"):
            st.session_state.debut_list = []

        debut_list = st.session_state.debut_list
        st.write("Périodes sélectionnées :", debut_list)

        extracted = []

        if debut_list:
            fig = go.Figure()

            for d0 in debut_list:
                d1 = d0 + delta
                subset = df[(df["Datetime"] >= d0) & (df["Datetime"] < d1)].copy()

                if not subset.empty:
                    subset["Temps relatif"] = (subset["Datetime"] - d0).dt.total_seconds()

                    if unite == "minutes":
                        subset["Temps relatif"] /= 60
                    elif unite == "jours":
                        subset["Temps relatif"] /= 3600 * 24
                    else:
                        subset["Temps relatif"] /= 3600

                    subset["Periode"] = f"Début {d0}"
                    extracted.append(subset[["Datetime", "Temps relatif", var, "Periode"]])

                    fig.add_trace(go.Scatter(
                        x=subset["Temps relatif"], y=subset[var],
                        mode="lines", name=f"Début {d0}"
                    ))

            fig.update_layout(
                title=f"Comparaison de {var} sur plusieurs périodes",
                xaxis_title=f"Temps relatif ({unite_label})",
                yaxis_title=var
            )

            st.plotly_chart(fig, use_container_width=True)

            # Export CSV
            if extracted:
                df_export = pd.concat(extracted, ignore_index=True)
                csv_buffer = StringIO()
                df_export.to_csv(csv_buffer, index=False, sep=";")

                st.download_button(
                    label="📥 Télécharger les périodes extraites (CSV)",
                    data=csv_buffer.getvalue(),
                    file_name=f"comparaison_{var}.csv",
                    mime="text/csv"
                )
