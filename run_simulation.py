import sys
import json
import base64
import io
import os
from io import StringIO

# Parse command-line arguments for simulation parameters
# Usage: python run_simulation.py [duration] [points] [simulation_type]
# simulation_type: 'tc7' (default, 4-node 2-station) or 'tc9' (9-node 4-station)
t_final_arg = None
n_points_arg = None
sim_type_arg = 'tc7'  # default

if len(sys.argv) > 1:
    try:
        t_final_arg = float(sys.argv[1])
    except (ValueError, IndexError):
        pass
if len(sys.argv) > 2:
    try:
        n_points_arg = int(sys.argv[2])
    except (ValueError, IndexError):
        pass
if len(sys.argv) > 3:
    sim_type_arg = sys.argv[3].lower().strip()

# Add current directory to path to import ev_tc_7
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup matplotlib for better graph quality
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Set style for brighter, cleaner graphs
plt.rcParams.update({
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'axes.edgecolor': '#333333',
    'axes.labelcolor': '#333333',
    'axes.titleweight': 'bold',
    'axes.grid': True,
    'grid.alpha': 0.3,
    'grid.color': '#cccccc',
    'xtick.color': '#333333',
    'ytick.color': '#333333',
    'text.color': '#333333',
    'font.size': 11,
    'axes.titlesize': 13,
    'axes.labelsize': 11,
    'legend.framealpha': 0.9,
    'legend.fontsize': 10,
    'lines.linewidth': 2.5,
})

# Capture all plots as base64 encoded images
captured_figures = []
figure_counter = 0
animation_gif_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'network_animation.gif')

def save_current_figure():
    """Save current matplotlib figure as base64 encoded PNG."""
    global figure_counter
    try:
        # Get current figure
        fig = plt.gcf()
        
        # Skip if no figure is active
        if fig.get_axes():
            # Set larger figure size for better web display
            fig.set_size_inches(20, 14)
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight', dpi=120, facecolor='white')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            captured_figures.append(image_base64)
            figure_counter += 1
            print(f"[Capture] Figure {figure_counter} saved ({len(image_base64)//1024}KB)", file=sys.stderr)
        
        plt.close('all')
    except Exception as e:
        print(f"[Error] Failed to save figure: {e}", file=sys.stderr)

# Monkey patch plt.show to capture figures instead
original_show = plt.show
plt.show = save_current_figure

try:
    # Suppress print output from the simulation
    # Redirect stdout to capture it but don't display it
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = StringIO()
    sys.stderr = StringIO()
    
    # Import and run the simulation based on type parameter
    if sim_type_arg == 'tc9':
        from ev_tc_9_web import run_simulation, create_network, enumerate_paths, create_od_demand
        from ev_tc_9_web import get_station_parameters as get_params
    else:
        from ev_tc_7 import run_simulation, create_network_with_charging_stations, enumerate_paths, create_od_demand
        from ev_tc_7 import get_station_parameters as get_params
    
    # Run the simulation with provided parameters and save animation, get network data
    network_data = run_simulation(save_animation_path=animation_gif_path, t_final=t_final_arg, n_points=n_points_arg, return_data=True)
    
    # Restore stdout/stderr
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    
    # Read animation GIF as base64 if it exists
    animation_base64 = None
    if os.path.exists(animation_gif_path):
        with open(animation_gif_path, 'rb') as f:
            animation_base64 = base64.b64encode(f.read()).decode('utf-8')
        print(f"Animation GIF loaded ({len(animation_base64)//1024}KB)", file=sys.stderr)
    
    # Output only the JSON result
    if len(captured_figures) == 0:
        print("Warning: No figures captured", file=sys.stderr)
    
    output = {
        'success': True,
        'message': f'Simulation completed successfully. Captured {len(captured_figures)} graphs.',
        'graphs': captured_figures,
        'animation': animation_base64,  # Animated GIF as base64
        'networkData': network_data  # Interactive network data
    }
    print(json.dumps(output))
    
except ImportError as e:
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    output = {
        'success': False,
        'message': f'Import Error: {str(e)}',
        'graphs': captured_figures
    }
    print(json.dumps(output))
    sys.exit(1)
    
except Exception as e:
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    output = {
        'success': False,
        'message': f'Error: {str(e)}',
        'graphs': captured_figures
    }
    print(json.dumps(output))
    sys.exit(1)
