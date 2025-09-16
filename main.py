import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
from io import BytesIO
import plotly.express as px

# =======================
# UPLOAD MULTI-FICHIERS
# =======================
uploaded_files = st.file_uploader(
    "Choisir un ou plusieurs fichiers CSV DCS",
    type=["csv"], accept_multiple_files=True
)

if uploaded_files:
    dfs = []
    var_names_global = None  # cohérence des variables entre fichiers

    for f in uploaded_files:
        df_raw = pd.read_csv(f, sep=",", header=None, encoding="latin1")

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

        if var_names_global is None:
            var_names_global = var_names
        else:
            var_names_global = list(set(var_names_global).intersection(var_names))

        # Extraction données
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
        df["Source"] = f.name  # identifiant du fichier

        dfs.append(df)

    # Concat global
    df = pd.concat(dfs, ignore_index=True)

    # =======================
    # OPTIONS D'EXPORT
    # =======================
    st.markdown("### ⚙️ Options d'export")
    export_mode = st.radio(
        "Niveau de détail des données exportées :",
        ["Toutes les données", "Un point toutes les X secondes", "Un point toutes les X minutes"]
    )
    if export_mode != "Toutes les données":
        step_val = st.number_input("Intervalle d'échantillonnage", min_value=1, value=60)

    def downsample(subset):
        if export_mode == "Un point toutes les X secondes":
            return subset.iloc[::step_val, :]
        elif export_mode == "Un point toutes les X minutes":
            step = step_val * 60
            return subset.iloc[::step, :]
        return subset

    # =======================
    # INTERFACE CÔTE À CÔTE
    # =======================
    col_visu, col_comp = st.columns([1, 1])

    # --- Visualisation simple ---
    with col_visu:
        st.subheader("Visualisation simple")

        choix = st.multiselect("Sélectionner les variables à afficher",
                               var_names_global, default=var_names_global[:1])

        min_date = df["Datetime"].min().to_pydatetime()
        max_date = df["Datetime"].max().to_pydatetime()

        start, end = st.slider(
            "Sélectionner la période globale",
            min_value=min_date, max_value=max_date,
            value=(min_date, max_date),
            format="YYYY-MM-DD HH:mm"
        )

        df_filtered = df[(df["Datetime"] >= start) & (df["Datetime"] <= end)]

        if choix:
            fig = go.Figure()
            colors = px.colors.qualitative.Set1
            for i, (src, group) in enumerate(df_filtered.groupby("Source")):
                for var in choix:
                    fig.add_trace(go.Scatter(
                        x=group["Datetime"], y=group[var],
                        mode="lines", name=f"{var} ({src})",
                        line=dict(color=colors[i % len(colors)])
                    ))
            fig.update_layout(title="Données process DCS",
                              xaxis_title="Temps", yaxis_title="Valeurs",
                              legend=dict(orientation="h", yanchor="bottom",
                                          y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

            # ✅ Export données affichées
            export_graph = downsample(df_filtered[["Datetime", "Source"] + choix])
            csv = export_graph.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Télécharger les données affichées (CSV)", data=csv,
                               file_name="donnees_graph_simple.csv", mime="text/csv")

            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                export_graph.to_excel(writer, sheet_name="Graph", index=False)
            st.download_button("⬇️ Télécharger les données affichées (Excel)",
                               data=buffer.getvalue(),
                               file_name="donnees_graph_simple.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # --- Comparaison multi-périodes ---
    with col_comp:
        st.subheader("Comparaison multi-périodes")

        var = st.selectbox("Variable à comparer", var_names_global)

        duree_val = st.number_input("Durée de la fenêtre", min_value=1, value=6)
        unite = st.selectbox("Unité", ["minutes", "heures", "jours"])
        if unite == "minutes":
            delta = pd.Timedelta(minutes=duree_val)
        elif unite == "jours":
            delta = pd.Timedelta(days=duree_val)
        else:
            delta = pd.Timedelta(hours=duree_val)

        col1, col2 = st.columns(2)
        with col1:
            date_sel = st.date_input("Date de début",
                                     value=df["Datetime"].min().date())
        with col2:
            time_sel = st.time_input("Heure de début", value=datetime.time(0, 0))
        start_dt = datetime.datetime.combine(date_sel, time_sel)

        if "debut_list" not in st.session_state:
            st.session_state.debut_list = []
        if st.button("➕ Ajouter cette période"):
            if start_dt not in st.session_state.debut_list:
                st.session_state.debut_list.append(start_dt)
        if st.button("♻️ Réinitialiser toutes les périodes"):
            st.session_state.debut_list = []

        debut_list = st.session_state.debut_list

        if debut_list:
            st.write("### 📋 Périodes sélectionnées")
            st.write([d.strftime("%Y-%m-%d %H:%M") for d in debut_list])

            fig_multi = go.Figure()
            colors = px.colors.qualitative.Set2
            export_dfs = []

            for src, gdf in df.groupby("Source"):
                for i, d0 in enumerate(debut_list):
                    d1 = d0 + delta
                    subset = gdf[(gdf["Datetime"] >= d0) & (gdf["Datetime"] < d1)].copy()
                    if not subset.empty:
                        subset = downsample(subset)
                        subset["Temps relatif (h)"] = (subset["Datetime"] - d0).dt.total_seconds()/3600

                        fig_multi.add_trace(go.Scatter(
                            x=subset["Temps relatif (h)"], y=subset[var],
                            mode="lines",
                            name=f"{src} | Période {i+1} ({d0.strftime('%Y-%m-%d %H:%M')})",
                            line=dict(color=colors[i % len(colors)])
                        ))

                        export_dfs.append((src, i+1, d0, subset))

            fig_multi.update_layout(title=f"Superposition {var}",
                                    xaxis_title="Temps relatif (h)", yaxis_title=var,
                                    legend=dict(orientation="h", yanchor="bottom",
                                                y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_multi, use_container_width=True)

            # Export Excel en format large
            if export_dfs:
                merged = pd.DataFrame()
                merged["Temps relatif (h)"] = sorted(
                    set().union(*[s[3]["Temps relatif (h)"] for s in export_dfs])
                )

                for src, i, d0, subset in export_dfs:
                    time_col = f"Datetime - {src} - Période {i} ({d0.strftime('%Y-%m-%d %H:%M')})"
                    val_col  = f"Valeur - {src} - Période {i} ({d0.strftime('%Y-%m-%d %H:%M')})"

                    merged = pd.merge(
                        merged,
                        subset[["Temps relatif (h)", "Datetime", var]].rename(
                            columns={"Datetime": time_col, var: val_col}
                        ),
                        on="Temps relatif (h)", how="outer"
                    )

                # Téléchargement
                csv = merged.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Télécharger les données superposées (CSV)", data=csv,
                                   file_name="donnees_superposees.csv", mime="text/csv")

                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    merged.to_excel(writer, sheet_name="Superposées", index=False)
                st.download_button("⬇️ Télécharger les données superposées (Excel)",
                                   data=buffer.getvalue(),
                                   file_name="donnees_superposees.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
