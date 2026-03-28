import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io

st.set_page_config(page_title="CCS Analytics Dashboard", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');

    * {font-family: 'Roboto', sans-serif;}
    .main {background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 2rem;}
    .stApp {background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);}

    h1 {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(10px);
        color: #ffffff !important;
        padding: 2rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        font-weight: 500;
        border: 1px solid rgba(255, 255, 255, 0.18);
    }

    h2, h3, h4 {color: #ffffff !important; font-weight: 500;}
    p, label, .stMarkdown {color: #e8eaf6 !important;}

    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        border: 1px solid rgba(255, 255, 255, 0.18);
        transition: all 0.3s ease;
    }

    div[data-testid="metric-container"]:hover {
        background: rgba(255, 255, 255, 0.15);
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
    }

    div[data-testid="stMetricValue"] {
        font-size: 2.2rem;
        font-weight: 700;
        color: #ffffff !important;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        color: #b0bec5 !important;
        font-weight: 500;
    }

    div[data-testid="stMetricDelta"] {
        font-size: 0.8rem;
        color: #90caf9 !important;
    }

    div[data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255, 255, 255, 0.15);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255, 255, 255, 0.05);
        padding: 8px;
        border-radius: 10px;
    }

    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 12px 24px;
        color: #ffffff;
        font-weight: 500;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }

    .stDataFrame {background: rgba(255, 255, 255, 0.08); border-radius: 10px;}
    table {color: #ffffff !important;}
    thead tr th {background: rgba(102, 126, 234, 0.3) !important; color: #ffffff !important; font-weight: 600;}
    tbody tr td {color: #e0e0e0 !important; border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;}

    .upload-section {
        background: rgba(255, 255, 255, 0.1);
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px dashed rgba(255, 255, 255, 0.3);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def merge_uploaded_data(clients_file, io_file, naars_file):
    try:
        clients_df = pd.read_excel(clients_file)
        clients_df['Client UID'] = clients_df['Client UID'].astype(str).str.strip()

        date_cols = ['Birthdate', 'Arrival Date', 'Landing Date']
        for col in date_cols:
            if col in clients_df.columns:
                clients_df[col] = pd.to_datetime(clients_df[col], errors='coerce')

        current_date = pd.Timestamp.now()
        if 'Birthdate' in clients_df.columns:
            clients_df['age'] = ((current_date - clients_df['Birthdate']).dt.days / 365.25).round(1)
        if 'Arrival Date' in clients_df.columns:
            clients_df['years_in_canada'] = ((current_date - clients_df['Arrival Date']).dt.days / 365.25).round(2)
        if 'Landing Date' in clients_df.columns:
            clients_df['months_since_landing'] = ((current_date - clients_df['Landing Date']).dt.days / 30.44).round(1)

        io_sheets = pd.read_excel(io_file, sheet_name=None)
        io_dfs = []
        for sheet_name, df in io_sheets.items():
            df['data_source_month'] = sheet_name
            io_dfs.append(df)
        io_df = pd.concat(io_dfs, ignore_index=True)
        io_df['Client UID'] = io_df['Client UID'].astype(str).str.strip()
        if 'Service Date' in io_df.columns:
            io_df['Service Date'] = pd.to_datetime(io_df['Service Date'], errors='coerce')
        io_df = io_df.drop_duplicates()

        naars_sheets = pd.read_excel(naars_file, sheet_name=None)
        naars_dfs = []
        for sheet_name, df in naars_sheets.items():
            df['data_source_month'] = sheet_name
            naars_dfs.append(df)
        naars_df = pd.concat(naars_dfs, ignore_index=True)
        naars_df['Client UID'] = naars_df['Client UID'].astype(str).str.strip()
        if 'Assessment Date' in naars_df.columns:
            naars_df['Assessment Date'] = pd.to_datetime(naars_df['Assessment Date'], errors='coerce')
        naars_df = naars_df.drop_duplicates()

        naars_summary = naars_df.groupby('Client UID').agg({
            'Assessment Date': ['min', 'max', 'count']
        }).reset_index()
        naars_summary.columns = ['Client UID', 'first_assessment_date', 'last_assessment_date', 'total_assessments']

        first_assessments = naars_df.sort_values('Assessment Date').groupby('Client UID').first().reset_index()
        needs_cols = [col for col in first_assessments.columns if 'Needs' in col or 'Need' in col]
        asset_cols = [col for col in first_assessments.columns if 'Asset' in col]
        referral_cols = [col for col in first_assessments.columns if 'referral' in col]
        required_cols = [col for col in first_assessments.columns if 'Required' in col]

        first_assessment_cols = ['Client UID'] + needs_cols + asset_cols + referral_cols + required_cols
        first_assessments_filtered = first_assessments[first_assessment_cols].copy()
        rename_dict = {col: f'first_assess_{col}' for col in first_assessments_filtered.columns if col != 'Client UID'}
        first_assessments_filtered = first_assessments_filtered.rename(columns=rename_dict)

        naars_client_summary = naars_summary.merge(first_assessments_filtered, on='Client UID', how='left')

        io_summary = io_df.groupby('Client UID').agg({
            'Service Date': ['min', 'max', 'count'],
            'Service Duration': 'sum',
            'Program Name': 'nunique',
            'Service Type': 'nunique'
        }).reset_index()
        io_summary.columns = ['Client UID', 'first_service_date', 'last_service_date', 
                              'total_services', 'total_service_hours', 'unique_programs', 'unique_service_types']

        if 'Service Type' in io_df.columns:
            service_type_counts = io_df.groupby(['Client UID', 'Service Type']).size().unstack(fill_value=0)
            service_type_counts.columns = [f'services_{col.lower().replace(" ", "_")}_count' for col in service_type_counts.columns]
            service_type_counts = service_type_counts.reset_index()
            io_summary = io_summary.merge(service_type_counts, on='Client UID', how='left')

        topic_cols = ['National Info', 'Provincial Info', 'Community Info', 'Empl,Educ,Financ', 
                      'Health-Wellbeing', 'Francophone', 'Equity', 'Indigenous']
        for topic in topic_cols:
            if topic in io_df.columns:
                topic_flag = io_df[io_df[topic] == 1].groupby('Client UID').size().reset_index()
                topic_flag.columns = ['Client UID', f'received_{topic.lower().replace(",", "_").replace("-", "_").replace(" ", "_")}']
                io_summary = io_summary.merge(topic_flag, on='Client UID', how='left')
                io_summary[f'received_{topic.lower().replace(",", "_").replace("-", "_").replace(" ", "_")}'] = \
                    io_summary[f'received_{topic.lower().replace(",", "_").replace("-", "_").replace(" ", "_")}'].fillna(0).astype(int)

        client_master = clients_df.copy()
        client_master = client_master.merge(naars_client_summary, on='Client UID', how='left')
        client_master = client_master.merge(io_summary, on='Client UID', how='left')

        if 'first_assessment_date' in client_master.columns and 'Landing Date' in client_master.columns:
            client_master['days_landing_to_assessment'] = \
                (client_master['first_assessment_date'] - client_master['Landing Date']).dt.days

        if 'first_service_date' in client_master.columns and 'first_assessment_date' in client_master.columns:
            client_master['days_assessment_to_service'] = \
                (client_master['first_service_date'] - client_master['first_assessment_date']).dt.days

        def categorize_engagement(row):
            has_assessment = pd.notna(row.get('first_assessment_date'))
            has_service = pd.notna(row.get('first_service_date'))
            if has_assessment and has_service:
                return 'Assessed and Served'
            elif has_assessment and not has_service:
                return 'Assessed Only'
            elif not has_assessment and has_service:
                return 'Served Only'
            else:
                return 'Not Engaged'

        client_master['engagement_status'] = client_master.apply(categorize_engagement, axis=1)

        return client_master, "Data processed successfully!"

    except Exception as e:
        return None, f"Error processing data: {str(e)}"

if 'uploaded_data' not in st.session_state:
    st.session_state.uploaded_data = None
if 'use_uploaded' not in st.session_state:
    st.session_state.use_uploaded = False

st.title("CCS Outcome Measurement Dashboard")

st.sidebar.markdown("### Data Source")
st.sidebar.markdown("")

data_source = st.sidebar.radio(
    "Select data source:",
    ["Default Data (Jun-Dec 2024)", "Upload New Data"],
    key='data_source'
)

if data_source == "Upload New Data":
    st.sidebar.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.sidebar.markdown("#### Upload Files")

    clients_file = st.sidebar.file_uploader("Clients Excel File", type=['xlsx'], key='clients')
    io_file = st.sidebar.file_uploader("Services (IO) Excel File", type=['xlsx'], key='io')
    naars_file = st.sidebar.file_uploader("Assessments (NAARS) Excel File", type=['xlsx'], key='naars')

    if clients_file and io_file and naars_file:
        if st.sidebar.button("Process Uploaded Data", type="primary"):
            with st.spinner("Processing data..."):
                processed_data, message = merge_uploaded_data(clients_file, io_file, naars_file)

                if processed_data is not None:
                    st.session_state.uploaded_data = processed_data
                    st.session_state.use_uploaded = True
                    st.sidebar.success(message)
                    st.rerun()
                else:
                    st.sidebar.error(message)
    else:
        st.sidebar.info("Upload all 3 files to process")

    st.sidebar.markdown('</div>', unsafe_allow_html=True)

@st.cache_data
def load_default_data():
    df = pd.read_csv(r"c:\Users\HP\Downloads\Capstone\Sponsor Files\CCS_Client_Level_Master.csv")
    date_cols = ['Birthdate', 'Landing Date', 'Arrival Date', 'first_assessment_date', 
                 'first_service_date', 'last_assessment_date', 'last_service_date']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    return df

if st.session_state.use_uploaded and st.session_state.uploaded_data is not None:
    client_master = st.session_state.uploaded_data
    data_label = "Uploaded Data"
else:
    client_master = load_default_data()
    data_label = "Jun-Dec 2024"

st.markdown(f"<p style='text-align: center; color: #b0bec5; font-size: 1rem; margin-top: -1.5rem;'><strong>Data Source:</strong> {data_label} | <strong>Total Clients:</strong> {len(client_master):,} | <strong>Last Updated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### Dashboard Filters")
st.sidebar.markdown("")

if 'immigration_class' in client_master.columns:
    immigration_classes = ['All'] + sorted(client_master['immigration_class'].dropna().unique().tolist())
    selected_class = st.sidebar.selectbox("Immigration Class", immigration_classes)
else:
    selected_class = 'All'

if 'Country of Origin' in client_master.columns:
    countries = ['All'] + sorted(client_master['Country of Origin'].dropna().unique().tolist())
    selected_country = st.sidebar.selectbox("Country of Origin", countries)
else:
    selected_country = 'All'

filtered_df = client_master.copy()
if selected_class != 'All':
    filtered_df = filtered_df[filtered_df['immigration_class'] == selected_class]
if selected_country != 'All':
    filtered_df = filtered_df[filtered_df['Country of Origin'] == selected_country]

st.sidebar.markdown("---")
filter_pct = len(filtered_df)/len(client_master)*100
st.sidebar.metric("Filtered Clients", f"{len(filtered_df):,}", f"{filter_pct:.1f}%")

total_clients = len(filtered_df)
assessed_clients = filtered_df['first_assessment_date'].notna().sum()
served_clients = filtered_df['first_service_date'].notna().sum()
assessment_rate = (assessed_clients / total_clients * 100) if total_clients > 0 else 0
service_rate = (served_clients / total_clients * 100) if total_clients > 0 else 0

days_to_assessment = filtered_df['days_landing_to_assessment'].dropna()
avg_days_to_assessment = days_to_assessment.mean() if len(days_to_assessment) > 0 else None

days_to_service = filtered_df['days_assessment_to_service'].abs().dropna()
avg_days_to_service = days_to_service.mean() if len(days_to_service) > 0 else None

if 'first_service_date' in filtered_df.columns and 'last_service_date' in filtered_df.columns:
    engagement_duration = (filtered_df['last_service_date'] - filtered_df['first_service_date']).dt.days.abs()
    multi_month = (engagement_duration >= 30).sum()
    retention_rate = (multi_month / served_clients * 100) if served_clients > 0 else 0
else:
    retention_rate = 0
    multi_month = 0

tab1, tab2, tab3, tab4 = st.tabs([
    "Overview",
    "Client Access & Engagement",
    "Demographics & Characteristics", 
    "Assessment Quality"
])

with tab1:
    st.markdown("## Executive Summary")
    st.markdown("")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Clients", f"{total_clients:,}")
    with col2:
        st.metric("Assessment Rate", f"{assessment_rate:.1f}%", f"{assessed_clients:,} clients")
    with col3:
        st.metric("Service Rate", f"{service_rate:.1f}%", f"{served_clients:,} clients")
    with col4:
        avg_services = filtered_df['total_services'].mean() if 'total_services' in filtered_df.columns else 0
        st.metric("Avg Services/Client", f"{avg_services:.1f}")

    st.markdown('<div style="margin: 2rem 0;"></div>', unsafe_allow_html=True)

    row1_col1, row1_col2 = st.columns([1, 1])

    with row1_col1:
        st.markdown("### Engagement Status Overview")

        if 'engagement_status' in filtered_df.columns:
            engagement_counts = filtered_df['engagement_status'].value_counts().reset_index()
            engagement_counts.columns = ['Status', 'Count']

            fig = px.bar(
                engagement_counts,
                x='Status',
                y='Count',
                text='Count',
                color='Status',
                color_discrete_map={
                    'Assessed and Served': '#2ecc71',
                    'Assessed Only': '#f39c12',
                    'Served Only': '#3498db',
                    'Not Engaged': '#95a5a6'
                }
            )

            fig.update_traces(
                texttemplate='%{text:,}',
                textposition='outside',
                textfont=dict(size=11, color='#ffffff'),
                marker_line_color='rgba(30, 60, 114, 0.8)',
                marker_line_width=2
            )

            fig.update_layout(
                height=400,
                margin=dict(t=20, b=90, l=60, r=20),
                xaxis_title='Engagement Category',
                yaxis_title='Number of Clients',
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(255,255,255,0.02)',
                font=dict(color='#ffffff'),
                xaxis=dict(tickangle=-15, showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
            )

            st.plotly_chart(fig, use_container_width=True)

    with row1_col2:
        st.markdown("### Top 10 Countries of Origin")

        if 'Country of Origin' in filtered_df.columns:
            country_counts = filtered_df['Country of Origin'].value_counts().head(10).reset_index()
            country_counts.columns = ['Country', 'Count']

            fig = px.bar(
                country_counts,
                y='Country',
                x='Count',
                orientation='h',
                text='Count',
                color='Count',
                color_continuous_scale='Viridis'
            )

            fig.update_traces(
                texttemplate='%{text:,}',
                textposition='outside',
                textfont=dict(size=11, color='#ffffff'),
                marker_line_color='rgba(30, 60, 114, 0.8)',
                marker_line_width=1.5
            )

            fig.update_layout(
                height=400,
                margin=dict(t=20, b=40, l=120, r=40),
                xaxis_title='Number of Clients',
                yaxis_title='Country',
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(255,255,255,0.02)',
                font=dict(color='#ffffff'),
                xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                yaxis=dict(showgrid=False)
            )

            st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown("## Client Access & Engagement Metrics")
    st.markdown("")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Assessment Coverage", f"{assessment_rate:.1f}%", f"{assessed_clients:,} / {total_clients:,}")
        if assessment_rate >= 90:
            st.markdown('<p style="color: #2ecc71; font-weight: 600; font-size: 0.8rem;">Target: ≥90%</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p style="color: #f39c12; font-weight: 600; font-size: 0.8rem;">Target: ≥90%</p>', unsafe_allow_html=True)

    with col2:
        if avg_days_to_assessment:
            within = (days_to_assessment <= 30).sum()/len(days_to_assessment)*100
            st.metric("Days to Assessment", f"{avg_days_to_assessment:.0f}", f"{within:.0f}% ≤30d")
            if avg_days_to_assessment <= 30:
                st.markdown('<p style="color: #2ecc71; font-weight: 600; font-size: 0.8rem;">Target: ≤30d</p>', unsafe_allow_html=True)
            else:
                st.markdown('<p style="color: #f39c12; font-weight: 600; font-size: 0.8rem;">Target: ≤30d</p>', unsafe_allow_html=True)
        else:
            st.metric("Days to Assessment", "N/A")

    with col3:
        if avg_days_to_service:
            within = (days_to_service <= 14).sum()/len(days_to_service)*100
            st.metric("Days to Service", f"{avg_days_to_service:.0f}", f"{within:.0f}% ≤14d")
            if avg_days_to_service <= 14:
                st.markdown('<p style="color: #2ecc71; font-weight: 600; font-size: 0.8rem;">Target: ≤14d</p>', unsafe_allow_html=True)
            else:
                st.markdown('<p style="color: #f39c12; font-weight: 600; font-size: 0.8rem;">Target: ≤14d</p>', unsafe_allow_html=True)
        else:
            st.metric("Days to Service", "N/A")

    with col4:
        st.metric("Service Participation", f"{service_rate:.1f}%", f"{served_clients:,} / {total_clients:,}")
        if service_rate >= 95:
            st.markdown('<p style="color: #2ecc71; font-weight: 600; font-size: 0.8rem;">Target: ≥95%</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p style="color: #3498db; font-weight: 600; font-size: 0.8rem;">Monitoring</p>', unsafe_allow_html=True)

    with col5:
        st.metric("Client Retention", f"{retention_rate:.1f}%", f"{int(multi_month):,} clients")
        st.markdown('<p style="color: #3498db; font-weight: 600; font-size: 0.8rem;">Monitoring</p>', unsafe_allow_html=True)

    st.markdown('<div style="margin: 2rem 0;"></div>', unsafe_allow_html=True)

    row1_col1, row1_col2 = st.columns([1, 1])

    with row1_col1:
        st.markdown("### Assessment Coverage")

        assessment_data = pd.DataFrame({
            'Status': ['Assessed', 'Not Assessed'],
            'Count': [assessed_clients, total_clients - assessed_clients]
        })

        fig = px.pie(
            assessment_data,
            values='Count',
            names='Status',
            hole=0.5,
            color='Status',
            color_discrete_map={'Assessed': '#2ecc71', 'Not Assessed': '#e74c3c'}
        )

        fig.update_traces(
            textposition='outside',
            textinfo='label+percent',
            textfont=dict(size=13, color='#ffffff'),
            pull=[0.05, 0.05],
            marker=dict(line=dict(color='rgba(30, 60, 114, 0.8)', width=3))
        )

        fig.update_layout(
            height=380,
            margin=dict(t=20, b=20, l=40, r=40),
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            annotations=[dict(
                text=f'<b>{assessment_rate:.1f}%</b><br><span style="font-size:12px; color:#b0bec5;">Coverage</span>',
                x=0.5, y=0.5,
                font_size=28,
                font_color='#ffffff',
                showarrow=False
            )]
        )

        st.plotly_chart(fig, use_container_width=True)

    with row1_col2:
        st.markdown("### Timing: Days to Assessment")

        if len(days_to_assessment) > 0:
            fig = go.Figure()

            fig.add_trace(go.Histogram(
                x=days_to_assessment,
                nbinsx=35,
                marker_color='#667eea',
                marker_line_color='rgba(30, 60, 114, 0.8)',
                marker_line_width=1,
                opacity=0.9
            ))

            fig.add_vline(
                x=days_to_assessment.mean(),
                line_dash="dash",
                line_color="#e74c3c",
                line_width=2.5,
                annotation=dict(text=f"Avg: {days_to_assessment.mean():.0f}d", font=dict(size=11, color="#e74c3c"))
            )

            fig.add_vline(
                x=30,
                line_dash="dot",
                line_color="#f39c12",
                line_width=2.5,
                annotation=dict(text="Target: 30d", font=dict(size=11, color="#f39c12"), yanchor="bottom")
            )

            fig.update_layout(
                height=380,
                margin=dict(t=20, b=60, l=60, r=20),
                xaxis_title='Days from Landing',
                yaxis_title='Number of Clients',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(255,255,255,0.02)',
                font=dict(color='#ffffff'),
                xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No data available")

with tab3:
    st.markdown("## Client Demographics & Characteristics")
    st.markdown("")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        countries_count = filtered_df['Country of Origin'].nunique() if 'Country of Origin' in filtered_df.columns else 0
        st.metric("Countries Represented", f"{countries_count}")

    with col2:
        classes_count = filtered_df['immigration_class'].nunique() if 'immigration_class' in filtered_df.columns else 0
        st.metric("Immigration Classes", f"{classes_count}")

    with col3:
        avg_age = filtered_df['age'].mean() if 'age' in filtered_df.columns else 0
        st.metric("Average Age", f"{avg_age:.1f} yrs")

    with col4:
        avg_time = filtered_df['years_in_canada'].mean() if 'years_in_canada' in filtered_df.columns else 0
        st.metric("Avg Time in Canada", f"{avg_time:.1f} yrs")

    st.markdown('<div style="margin: 2rem 0;"></div>', unsafe_allow_html=True)

    row1, row2 = st.columns([1, 1])

    with row1:
        st.markdown("### Gender Distribution")

        if 'Gender' in filtered_df.columns:
            gender_counts = filtered_df['Gender'].value_counts().reset_index()
            gender_counts.columns = ['Gender', 'Count']

            fig = px.pie(
                gender_counts,
                values='Count',
                names='Gender',
                hole=0.4,
                color_discrete_sequence=['#3498db', '#e74c3c', '#95a5a6']
            )

            fig.update_traces(
                textposition='outside',
                textinfo='label+percent',
                textfont=dict(size=12, color='#ffffff'),
                marker=dict(line=dict(color='rgba(30, 60, 114, 0.8)', width=2))
            )

            fig.update_layout(
                height=350,
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=20, b=20, l=20, r=20)
            )

            st.plotly_chart(fig, use_container_width=True)

    with row2:
        st.markdown("### Immigration Class Distribution")

        if 'immigration_class' in filtered_df.columns:
            class_counts = filtered_df['immigration_class'].value_counts().head(8).reset_index()
            class_counts.columns = ['Class', 'Count']

            fig = px.bar(
                class_counts,
                y='Class',
                x='Count',
                orientation='h',
                text='Count',
                color='Count',
                color_continuous_scale='Blues'
            )

            fig.update_traces(
                texttemplate='%{text:,}',
                textposition='outside',
                textfont=dict(size=11, color='#ffffff'),
                marker_line_color='rgba(30, 60, 114, 0.8)',
                marker_line_width=1.5
            )

            fig.update_layout(
                height=350,
                margin=dict(t=20, b=40, l=180, r=40),
                xaxis_title='Number of Clients',
                yaxis_title='Immigration Class',
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(255,255,255,0.02)',
                font=dict(color='#ffffff'),
                xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                yaxis=dict(showgrid=False)
            )

            st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.markdown("## Assessment Quality Metrics")
    st.markdown("")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        avg_needs = filtered_df['total_unique_needs_identified'].mean() if 'total_unique_needs_identified' in filtered_df.columns else 0
        st.metric("Avg Needs/Client", f"{avg_needs:.1f}")

    with col2:
        avg_referrals = filtered_df['total_referrals_given'].mean() if 'total_referrals_given' in filtered_df.columns else 0
        st.metric("Avg Referrals/Client", f"{avg_referrals:.1f}")

    with col3:
        if 'total_assessments' in filtered_df.columns:
            reassessed = (filtered_df['total_assessments'] > 1).sum()
            reassess_rate = (reassessed / assessed_clients * 100) if assessed_clients > 0 else 0
            st.metric("Reassessment Rate", f"{reassess_rate:.1f}%", f"{reassessed} clients")

    with col4:
        if 'total_unique_needs_identified' in filtered_df.columns:
            high_complexity = (filtered_df['total_unique_needs_identified'] >= 5).sum()
            complexity_rate = (high_complexity / assessed_clients * 100) if assessed_clients > 0 else 0
            st.metric("High Complexity Rate", f"{complexity_rate:.1f}%", f"{high_complexity} clients")

    st.markdown('<div style="margin: 2rem 0;"></div>', unsafe_allow_html=True)

    row1, row2 = st.columns([1, 1])

    with row1:
        st.markdown("### Needs Identified per Client")

        if 'total_unique_needs_identified' in filtered_df.columns:
            needs_data = filtered_df['total_unique_needs_identified'].dropna()

            fig = go.Figure()

            fig.add_trace(go.Histogram(
                x=needs_data,
                marker_color='#e74c3c',
                marker_line_color='rgba(30, 60, 114, 0.8)',
                marker_line_width=1,
                opacity=0.9
            ))

            fig.add_vline(
                x=needs_data.mean(),
                line_dash="dash",
                line_color="#2ecc71",
                line_width=2.5,
                annotation=dict(text=f"Mean: {needs_data.mean():.1f}", font=dict(size=11, color="#2ecc71"))
            )

            fig.update_layout(
                height=350,
                margin=dict(t=20, b=60, l=60, r=20),
                xaxis_title='Number of Needs',
                yaxis_title='Number of Clients',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(255,255,255,0.02)',
                font=dict(color='#ffffff'),
                xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
            )

            st.plotly_chart(fig, use_container_width=True)

    with row2:
        st.markdown("### Service Intensity Distribution")

        if 'total_services' in filtered_df.columns:
            services_data = filtered_df['total_services'].dropna()

            fig = go.Figure()

            fig.add_trace(go.Histogram(
                x=services_data,
                nbinsx=25,
                marker_color='#9b59b6',
                marker_line_color='rgba(30, 60, 114, 0.8)',
                marker_line_width=1,
                opacity=0.9
            ))

            fig.add_vline(
                x=services_data.mean(),
                line_dash="dash",
                line_color="#2ecc71",
                line_width=2.5,
                annotation=dict(text=f"Mean: {services_data.mean():.1f}", font=dict(size=11, color="#2ecc71"))
            )

            fig.update_layout(
                height=350,
                margin=dict(t=20, b=60, l=60, r=20),
                xaxis_title='Number of Services',
                yaxis_title='Number of Clients',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(255,255,255,0.02)',
                font=dict(color='#ffffff'),
                xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
            )

            st.plotly_chart(fig, use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### KPI Targets")
st.sidebar.markdown("""
- **Assessment Coverage:** ≥90%
- **Days to Assessment:** ≤30 days
- **Days to Service:** ≤14 days
- **Service Participation:** ≥95%
""")

if st.session_state.use_uploaded:
    st.sidebar.markdown("---")
    if st.sidebar.button("Reset to Default Data"):
        st.session_state.use_uploaded = False
        st.session_state.uploaded_data = None
        st.rerun()

st.markdown('<div style="margin: 3rem 0 1rem 0;"></div>', unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; background: rgba(255, 255, 255, 0.08); padding: 1.5rem; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.15);'>
    <p style='color: #b0bec5; margin: 0;'>
        <strong style='color: #ffffff;'>Data:</strong> CCS Client-Level Master ({len(client_master):,} clients) | 
        <strong style='color: #ffffff;'>Version:</strong> 1.0
    </p>
</div>
""", unsafe_allow_html=True)
