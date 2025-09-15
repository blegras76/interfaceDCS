import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
from io import StringIO, BytesIO
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

        if st.button("➕ Ajouter cette période"):
            if start_dt not in st.session_state.debut_list:  # ✅ on évite les doublons
                st.session_state.debut_list.append(start_dt)

        if st.button("♻️ Réinitialiser la sélection"):
            st.session_state.debut_list = []

        debut_list = st.session_state.debut_list

        if debut_list:
            st.write("### Périodes sélectionnées")
            st.dataframe(pd.DataFrame({
                "Période": [f"Période {i+1}" for i in range(len(debut_list))],
                "Début": debut_list
            }))

        # -----------------------------
        # Superposition des périodes
        # -----------------------------
        if debut_list:
            st.subheader("Superposition des périodes sélectionnées")

            fig_multi = go.Figure()
            colors = px.colors.qualitative.Set1
            summary_rows = []

            for i, d0 in enumerate(debut_list):
                d1 = d0 + delta
                subset = df[(df["Datetime"] >= d0) & (df["Datetime"] < d1)].copy()

                if not subset.empty:
                    subset["Temps relatif (h)"] = (subset["Datetime"] - d0).dt.total_seconds() / 3600

                    vals = subset[var].astype(float)
                    mean_val = vals.mean()
                    min_val = vals.min()
                    max_val = vals.max()

                    color = colors[i % len(colors)]
                    label = (
                        f"Période {i+1} (début {d0.strftime('%Y-%m-%d %H:%M')}) "
                        f"| Moy={mean_val:.1f}, Min={min_val:.1f}, Max={max_val:.1f}"
                    )

                    fig_multi.add_trace(go.Scatter(
                        x=subset["Temps relatif (h)"],
                        y=subset[var],
                        mode="lines",
                        name=label,
                        line=dict(color=color)
                    ))

                    summary_rows.append({
                        "Période": f"Période {i+1}",
                        "Début": d0,
                        "Durée": delta,
                        "Moyenne": round(mean_val, 2),
                        "Min": round(min_val, 2),
                        "Max": round(max_val, 2)
                    })

            fig_multi.update_layout(
                title=f"Superposition de {var} sur plusieurs périodes",
                xaxis_title="Temps relatif (h)",
                yaxis_title=var,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig_multi, use_container_width=True)

            if summary_rows:
                st.markdown("### 📊 Résumé multi-périodes")
                summary_df = pd.DataFrame(summary_rows)
                st.dataframe(summary_df)

        # -----------------------------
        # Analyse détaillée (rectangular selection uniquement)
        # -----------------------------
        st.subheader("Analyse d'une période sélectionnée")

        if debut_list:
            periode_choisie = st.selectbox("Choisir une période pour l'analyse", debut_list)
            d1 = periode_choisie + delta
            subset = df[(df["Datetime"] >= periode_choisie) & (df["Datetime"] < d1)].copy()

            if not subset.empty and has_plotly_events:
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(
                    x=subset["Datetime"], y=subset[var],
                    mode="lines+markers", name=var
                ))
                fig2.update_layout(
                    title=f"Sélectionner une plage ({var})",
                    xaxis_title="Temps",
                    yaxis_title=var,
                    dragmode="select"
                )

                p1_time, p2_time = None, None
                selected_zone = plotly_events(fig2, click_event=False, select_event=True, key="drag")
                if selected_zone:
                    xs = [pd.to_datetime(p["x"]) for p in selected_zone]
                    p1_time, p2_time = min(xs), max(xs)

                if p1_time is not None and p2_time is not None:
                    sub_window = subset[(subset["Datetime"] >= p1_time) & (subset["Datetime"] <= p2_time)]

                    if not sub_window.empty:
                        values = sub_window[var].astype(float)
                        times = (sub_window["Datetime"] - sub_window["Datetime"].iloc[0]).dt.total_seconds() / 3600

                        mean_val = values.mean()
                        std_val = values.std()
                        min_val = values.min()
                        max_val = values.max()

                        slope_simple = (values.iloc[-1] - values.iloc[0]) / (
                            (sub_window["Datetime"].iloc[-1] - sub_window["Datetime"].iloc[0]).total_seconds() / 3600
                        )
                        coeffs = np.polyfit(times, values, 1)
                        slope_reg = coeffs[0]

                        duration = (p2_time - p1_time)

                        results = pd.DataFrame([{
                            "Variable": var,
                            "P1": p1_time,
                            "P2": p2_time,
                            "Durée": duration,
                            "Moyenne": round(mean_val, 3),
                            "Écart-type": round(std_val, 3),
                            "Min": round(min_val, 3),
                            "Max": round(max_val, 3),
                            "Pente simple (par heure)": round(slope_simple, 3),
                            "Pente (régression, par heure)": round(slope_reg, 3),
                        }])

                        fig2.add_vrect(
                            x0=p1_time, x1=p2_time,
                            fillcolor="LightSalmon", opacity=0.3,
                            layer="below", line_width=0
                        )

                        st.plotly_chart(fig2, use_container_width=True)
                        st.markdown("### 📊 Résultats d'analyse")
                        st.dataframe(results)
