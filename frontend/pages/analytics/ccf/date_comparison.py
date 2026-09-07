import dash
from dash import html, dcc, callback, Input, Output, State
from dash_bootstrap_components import Container, Row, Col, Card, CardHeader, CardBody
import dash_ag_grid as dag
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from frontend.shared.theme import get_plotly_template, make_header_with_download, make_export_dropdown, should_use_log
from frontend.shared.api_client import get_dataframe
import dash_bootstrap_components as dbc
from frontend.components.cards import make_kpi_card, wrap_chart_card
from frontend.components.empty_state import render_empty_state, e_ui

dash.register_page(__name__, path='/ccf/date_comparison', name='Date Comparison')

layout = Container([
    Row([
        Col([
            html.Div([
                html.H3("Specific Date Comparison", className="display-xl mb-0"),
                html.P("Compare key performance metrics across selected discrete dates and days of the week.", className="text-muted mb-0 mt-2")
            ])
        ], width=8),
        Col([
            html.Div([
                make_export_dropdown("compare"),
                dcc.Download(id={'type': 'download-data-compare', 'index': 'compare'})
            ])
        ], width=4, className="d-flex align-items-center justify-content-end mb-4")
    ]),

    Row(style={"position": "relative", "zIndex": 100}, children=[
        Col([
            Card([
                CardBody([
                    Row([
                        Col([
                            html.H6("SPECIFIC DATES", className="section-title mb-2"),
                            dcc.Dropdown(
                                id='discrete-date-selector',
                                options=[],
                                value=[],
                                multi=True,
                                placeholder="Select Dates..."
                            )
                        ], width=12, md=6, className="mb-3 mb-md-0"),
                        Col([
                            html.H6("DAYS OF WEEK", className="section-title mb-2"),
                            dcc.Dropdown(
                                id='day-of-week-selector',
                                options=[
                                    {'label': 'Monday', 'value': 'Monday'},
                                    {'label': 'Tuesday', 'value': 'Tuesday'},
                                    {'label': 'Wednesday', 'value': 'Wednesday'},
                                    {'label': 'Thursday', 'value': 'Thursday'},
                                    {'label': 'Friday', 'value': 'Friday'},
                                    {'label': 'Saturday', 'value': 'Saturday'},
                                    {'label': 'Sunday', 'value': 'Sunday'}
                                ],
                                value=[],
                                multi=True,
                                placeholder="Select Days..."
                            )
                        ], width=12, md=6)
                    ])
                ])
            ], className="custom-card mb-4", style={'overflow': 'visible', 'position': 'relative', 'zIndex': 999})
        ], width=12)
    ]),

    # KPI Row
    dcc.Loading(type="dot", color="var(--color-primary)", children=Row(id='comparison-kpi-row', className="mb-4")),

    # Charts Row 1: Company Performance
    Row([
        Col([wrap_chart_card("compare-volume-chart", "Company Performance (Volume & SL%)", "compare")], width=12, className="mb-4"),
    ]),

    # Charts Row 2: Hourly Trends
    Row([
        Col([wrap_chart_card("compare-hourly-chart", "Hourly Volume Trends", "compare")], width=12, className="mb-4"),
    ]),

    # Charts Row 3: Funnel
    Row([
        Col([wrap_chart_card("compare-funnel-chart", "Abandonment Flow", "compare")], width=12, className="mb-4"),
    ]),
    
    # Charts Row 4: Language & Radar
    Row([
        Col([wrap_chart_card("compare-lang-chart", "Total Volume by Language", "compare")], width=12, lg=6, className="mb-4"),
        Col([wrap_chart_card("compare-radar-chart", "Vendor Performance Footprint (Averaged)", "compare")], width=12, lg=6, className="mb-4"),
    ]),
    
    # Data Table Row
    Row([
        Col([
            Card([
                CardHeader("Raw Data (Aggregated by Selected Dates)"),
                CardBody(id='comparison-data-table')
            ], className="custom-card h-100")
        ], width=12, className="mb-5")
    ]),
])

@callback(
    Output('discrete-date-selector', 'options'),
    Input('data-store', 'data'),
    State('auth-state', 'data')
)
def populate_date_selector(data_ref, auth_state):
    if not data_ref or not isinstance(data_ref, dict) or 'filename' not in data_ref:
        return []
        
    token = auth_state.get('token') if auth_state else None
    if not token:
        return []
        
    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
    
    date_col = None
    if 'Timestamp' in df.columns:
        date_col = 'Timestamp'
    elif 'Date' in df.columns:
        date_col = 'Date'
    elif 'Call Start Time' in df.columns:
        date_col = 'Call Start Time'
        
    if not date_col:
        return []
        
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=[date_col])
    
    if df.empty:
        return []
        
    unique_dates = df[date_col].dt.date.unique()
    unique_dates = sorted(unique_dates, reverse=True)
    d_options = [{'label': d.strftime('%Y-%m-%d'), 'value': d.strftime('%Y-%m-%d')} for d in unique_dates]
    
    return d_options

@callback(
    Output('comparison-kpi-row', 'children'),
    Output('compare-volume-chart-container', 'children'),
    Output('compare-hourly-chart-container', 'children'),
    Output('compare-funnel-chart-container', 'children'),
    Output('compare-lang-chart-container', 'children'),
    Output('compare-radar-chart-container', 'children'),
    Output('comparison-data-table', 'children'),
    Input('data-store', 'data'),
    Input('discrete-date-selector', 'value'),
    Input('day-of-week-selector', 'value'),
    Input('company-filter', 'value'),
    Input('language-filter', 'value'),
    State('auth-state', 'data')
)
def update_comparison_charts(data_ref, selected_dates, selected_days, companies, languages, auth_state):

    template = get_plotly_template()
    no_data_table = html.P("No data available.")
    
    if not data_ref or not isinstance(data_ref, dict) or 'filename' not in data_ref or (not selected_dates and not selected_days):
        return [], e_ui('compare-volume-chart'), e_ui('compare-hourly-chart'), e_ui('compare-funnel-chart'), e_ui('compare-lang-chart'), e_ui('compare-radar-chart'), html.P("Select dates or days to view comparison.")
        
    token = auth_state.get('token') if auth_state else None
    if not token:
        return [], e_ui('compare-volume-chart'), e_ui('compare-hourly-chart'), e_ui('compare-funnel-chart'), e_ui('compare-lang-chart'), e_ui('compare-radar-chart'), html.P("Unauthorized.")
        
    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
    if df is None or df.empty:
        return [], e_ui('compare-volume-chart'), e_ui('compare-hourly-chart'), e_ui('compare-funnel-chart'), e_ui('compare-lang-chart'), e_ui('compare-radar-chart'), no_data_table
    
    # Filter by Company and Language
    if companies and 'Company' in df.columns:
        df = df[df['Company'].isin(companies)]
    if languages and 'Language' in df.columns:
        df = df[df['Language'].isin(languages)]
        
    date_col = None
    if 'Timestamp' in df.columns:
        date_col = 'Timestamp'
    elif 'Date' in df.columns:
        date_col = 'Date'
    elif 'Call Start Time' in df.columns:
        date_col = 'Call Start Time'
        
    if not date_col:
        return [], e_ui('compare-volume-chart'), e_ui('compare-hourly-chart'), e_ui('compare-funnel-chart'), e_ui('compare-lang-chart'), e_ui('compare-radar-chart'), no_data_table

    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=[date_col])
    if df.empty:
        return [], e_ui('compare-volume-chart'), e_ui('compare-hourly-chart'), e_ui('compare-funnel-chart'), e_ui('compare-lang-chart'), e_ui('compare-radar-chart'), no_data_table

    df['Date_Str'] = df[date_col].dt.strftime('%Y-%m-%d')
    df['Day_Name'] = df[date_col].dt.day_name()
    
    # Resolve dates
    dates_to_include = set(selected_dates or [])
    if selected_days:
        resolved_dates = df[df['Day_Name'].isin(selected_days)]['Date_Str'].unique()
        dates_to_include.update(resolved_dates)
        
    if not dates_to_include:
        return [], e_ui('compare-volume-chart'), e_ui('compare-hourly-chart'), e_ui('compare-funnel-chart'), e_ui('compare-lang-chart'), e_ui('compare-radar-chart'), html.P("No matching dates found.")
        
    df = df[df['Date_Str'].isin(dates_to_include)]
    
    if df.empty:
        return [], e_ui('compare-volume-chart'), e_ui('compare-hourly-chart'), e_ui('compare-funnel-chart'), e_ui('compare-lang-chart'), e_ui('compare-radar-chart'), html.P("No data available for selected dates.")
        
    has_company = 'Company' in df.columns
    has_lang = 'Language' in df.columns
    
    # --- CALCULATE KPIS & TABLE DATA ---
    grouped = df.groupby('Date_Str').sum(numeric_only=True).reset_index()
    grouped = grouped.sort_values(by='Date_Str')
    
    if 'Call Offered' in grouped.columns:
        grouped['Volume'] = grouped['Call Offered']
    else:
        vol_counts = df.groupby('Date_Str').size().reset_index(name='Volume')
        grouped = pd.merge(grouped, vol_counts, on='Date_Str')
        
    if all(c in grouped.columns for c in ['ACD Calls in 20 Sec', 'Call Offered', 'ABAN Calls in 10 Sec']):
        denom = grouped['Call Offered'] - grouped['ABAN Calls in 10 Sec']
        grouped['SL%'] = np.where(denom == 0, 0, (grouped['ACD Calls in 20 Sec'] / denom * 100))
    else:
        grouped['SL%'] = 0
        
    if all(c in grouped.columns for c in ['ACD Time', 'ACW Time', 'Hold Time', 'ACD Calls']):
        den = grouped['ACD Calls']
        grouped['Talk Time'] = np.where(den == 0, 0, grouped['ACD Time'] / den)
        grouped['Hold Time Avg'] = np.where(den == 0, 0, grouped['Hold Time'] / den)
        grouped['AHT'] = np.where(den == 0, 0, (grouped['ACD Time'] + grouped['ACW Time'] + grouped['Hold Time']) / den)
    else:
        grouped['Talk Time'] = 0
        grouped['Hold Time Avg'] = 0
        grouped['AHT'] = 0
        
    if 'ABAN Calls' in grouped.columns and 'Call Offered' in grouped.columns:
        grouped['Abandon Rate %'] = np.where(grouped['Call Offered'] == 0, 0, (grouped['ABAN Calls'] / grouped['Call Offered'] * 100))
    else:
        grouped['Abandon Rate %'] = 0

    # --- KPI CARDS (Delta Logic) ---
    if len(grouped) == 2:
        row1 = grouped.iloc[0]
        row2 = grouped.iloc[1]
        
        def format_delta(v1, v2, is_percentage_metric, is_lower_better=False):
            if v1 == 0:
                return f"{v2:,.1f}", "Neutral"
            if is_percentage_metric:
                diff = v2 - v1 
                sign = "+" if diff > 0 else ""
                val_str = f"{v2:.1f}% ({sign}{diff:.1f}%)"
            else:
                pct_change = ((v2 - v1) / v1) * 100
                sign = "+" if pct_change > 0 else ""
                val_str = f"{int(v2):,} ({sign}{pct_change:.1f}%)"
            
            if v2 > v1:
                status = "Penalty" if is_lower_better else "Good"
            elif v2 < v1:
                status = "Good" if is_lower_better else "Penalty"
            else:
                status = "Neutral"
                
            return val_str, status
            
        vol_str, vol_stat = format_delta(row1['Volume'], row2['Volume'], False, False)
        sl_str, sl_stat = format_delta(row1['SL%'], row2['SL%'], True, False)
        aht_str, aht_stat = format_delta(row1['AHT'], row2['AHT'], False, True)
        aban_str, aban_stat = format_delta(row1['Abandon Rate %'], row2['Abandon Rate %'], True, True)
        
        subtitle = f"{row2['Date_Str']} vs {row1['Date_Str']}"
        kpis = [
            Col(make_kpi_card(f"Volume ({subtitle})", vol_str, vol_stat), className="col-12 col-md-6 col-lg-3 mb-3 mb-lg-0"),
            Col(make_kpi_card(f"SL% ({subtitle})", sl_str, sl_stat), className="col-12 col-md-6 col-lg-3 mb-3 mb-lg-0"),
            Col(make_kpi_card(f"AHT ({subtitle})", aht_str, aht_stat), className="col-12 col-md-6 col-lg-3 mb-3 mb-lg-0"),
            Col(make_kpi_card(f"Aban % ({subtitle})", aban_str, aban_stat), className="col-12 col-md-6 col-lg-3"),
        ]
    else:
        total_vol = grouped['Volume'].sum()
        avg_sl = grouped['SL%'].mean() if not grouped.empty else 0
        avg_aht = grouped['AHT'].mean() if not grouped.empty else 0
        avg_aban = grouped['Abandon Rate %'].mean() if not grouped.empty else 0
        
        sl_status = "Good" if avg_sl > 85 else "Penalty"
        aht_status = "Good" if avg_aht <= 240 else "Penalty"
        
        kpis = [
            Col(make_kpi_card("Total Volume (Selected)", f"{int(total_vol):,}"), className="col-12 col-md-6 col-lg-3 mb-3 mb-lg-0"),
            Col(make_kpi_card("Avg Service Level", f"{avg_sl:.1f}%", sl_status), className="col-12 col-md-6 col-lg-3 mb-3 mb-lg-0"),
            Col(make_kpi_card("Avg AHT", f"{avg_aht:.0f}s", aht_status), className="col-12 col-md-6 col-lg-3 mb-3 mb-lg-0"),
            Col(make_kpi_card("Avg Abandon Rate", f"{avg_aban:.1f}%", "Neutral"), className="col-12 col-md-6 col-lg-3"),
        ]

    # --- 1. Company Performance (Dual-Axis Combo Chart) ---
    if has_company and all(c in df.columns for c in ['ACD Calls in 20 Sec', 'Call Offered', 'ABAN Calls in 10 Sec']):
        vol_comp_grouped = df.groupby(['Date_Str', 'Company']).sum(numeric_only=True).reset_index()
        vol_comp_grouped = vol_comp_grouped.sort_values(by=['Date_Str', 'Company'])
        
        if 'Call Offered' in vol_comp_grouped.columns:
            vol_comp_grouped['Volume'] = vol_comp_grouped['Call Offered']
        else:
            vc = df.groupby(['Date_Str', 'Company']).size().reset_index(name='Volume')
            vol_comp_grouped = pd.merge(vol_comp_grouped, vc, on=['Date_Str', 'Company'])
            
        comp_denom = vol_comp_grouped['Call Offered'] - vol_comp_grouped['ABAN Calls in 10 Sec']
        vol_comp_grouped['SL%'] = np.where(comp_denom == 0, 0, (vol_comp_grouped['ACD Calls in 20 Sec'] / comp_denom * 100))
        
        fig_vol = go.Figure()
        
        # Colors for companies
        colors = ['#3182ce', '#38a169', '#dd6b20', '#805ad5']
        
        companies_list = vol_comp_grouped['Company'].unique()
        for i, comp in enumerate(companies_list):
            comp_data = vol_comp_grouped[vol_comp_grouped['Company'] == comp]
            c = colors[i % len(colors)]
            
            # Bar for Volume
            fig_vol.add_trace(go.Bar(
                x=comp_data['Date_Str'], y=comp_data['Volume'],
                name=f"{comp} Volume", marker_color=c, opacity=0.7, yaxis='y'
            ))
            
            # Smooth Line for SL
            fig_vol.add_trace(go.Scatter(
                x=comp_data['Date_Str'], y=comp_data['SL%'],
                name=f"{comp} SL%", mode='lines+markers', 
                line=dict(color=c, width=3, shape='spline', smoothing=1.3), yaxis='y2'
            ))
            
        fig_vol.update_layout(
            barmode='group', template=template, margin=dict(t=30, b=30, l=10, r=10),
            xaxis=dict(title='Date', type='category'),
            yaxis=dict(title='Call Volume', side='left', showgrid=False),
            yaxis2=dict(title='Service Level %', side='right', overlaying='y', range=[0, 105], showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        ui_vol = dcc.Graph(id='compare-volume-chart', figure=fig_vol, config={'displayModeBar': False})
    else:
        ui_vol = e_ui('compare-volume-chart')

    # --- 2. Hourly Volume Trends (Multi-Line Chart) ---
    if 'Call Timestamp' in df.columns:
        df['Hour'] = pd.to_datetime(df['Call Timestamp']).dt.hour
        heat_grp = df.groupby(['Date_Str', 'Hour']).size().reset_index(name='Volume')
        
        fig_heat = px.line(
            heat_grp, x='Hour', y='Volume', color='Date_Str',
            markers=True, template=template, render_mode='svg'
        )
        # Apply spline smoothing to all traces
        fig_heat.update_traces(line_shape='spline')
        fig_heat.update_layout(xaxis_title="Hour of Day", yaxis_title="Call Volume", legend_title="Date", margin=dict(l=20, r=20, t=20, b=20), xaxis=dict(tickmode='linear', tick0=0, dtick=1))
        ui_heat = dcc.Graph(id='compare-hourly-chart', figure=fig_heat, config={'displayModeBar': False})
    else:
        ui_heat = e_ui('compare-hourly-chart')

    # --- 3. Abandonment Flow (Grouped Bar Chart) ---
    if all(c in grouped.columns for c in ['Call Offered', 'ACD Calls in 20 Sec', 'ABAN Calls']):
        # Prepare data for grouped bar chart
        melted_flow = grouped.melt(
            id_vars=['Date_Str'], 
            value_vars=['Call Offered', 'ACD Calls in 20 Sec', 'ABAN Calls'],
            var_name='Stage', value_name='Calls'
        )
        
        # Rename stages for UI
        stage_map = {
            'Call Offered': '1. Offered',
            'ACD Calls in 20 Sec': '2. Answered (20s)',
            'ABAN Calls': '3. Abandoned'
        }
        melted_flow['Stage'] = melted_flow['Stage'].map(stage_map)
        melted_flow = melted_flow.sort_values(by=['Stage', 'Date_Str'])
        
        fig_funnel = px.area(
            melted_flow, x='Stage', y='Calls', color='Date_Str',
            template=template, line_shape='spline'
        )
        fig_funnel.update_traces(mode='lines+markers', marker=dict(size=8), fill='tozeroy', opacity=0.6)
        fig_funnel.update_layout(xaxis_title="Call Flow Stage", yaxis_title="Number of Calls", legend_title="Date", margin=dict(l=20, r=20, t=20, b=20))
        ui_funnel = dcc.Graph(id='compare-funnel-chart', figure=fig_funnel, config={'displayModeBar': False}, style={'height': '450px'})
    else:
        ui_funnel = e_ui('compare-funnel-chart')
        
    # --- 4. Language breakdown (Pie Chart) ---
    if has_lang:
        lang_grp = df.groupby('Language').size().reset_index(name='Volume')
        fig_lang = px.pie(lang_grp, values='Volume', names='Language', hole=0.4, template=template)
        fig_lang.update_traces(textinfo='percent+label', textposition='inside', hoverinfo='label+percent+value')
        fig_lang.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        ui_lang = dcc.Graph(id='compare-lang-chart', figure=fig_lang, config={'displayModeBar': False}, style={'height': '450px'})
    else:
        ui_lang = e_ui('compare-lang-chart')

    # --- 5. Vendor Radar Chart (Averaged Footprint) ---
    if has_company and all(c in df.columns for c in ['Call Offered', 'ACD Calls in 20 Sec', 'ABAN Calls in 10 Sec', 'ACD Time', 'ACW Time', 'Hold Time', 'ACD Calls']):
        # Group by Company ONLY (averaging across dates effectively by summing first)
        comp_radar_grp = df.groupby('Company').sum(numeric_only=True).reset_index()
        
        rad_denom = comp_radar_grp['Call Offered'] - comp_radar_grp['ABAN Calls in 10 Sec']
        comp_radar_grp['SL%'] = np.where(rad_denom == 0, 0, (comp_radar_grp['ACD Calls in 20 Sec'] / rad_denom * 100))
        
        acd_den = comp_radar_grp['ACD Calls']
        comp_radar_grp['AHT'] = np.where(acd_den == 0, 0, (comp_radar_grp['ACD Time'] + comp_radar_grp['ACW Time'] + comp_radar_grp['Hold Time']) / acd_den)
        
        comp_radar_grp['Talk Time'] = np.where(acd_den == 0, 0, comp_radar_grp['ACD Time'] / acd_den)
        comp_radar_grp['Wrap Time'] = np.where(acd_den == 0, 0, comp_radar_grp['ACW Time'] / acd_den)
        comp_radar_grp['Hold Time'] = np.where(acd_den == 0, 0, comp_radar_grp['Hold Time'] / acd_den)
        
        comp_radar_grp['Abandon%'] = np.where(comp_radar_grp['Call Offered'] == 0, 0, (comp_radar_grp['ABAN Calls'] / comp_radar_grp['Call Offered'] * 100))
        
        # Normalize metrics to 0-100 scale for radar so they fit beautifully
        max_vol = comp_radar_grp['Call Offered'].max() if comp_radar_grp['Call Offered'].max() > 0 else 1
        max_aht = comp_radar_grp['AHT'].max() if comp_radar_grp['AHT'].max() > 0 else 1
        max_talk = comp_radar_grp['Talk Time'].max() if comp_radar_grp['Talk Time'].max() > 0 else 1
        max_wrap = comp_radar_grp['Wrap Time'].max() if comp_radar_grp['Wrap Time'].max() > 0 else 1
        max_hold = comp_radar_grp['Hold Time'].max() if comp_radar_grp['Hold Time'].max() > 0 else 1
        max_aban = comp_radar_grp['Abandon%'].max() if comp_radar_grp['Abandon%'].max() > 0 else 1
        
        fig_radar = go.Figure()
        categories = ['Volume', 'Service Level %', 'AHT', 'Talk Time', 'Wrap Time', 'Hold Time', 'Abandon %']
        
        for idx, row in comp_radar_grp.iterrows():
            r_vals = [
                (row['Call Offered'] / max_vol) * 100,
                row['SL%'],
                (row['AHT'] / max_aht) * 100,
                (row['Talk Time'] / max_talk) * 100,
                (row['Wrap Time'] / max_wrap) * 100,
                (row['Hold Time'] / max_hold) * 100,
                (row['Abandon%'] / max_aban) * 100
            ]
            r_vals.append(r_vals[0]) # Close the loop
            cat_closed = categories + [categories[0]]
            
            fig_radar.add_trace(go.Scatterpolar(
                r=r_vals,
                theta=cat_closed,
                fill='toself',
                name=row['Company'],
                opacity=0.6
            ))
            
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], showticklabels=False),
            ),
            showlegend=True, template=template, margin=dict(l=80, r=80, t=40, b=40)
        )
        ui_radar = dcc.Graph(id='compare-radar-chart', figure=fig_radar, config={'displayModeBar': False}, style={'height': '450px'})
    else:
        ui_radar = e_ui('compare-radar-chart')

    # --- 6. Data Table ---
    # Round numerical columns for display
    table_df = grouped[['Date_Str', 'Volume', 'SL%', 'AHT', 'Talk Time', 'Hold Time Avg', 'Abandon Rate %']].copy()
    table_df = table_df.round(2)
    
    data_table = dag.AgGrid(
        id="comparison-grid",
        rowData=table_df.to_dict("records"),
        columnDefs=[{"field": i} for i in table_df.columns],
        defaultColDef={"sortable": True, "filter": True, "resizable": True},
        className="ag-theme-alpine",
        style={"height": 300, "width": "100%"},
    )
        
    return kpis, ui_vol, ui_heat, ui_funnel, ui_lang, ui_radar, data_table

# CSV Export Callback
@callback(
    Output({'type': 'download-data-compare', 'index': dash.MATCH}, "data"),
    Input({'type': 'export-csv-compare', 'index': dash.MATCH}, "n_clicks"),
    State('data-store', 'data'),
    State('discrete-date-selector', 'value'),
    State('day-of-week-selector', 'value'),
    State('auth-state', 'data'),
    prevent_initial_call=True
)
def export_csv_compare(n_clicks, data_ref, selected_dates, selected_days, auth_state):
    from dash import ctx
    if not n_clicks or not data_ref or not isinstance(data_ref, dict) or 'filename' not in data_ref or (not selected_dates and not selected_days):
        return dash.no_update
        
    triggered_id = ctx.triggered_id
    if triggered_id['index'] != 'compare':
        return dash.no_update
        
    token = auth_state.get('token') if auth_state else None
    if not token: return dash.no_update
    
    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
    if df.empty: return dash.no_update
    
    date_col = 'Date' if 'Date' in df.columns else 'Timestamp' if 'Timestamp' in df.columns else 'Call Start Time' if 'Call Start Time' in df.columns else None
    if date_col:
        df['Date'] = pd.to_datetime(df[date_col])
        df['DayOfWeek'] = df['Date'].dt.day_name()
        
        # Apply filters
        if selected_dates and selected_days:
            df = df[df['Date'].dt.strftime('%Y-%m-%d').isin(selected_dates) | df['DayOfWeek'].isin(selected_days)]
        elif selected_dates:
            df = df[df['Date'].dt.strftime('%Y-%m-%d').isin(selected_dates)]
        elif selected_days:
            df = df[df['DayOfWeek'].isin(selected_days)]
            
        if 'DayOfWeek' in df.columns:
            df = df.drop(columns=['DayOfWeek'])

    if 'Date' in df.columns:
        df = df.drop(columns=['Date'])

    return dcc.send_data_frame(df.to_csv, "comparison_data.csv", index=False)

# Backend PDF and JPG Export Callbacks
from dash import ctx
from frontend.shared.pdf_generator import generate_single_chart_pdf, generate_dashboard_pdf, generate_single_chart_png, generate_single_chart_html, generate_dashboard_html

@callback(
    Output({'type': 'download-data-compare', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-pdf-compare', 'index': dash.MATCH}, "n_clicks"),
    State('compare-volume-chart', 'figure'),
    State('compare-hourly-chart', 'figure'),
    State('compare-funnel-chart', 'figure'),
    State('compare-lang-chart', 'figure'),
    State('compare-radar-chart', 'figure'),
    prevent_initial_call=True
)
def export_pdf_compare(n_clicks, vol, hourly, funnel, lang, radar):
    if not n_clicks: return dash.no_update
    
    triggered_id = ctx.triggered_id
    index = triggered_id['index']
    
    figures = {
        'compare-volume-chart': vol,
        'compare-hourly-chart': hourly,
        'compare-funnel-chart': funnel,
        'compare-lang-chart': lang,
        'compare-radar-chart': radar
    }
    
    if index == 'compare':
        pdf_bytes = generate_dashboard_pdf(figures, "Date Comparison")
        return dcc.send_bytes(pdf_bytes, "compare_export.pdf")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        pdf_bytes = generate_single_chart_pdf(fig_dict)
        return dcc.send_bytes(pdf_bytes, f"{index}_export.pdf")


@callback(
    Output({'type': 'download-data-compare', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-png-compare', 'index': dash.MATCH}, "n_clicks"),
    State('compare-volume-chart', 'figure'),
    State('compare-hourly-chart', 'figure'),
    State('compare-funnel-chart', 'figure'),
    State('compare-lang-chart', 'figure'),
    State('compare-radar-chart', 'figure'),
    prevent_initial_call=True
)
def export_png_compare(n_clicks, vol, hourly, funnel, lang, radar):
    if not n_clicks: return dash.no_update
    
    triggered_id = ctx.triggered_id
    index = triggered_id['index']
    
    figures = {
        'compare-volume-chart': vol,
        'compare-hourly-chart': hourly,
        'compare-funnel-chart': funnel,
        'compare-lang-chart': lang,
        'compare-radar-chart': radar
    }
    
    if index == 'compare':
        pdf_bytes = generate_dashboard_pdf(figures, "Date Comparison")
        return dcc.send_bytes(pdf_bytes, "compare_export.pdf")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        png_bytes = generate_single_chart_png(fig_dict)
        return dcc.send_bytes(png_bytes, f"{index}_export.png")

@callback(
    Output({'type': 'download-data-compare', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-html-compare', 'index': dash.MATCH}, "n_clicks"),
    State('compare-volume-chart', 'figure'),
    State('compare-hourly-chart', 'figure'),
    State('compare-funnel-chart', 'figure'),
    State('compare-lang-chart', 'figure'),
    State('compare-radar-chart', 'figure'),
    prevent_initial_call=True
)
def export_html_compare(n_clicks, vol, hourly, funnel, lang, radar):
    if not n_clicks: return dash.no_update
    
    triggered_id = ctx.triggered_id
    index = triggered_id['index']
    
    figures = {
        'compare-volume-chart': vol,
        'compare-hourly-chart': hourly,
        'compare-funnel-chart': funnel,
        'compare-lang-chart': lang,
        'compare-radar-chart': radar
    }
    
    if index == 'compare':
        html_str = generate_dashboard_html(figures, "Date Comparison")
        return dcc.send_string(html_str, "compare_export.html")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        html_str = generate_single_chart_html(fig_dict)
        return dcc.send_string(html_str, f"{index}_export.html")
