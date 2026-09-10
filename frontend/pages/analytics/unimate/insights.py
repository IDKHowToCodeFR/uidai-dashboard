import dash
from dash import html, dcc, callback, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from frontend.shared.api_client import get_dataframe
from frontend.shared.theme import get_plotly_template, make_export_dropdown, should_use_log, COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_NEUTRAL, COLOR_INFO
from frontend.components.cards import wrap_chart_card, make_kpi_card
from frontend.components.empty_state import render_empty_state
from frontend.shared.pdf_generator import generate_single_chart_pdf, generate_dashboard_pdf, generate_single_chart_png, generate_single_chart_html, generate_dashboard_html

dash.register_page(__name__, path='/unimate/insights', name='UniMate Insights')

layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H3("Operational Insights", className="display-xl mb-0"),
                html.P("Deep dive into UniMate call resolution, non-transferred calls, and system errors.", className="text-muted mb-0 mt-2"),
            ])
        ], width=8),
        dbc.Col([
            html.Div([
                make_export_dropdown("unimate-insights"),
                dcc.Download(id={'type': 'download-data-unimate-insights', 'index': 'unimate-insights'})
            ])
        ], width=4, className="d-flex align-items-center justify-content-end mb-4")
    ]),

    dcc.Loading(type="dot", color=COLOR_PRIMARY, children=dbc.Row(id='unimate-insights-kpi', className="mb-4 g-3")),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('unimate-resolution', "Resolution Rate Trend (%)", "unimate-insights")
        ], width=12, className="mb-4")
    ]),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('unimate-auth-funnel', "Authentication Funnel", "unimate-insights")
        ], width=12, lg=5, className="mb-4"),
        dbc.Col([
            wrap_chart_card('unimate-auth-mech', "Authentication Mechanism Breakdown", "unimate-insights")
        ], width=12, lg=7, className="mb-4")
    ]),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('unimate-term-reason', "Termination Type vs Reason", "unimate-insights")
        ], width=12, className="mb-4")
    ]),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('unimate-lang-heatmap', "Language vs Half-Hourly Volume", "unimate-insights")
        ], width=12, className="mb-4")
    ]),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('unimate-error-heatmap', "System & Error Outage Heatmap", "unimate-insights")
        ], width=12, className="mb-4")
    ])
], className="container-fluid py-4")

@callback(
    Output('unimate-insights-kpi', 'children'),
    Output('unimate-resolution-container', 'children'),
    Output('unimate-auth-funnel-container', 'children'),
    Output('unimate-auth-mech-container', 'children'),
    Output('unimate-error-heatmap-container', 'children'),
    Output('unimate-lang-heatmap-container', 'children'),
    Output('unimate-term-reason-container', 'children'),
    Input('data-store', 'data'),
    Input('company-filter', 'value'),
    Input('language-filter', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date'),
    Input('sl-granularity', 'value'),
    Input('sl-scale-toggle', 'value'),
    State('auth-state', 'data')
)
def update_insights(data_ref, companies, languages, start_date, end_date, sl_granularity, sl_scale, auth_state):
    def e_ui(gid=None):
        return render_empty_state(graph_id=gid)

    empty_kpi = dbc.Col(html.Div(e_ui(), style={"height": "120px"}), width=12)
    outs = [empty_kpi] + [e_ui(gid) for gid in ['unimate-resolution', 'unimate-auth-funnel', 'unimate-auth-mech', 'unimate-error-heatmap', 'unimate-lang-heatmap', 'unimate-term-reason']]

    if not data_ref or 'filename' not in data_ref: return outs
    token = auth_state.get('token') if auth_state else None
    if not token: return outs
    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
    if df is None or df.empty: return outs

    if 'Call Start Time' in df.columns:
        df['Date'] = pd.to_datetime(df['Call Start Time'], errors='coerce')
    else:
        df['Date'] = pd.NaT

    mask = pd.Series(True, index=df.index)
    if companies and 'Company' in df.columns:
        mask = mask & df['Company'].isin(companies)
    if languages and 'Language' in df.columns:
        mask = mask & df['Language'].isin(languages)

    if start_date and not end_date: end_date = start_date
    if start_date and end_date and not df['Date'].isna().all():
        s = pd.to_datetime(start_date)
        e = pd.to_datetime(end_date) + pd.Timedelta(days=1)
        mask = mask & (df['Date'] >= s) & (df['Date'] < e)
        df = df[mask].copy()
    if df.empty: return outs
    
    date_col = 'Date' if not df['Date'].isna().all() else None
    total_calls = len(df)

    # KPI: Resolution Rate
    kpis = []
    if 'Termination Type' in df.columns:
        resolved = df[~df['Termination Type'].astype(str).str.lower().isin(['transfer', 'transferred'])].shape[0]
        if total_calls > 0:
            resolution_rate = resolved / total_calls * 100
            kpis.append(dbc.Col(make_kpi_card("Overall Resolution Rate", f"{resolution_rate:.1f}%", "good" if resolution_rate > 60 else "neutral", sla_text="Target > 60%"), width=True))
        else:
            kpis.append(dbc.Col(make_kpi_card("Overall Resolution Rate", "0.0%", "neutral", sla_text="Target > 60%"), width=True))
    else:
        kpis.append(dbc.Col(make_kpi_card("Overall Resolution Rate", "N/A", "neutral", sla_text="Target > 60%"), width=True))

    # Time Bucketing
    if date_col:
        if sl_granularity and sl_granularity != 'Auto':
            freq = sl_granularity
        else:
            days_diff = (df['Date'].max() - df['Date'].min()).days
            freq = 'M' if days_diff > 90 else ('W-MON' if days_diff > 31 else 'D')
            
        if freq == 'D':
            df['Date_Bucket'] = df['Date'].dt.floor('D')
        else:
            df['Date_Bucket'] = df['Date'].dt.to_period(freq).dt.to_timestamp()
    else:
        df['Date_Bucket'] = pd.NaT

    # 1. Resolution Rate Trend
    if date_col and 'Termination Type' in df.columns:
        res_grp = df.groupby('Date_Bucket').agg(
            Volume=('Termination Type', 'size'),
            Resolved=('Termination Type', lambda x: (~x.astype(str).str.lower().isin(['transfer', 'transferred'])).sum())
        ).reset_index()
        res_grp['Resolution Rate'] = np.where(res_grp['Volume'] == 0, 0, (res_grp['Resolved'] / res_grp['Volume']) * 100)
        
        fig_res = go.Figure()
        fig_res.add_trace(go.Scatter(
            x=res_grp['Date_Bucket'], y=res_grp['Resolution Rate'], name="Resolution %", 
            mode='lines+markers', 
            line=dict(color=COLOR_PRIMARY, width=3, shape='spline'),
            marker=dict(size=6, line=dict(width=1, color='white')),
            fill='tozeroy', 
            fillcolor=f'rgba(37, 99, 235, 0.1)',
            hovertemplate='<b>Date:</b> %{x}<br><b>Resolution Rate:</b> %{y:.2f}%<br><b>Resolved Calls:</b> %{customdata:,}<extra></extra>',
            customdata=res_grp['Resolved']
        ))
        fig_res.update_layout(template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10), showlegend=False, yaxis_title="% Resolved")
        if sl_scale and 1 in sl_scale:
            fig_res.update_yaxes(range=[max(0, min(res_grp['Resolution Rate'].min() - 2, 80)), min(100, res_grp['Resolution Rate'].max() + 2)])
        else:
            fig_res.update_yaxes(range=[0, 100])
        res_ui = dcc.Graph(id='unimate-resolution', figure=fig_res, config={'displayModeBar': False})
    else:
        res_ui = e_ui('unimate-resolution')

    # 1.5 Auth Funnel
    if 'Authentication' in df.columns:
        total_calls = len(df)
        auths = df['Authentication'].astype(str).str.lower().isin(['true', '1', '1.0']).sum()
        
        funnel_data = dict(
            Stage=["Total Calls", "Authenticated"],
            Count=[total_calls, auths]
        )
        fig_funnel = px.funnel(funnel_data, x='Count', y='Stage', color_discrete_sequence=[COLOR_PRIMARY])
        fig_funnel.update_layout(template=get_plotly_template(), margin=dict(t=10, b=10, l=10, r=10))
        ui_funnel = dcc.Graph(id='unimate-auth-funnel', figure=fig_funnel, config={'displayModeBar': False})
    else:
        ui_funnel = e_ui('unimate-auth-funnel')

    # 2. Auth Mechanism Stacked Bar
    if 'Authentication Mechanism' in df.columns:
        auth_df = df[df['Authentication Mechanism'].notna() & (df['Authentication Mechanism'].astype(str).str.strip() != '')].copy()
        if not auth_df.empty:
            mech_df = auth_df['Authentication Mechanism'].value_counts().reset_index()
            mech_df.columns = ['Mechanism', 'Count']
            
            min_val = mech_df['Count'].min()
            max_val = mech_df['Count'].max()
            use_log = should_use_log(min_val, max_val)
            
            fig_mech = px.bar(mech_df, x='Mechanism', y='Count', color='Mechanism', color_discrete_sequence=px.colors.qualitative.Pastel, log_y=use_log)
            fig_mech.update_traces(
                hovertemplate='<b>%{x}</b><br>Count: %{y:,}<extra></extra>', 
                marker_line_width=0, 
            )
            fig_mech.update_layout(template=get_plotly_template(), margin=dict(t=10, b=30, l=10, r=10), showlegend=False, bargap=0.15)
            if not mech_df.empty and 'Count' in mech_df.columns and not use_log:
                if max_val > min_val:
                    fig_mech.update_yaxes(range=[0, max_val * 1.1])
            mech_ui = dcc.Graph(id='unimate-auth-mech', figure=fig_mech, config={'displayModeBar': False})
        else:
            mech_ui = e_ui('unimate-auth-mech')
    else:
        mech_ui = e_ui('unimate-auth-mech')

    # 3. Error Outage Heatmap
    if date_col and 'Termination Reason' in df.columns:
        err_df = df[df['Termination Reason'].astype(str).str.lower().isin(['system', 'error'])].copy()
        if not err_df.empty:
            err_df['DayOfWeek'] = err_df['Date'].dt.day_name()
            err_df['Hour'] = err_df['Date'].dt.hour
            
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            heat_grp = err_df.groupby(['DayOfWeek', 'Hour']).size().reset_index(name='Errors')
            
            heat_pivot = heat_grp.pivot(index='DayOfWeek', columns='Hour', values='Errors').reindex(days_order).fillna(0)
            for h in range(24):
                if h not in heat_pivot.columns:
                    heat_pivot[h] = 0
            heat_pivot = heat_pivot[range(24)]
            
            fig_heat = px.imshow(
                heat_pivot, 
                labels=dict(x="Hour of Day", y="Day of Week", color="Error Count"),
                x=[f"{h:02d}:00" for h in range(24)],
                y=days_order,
                color_continuous_scale="rdbu_r",
                aspect="auto",
                text_auto=True
            )
            fig_heat.update_traces(
                hovertemplate='<b>%{y}, %{x}</b><br>Errors: %{z}<extra></extra>',
                xgap=2, 
                ygap=2
            )
            fig_heat.update_layout(
                template=get_plotly_template(), 
                margin=dict(t=20, b=20, l=10, r=10), 
                coloraxis_showscale=True,
                plot_bgcolor='rgba(0,0,0,0)',
            )
            error_ui = dcc.Graph(id='unimate-error-heatmap', figure=fig_heat, config={'displayModeBar': False})
        else:
            error_ui = e_ui('unimate-error-heatmap')
    else:
        error_ui = e_ui('unimate-error-heatmap')

    # 4. Language vs Half-Hourly Volume Heatmap
    if date_col and 'Language' in df.columns:
        df_time = df.copy()
        df_time['Time_30'] = df_time[date_col].dt.floor('30min').dt.strftime('%H:%M')
        lang_time_grp = df_time.groupby(['Language', 'Time_30']).size().reset_index(name='Volume')
        if not lang_time_grp.empty:
            pivot_df = lang_time_grp.pivot(index='Language', columns='Time_30', values='Volume').fillna(0)
            fig_lang_heat = px.imshow(
                pivot_df, text_auto=True, aspect="auto", color_continuous_scale='rdbu_r', origin='upper'
            )
            fig_lang_heat.update_layout(template=get_plotly_template(), margin=dict(t=10, b=10, l=10, r=10), xaxis_title="Time (Half-Hourly)", yaxis_title="")
            lang_heat_ui = dcc.Graph(id='unimate-lang-heatmap', figure=fig_lang_heat, config={'displayModeBar': False})
        else:
            lang_heat_ui = e_ui('unimate-lang-heatmap')
    else:
        lang_heat_ui = e_ui('unimate-lang-heatmap')

    # Termination Type vs Reason
    if 'Termination Type' in df.columns and 'Termination Reason' in df.columns:
        term_grp = df.groupby(['Termination Type', 'Termination Reason']).size().reset_index(name='Count')
        term_grp = term_grp.sort_values(by='Count', ascending=True)
        fig_term = px.bar(
            term_grp, x='Count', y='Termination Reason', color='Termination Type', orientation='h',
            template=get_plotly_template(), barmode='stack'
        )
        fig_term.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            yaxis={'title': '', 'categoryorder': 'total ascending'}
        )
        term_ui = dcc.Graph(id='unimate-term-reason', figure=fig_term, config={'displayModeBar': False}, style={'height': '400px'})
    else:
        term_ui = e_ui('unimate-term-reason')

    return kpis, res_ui, ui_funnel, mech_ui, error_ui, lang_heat_ui, term_ui

# ---------------- EXPORT CALLBACKS ----------------

@callback(
    Output({'type': 'download-data-unimate-insights', 'index': dash.MATCH}, "data"),
    Input({'type': 'export-csv-unimate-insights', 'index': dash.MATCH}, "n_clicks"),
    State('data-store', 'data'),
    State('company-filter', 'value'),
    State('language-filter', 'value'),
    State('date-picker-range', 'start_date'),
    State('date-picker-range', 'end_date'),
    State('auth-state', 'data'),
    prevent_initial_call=True
)
def export_csv_insights(n_clicks, data_ref, company_filter, language_filter, start_date, end_date, auth_state):
    if not n_clicks or not data_ref or 'filename' not in data_ref: return dash.no_update
    if ctx.triggered_id['index'] != 'unimate-insights': return dash.no_update
        
    token = auth_state.get('token') if auth_state else None
    if not token: return dash.no_update
        
    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
    if df.empty: return dash.no_update

    if company_filter and 'Company' in df.columns:
        df = df[df['Company'].isin(company_filter)]
    if language_filter and 'Language' in df.columns:
        df = df[df['Language'].isin(language_filter)]

    if 'Call Start Time' in df.columns:
        df['Date'] = pd.to_datetime(df['Call Start Time'], errors='coerce')
        if start_date and not end_date: end_date = start_date
        if start_date and end_date and not df['Date'].isna().all():
            start_dt, end_dt = pd.to_datetime(start_date), pd.to_datetime(end_date) + pd.Timedelta(days=1)
            df = df[(df['Date'] >= start_dt) & (df['Date'] < end_dt)]
        df = df.drop(columns=['Date'])

    return dcc.send_data_frame(df.to_csv, "unimate_insights_data.csv", index=False)


@callback(
    Output({'type': 'download-data-unimate-insights', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-pdf-unimate-insights', 'index': dash.MATCH}, "n_clicks"),
    State('unimate-resolution', 'figure'),
    State('unimate-auth-funnel', 'figure'),
    State('unimate-auth-mech', 'figure'),
    State('unimate-error-heatmap', 'figure'),
    State('unimate-lang-heatmap', 'figure'),
    State('unimate-term-reason', 'figure'),
    prevent_initial_call=True
)
def export_pdf_insights(n_clicks, res, funnel, mech, err, lang_heat, term_reason):
    if not n_clicks: return dash.no_update
    index = ctx.triggered_id['index']
    
    figures = {
        'unimate-resolution': res, 'unimate-auth-funnel': funnel, 'unimate-auth-mech': mech, 'unimate-error-heatmap': err, 'unimate-lang-heatmap': lang_heat, 'unimate-term-reason': term_reason
    }
    
    if index == 'unimate-insights':
        pdf_bytes = generate_dashboard_pdf(figures, "UniMate Insights")
        return dcc.send_bytes(pdf_bytes, "unimate_insights_report.pdf")
        
    return dash.no_update

@callback(
    Output({'type': 'download-data-unimate-insights', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-html-unimate-insights', 'index': dash.MATCH}, "n_clicks"),
    State('unimate-resolution', 'figure'),
    State('unimate-auth-funnel', 'figure'),
    State('unimate-auth-mech', 'figure'),
    State('unimate-error-heatmap', 'figure'),
    State('unimate-lang-heatmap', 'figure'),
    State('unimate-term-reason', 'figure'),
    prevent_initial_call=True
)
def export_html_insights(n_clicks, res, funnel, mech, err, lang_heat, term_reason):
    if not n_clicks: return dash.no_update
    index = ctx.triggered_id['index']
    
    figures = {
        'unimate-resolution': res, 'unimate-auth-funnel': funnel, 'unimate-auth-mech': mech, 'unimate-error-heatmap': err, 'unimate-lang-heatmap': lang_heat, 'unimate-term-reason': term_reason
    }
    
    if index == 'unimate-insights':
        html_bytes = generate_dashboard_html(figures, "UniMate Insights")
        return dcc.send_bytes(html_bytes, "unimate_insights_report.html")
        
    return dash.no_update
