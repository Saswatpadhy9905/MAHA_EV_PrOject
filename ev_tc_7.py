import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
import matplotlib.animation as animation
from matplotlib.patches import FancyBboxPatch
import matplotlib.patches as mpatches
import warnings
warnings.filterwarnings('ignore')

# --- REPLICATOR DYNAMICS PARAMETERS ---
eta_EV = 0.05      # Imitation rate for EV users
eta_NEV = 0.05     # Imitation rate for non-EV users
alpha = 0.3        # Weight for waiting time in EV cost 
gamma = 1.0        # Price weight conversion (monetary to time)

# --- TRAFFIC FLOW PARAMETERS ---
LINK_CAPACITY = 0.5           
LATENCY_STEEPNESS = 1.0       

# --- SIMULATION PARAMETERS ---
# Simplified for cloud deployment (faster execution)
T_FINAL = 100.0
N_TIME_POINTS = 400          
SOLVER_RTOL = 1e-4
SOLVER_ATOL = 1e-6
MAX_STEP = 5.0

# PIECEWISE PRICING STRATEGY
def get_station_parameters(t, station_id):
    if station_id == 'S1':
        if t < 100:
            return {'p_s': 0.5, 'mu_s': 1.5, 'c_s': 0.1, 'nu_s': 10.0}
        elif t < 200:
            return {'p_s': 0.5, 'mu_s': 1.5, 'c_s': 0.1, 'nu_s': 10.0}
        elif t < 300:
            return {'p_s': 0.42, 'mu_s': 2.5, 'c_s': 0.18, 'nu_s': 15.0}
        else:
            return {'p_s': 0.45, 'mu_s': 2.5, 'c_s': 0.16, 'nu_s': 15.0}
    elif station_id == 'S2':
        if t < 100:
            return {'p_s': 0.5, 'mu_s': 1.5, 'c_s': 0.1, 'nu_s': 10.0}
        elif t < 200:
            return {'p_s': 0.25, 'mu_s': 1.5, 'c_s': 0.1, 'nu_s': 10.0}
        elif t < 300:
            return {'p_s': 0.25, 'mu_s': 1.5, 'c_s': 0.14, 'nu_s': 10.0}
        else:
            return {'p_s': 0.38, 'mu_s': 2.0, 'c_s': 0.20, 'nu_s': 13.0}
    return {'p_s': 0.5, 'mu_s': 1.5, 'c_s': 0.1, 'nu_s': 10.0}


# ============================================================================
# NETWORK CONSTRUCTION
# ============================================================================
def create_network_with_charging_stations():
    G = nx.MultiDiGraph()
    physical_nodes = ['O', 'A', 'B', 'D']
    G.add_nodes_from(physical_nodes)
    
    link_id = 0
    G.add_edge('O', 'O', key=0, link_id=link_id, link_type='origin', 
               origin_id='O1', is_origin=True)
    origin_link_1 = link_id
    link_id += 1
  
    G.add_edge('O', 'A', key=0, link_id=link_id, link_type='mixed'); link_id += 1
    G.add_edge('O', 'A', key=1, link_id=link_id, link_type='EV-only', station_id='S1'); s1_link = link_id; link_id += 1
    G.add_edge('O', 'B', key=0, link_id=link_id, link_type='mixed'); link_id += 1
    G.add_edge('A', 'B', key=0, link_id=link_id, link_type='mixed'); link_id += 1
    G.add_edge('B', 'D', key=0, link_id=link_id, link_type='mixed'); link_id += 1    
    G.add_edge('A', 'D', key=0, link_id=link_id, link_type='mixed'); link_id += 1
    G.add_edge('B', 'D', key=1, link_id=link_id, link_type='EV-only', station_id='S2'); s2_link = link_id; link_id += 1
    
    G.add_edge('D', 'D', key=0, link_id=link_id, link_type='destination', dest_id='D1', is_destination=True)
    d1_link = link_id; link_id += 1
    
    origins = [origin_link_1]
    destinations = [d1_link]
    charging_stations = {'S1': s1_link, 'S2': s2_link}

    pos = {'O': (0, 3), 'B': (3, 0), 'A': (3, 6), 'D': (6, 3)}
    nx.set_node_attributes(G, pos, 'pos')
    return G, origins, destinations, charging_stations


def enumerate_paths(G, origins, destinations, charging_stations):
    edges = list(G.edges(keys=True))
    edge_to_idx = {edge: i for i, edge in enumerate(edges)}
    idx_to_edge = edges
    
    paths_EV = {}
    paths_NEV = {}
    
    link_info = {}
    for u, v, k, data in G.edges(keys=True, data=True):
        link_id = data['link_id']
        edge = (u, v, k)
        link_info[link_id] = {'edge': edge, 'data': data, 'start_node': u, 'end_node': v}
    
    for origin_link_id in origins:
        origin_info = link_info[origin_link_id]
        start_node = origin_info['start_node']
        
        for dest_link_id in destinations:
            dest_info = link_info[dest_link_id]
            end_node = dest_info['start_node']
            od_pair = (origin_link_id, dest_link_id)
            
            temp_mixed_paths = []
            temp_charging_paths = []
            
            if nx.has_path(G, start_node, end_node):
                all_paths = list(nx.all_simple_edge_paths(G, source=start_node, target=end_node))
                
                for path_edges in all_paths:
                    skip_path = False
                    for edge in path_edges:
                        edge_data = G.edges[edge]
                        if edge_data.get('is_origin', False) or edge_data.get('is_destination', False):
                            skip_path = True
                            break
                    
                    if skip_path:
                        continue
                    
                    path_indices = [edge_to_idx[edge] for edge in path_edges]
                    full_path = [origin_link_id] + path_indices + [dest_link_id]
                    
                    ev_only_count = sum(1 for link_idx in full_path 
                                       if link_info[link_idx]['data'].get('link_type') == 'EV-only')
                    
                    if ev_only_count == 0:
                        temp_mixed_paths.append(full_path)
                    elif ev_only_count == 1:
                        temp_charging_paths.append(full_path)
            
            paths_NEV[od_pair] = temp_mixed_paths
            paths_EV[od_pair] = temp_mixed_paths + temp_charging_paths if temp_charging_paths else temp_mixed_paths
                        
    return paths_EV, paths_NEV, edge_to_idx, idx_to_edge


def create_od_demand(G, origins, destinations):
    edges_data = {data['link_id']: data for u, v, k, data in G.edges(keys=True, data=True)}
    
    dest_id_to_link = {}
    for link_id, data in edges_data.items():
        if data.get('link_type') == 'destination':
            dest_id_to_link[data.get('dest_id')] = link_id
    
    scenario_config = {
        'O1': {
            'total_flow': 1.0,
            'beta_EV': 0.6,
            'destinations': {'D1': 1.0}
        }
    }
    
    lambda_od_EV = {}
    lambda_od_NEV = {}
    
    for origin_link_id in origins:
        origin_data = edges_data.get(origin_link_id, {})
        origin_id = origin_data.get('origin_id')
        
        if origin_id in scenario_config:
            config = scenario_config[origin_id]
            total_flow = config['total_flow']
            beta_EV = config['beta_EV']
            
            for dest_id, proportion in config['destinations'].items():
                dest_link_id = dest_id_to_link[dest_id]
                od_pair = (origin_link_id, dest_link_id)
                
                lambda_od_EV[od_pair] = total_flow * beta_EV * proportion
                lambda_od_NEV[od_pair] = total_flow * (1 - beta_EV) * proportion
    
    return lambda_od_EV, lambda_od_NEV


# ============================================================================
# TRAFFIC DYNAMICS FUNCTIONS
# ============================================================================
def outflow_function(x, mu=None, nu=None, is_charging=False):
    """Smooth exponential outflow function"""
    if is_charging and mu is not None and nu is not None:
        if mu < 1e-9: 
            return 0.0
        return mu * (1.0 - np.exp(-(nu/mu) * x))
    else:
        return LINK_CAPACITY * (1.0 - np.exp(-LATENCY_STEEPNESS * x))


def latency_function(x, is_charging=False):
    """Latency (travel time) function"""
    if is_charging:
        return 0.1
    else:
        flow = outflow_function(x)
        return 1.0 + 2.0 * (flow / LINK_CAPACITY) ** 4


def compute_routing_matrix(y_EV, y_NEV, paths_EV, paths_NEV, od_pairs_EV, od_pairs_NEV, n_links):
    """Compute routing matrix R(y) based on path flows"""
    R = np.zeros((n_links, n_links))
    
    downstream_demand = np.zeros(n_links)
    link_pair_demand = {}
    
    # Process EV paths
    idx = 0
    for od in od_pairs_EV:
        paths = paths_EV[od]
        for p_idx, path in enumerate(paths):
            y_p = y_EV[idx]
            idx += 1
            
            for k in range(len(path) - 1):
                j = path[k]
                i = path[k + 1]
                
                if (j, i) not in link_pair_demand:
                    link_pair_demand[(j, i)] = 0.0
                link_pair_demand[(j, i)] += y_p
                downstream_demand[j] += y_p
    
    # Process NEV paths
    idx = 0
    for od in od_pairs_NEV:
        paths = paths_NEV[od]
        for p_idx, path in enumerate(paths):
            y_p = y_NEV[idx]
            idx += 1
            
            for k in range(len(path) - 1):
                j = path[k]
                i = path[k + 1]
                
                if (j, i) not in link_pair_demand:
                    link_pair_demand[(j, i)] = 0.0
                link_pair_demand[(j, i)] += y_p
                downstream_demand[j] += y_p
    
    # Build routing matrix
    for (j, i), demand in link_pair_demand.items():
        if downstream_demand[j] > 1e-9:
            R[j, i] = demand / downstream_demand[j]
        else:
            successors = [k for (j_, k) in link_pair_demand.keys() if j_ == j]
            if len(successors) > 0:
                R[j, i] = 1.0 / len(successors)
    
    return R


def compute_path_costs(x, paths_all, od_pairs, charging_stations, idx_to_edge, G, t, vehicle_class='EV'):
    """Compute perceived path costs"""
    path_costs = []
    
    for od in od_pairs:
        paths = paths_all[od]
        
        for path in paths:
            cost = 0.0
            
            for link_id in path:
                edge = idx_to_edge[link_id]
                edge_data = G.edges[edge]
                link_type = edge_data.get('link_type', 'mixed')
                
                if link_type == 'EV-only' and vehicle_class == 'EV':
                    station_id = edge_data.get('station_id')
                    params = get_station_parameters(t, station_id)
                    
                    p_s = params['p_s']
                    mu_s = params['mu_s']
                    nu_s = params['nu_s']
                    x_is = x[link_id]
                    
                    service_rate = outflow_function(x_is, mu=mu_s, nu=nu_s, is_charging=True)
                    
                    if service_rate > 1e-6:
                        waiting_time = x_is / service_rate
                    else:
                        waiting_time = 1.0 / (nu_s + 1e-9)
                    
                    base_latency = latency_function(x_is, is_charging=True)
                    cost += base_latency + alpha * waiting_time + gamma * p_s
                    
                elif link_type == 'origin' or link_type == 'destination':
                    continue
                else:
                    cost += latency_function(x[link_id], is_charging=False)
            
            path_costs.append(cost)
    
    return np.array(path_costs)


# ============================================================================
# ODE SYSTEM
# ============================================================================
def coupled_dynamics(t, state, params):
    """
    Coupled ODE system with PROPER NORMALIZATION
    """
    n_links = params['n_links']
    n_paths_EV = params['n_paths_EV']
    n_paths_NEV = params['n_paths_NEV']
    
    # Unpack state
    x = state[:n_links]
    y_EV = state[n_links:n_links + n_paths_EV]
    y_NEV = state[n_links + n_paths_EV:]
    
    # Compute routing matrix
    R = compute_routing_matrix(y_EV, y_NEV, params['paths_EV'], params['paths_NEV'], 
                               params['od_pairs_EV'], params['od_pairs_NEV'], n_links)
    
    # Compute outflows for all links
    f = np.zeros(n_links)
    for i in range(n_links):
        edge = params['idx_to_edge'][i]
        edge_data = params['G'].edges[edge]
        link_type = edge_data.get('link_type', 'mixed')
        
        if link_type == 'origin':
            # CRITICAL: Origin constant outflow
            f[i] = params['lambda_origin'][i]
        elif link_type == 'EV-only':
            station_id = edge_data.get('station_id')
            station_params = get_station_parameters(t, station_id)
            f[i] = outflow_function(x[i], mu=station_params['mu_s'], nu=station_params['nu_s'], is_charging=True)
        else:
            f[i] = outflow_function(x[i])
    
    # Traffic flow dynamics: dx/dt = R^T f - f
    dx_dt = R.T @ f - f
    
    # --- REPLICATOR DYNAMICS for EV with NORMALIZATION ---
    dy_EV_dt = np.zeros(n_paths_EV)
    
    tau_EV = compute_path_costs(x, params['paths_EV'], params['od_pairs_EV'], 
                                 params['charging_stations'], params['idx_to_edge'], 
                                 params['G'], t, vehicle_class='EV')
    
    idx = 0
    for od in params['od_pairs_EV']:
        paths = params['paths_EV'][od]
        n_paths_od = len(paths)
        
        y_od = np.maximum(y_EV[idx:idx + n_paths_od], 1e-12)
        tau_od = tau_EV[idx:idx + n_paths_od]
        lambda_od = params['lambda_od_EV'][od]
        
        # RENORMALIZE to conserve flow
        total_flow = np.sum(y_od)
        if total_flow > 1e-12:
            y_od = y_od * (lambda_od / total_flow)
        else:
            y_od = np.ones(n_paths_od) * (lambda_od / n_paths_od)
        
        if lambda_od > 1e-9:
            tau_avg = np.sum(y_od * tau_od) / lambda_od
            
            for i in range(n_paths_od):
                dy_EV_dt[idx + i] = eta_EV * y_od[i] * (tau_avg - tau_od[i])
        
        idx += n_paths_od
    
    # --- REPLICATOR DYNAMICS for NEV with NORMALIZATION ---
    dy_NEV_dt = np.zeros(n_paths_NEV)
    
    tau_NEV = compute_path_costs(x, params['paths_NEV'], params['od_pairs_NEV'], 
                                  params['charging_stations'], params['idx_to_edge'], 
                                  params['G'], t, vehicle_class='NEV')
    
    idx = 0
    for od in params['od_pairs_NEV']:
        paths = params['paths_NEV'][od]
        n_paths_od = len(paths)
        
        y_od = np.maximum(y_NEV[idx:idx + n_paths_od], 1e-12)
        tau_od = tau_NEV[idx:idx + n_paths_od]
        lambda_od = params['lambda_od_NEV'][od]
        
        # RENORMALIZE to conserve flow
        total_flow = np.sum(y_od)
        if total_flow > 1e-12:
            y_od = y_od * (lambda_od / total_flow)
        else:
            y_od = np.ones(n_paths_od) * (lambda_od / n_paths_od)
        
        if lambda_od > 1e-9:
            tau_avg = np.sum(y_od * tau_od) / lambda_od
            
            for i in range(n_paths_od):
                dy_NEV_dt[idx + i] = eta_NEV * y_od[i] * (tau_avg - tau_od[i])
        
        idx += n_paths_od
    
    # Combine derivatives
    dstate_dt = np.concatenate([dx_dt, dy_EV_dt, dy_NEV_dt])
    
    return dstate_dt


# ============================================================================
# SIMULATION RUNNER
# ============================================================================
def run_simulation(save_animation_path=None):
    """Main simulation with segmented ODE integration
    
    Args:
        save_animation_path: If provided, saves animation to this file path (e.g., 'network_animation.gif')
    """
    
    print("\n" + "="*70)
    print("EV CHARGING STATION COMPETITION SIMULATION")
    print("Dynamic Pricing with Time-Varying Parameters")
    print("="*70 + "\n")
    
    # Create network
    print("1. Building network...")
    G, origins, destinations, charging_stations = create_network_with_charging_stations()
    paths_EV, paths_NEV, edge_to_idx, idx_to_edge = enumerate_paths(G, origins, destinations, charging_stations)
    lambda_od_EV, lambda_od_NEV = create_od_demand(G, origins, destinations)
    
    n_links = len(idx_to_edge)
    print(f"   Network: {n_links} links, {len(charging_stations)} charging stations")
    
    # Initialize state
    print("\n2. Initializing state variables...")
    x0 = np.zeros(n_links)
    
    # Initialize EV path flows
    y_EV_0 = []
    od_pairs_EV = sorted(paths_EV.keys())
    for od in od_pairs_EV:
        n_paths = len(paths_EV[od])
        lambda_od = lambda_od_EV.get(od, 0.0)
        y_EV_0.extend([lambda_od / n_paths] * n_paths)
    
    # Initialize NEV path flows
    y_NEV_0 = []
    od_pairs_NEV = sorted(paths_NEV.keys())
    for od in od_pairs_NEV:
        n_paths = len(paths_NEV[od])
        lambda_od = lambda_od_NEV.get(od, 0.0)
        y_NEV_0.extend([lambda_od / n_paths] * n_paths)
    
    state0 = np.concatenate([x0, y_EV_0, y_NEV_0])
    
    n_paths_EV = len(y_EV_0)
    n_paths_NEV = len(y_NEV_0)
    
    print(f"   State dimension: {len(state0)} ({n_links} links + {n_paths_EV} EV paths + {n_paths_NEV} NEV paths)")
    
    # CRITICAL: Prepare lambda_origin for constant origin outflow
    lambda_origin = np.zeros(n_links)
    for origin_link_id in origins:
        total_demand = sum(lambda_od_EV.get((origin_link_id, d), 0.0) for d in destinations)
        total_demand += sum(lambda_od_NEV.get((origin_link_id, d), 0.0) for d in destinations)
        lambda_origin[origin_link_id] = total_demand
    
    params = {
        'n_links': n_links,
        'n_paths_EV': n_paths_EV,
        'n_paths_NEV': n_paths_NEV,
        'paths_EV': paths_EV,
        'paths_NEV': paths_NEV,
        'od_pairs_EV': od_pairs_EV,
        'od_pairs_NEV': od_pairs_NEV,
        'lambda_od_EV': lambda_od_EV,
        'lambda_od_NEV': lambda_od_NEV,
        'lambda_origin': lambda_origin,  # CRITICAL!
        'charging_stations': charging_stations,
        'G': G,
        'idx_to_edge': idx_to_edge
    }
    
    # SEGMENTED INTEGRATION
    print("\n3. Running segmented simulation across phases...")
    
    # Simplified: single phase for faster cloud execution
    phase_boundaries = [0, T_FINAL]
    
    t_all = []
    x_all = []
    y_EV_all = []
    y_NEV_all = []
    
    current_state = state0

    def dynamics_wrapper(t, state):
        return coupled_dynamics(t, state, params)
    
    for phase_idx in range(len(phase_boundaries) - 1):
        t_start = phase_boundaries[phase_idx]
        t_end = phase_boundaries[phase_idx + 1]
        
        print(f"\n   Phase {phase_idx + 1}: t = {t_start} to {t_end}")
        
        n_points_phase = int(N_TIME_POINTS * (t_end - t_start) / T_FINAL)
        t_eval_phase = np.linspace(t_start, t_end, n_points_phase)
        
        sol = solve_ivp(
            dynamics_wrapper, 
            [t_start, t_end], 
            current_state,
            method='Radau',
            t_eval=t_eval_phase,
            rtol=SOLVER_RTOL,
            atol=SOLVER_ATOL,
            max_step=MAX_STEP
        )
        
        if not sol.success:
            print(f"   WARNING: Integration failed in phase {phase_idx + 1}")
            print(f"   Message: {sol.message}")
        else:
            print(f"   Phase {phase_idx + 1} complete: {len(sol.t)} time points")
        
        t_phase = sol.t
        x_phase = sol.y[:n_links, :]
        y_EV_phase = sol.y[n_links:n_links + n_paths_EV, :]
        y_NEV_phase = sol.y[n_links + n_paths_EV:, :]
        
        if phase_idx == 0:
            t_all = t_phase
            x_all = x_phase
            y_EV_all = y_EV_phase
            y_NEV_all = y_NEV_phase
        else:
            t_all = np.concatenate([t_all, t_phase[1:]])
            x_all = np.concatenate([x_all, x_phase[:, 1:]], axis=1)
            y_EV_all = np.concatenate([y_EV_all, y_EV_phase[:, 1:]], axis=1)
            y_NEV_all = np.concatenate([y_NEV_all, y_NEV_phase[:, 1:]], axis=1)
        
        current_state = sol.y[:, -1]
    
    print(f"\n   Total simulation: {len(t_all)} time points")
    
    # Extract station metrics
    print("\n4. Extracting station metrics...")
    q_s_traj = {}
    p_s_traj = {}
    for sid, link_id in charging_stations.items():
        q_s_traj[sid] = np.array([
            outflow_function(x_all[link_id, i],
                           mu=get_station_parameters(t_all[i], sid)['mu_s'],
                           nu=get_station_parameters(t_all[i], sid)['nu_s'],
                           is_charging=True)
            for i in range(len(t_all))
        ])
        p_s_traj[sid] = np.array([
            get_station_parameters(t_all[i], sid)['p_s'] for i in range(len(t_all))
        ])
    
    # Create visualizations
    print("\n5. Creating visualizations...")
    print("   [VIZ 1/4] Network animation...")

    create_network_animation(G, x_all, t_all, idx_to_edge, charging_stations, get_station_parameters, save_path=save_animation_path)
    
    print("   [VIZ 2/4] Path demands...")
    plot_path_demands(t_all, y_EV_all, y_NEV_all, paths_EV, paths_NEV, od_pairs_EV, od_pairs_NEV,
                     lambda_od_EV, lambda_od_NEV)
    
    print("   [VIZ 3/4] Link densities...")
    plot_link_densities(t_all, x_all, G, idx_to_edge)
    
    print("   [VIZ 4/4] Competition metrics...")
    plot_charging_station_metrics(q_s_traj, p_s_traj, t_all, charging_stations,
                                  get_station_parameters, x_all, paths_EV, od_pairs_EV)


# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================
def create_network_animation(G, x_traj, t, idx_to_edge, charging_stations, get_params_func, save_path=None):
    """Create animated network visualization
    
    Args:
        save_path: If provided, saves animation to this file path (e.g., 'network_animation.gif')
    """
    
    # Compute link demands (total flow wanting to use each link)
    link_demands = np.zeros_like(x_traj)
    
    # This part computes y (demand) from the path flows
    # Since we don't have the path flow trajectories passed in, 
    # we'll use x_traj as a proxy for visualization
    # In the original, this was computed from y_EV_traj and y_NEV_traj
    # For now, we'll set link_demands = x_traj for simplicity
    link_demands = x_traj.copy()
    
    # Setup animation
    pos = nx.get_node_attributes(G, 'pos')
    fig, ax = plt.subplots(figsize=(14, 9))
    
    # Legend
    legend_elements = [
        mpatches.Patch(color='black', label='Mixed Link'),
        mpatches.Patch(color='green', label='EV Charging Link', linestyle='--'),
        mpatches.Patch(facecolor='white', edgecolor='black', label='Mixed Data (x, y)'),
        mpatches.Patch(facecolor='#daffda', edgecolor='green', label='EV Data (x, y)') 
    ]
    
    def update(frame):
        ax.clear()
        ax.set_title(f"Network Simulation: t={t[frame]:.2f}s", fontsize=16, fontweight='bold')
        ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
        
        # Draw Nodes
        nx.draw_networkx_nodes(G, pos, ax=ax, node_color='lightgrey', node_size=600, edgecolors='black')
        nx.draw_networkx_labels(G, pos, ax=ax, font_weight='bold')
        
        # Draw Edges
        for i, edge_key in enumerate(idx_to_edge):
            u, v, k = edge_key
            data = G.edges[edge_key]
            ltype = data.get('link_type', 'mixed')
            
            if u == v: continue  # Skip self-loops
            
            x_val = x_traj[i, frame]
            y_val = link_demands[i, frame]
            
            # Geometry & Style
            color = 'black'
            style = 'solid'
            width = 1.5 + (x_val * 4.0)
            
            # Defaults
            conn = "arc3,rad=0.0"
            label_offset_dir = 1 
            label_offset_dist = 0.2
            
            is_parallel = len(G[u][v]) > 1
            
            if is_parallel:
                if ltype == 'EV-only':
                    conn = "arc3,rad=0.3"  # Curve Left/Up (Top)
                    color = 'green'
                    style = 'dashed'
                    label_offset_dir = 1   # Push Label UP
                    label_offset_dist = 0.6 
                else:
                    conn = "arc3,rad=-0.3"  # Curve Right/Down (Bottom)
                    label_offset_dir = -1  # Push Label DOWN
                    label_offset_dist = 0.6
            else:
                label_offset_dir = 1
                label_offset_dist = 0.3 

            # Draw Arrow
            ax.annotate("", xy=pos[v], xytext=pos[u],
                        arrowprops=dict(arrowstyle="-|>", color=color, 
                                        lw=width, linestyle=style, 
                                        connectionstyle=conn, shrinkA=15, shrinkB=15))
            
            # Label Placement
            x1, y1 = pos[u]; x2, y2 = pos[v]
            mid_x, mid_y = (x1+x2)/2, (y1+y2)/2
            
            dx, dy = x2-x1, y2-y1
            norm = np.sqrt(dx**2 + dy**2)
            
            if norm > 0:
                perp_x, perp_y = -dy/norm, dx/norm 
                mid_x += perp_x * (label_offset_dist * label_offset_dir)
                mid_y += perp_y * (label_offset_dist * label_offset_dir)

            # Label Content
            label_text = f"x:{x_val:.2f}\ny:{y_val:.2f}"
            
            if ltype == 'EV-only':
                sid = data.get('station_id', '?')
                label_text = f"{sid}\n" + label_text 
                box_color = '#daffda'  # Light Green
                edge_color = 'green'
            else:
                box_color = 'white' 
                edge_color = 'black'
            
            # Draw Box
            ax.text(mid_x, mid_y, label_text, fontsize=8, ha='center', va='center', fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.2", fc=box_color, ec=edge_color, alpha=0.9))
            
        ax.axis('off')

    ani = animation.FuncAnimation(fig, update, frames=np.arange(0, len(t), 10), interval=100)
    
    # Save animation if path provided
    if save_path:
        try:
            print(f"   Saving animation to {save_path}...")
            ani.save(save_path, writer='pillow', fps=10)
            print(f"   Animation saved successfully!")
        except Exception as e:
            print(f"   Warning: Could not save animation: {e}")
    
    plt.show()

def plot_path_demands(t, y_EV_all, y_NEV_all, paths_EV, paths_NEV, od_pairs_EV, od_pairs_NEV,
                     lambda_od_EV, lambda_od_NEV):
    """Plot path demand evolution"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('Path Demand Dynamics', fontsize=14, fontweight='bold')
    
    # NEV paths
    idx = 0
    for od in od_pairs_NEV:
        paths = paths_NEV[od]
        for p_idx in range(len(paths)):
            ax1.plot(t, y_NEV_all[idx, :], label=f'Path {p_idx}', linewidth=2)
            idx += 1
    
    ax1.axhline(y=lambda_od_NEV[od_pairs_NEV[0]], color='red', linestyle='--', 
               label=f'Total Demand={lambda_od_NEV[od_pairs_NEV[0]]:.2f}')
    ax1.set_title('NEV: O1 -> D1')
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Path Flow')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # EV paths
    idx = 0
    for od in od_pairs_EV:
        paths = paths_EV[od]
        for p_idx in range(len(paths)):
            ax2.plot(t, y_EV_all[idx, :], label=f'Path {p_idx}', linewidth=2)
            idx += 1
    
    ax2.axhline(y=lambda_od_EV[od_pairs_EV[0]], color='red', linestyle='--',
               label=f'Total Demand={lambda_od_EV[od_pairs_EV[0]]:.2f}')
    ax2.set_title('EV: O1 -> D1')
    ax2.set_xlabel('Time')
    ax2.set_ylabel('Path Flow')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()


def plot_link_densities(t, x_traj, G, idx_to_edge):
    """Plot link traffic densities"""
    n_links = x_traj.shape[0]
    n_cols = 3
    n_rows = (n_links + n_cols - 1) // n_cols
    
    fig, axs = plt.subplots(n_rows, n_cols, figsize=(15, 3 * n_rows))
    fig.suptitle('Link Traffic Densities', fontsize=14, fontweight='bold')
    plt.subplots_adjust(hspace=0.6, wspace=0.3, top=0.93, bottom=0.08)
    
    axs = axs.flatten() if n_links > 1 else [axs]
    
    for i in range(n_links):
        edge = idx_to_edge[i]
        edge_data = G.edges[edge]
        link_type = edge_data.get('link_type', 'mixed')
        station_info = f" ({edge_data.get('station_id', '')})" if link_type == 'EV-only' else ''
        
        color = 'green' if link_type == 'EV-only' else 'blue'
        axs[i].plot(t, x_traj[i], label=f"Link {i}", color=color, linewidth=2)
        axs[i].set_title(f"Link {i}: {edge[0]}->{edge[1]} [{link_type}]{station_info}", fontsize=10, pad=8)
        axs[i].set_xlabel("Time", fontsize=9)
        axs[i].set_ylabel(r"Density $x_i$", fontsize=9)
        axs[i].grid(True, alpha=0.3)
        axs[i].legend(fontsize=8)
    
    for k in range(n_links, len(axs)):
        axs[k].axis('off')
    
    plt.show()


def plot_charging_station_metrics(q_s_traj, p_s_traj, t, charging_stations, 
                                   station_params, x_traj, paths_EV, od_pairs):
    """Plot charging station competition metrics"""
    n_stations = len(charging_stations)
    station_ids = sorted(charging_stations.keys())
    
    fig, axs = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle('Competition Metrics (Dynamic Pricing Game)', fontsize=16, fontweight='bold')
    
    colors = {'S1': '#ff6b6b', 'S2': '#4ecdc4'}
    
    # Market Share Evolution
    ax = axs[0, 0]
    total_flow = sum(q_s_traj[sid] for sid in station_ids)
    for sid in station_ids:
        market_share = 100 * q_s_traj[sid] / (total_flow + 1e-9)
        ax.plot(t, market_share, label=sid, linewidth=2.5, color=colors[sid])
    ax.axvline(x=100, color='gray', linestyle='--', alpha=0.5, label='Phase Change')
    ax.axvline(x=200, color='gray', linestyle='--', alpha=0.5)
    ax.axvline(x=300, color='gray', linestyle='--', alpha=0.5)
    ax.set_title('Market Share Evolution (%)')
    ax.set_ylabel('Market Share (%)')
    ax.set_xlabel('Time (s)')
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Pricing Strategy
    ax = axs[0, 1]
    for sid in station_ids:
        ax.plot(t, p_s_traj[sid], label=f'{sid} Price', linewidth=2.5, color=colors[sid])
    ax.axvline(x=100, color='gray', linestyle='--', alpha=0.5)
    ax.axvline(x=200, color='gray', linestyle='--', alpha=0.5)
    ax.axvline(x=300, color='gray', linestyle='--', alpha=0.5)
    ax.set_title('Pricing Strategy')
    ax.set_ylabel('Price ($/vehicle)')
    ax.set_xlabel('Time (s)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Queue Lengths
    ax = axs[0, 2]
    for sid in station_ids:
        link_id = charging_stations[sid]
        ax.plot(t, x_traj[link_id, :], label=f'{sid} Queue', linewidth=2.5, color=colors[sid])
    ax.axvline(x=100, color='gray', linestyle='--', alpha=0.5)
    ax.axvline(x=200, color='gray', linestyle='--', alpha=0.5)
    ax.axvline(x=300, color='gray', linestyle='--', alpha=0.5)
    ax.set_title('Queue Lengths')
    ax.set_ylabel('Vehicles in Queue')
    ax.set_xlabel('Time (s)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Phase comparison bar charts
    phases = [
        ('Phase 1\n(0-100s)', 0, 100),
        ('Phase 2\n(100-200s)', 100, 200),
        ('Phase 3\n(200-300s)', 200, 300),
        ('Phase 4\n(300-400s)', 300, T_FINAL)
    ]
    
    x_pos = np.arange(len(phases))
    width = 0.35
    
    # Revenue by Phase
    ax = axs[1, 0]
    for i, sid in enumerate(station_ids):
        revenues = []
        for _, start_t, end_t in phases:
            mask = (t >= start_t) & (t <= end_t)
            t_phase = t[mask]
            if len(t_phase) > 1:
                service_rates = q_s_traj[sid][mask]
                revenue_rate = p_s_traj[sid][mask] * service_rates
                revenues.append(np.trapz(revenue_rate, t_phase))
            else:
                revenues.append(0.0)
        ax.bar(x_pos + i*width, revenues, width, label=sid, color=colors[sid], alpha=0.8, edgecolor='black')
        
        for j, (xpos, rev) in enumerate(zip(x_pos + i*width, revenues)):
            ax.text(xpos, rev + max(revenues)*0.02 if max(revenues) > 0 else 0.5, 
                   f'{rev:.1f}', ha='center', va='bottom', fontsize=8, fontweight='bold')
    
    ax.set_xticks(x_pos + width/2)
    ax.set_xticklabels([p[0] for p in phases])
    ax.set_ylabel('Integrated Revenue ($·vehicles)')
    ax.set_title('Integrated Revenue ($/vehicles)')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # Net Profit by Phase
    ax = axs[1, 1]
    for i, sid in enumerate(station_ids):
        net_profits = []
        for _, start_t, end_t in phases:
            mask = (t >= start_t) & (t <= end_t)
            t_phase = t[mask]
            if len(t_phase) > 1:
                prices = p_s_traj[sid][mask]
                costs = np.array([get_station_parameters(ti, sid)['c_s'] for ti in t_phase])
                service_rates = q_s_traj[sid][mask]
                profit_rate = (prices - costs) * service_rates
                net_profits.append(np.trapz(profit_rate, t_phase))
            else:
                net_profits.append(0.0)
        ax.bar(x_pos + i*width, net_profits, width, label=sid, color=colors[sid], alpha=0.8, edgecolor='black')
        
        for j, (xpos, profit) in enumerate(zip(x_pos + i*width, net_profits)):
            offset = max(abs(min(net_profits)), max(net_profits))*0.02 if len(net_profits) > 0 else 0.5
            ax.text(xpos, profit + (offset if profit >= 0 else -offset),
                   f'{profit:.1f}', ha='center', va='bottom' if profit >= 0 else 'top',
                   fontsize=8, fontweight='bold')
    
    ax.set_xticks(x_pos + width/2)
    ax.set_xticklabels([p[0] for p in phases])
    ax.set_ylabel('Integrated Net Profit ($·vehicles)')
    ax.set_title('Integrated Net Profit ($/vehicles)')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    
    # Market Share
    ax = axs[1, 2]
    total_integrated_flows = {}
    for sid in station_ids:
        service_rates = q_s_traj[sid]
        total_integrated_flows[sid] = np.trapz(service_rates, t)
    
    total_flow_all_stations = sum(total_integrated_flows.values())
    
    flow_shares = []
    labels = []
    for sid in station_ids:
        pct = (total_integrated_flows[sid] / total_flow_all_stations * 100) if total_flow_all_stations > 1e-9 else 0.0
        flow_shares.append(pct)
        labels.append(sid)
    
    bars = ax.bar(labels, flow_shares, color=[colors[sid] for sid in station_ids], 
                  edgecolor='black', alpha=0.8)
    
    ax.set_ylabel('Market Share (%)')
    ax.set_title('Market Share (%)')
    ax.set_ylim(0, 110)
    ax.grid(True, alpha=0.3, axis='y')
    
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 2,
                f'{height:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=11)
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    plt.show()


# ============================================================================
# MAIN EXECUTION
# ============================================================================
if __name__ == "__main__":
    run_simulation(save_animation_path='network_animation.gif')
    print("\n" + "="*70)
    print("SIMULATION COMPLETE")
    print("="*70)