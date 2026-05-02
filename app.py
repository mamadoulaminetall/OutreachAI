import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io
import csv
import os
from dotenv import load_dotenv

load_dotenv()

from db import init_db, add_prospect, get_all_prospects, update_prospect, delete_prospect, get_stats
from email_generator import generate_email
from stripe_client import get_revenue, get_subscriptions

st.set_page_config(
    page_title="OutreachAI — Sales Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

.kpi-card {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    text-align: center;
}
.kpi-value { font-size: 2rem; font-weight: 700; color: #f1f5f9; line-height: 1; }
.kpi-label { font-size: 0.75rem; color: #94a3b8; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
.kpi-delta { font-size: 0.8rem; margin-top: 4px; }

.status-draft     { background:#334155; color:#cbd5e1; padding:2px 8px; border-radius:20px; font-size:0.72rem; }
.status-sent      { background:#1e3a5f; color:#60a5fa; padding:2px 8px; border-radius:20px; font-size:0.72rem; }
.status-replied   { background:#1a3a2a; color:#4ade80; padding:2px 8px; border-radius:20px; font-size:0.72rem; }
.status-converted { background:#2d1f4a; color:#c084fc; padding:2px 8px; border-radius:20px; font-size:0.72rem; }

.section-title {
    font-size: 1.1rem; font-weight: 600; color: #e2e8f0;
    border-left: 3px solid #3b82f6; padding-left: 10px; margin-bottom: 1rem;
}
.demo-banner {
    background: #1e3a5f; border: 1px solid #3b82f6; color: #93c5fd;
    border-radius: 8px; padding: 8px 14px; font-size: 0.82rem; margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Products catalog (pre-filled with MedFlow AI tools)
# ---------------------------------------------------------------------------
DEFAULT_PRODUCTS = [
    {"name": "BioReport AI",      "desc": "Automated medical lab report interpretation (PDF/photo/text → 5-section report). Claude API + ReportLab.", "price": "49 €/mois"},
    {"name": "GenGI",             "desc": "Variant pathogenicity prediction from WES data using DNA-LLM (Nucleotide Transformer) + PyTorch TransformerEncoder.", "price": "99 €/mois"},
    {"name": "MYOomics",          "desc": "scRNA-seq multi-omics platform for myopathy research: clustering, pseudotime, cell annotation.", "price": "149 €/mois"},
    {"name": "MedFlow Posologie", "desc": "AI-powered drug dosage recommender adapted to patient context (renal function, transplant, pediatrics).", "price": "39 €/mois"},
    {"name": "AMR-AI",            "desc": "Antimicrobial resistance prediction and antibiogram interpretation for clinical microbiology labs.", "price": "69 €/mois"},
    {"name": "CardioSurg AI",     "desc": "Surgical risk scoring and cardiac surgery outcome prediction with XAI explanations.", "price": "79 €/mois"},
]

STATUS_OPTIONS = ["draft", "sent", "replied", "converted", "archived"]
STATUS_COLORS  = {"draft": "⬜", "sent": "🔵", "replied": "🟢", "converted": "🟣", "archived": "⬛"}

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style='text-align:center; padding:1.2rem 0 0.8rem 0;'>
          <div style='font-size:1.4rem; font-weight:700; color:#3b82f6; letter-spacing:-0.5px;'>🚀 OutreachAI</div>
          <div style='font-size:0.72rem; color:#64748b; margin-top:2px;'>Sales & Revenue Dashboard</div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        page = st.radio(
            "Navigation",
            ["📊 Revenue", "✉️ Prospects", "📋 Campaigns", "⚙️ Settings"],
            label_visibility="collapsed",
        )
        st.divider()

        stats = get_stats()
        st.markdown(f"""
        <div style='font-size:0.75rem; color:#64748b; line-height:2;'>
          📬 Prospects : <b style='color:#e2e8f0;'>{stats['total']}</b><br>
          ✈️ Envoyés   : <b style='color:#60a5fa;'>{stats['sent']}</b><br>
          💬 Réponses  : <b style='color:#4ade80;'>{stats['replied']}</b><br>
          💰 Convertis : <b style='color:#c084fc;'>{stats['converted']}</b><br>
          💵 CA généré : <b style='color:#fbbf24;'>{stats['revenue']:.0f} €</b>
        </div>
        """, unsafe_allow_html=True)

    return page


# ---------------------------------------------------------------------------
# Page 1 — Revenue Dashboard
# ---------------------------------------------------------------------------
def render_revenue():
    st.markdown("<div class='section-title'>📊 Revenue Dashboard</div>", unsafe_allow_html=True)

    days = st.select_slider("Période", options=[7, 14, 30, 60, 90], value=30)

    revenue = get_revenue(days)
    subs    = get_subscriptions()

    if revenue.get("demo"):
        st.markdown("<div class='demo-banner'>⚠️ Mode démo — connectez votre clé Stripe dans <b>⚙️ Settings</b> pour les vraies données.</div>", unsafe_allow_html=True)
        revenue = _demo_revenue(days)
        subs    = {"active": 7, "mrr": 423.0, "demo": True}

    total   = revenue.get("total", 0)
    by_day  = revenue.get("by_day", {})
    recent  = revenue.get("recent", [])
    mrr     = subs.get("mrr", 0)
    active  = subs.get("active", 0)
    avg_day = total / days if days else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='kpi-card'><div class='kpi-value'>{total:,.0f} €</div><div class='kpi-label'>CA {days}j</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='kpi-card'><div class='kpi-value'>{mrr:,.0f} €</div><div class='kpi-label'>MRR (abonnements)</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='kpi-card'><div class='kpi-value'>{active}</div><div class='kpi-label'>Abonnés actifs</div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='kpi-card'><div class='kpi-value'>{avg_day:,.1f} €</div><div class='kpi-label'>Moy. / jour</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if by_day:
        df_day = pd.DataFrame(
            [{"Date": k, "Revenu (€)": v} for k, v in sorted(by_day.items())]
        )
        fig = px.area(
            df_day, x="Date", y="Revenu (€)",
            color_discrete_sequence=["#3b82f6"],
            template="plotly_dark",
            title=f"Revenu journalier — {days} derniers jours",
        )
        fig.update_layout(
            plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
            font_color="#e2e8f0", margin=dict(t=40, b=20, l=0, r=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    if recent:
        st.markdown("<div class='section-title' style='margin-top:1rem;'>Transactions récentes</div>", unsafe_allow_html=True)
        st.dataframe(
            pd.DataFrame(recent),
            use_container_width=True,
            hide_index=True,
        )


def _demo_revenue(days: int) -> dict:
    import random, math
    random.seed(42)
    base = datetime.now()
    by_day, recent = {}, []
    total = 0.0
    for i in range(days):
        d = (base - timedelta(days=days - i)).strftime("%Y-%m-%d")
        v = round(abs(20 + 30 * math.sin(i / 5) + random.gauss(0, 8)), 2)
        by_day[d] = v
        total += v
        recent.append({"date": d, "amount": v, "currency": "EUR", "description": "Demo transaction"})
    return {"total": round(total, 2), "by_day": by_day, "recent": recent[-10:], "demo": True}


# ---------------------------------------------------------------------------
# Page 2 — Prospect Generator
# ---------------------------------------------------------------------------
def render_prospects():
    st.markdown("<div class='section-title'>✉️ Générateur de prospects</div>", unsafe_allow_html=True)

    products = _load_products()
    product_names = [p["name"] for p in products]

    tabs = st.tabs(["Saisie manuelle", "Import CSV"])

    # --- Tab: Manual entry ---
    with tabs[0]:
        col1, col2 = st.columns(2)
        with col1:
            name    = st.text_input("Nom complet *", placeholder="Dr. Marie Dupont")
            email   = st.text_input("Email *", placeholder="m.dupont@chu-bordeaux.fr")
            company = st.text_input("Établissement", placeholder="CHU Bordeaux")
        with col2:
            role    = st.text_input("Rôle / Fonction", placeholder="Biologiste médical")
            product = st.selectbox("Produit à pitcher", product_names)
            lang    = st.selectbox("Langue", ["fr", "en"])

        context = st.text_area(
            "Contexte / douleur (1-2 phrases)",
            placeholder="Gère 300+ bilans/jour, manque de temps pour l'interprétation approfondie.",
            height=80,
        )
        tone = st.radio("Ton", ["professional", "friendly", "technical"], horizontal=True)

        col_gen, col_save = st.columns([1, 1])
        if col_gen.button("🤖 Générer l'email", use_container_width=True, type="primary"):
            if not name or not email:
                st.error("Nom et email requis.")
            elif not os.environ.get("ANTHROPIC_API_KEY"):
                st.error("Clé ANTHROPIC_API_KEY manquante — configurez-la dans ⚙️ Settings.")
            else:
                prod_obj = next((p for p in products if p["name"] == product), products[0])
                with st.spinner("Génération en cours…"):
                    try:
                        text = generate_email(
                            name=name, company=company, role=role, context=context,
                            product_name=prod_obj["name"], product_desc=prod_obj["desc"],
                            tone=tone, lang=lang,
                        )
                        st.session_state["gen_email"] = text
                        st.session_state["gen_prospect"] = {
                            "name": name, "email": email, "company": company,
                            "role": role, "context": context, "product": product,
                        }
                    except Exception as exc:
                        st.error(f"Erreur génération : {exc}")

        if "gen_email" in st.session_state:
            st.text_area("Email généré", st.session_state["gen_email"], height=260, key="email_preview")
            if col_save.button("💾 Sauvegarder dans Campaigns", use_container_width=True):
                p = st.session_state["gen_prospect"]
                add_prospect(**p, generated_email=st.session_state["gen_email"])
                st.success(f"Prospect {p['name']} ajouté aux campaigns.")
                del st.session_state["gen_email"]
                del st.session_state["gen_prospect"]

    # --- Tab: CSV import ---
    with tabs[1]:
        st.markdown("""
        **Format CSV attendu** (colonnes obligatoires : `name`, `email`) :
        ```
        name,email,company,role,context,product
        Dr. Dupont,m.dupont@chu.fr,CHU Bordeaux,Biologiste,300 bilans/jour,BioReport AI
        ```
        """)
        f = st.file_uploader("Importer un fichier CSV", type=["csv"])
        if f:
            df = pd.read_csv(f)
            st.dataframe(df.head(10), use_container_width=True)
            prod_csv = st.selectbox("Produit à pitcher pour tout le CSV", product_names, key="csv_prod")
            lang_csv = st.selectbox("Langue", ["fr", "en"], key="csv_lang")
            tone_csv = st.radio("Ton", ["professional", "friendly", "technical"], horizontal=True, key="csv_tone")

            if st.button("🤖 Générer tous les emails", type="primary"):
                if not os.environ.get("ANTHROPIC_API_KEY"):
                    st.error("Clé ANTHROPIC_API_KEY manquante.")
                else:
                    prod_obj = next((p for p in products if p["name"] == prod_csv), products[0])
                    results = []
                    progress = st.progress(0)
                    for i, row in df.iterrows():
                        progress.progress((i + 1) / len(df))
                        try:
                            text = generate_email(
                                name=str(row.get("name", "")),
                                company=str(row.get("company", "")),
                                role=str(row.get("role", "")),
                                context=str(row.get("context", "")),
                                product_name=prod_obj["name"],
                                product_desc=prod_obj["desc"],
                                tone=tone_csv, lang=lang_csv,
                            )
                            add_prospect(
                                name=str(row.get("name", "")),
                                email=str(row.get("email", "")),
                                company=str(row.get("company", "")),
                                role=str(row.get("role", "")),
                                context=str(row.get("context", "")),
                                product=prod_csv,
                                generated_email=text,
                            )
                            results.append({"name": row.get("name"), "email": row.get("email"), "status": "✅"})
                        except Exception as exc:
                            results.append({"name": row.get("name"), "email": row.get("email"), "status": f"❌ {exc}"})
                    progress.empty()
                    st.dataframe(pd.DataFrame(results), use_container_width=True)
                    st.success(f"{len(df)} prospects traités → ajoutés dans Campaigns.")


def _load_products():
    custom = st.session_state.get("custom_products")
    return custom if custom else DEFAULT_PRODUCTS


# ---------------------------------------------------------------------------
# Page 3 — Campaign Tracker
# ---------------------------------------------------------------------------
def render_campaigns():
    st.markdown("<div class='section-title'>📋 Campaign Tracker</div>", unsafe_allow_html=True)

    prospects = get_all_prospects()
    if not prospects:
        st.info("Aucun prospect pour l'instant — générez des emails dans ✉️ Prospects.")
        return

    df = pd.DataFrame(prospects)

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        f_status = st.multiselect("Filtrer par statut", STATUS_OPTIONS, default=STATUS_OPTIONS[:-1])
    with col2:
        f_product = st.multiselect("Filtrer par produit", df["product"].dropna().unique().tolist())
    with col3:
        f_search = st.text_input("Recherche (nom / email / société)", placeholder="dupont…")

    if f_status:
        df = df[df["status"].isin(f_status)]
    if f_product:
        df = df[df["product"].isin(f_product)]
    if f_search:
        mask = (
            df["name"].str.contains(f_search, case=False, na=False)
            | df["email"].str.contains(f_search, case=False, na=False)
            | df["company"].str.contains(f_search, case=False, na=False)
        )
        df = df[mask]

    st.caption(f"{len(df)} prospect(s) affiché(s)")

    # Export
    if st.button("⬇️ Exporter CSV"):
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        st.download_button("Télécharger", buf.getvalue(), "campaigns_export.csv", "text/csv")

    # Table with inline edit
    for _, row in df.iterrows():
        pid = row["id"]
        with st.expander(
            f"{STATUS_COLORS.get(row['status'], '⬜')} **{row['name']}** — {row.get('company','') or '—'}  ·  {row.get('product','')}  ·  `{row['status']}`",
            expanded=False,
        ):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.write(f"📧 {row['email']}")
                st.write(f"🏢 {row.get('company') or '—'} · {row.get('role') or '—'}")
                st.write(f"🗓 Ajouté le {row.get('date_added','')[:10]}")
            with c2:
                new_status = st.selectbox(
                    "Statut", STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(row["status"]) if row["status"] in STATUS_OPTIONS else 0,
                    key=f"status_{pid}",
                )
                revenue_input = st.number_input(
                    "CA attribué (€)", value=float(row.get("revenue_attributed") or 0),
                    min_value=0.0, step=10.0, key=f"rev_{pid}",
                )
                notes = st.text_input("Notes", value=row.get("notes") or "", key=f"notes_{pid}")
            with c3:
                if st.button("💾 Sauvegarder", key=f"save_{pid}", use_container_width=True):
                    updates = {"status": new_status, "revenue_attributed": revenue_input, "notes": notes}
                    if new_status == "sent" and not row.get("date_sent"):
                        updates["date_sent"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    if new_status == "replied" and not row.get("date_replied"):
                        updates["date_replied"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    update_prospect(pid, **updates)
                    st.success("Mis à jour.")
                    st.rerun()
                if st.button("🗑 Supprimer", key=f"del_{pid}", use_container_width=True):
                    delete_prospect(pid)
                    st.rerun()

            if row.get("generated_email"):
                st.text_area("Email généré", row["generated_email"], height=200, key=f"email_{pid}", disabled=True)
                lines = row["generated_email"].split("\n")
                subject = next((l.replace("Subject:", "").replace("Objet:", "").strip() for l in lines if l.startswith(("Subject:", "Objet:"))), "")
                body_text = "\n".join(l for l in lines if not l.startswith(("Subject:", "Objet:"))).strip()
                mailto = f"mailto:{row['email']}?subject={subject}&body={body_text[:800]}"
                st.markdown(f"[📨 Ouvrir dans votre client mail]({mailto})")

    # Funnel chart
    st.divider()
    st.markdown("<div class='section-title'>Entonnoir de conversion</div>", unsafe_allow_html=True)
    all_prospects = get_all_prospects()
    counts = {s: sum(1 for p in all_prospects if p["status"] == s) for s in STATUS_OPTIONS[:-1]}
    fig = go.Figure(go.Funnel(
        y=list(counts.keys()),
        x=list(counts.values()),
        marker_color=["#475569", "#3b82f6", "#22c55e", "#a855f7"],
        textinfo="value+percent initial",
    ))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a", font_color="#e2e8f0",
        margin=dict(t=10, b=10, l=0, r=0), height=300,
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Page 4 — Settings
# ---------------------------------------------------------------------------
def render_settings():
    st.markdown("<div class='section-title'>⚙️ Settings</div>", unsafe_allow_html=True)

    st.markdown("#### 🔑 API Keys")
    st.info("Sur Streamlit Cloud, utilisez les **Secrets** (Settings → Secrets) plutôt que ce formulaire.")

    with st.form("api_keys_form"):
        anthropic_key = st.text_input(
            "ANTHROPIC_API_KEY",
            value=os.environ.get("ANTHROPIC_API_KEY", ""),
            type="password",
            placeholder="sk-ant-...",
        )
        stripe_key = st.text_input(
            "STRIPE_API_KEY",
            value=os.environ.get("STRIPE_API_KEY", ""),
            type="password",
            placeholder="sk_live_...",
        )
        if st.form_submit_button("💾 Sauvegarder dans la session", type="primary"):
            os.environ["ANTHROPIC_API_KEY"] = anthropic_key
            os.environ["STRIPE_API_KEY"] = stripe_key
            st.success("Clés mises à jour pour cette session.")

    st.divider()
    st.markdown("#### 🏷 Produits")
    st.markdown("Personnalisez les produits à pitcher :")

    products = _load_products()
    df_prod = pd.DataFrame(products)
    edited = st.data_editor(
        df_prod,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "name":  st.column_config.TextColumn("Nom", width="medium"),
            "desc":  st.column_config.TextColumn("Description", width="large"),
            "price": st.column_config.TextColumn("Prix", width="small"),
        },
    )
    if st.button("💾 Sauvegarder les produits"):
        st.session_state["custom_products"] = edited.to_dict("records")
        st.success("Catalogue produits mis à jour.")

    st.divider()
    st.markdown("#### ℹ️ À propos")
    st.markdown("""
    **OutreachAI** — Tableau de bord de prospection commerciale
    Propulsé par Claude API (Anthropic) + Stripe API
    © 2026 Mamadou Lamine TALL — [github.com/mamadoulaminetall](https://github.com/mamadoulaminetall)
    """)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    init_db()
    page = render_sidebar()

    if page == "📊 Revenue":
        render_revenue()
    elif page == "✉️ Prospects":
        render_prospects()
    elif page == "📋 Campaigns":
        render_campaigns()
    elif page == "⚙️ Settings":
        render_settings()


main()
