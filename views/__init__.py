# Sentinel-Edu 视图模块
from views.helpers import (
    highlight_toxic, context_snippet, strategy_to_color,
    safe_json_loads, to_native, check_api_connection, run_concurrently
)
from views.tab1_build import render_tab1
from views.tab2_detect import render_tab2
from views.tab3_analysis import render_tab3
