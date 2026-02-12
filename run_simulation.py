import sys
import json
import base64
import io
import os
from io import StringIO

# Parse command-line arguments for simulation parameters
t_final_arg = None
n_points_arg = None
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

# Add current directory to path to import ev_tc_7
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

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
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
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
    
    # Import and run the simulation (using ev_tc_7 with configurable parameters)
    from ev_tc_7 import run_simulation
    
    # Run the simulation with provided parameters and save animation
    run_simulation(save_animation_path=animation_gif_path, t_final=t_final_arg, n_points=n_points_arg)
    
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
        'animation': animation_base64  # Animated GIF as base64
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
