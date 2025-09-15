import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime

uploaded_file = st.file_uploader("Choisir un fichier CSV DCS", type=["csv"])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file, sep=",", header=None, encoding="latin1")

    # Extraction des variables
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

    # Données à partir de la ligne 14
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

    # ---------------------
    # Graph multi-axes
    # ---------------------
    if choix:
        fig = go.Figure()

        for i, var in enumerate(choix):
            # yaxis id pour la trace (y, y2, y3...)
            yaxis_ref = "y" if i == 0 else f"y{i+1}"

            # Layout key (yaxis, yaxis2, ...)
            layout_key = "yaxis" if i == 0 else f"yaxis{i+1}"

            side = "left" if i % 2 == 0 else "right"
            overlay = "y" if i > 0 else None

            # Trace
            fig.add_trace(go.Scatter(
                x=df_filtered["Datetime"], y=df_filtered[var],
                mode="lines", name=var, yaxis=yaxis_ref
            ))

            # Axe
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
