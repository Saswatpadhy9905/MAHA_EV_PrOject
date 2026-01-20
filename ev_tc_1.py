import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
import matplotlib.animation as animation
from matplotlib.patches import FancyBboxPatch
import warnings
warnings.filterwarnings('ignore')

# --- REPLICATOR DYNAMICS PARAMETERS ---
eta_EV = 0.05      # Imitation rate for EV users 
eta_NEV = 0.05    # Imitation rate for non-EV users
alpha = 0.3       # Weight for waiting time in EV cost 

# --- TRAFFIC FLOW PARAMETERS ---
LINK_CAPACITY = 0.5           # Maximum outflow capacity per link (used in link_outflows)
LATENCY_STEEPNESS = 1.0       # How steeply latency increases with density (used in latency_function)

# --- SIMULATION PARAMETERS ---
T_FINAL = 100.0              
N_TIME_POINTS = 800          
SOLVER_RTOL = 1e-3          
SOLVER_ATOL = 1e-5           
MAX_STEP = 1.0             


# NETWORK CONSTRUCTION - MODIFY THIS FOR DIFFERENT TOPOLOGIES

def create_network_with_charging_stations():
    """
    Creates network where Origin and Destination are LINKS, not nodes.
    No virtual source/sink nodes needed in visualization.
    """
    G = nx.MultiDiGraph()
    
    # Only Physical Nodes (no virtual nodes needed)
    physical_nodes = ['O1', 'O2', 'A', 'B', 'C', 'D_node', 'D1_node', 'D2_node', 'D3_node']
    G.add_nodes_from(physical_nodes)
    
    link_id = 0
    
    # --- ORIGIN LINKS (these ARE the origins) ---
    # Origin 1: Injects at node n1
    G.add_edge('O1', 'O1', key=0, link_id=link_id, link_type='origin', 
               origin_id='O1', is_origin=True)
    origin_link_1 = link_id
    link_id += 1
    
    # Origin 2: Injects at node n2
    G.add_edge('O2', 'O2', key=0, link_id=link_id, link_type='origin', 
               origin_id='O2', is_origin=True)
    origin_link_2 = link_id
    link_id += 1
    
    # --- PHYSICAL NETWORK LINKS ---
    G.add_edge('O1', 'D1_node', key=0, link_id=link_id, link_type='mixed'); link_id += 1 # Top Road
    G.add_edge('O1', 'D1_node', key=1, link_id=link_id, link_type='EV-only', station_id='S1'); s1_link = link_id; link_id += 1
    G.add_edge('O1', 'C', key=0, link_id=link_id, link_type='mixed'); link_id += 1

    # From O2
    G.add_edge('O2', 'B', key=0, link_id=link_id, link_type='mixed'); link_id += 1
    G.add_edge('O2', 'D2_node', key=0, link_id=link_id, link_type='mixed'); link_id += 1
    G.add_edge('O2', 'D_node', key=0, link_id=link_id, link_type='mixed'); link_id += 1 # Middle Road
    G.add_edge('O2', 'D_node', key=1, link_id=link_id, link_type='EV-only', station_id='S3'); s3_link = link_id; link_id += 1
    G.add_edge('O2', 'A', key=0, link_id=link_id, link_type='mixed'); link_id += 1

    # From Intermediate Nodes
    G.add_edge('B', 'C', key=0, link_id=link_id, link_type='mixed'); link_id += 1
    G.add_edge('B', 'D1_node', key=0, link_id=link_id, link_type='mixed'); link_id += 1
    G.add_edge('C', 'D_node', key=0, link_id=link_id, link_type='mixed'); link_id += 1
    G.add_edge('C', 'D1_node', key=0, link_id=link_id, link_type='mixed'); link_id += 1 # This is the "Top Station Road"
    G.add_edge('C', 'D1_node', key=1, link_id=link_id, link_type='EV-only', station_id='S2'); s2_link = link_id; link_id += 1
    G.add_edge('C', 'D2_node', key=0, link_id=link_id, link_type='mixed'); link_id += 1
    G.add_edge('D_node', 'D2_node', key=0, link_id=link_id, link_type='mixed'); link_id += 1
    G.add_edge('D_node', 'D3_node', key=0, link_id=link_id, link_type='mixed'); link_id += 1
    G.add_edge('D_node', 'A', key=0, link_id=link_id, link_type='mixed'); link_id += 1
    G.add_edge('A', 'D3_node', key=0, link_id=link_id, link_type='mixed'); link_id += 1 # Bottom Station Road
    G.add_edge('A', 'D3_node', key=1, link_id=link_id, link_type='EV-only', station_id='S4'); s4_link = link_id; link_id += 1
    
    # --- DESTINATION LINKS (these ARE the destinations) ---
    G.add_edge('D1_node', 'D1_node', key=0, link_id=link_id, link_type='destination', dest_id='D1', is_destination=True)
    d1_link = link_id; link_id += 1
    G.add_edge('D2_node', 'D2_node', key=0, link_id=link_id, link_type='destination', dest_id='D2', is_destination=True)
    d2_link = link_id; link_id += 1
    G.add_edge('D3_node', 'D3_node', key=0, link_id=link_id, link_type='destination', dest_id='D3', is_destination=True)
    d3_link = link_id; link_id += 1

    origins = [origin_link_1, origin_link_2]
    destinations = [d1_link, d2_link, d3_link]
    charging_stations = {'S1': s1_link, 'S2': s2_link, 'S3': s3_link, 'S4': s4_link}

    # Visual Layout (Adjust coordinates to match the sketch)
    pos = {
        'O1': (0, 6), 'O2': (0, 0),
        'B': (2, 4), 'C': (4, 5.5), 'D_node': (4.7, 1.7), 'A': (2, -1),
        'D1_node': (8, 6), 'D2_node': (8, 3), 'D3_node': (8, -1)
    }
    nx.set_node_attributes(G, pos, 'pos')
    return G, origins, destinations, charging_stations
def enumerate_paths(G, origins, destinations, charging_stations):
    """
    Fixed path enumeration that handles self-loop origin/destination links.
    """
    edges = list(G.edges(keys=True))
    edge_to_idx = {edge: i for i, edge in enumerate(edges)}
    idx_to_edge = edges
    
    paths_EV = {}
    paths_NEV = {}
    
    # Build link info map
    link_info = {}
    for u, v, k, data in G.edges(keys=True, data=True):
        link_id = data['link_id']
        edge = (u, v, k)
        link_info[link_id] = {
            'edge': edge, 
            'data': data, 
            'start_node': u, 
            'end_node': v
        }
    
    for origin_link_id in origins:
        origin_info = link_info[origin_link_id]
        # For self-loop origins, the start node IS the injection point
        start_node = origin_info['start_node']
        
        for dest_link_id in destinations:
            dest_info = link_info[dest_link_id]
            # For self-loop destinations, end node IS the collection point
            end_node = dest_info['start_node']
            
            od_pair = (origin_link_id, dest_link_id)
            
            temp_mixed_paths = []
            temp_charging_paths = []
            
            # Find paths from origin node to destination node
            if nx.has_path(G, start_node, end_node):
                all_paths = list(nx.all_simple_edge_paths(G, source=start_node, target=end_node))
                
                for path_edges in all_paths:
                    # Skip paths that use origin/destination links in middle
                    skip_path = False
                    for edge in path_edges:
                        edge_data = G.edges[edge]
                        if edge_data.get('is_origin', False) or edge_data.get('is_destination', False):
                            skip_path = True
                            break
                    
                    if skip_path:
                        continue
                    
                    # Convert to link indices
                    path_indices = [edge_to_idx[edge] for edge in path_edges]
                    
                    # Build COMPLETE path: origin -> middle links -> destination
                    full_path = [origin_link_id] + path_indices + [dest_link_id]
                    
                    # Count charging stations
                    ev_only_count = 0
                    for link_idx in full_path:
                        link_data = link_info[link_idx]['data']
                        if link_data.get('link_type') == 'EV-only':
                            ev_only_count += 1
                    
                    # Classify
                    if ev_only_count == 0:
                        temp_mixed_paths.append(full_path)
                    elif ev_only_count == 1:
                        temp_charging_paths.append(full_path)
            
            # Apply EV priority logic
            paths_NEV[od_pair] = temp_mixed_paths
            
            if len(temp_charging_paths) > 0:
                paths_EV[od_pair] = temp_charging_paths
            else:
                paths_EV[od_pair] = temp_mixed_paths
                        
    return paths_EV, paths_NEV, edge_to_idx, idx_to_edge



# OD DEMAND SPECIFICATION - MODIFY FOR DIFFERENT DEMAND PATTERNS
def create_od_demand(G, origins, destinations):
    """
    Creates demand keyed by (Origin_Link_ID, Destination_Link_ID).
    Fixed to use LINK IDs for destinations, not node names.
    """
    
    # 1. Build a map from dest_id tag to link_id
    edges_data = {data['link_id']: data for u, v, k, data in G.edges(keys=True, data=True)}
    
    dest_id_to_link = {}
    for link_id, data in edges_data.items():
        if data.get('link_type') == 'destination':
            dest_id_to_link[data.get('dest_id')] = link_id
    
    # 2. Define scenario using logical names
    scenario_config = {
        'O1': {'total': 1.0, 'beta': 0.4},
        'O2': {'total': 1.5, 'beta': 0.5}
    }
    
    # Split ratios now use DESTINATION IDs (D1, D2)
    split_ratios = {
        ('O1', 'D1'): 0.5, ('O1', 'D2'): 0.3,('O1', 'D3'): 0.2,
        ('O2', 'D1'): 0.2, ('O2', 'D2'): 0.4,('O2', 'D3'): 0.4
    }
    
    lambda_EV = {}
    lambda_NEV = {}
    lambda_total = {}
    
    # 3. Assign demand to Link IDs
    for origin_link_id in origins:
        link_data = edges_data.get(origin_link_id)
        origin_name = link_data.get('origin_id')  # 'O1' or 'O2'
        
        if not origin_name or origin_name not in scenario_config:
            continue
            
        total_flow = scenario_config[origin_name]['total']
        beta = scenario_config[origin_name]['beta']
        
        lambda_total[origin_link_id] = total_flow
        
        # Distribute to destinations
        for dest_link_id in destinations:
            dest_data = edges_data.get(dest_link_id)
            dest_name = dest_data.get('dest_id')  # 'D1' or 'D2'
            
            # Key for demand: (origin_link_id, dest_link_id)
            od_key = (origin_link_id, dest_link_id)
            
            # Get split ratio using logical names
            split = split_ratios.get((origin_name, dest_name), 0.0)
            pair_total = total_flow * split
            
            lambda_EV[od_key] = pair_total * beta
            lambda_NEV[od_key] = pair_total * (1 - beta)
            
    return lambda_EV, lambda_NEV, lambda_total, {}


# CHARGING STATION PARAMETERS - MODIFY FOR DIFFERENT STATION CHARACTERISTICS

def initialize_charging_stations(charging_stations):
    
    station_params = {}
    
    
    if 'S1' in charging_stations:
        station_params['S1'] = {
            'mu_s': 1.5,        # Service rate (vehicles/time)
            'c_s': 0.1,         # Operating cost
            'p_s_init': 0.1,    # Initial price
            'kappa_s': 0.01,    # Price adjustment rate
            'nu_s' :10        
        }
    
    
    if 'S2' in charging_stations:
        station_params['S2'] = {
            'mu_s': 1.5,       
            'c_s': 0.1,         
            'p_s_init': 0.5,    
            'kappa_s': 0.01,
            'nu_s' :10     
        }
    if 'S3' in charging_stations:
        station_params['S3'] = {
            'mu_s': 1.5,       
            'c_s': 0.1,         
            'p_s_init': 0.5,    
            'kappa_s': 0.01,
            'nu_s' :10     
        }
    if 'S4' in charging_stations:
        station_params['S4'] = {
            'mu_s': 1.5,       
            'c_s': 0.1,         
            'p_s_init': 0.5,    
            'kappa_s': 0.01,
            'nu_s' :10     
        }
    
    
   
    for station_id in charging_stations.keys():
        if station_id not in station_params:
            station_params[station_id] = {
                'mu_s': 1.5,
                'c_s': 0.1,
                'p_s_init': 0.5,
                'kappa_s': 0.05,
                'nu_s':10
            }
    
    return station_params


# ============================================================================
# HELPER FUNCTIONS - MODIFY THESE FOR DIFFERENT TRAFFIC MODELS
# ============================================================================
def link_outflows(x, capacity=None):
    
    if capacity is None:
        capacity = LINK_CAPACITY
    
    # === CURRENT MODEL: Linear with saturation ===
    # MODIFY: Change this to implement different outflow functions
    return x
    

    
    # # Exponential saturation model
    # beta = 0.5  # Adjust this parameter
    # return capacity * (1 - np.exp(-beta * x))
    
    # # Quadratic model
    # return np.minimum(0.5 * x**2, capacity)


def latency_function(x, steepness=None):
    
    if steepness is None:
        steepness = LATENCY_STEEPNESS
    
  
    return steepness * x
    
    # # Quadratic latency
    # return steepness * x**2
    
    # # Exponential latency 
    # return steepness * np.exp(0.5 * x)


def link_demand_flows(y_EV, y_NEV, paths_EV, paths_NEV, od_pairs, n_links):
   
    yl = np.zeros(n_links)
    
    for od in od_pairs:
        # NEV contribution
        if od in paths_NEV and od in y_NEV:
            for p_idx, path in enumerate(paths_NEV[od]):
                if p_idx < len(y_NEV[od]):
                    flow = max(0, y_NEV[od][p_idx])  # Ensure non-negative
                    for link_idx in path:
                        yl[link_idx] += flow
        
        # EV contribution
        if od in paths_EV and od in y_EV:
            for p_idx, path in enumerate(paths_EV[od]):
                if p_idx < len(y_EV[od]):
                    flow = max(0, y_EV[od][p_idx])  # Ensure non-negative
                    for link_idx in path:
                        yl[link_idx] += flow
    
    return yl


def path_latencies(ll, paths, od_pairs):
    
    lp = {}
    
    for od in od_pairs:
        if od not in paths:
            continue
        
        lp[od] = np.zeros(len(paths[od]))
        for p_idx, path in enumerate(paths[od]):
            for link_idx in path:
                lp[od][p_idx] += ll[link_idx]
    
    return lp


def compute_waiting_times(x, charging_stations, station_params):
    """
    Compute waiting time based on Little's Law proxy.
    w_s(t) = x_is(t) / mu_s  [Paper Eq. 21]
    """
    w_s = {}
    for station_id, link_id in charging_stations.items():
        mu_s = station_params[station_id]['mu_s']
        # The density on the access link IS the queue
        w_s[station_id] = x[link_id] / mu_s
    return w_s


def compute_ev_path_costs(lp_EV, w_s, p_s, paths_EV, od_pairs, 
                          charging_stations, idx_to_edge, G, alpha):
  
    U_EV = {}
    
    for od in od_pairs:
        if od not in paths_EV:
            continue
        
        U_EV[od] = np.copy(lp_EV[od])  # Start with travel latency
        
        # Add charging costs for EV-only paths
        for p_idx, path in enumerate(paths_EV[od]):
            for link_idx in path:
                edge = idx_to_edge[link_idx]
                edge_data = G.edges[edge]
                
                if edge_data.get('link_type') == 'EV-only':
                    station_id = edge_data['station_id']
                    U_EV[od][p_idx] += p_s[station_id] + alpha * w_s[station_id]
    
    return U_EV


def compute_routing_matrix(y_EV, y_NEV, paths_EV, paths_NEV, od_pairs, n_links):
    """
    Computes routing matrix R based on PATH FLOWS.
    R[u, v] = (Flow from link u to link v) / (Total flow leaving link u)
    
    FIXED VERSION - Properly handles consecutive link transitions
    """
    R_num = np.zeros((n_links, n_links))
    R_den = np.zeros(n_links)

    # Helper: Accumulate flow for every transition (u -> v) in every path
    def accumulate_flows(y_dict, paths_dict):
        for od in od_pairs:
            if od not in paths_dict or od not in y_dict:
                continue
                
            flows = y_dict[od]
            paths = paths_dict[od]
            
            for p_idx, path_links in enumerate(paths):
                if p_idx >= len(flows):
                    continue
                    
                path_flow = max(0, flows[p_idx])  # Ensure non-negative
                
                # Iterate through consecutive links in the path
                for k in range(len(path_links) - 1):
                    u = path_links[k]      # Upstream link index
                    v = path_links[k + 1]  # Downstream link index
                    
                    # Accumulate this transition
                    R_num[u, v] += path_flow
                    R_den[u] += path_flow

    # Process both EV and NEV flows
    accumulate_flows(y_EV, paths_EV)
    accumulate_flows(y_NEV, paths_NEV)

    # Compute R with safe division
    R = np.zeros((n_links, n_links))
    for u in range(n_links):
        if R_den[u] > 1e-9:
            R[u, :] = R_num[u, :] / R_den[u]
        # else: R[u, :] remains zero (no outflow from this link)
    
    return R

# ============================================================================
# COUPLED DYNAMICS
# ============================================================================
def coupled_dynamics_rhs(t, z, G, paths_EV, paths_NEV, od_pairs, 
                         charging_stations, station_params, 
                         lambda_EV, lambda_NEV, lambda_total,
                         edge_to_idx, idx_to_edge,
                         eta_EV, eta_NEV, alpha):

    if not np.all(np.isfinite(z)):
        return np.zeros_like(z)
    
    edges = list(G.edges(keys=True))
    n_links = len(edges)
    idx = 0

    # 1. Extract and clamp link densities
    x = np.maximum(z[idx:idx + n_links], 0)
    idx += n_links

    # 2. Extract path flows
    y_NEV = {}
    for od in od_pairs:
        n_paths = len(paths_NEV.get(od, []))
        if n_paths > 0:
            raw_y = np.maximum(z[idx:idx + n_paths], 1e-10)
            current_sum = np.sum(raw_y)
            target_demand = lambda_NEV.get(od, 0)
            if current_sum > 1e-9:
                y_NEV[od] = (raw_y / current_sum) * target_demand
            else:
                y_NEV[od] = np.ones(n_paths) * (target_demand / n_paths)
            idx += n_paths

    y_EV = {}
    for od in od_pairs:
        n_paths = len(paths_EV.get(od, []))
        if n_paths > 0:
            raw_y = np.maximum(z[idx:idx + n_paths], 1e-10)
            current_sum = np.sum(raw_y)
            target_demand = lambda_EV.get(od, 0)
            if current_sum > 1e-9:
                y_EV[od] = (raw_y / current_sum) * target_demand
            else:
                y_EV[od] = np.ones(n_paths) * (target_demand / n_paths)
            idx += n_paths

    # 3. Extract prices
    station_ids = sorted(charging_stations.keys())
    p_s = {sid: max(z[idx + i], 0.01) for i, sid in enumerate(station_ids)}
    idx += len(station_ids)

    # 4. Compute costs
    ll = latency_function(x)
    lp_NEV = path_latencies(ll, paths_NEV, od_pairs)
    lp_EV = path_latencies(ll, paths_EV, od_pairs)
    
    w_s = {}
    for station_id, link_id in charging_stations.items():
        mu_s = station_params[station_id]['mu_s']
        w_s[station_id] = x[link_id] / mu_s

    U_EV = compute_ev_path_costs(lp_EV, w_s, p_s, paths_EV, od_pairs,
                                 charging_stations, idx_to_edge, G, alpha)
    
    # 5. Compute outflows (default behavior)
    f = link_outflows(x)
    
    # 6. Build routing matrix
    R = compute_routing_matrix(y_EV, y_NEV, paths_EV, paths_NEV, od_pairs, n_links)
    
    # 7. LINK DYNAMICS with special handling
    x_dot = np.zeros(n_links)
    
    for i in range(n_links):
        edge = idx_to_edge[i]
        edge_data = G.edges[edge]
        link_type = edge_data.get('link_type', 'mixed')
        
        # ORIGIN LINKS: ẋ = 0 (constant source, no accumulation)
        if link_type == 'origin':
            x_dot[i] = 0.0
            # Override outflow to be the demand
            f[i] = lambda_total.get(i, 0)
            
        # DESTINATION LINKS: ẋ = inflow - outflow (normal dynamics)
        elif link_type == 'destination':
            inflow = np.sum([R[j, i] * f[j] for j in range(n_links)])
            x_dot[i] = inflow - f[i]
            
        # EV CHARGING LINKS: Special service rate
        elif link_type == 'EV-only':
            station_id = edge_data.get('station_id')
            mu = station_params[station_id]['mu_s']
            nu = station_params[station_id].get('nu_s', 10.0)
            f[i] = min(mu, nu * x[i])
            
            inflow = np.sum([R[j, i] * f[j] for j in range(n_links)])
            x_dot[i] = inflow - f[i]
            
        # NORMAL LINKS: Standard dynamics
        else:
            inflow = np.sum([R[j, i] * f[j] for j in range(n_links)])
            x_dot[i] = inflow - f[i]
    
    # 8. PATH DYNAMICS
    y_NEV_dot_list = []
    for od in od_pairs:
        if od in y_NEV and od in lp_NEV:
            lp = lp_NEV[od]
            y = y_NEV[od]
            target_demand = lambda_NEV.get(od, 0)
            
            if target_demand > 1e-9:
                l_avg = np.sum(y * lp) / target_demand
                y_dot = eta_NEV * y * (l_avg - lp)
            else:
                y_dot = np.zeros_like(y)
            
            y_NEV_dot_list.extend(y_dot)
    
    y_EV_dot_list = []
    for od in od_pairs:
        if od in y_EV and od in U_EV:
            U = U_EV[od]
            y = y_EV[od]
            target_demand = lambda_EV.get(od, 0)
            
            if target_demand > 1e-9:
                U_avg = np.sum(y * U) / target_demand
                y_dot = eta_EV * y * (U_avg - U)
            else:
                y_dot = np.zeros_like(y)
                
            y_EV_dot_list.extend(y_dot)
            
    # 9. Price dynamics
    p_s_dot = []
    for station_id in station_ids:
        params = station_params[station_id]
        kappa_s = params['kappa_s']  # Adjustment speed
        c_s = params['c_s']          # Operating cost
        p_current = p_s[station_id]
        
        # Simple competitive adjustment: 
        # Price increases if the queue (x[link_id]) is high relative to service rate
        link_id = charging_stations[station_id]
        queue_level = x[link_id]
        
        # Logic: Adjust price to balance queue length and profit margin
        # dp/dt = kappa * (Queue_Pressure - Price_Sensitivity)
        # This is a proxy for the station's profit-maximizing behavior
        adjustment = kappa_s * (queue_level - (p_current - c_s))
        p_s_dot.append(adjustment)
    
    return np.concatenate([x_dot, y_NEV_dot_list, y_EV_dot_list, p_s_dot])

# SIMULATION SETUP AND EXECUTION

def run_simulation():
    """Main simulation function."""
    print("="*70)
    print("EV CHARGING STATION COMPETITION MODEL (Link-Based + Integrated Queue)")
    print("="*70)
    
    # 1. Create network (Origins/Destinations are now LINK IDs and SINK NODES)
    print("\n[1/6] Creating network...")
    G, origins, destinations, charging_stations = create_network_with_charging_stations()
    n_links = G.number_of_edges()
    print(f"   Network: {G.number_of_nodes()} nodes, {n_links} links")
    print(f"   Origin Links: {origins}")
    print(f"   Destination Sinks: {destinations}")
    print(f"   Charging stations: {list(charging_stations.keys())}")
    
    # 2. Enumerate paths (From Origin Link Start -> Sink Node)
    print("\n[2/6] Enumerating paths...")
    paths_EV, paths_NEV, edge_to_idx, idx_to_edge = enumerate_paths(
        G, origins, destinations, charging_stations)
    
    # Identify active OD pairs (Origin Link -> Sink Node)
    od_pairs = []
    for o_link in origins:
        for d_node in destinations:
            has_ev_paths = (o_link, d_node) in paths_EV and len(paths_EV[(o_link, d_node)]) > 0
            has_nev_paths = (o_link, d_node) in paths_NEV and len(paths_NEV[(o_link, d_node)]) > 0
            if has_ev_paths or has_nev_paths:
                od_pairs.append((o_link, d_node))
    
    total_ev_paths = sum(len(paths_EV.get(od, [])) for od in od_pairs)
    total_nev_paths = sum(len(paths_NEV.get(od, [])) for od in od_pairs)
    print(f"   EV paths: {total_ev_paths}")
    print(f"   NEV paths: {total_nev_paths}")
    
    # 3. Create OD demand (Mapped to Link IDs)
    print("\n[3/6] Setting up demand...")
    # Note: create_od_demand needs G to lookup origin tags
    lambda_EV, lambda_NEV, lambda_total, _ = create_od_demand(G, origins, destinations)
    
    # 4. Initialize charging stations (With nu_s parameter)
    print("\n[4/6] Initializing charging stations...")
    station_params = initialize_charging_stations(charging_stations)
    
    for station_id, params in station_params.items():
        print(f"   {station_id}: Î¼={params['mu_s']}, Î½={params['nu_s']}, p_init={params['p_s_init']}")
    
    # 5. Setting initial conditions
    print("\n[5/6] Setting initial conditions...")
    
    z0 = []
    
    # A. Link densities (x) - Initialize with small noise
    x0 = np.random.rand(n_links) * 0.1 + 0.05
    z0.extend(x0)
    
    # B. Path flows (y)
    # NEV
    for od in od_pairs:
        n_paths = len(paths_NEV.get(od, []))
        if n_paths > 0:
            # Distribute demand evenly initially
            if od in lambda_NEV:
                val = lambda_NEV[od] / n_paths
                y0 = np.ones(n_paths) * val
            else:
                y0 = np.zeros(n_paths)
            z0.extend(y0)
            
    # EV
    for od in od_pairs:
        n_paths = len(paths_EV.get(od, []))
        if n_paths > 0:
            if od in lambda_EV:
                val = lambda_EV[od] / n_paths
                y0 = np.ones(n_paths) * val
            else:
                y0 = np.zeros(n_paths)
            z0.extend(y0)
            
    # C. Queues (REMOVED!)
    # We do NOT append queue variables anymore. The queue is x[link_id].
    
    # D. Prices (p)
    for station_id in sorted(charging_stations.keys()):
        z0.append(station_params[station_id]['p_s_init'])
    
    z0 = np.array(z0)
    print(f"   State dimension: {len(z0)}")
    
    # 6. Solving dynamics
    print("\n[6/6] Solving dynamics...")
    t_span = (0.0, T_FINAL)
    t_eval = np.linspace(0, T_FINAL, N_TIME_POINTS)
    
    try:
        sol = solve_ivp(
            lambda t, z: coupled_dynamics_rhs(
                t, z, G, paths_EV, paths_NEV, od_pairs,
                charging_stations, station_params,
                lambda_EV, lambda_NEV, lambda_total,
                edge_to_idx, idx_to_edge,
                eta_EV, eta_NEV, alpha
            ),
            t_span, z0, t_eval=t_eval, method='BDF', 
            rtol=SOLVER_RTOL, atol=SOLVER_ATOL, max_step=MAX_STEP
        )
    except Exception as e:
        print(f"Solver failed: {e}")
        return

    if not sol.success:
        print(f"   âš  Integration warning: {sol.message}")
    else:
        print("   âœ“ Integration successful")

    # 7. Extracting trajectories
    print("\n[7/7] Extracting trajectories...")
    idx = 0
    
    # Extract x (Link Densities)
    x_traj = sol.y[idx:idx + n_links, :]
    idx += n_links
    
    # Extract y (Path Flows)
    y_NEV_traj = {}
    for od in od_pairs:
        n_paths = len(paths_NEV.get(od, []))
        if n_paths > 0:
            y_NEV_traj[od] = sol.y[idx:idx + n_paths, :]
            idx += n_paths
    
    y_EV_traj = {}
    for od in od_pairs:
        n_paths = len(paths_EV.get(od, []))
        if n_paths > 0:
            y_EV_traj[od] = sol.y[idx:idx + n_paths, :]
            idx += n_paths
            
    # Extract Prices (p) - immediately follows flows now
    p_s_traj = {}
    station_ids = sorted(charging_stations.keys())
    for station_id in station_ids:
        p_s_traj[station_id] = sol.y[idx, :]
        idx += 1
        
    # DERIVE Queues (q) from x
    # q_s(t) is simply the density on the charging link
    q_s_traj = {}
    for station_id, link_id in charging_stations.items():
        q_s_traj[station_id] = x_traj[link_id, :]
    
    t = sol.t
    
    # 8. Check stability & Visualize
    print("\n[ANALYSIS] Checking system stability...")
    check_stability_condition(x_traj, y_NEV_traj, y_EV_traj, q_s_traj, t)
    
    print("\n" + "="*70)
    print("GENERATING VISUALIZATIONS")
    print("="*70)
    # Stability check
    print("\n[ANALYSIS] Checking system stability...")
    is_stable, stability_report = check_stability_condition(x_traj, y_NEV_traj, y_EV_traj, q_s_traj, t)
    
    # 1. Network animation (FIRST - most engaging)
    print("\n[VIZ 1/4] Network animation...")
    animate_network(G, x_traj, y_NEV_traj, y_EV_traj, q_s_traj, t,
               paths_EV, paths_NEV, od_pairs, edge_to_idx, idx_to_edge,
               charging_stations, lambda_total)
    
    # 2. Path demands (SECOND - shows convergence)
    print("[VIZ 2/4] Path demands...")
    plot_path_demands(y_NEV_traj, y_EV_traj, t, od_pairs, G, idx_to_edge)
    
    # 3. Link densities (THIRD - shows traffic evolution)
    print("[VIZ 3/4] Link densities...")
    plot_link_densities(x_traj, t, idx_to_edge, G)
    
    # 4. Charging station competition (FOURTH - shows final results)
    print("[VIZ 4/4] Charging station competition...")
    plot_charging_station_metrics(q_s_traj, p_s_traj, t, charging_stations, 
                                  station_params, x_traj, paths_EV, od_pairs)


# ============================================================================
# VISUALIZATION
# ============================================================================
def check_stability_condition(x_traj, y_NEV_traj, y_EV_traj, q_s_traj, t):
    """
    Checks necessary conditions for system stability.
    Returns True if stable, False otherwise.
    """
    print("\n" + "="*40)
    print("STABILITY CHECKER")
    print("="*40)
    
    is_stable = True
    
    # 1. Check Link Density Convergence (x)
    # Standard deviation of the last 10% of time steps should be small
    last_10_percent = int(len(t) * 0.1)
    x_tail = x_traj[:, -last_10_percent:]
    x_std = np.std(x_tail, axis=1)
    if np.any(x_std > 5e-3):
        print(f"[FAIL] Link Densities are oscillating (Max Std: {np.max(x_std):.5f})")
        is_stable = False
    else:
        print("[PASS] Link Densities have converged.")

    # 2. Check Queue Boundedness (q)
    # Queue should not be growing linearly at the end
    for s_id, q_data in q_s_traj.items():
        q_tail = q_data[-last_10_percent:]
        # Calculate slope (growth rate)
        q_slope = (q_tail[-1] - q_tail[0]) / (t[-1] - t[-last_10_percent])
        
        if q_slope > 0.01 and q_tail[-1] > 1.0: # Growing queue
            print(f"[FAIL] Queue at Station {s_id} is growing unstable (Slope: {q_slope:.4f})")
            is_stable = False
        else:
            print(f"[PASS] Queue at Station {s_id} is stable.")

    print("-" * 40)
    if is_stable:
        print(">>> SYSTEM STATUS: STABLE EQUILIBRIUM REACHED <<<")
    else:
        print(">>> SYSTEM STATUS: UNSTABLE OR OSCILLATING <<<")
    print("="*40 + "\n")
    
    # --- THIS RETURN STATEMENT WAS MISSING ---
    return is_stable, {}

def plot_link_densities(x_traj, t, idx_to_edge, G):
    """Plot link density evolution with fixed spacing."""
    n_links = x_traj.shape[0]
    n_cols = 3
    n_rows = (n_links + n_cols - 1) // n_cols
    
    fig, axs = plt.subplots(n_rows, n_cols, figsize=(15, 5*n_rows))
    fig.suptitle('Link Traffic Densities', fontsize=16, fontweight='bold', y=0.99)
    
    # FIX: Add height spacing (hspace) to prevent text overlap
    plt.subplots_adjust(hspace=0.6, wspace=0.3, top=0.93, bottom=0.08)
    
    axs = axs.flatten() if n_links > 1 else [axs]
    
    for i in range(n_links):
        edge = idx_to_edge[i]
        edge_data = G.edges[edge]
        link_type = edge_data.get('link_type', 'mixed')
        station_info = f" ({edge_data.get('station_id', '')})" if link_type == 'EV-only' else ''
        
        color = 'green' if link_type == 'EV-only' else 'blue'
        axs[i].plot(t, x_traj[i], label=f"Link {i}", color=color, linewidth=2)
        axs[i].set_title(f"Link {i}: {edge[0]}â†’{edge[1]} [{link_type}]{station_info}", 
                        fontsize=10, pad=8)
        axs[i].set_xlabel("Time", fontsize=9)
        axs[i].set_ylabel(r"Density $x_i$", fontsize=9)
        axs[i].grid(True, alpha=0.3)
        axs[i].legend(fontsize=8)
    
    for k in range(n_links, len(axs)):
        axs[k].axis('off')
    
    plt.show()

def plot_path_demands(y_NEV_traj, y_EV_traj, t, od_pairs, G, idx_to_edge):
    """
    Generalized plotter that dynamically grids available path groups
    and uses proper Origin/Destination names from the graph data.
    """
    plots_to_render = []

    # Helper to get friendly name from link ID
    def get_node_name(link_id, is_origin=True):
        if 0 <= link_id < len(idx_to_edge):
            edge_key = idx_to_edge[link_id]
            data = G.edges[edge_key]
            if is_origin:
                return data.get('origin_id', f"Link{link_id}")
            else:
                return data.get('dest_id', f"Link{link_id}")
        return f"Link{link_id}"

    for od in od_pairs:
        o_id, d_id = od
        # Resolve proper names
        o_name = get_node_name(o_id, is_origin=True)
        d_name = get_node_name(d_id, is_origin=False)

        # Check NEV paths
        if od in y_NEV_traj and y_NEV_traj[od].shape[0] > 0:
            plots_to_render.append({
                'title': f"NEV: {o_name} → {d_name}",
                'data': y_NEV_traj[od],
                'style': '-',
            })
            
        # Check EV paths
        if od in y_EV_traj and y_EV_traj[od].shape[0] > 0:
            plots_to_render.append({
                'title': f"EV: {o_name} → {d_name}",
                'data': y_EV_traj[od],
                'style': '--',
            })

    # Determine Grid Dimensions
    total_plots = len(plots_to_render)
    if total_plots == 0:
        print("No active paths to plot.")
        return

    n_cols = 2
    n_rows = (total_plots + n_cols - 1) // n_cols

    fig, axs = plt.subplots(n_rows, n_cols, figsize=(14, 4 * n_rows))
    fig.suptitle('Path Demand Dynamics (All Available Paths)', fontsize=16, fontweight='bold', y=0.99)
    plt.subplots_adjust(hspace=0.4, wspace=0.25, top=0.93, bottom=0.05)

    if total_plots > 1:
        axs = axs.flatten()
    else:
        axs = [axs]

    # Render
    for i, ax in enumerate(axs):
        if i < total_plots:
            plot_info = plots_to_render[i]
            data = plot_info['data']
            
            for p_idx in range(data.shape[0]):
                ax.plot(t, data[p_idx], 
                       label=f"Path {p_idx}", 
                       linewidth=2, 
                       linestyle=plot_info['style'])
            
            ax.set_title(plot_info['title'], fontsize=11, fontweight='bold')
            ax.set_xlabel("Time", fontsize=9)
            ax.set_ylabel("Path Flow", fontsize=9)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8, loc='best')
        else:
            ax.axis('off')

    plt.show()


def plot_charging_station_metrics(q_s_traj, p_s_traj, t, charging_stations, 
                                   station_params, x_traj, paths_EV, od_pairs):
    """Plot charging station competition metrics."""
    
    n_stations = len(charging_stations)
    station_ids = sorted(charging_stations.keys())
    
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Charging Station Competition Metrics', fontsize=16, fontweight='bold')
    
    # 1. Queue lengths
    ax = axs[0, 0]
    for station_id in station_ids:
        ax.plot(t, q_s_traj[station_id], label=station_id, linewidth=2, marker='o', markersize=2)
    ax.set_title('Queue Lengths at Charging Stations')
    ax.set_xlabel('Time')
    ax.set_ylabel('Queue Length (vehicles)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # 2. Waiting times
    ax = axs[0, 1]
    for station_id in station_ids:
        mu_s = station_params[station_id]['mu_s']
        waiting_time = q_s_traj[station_id] / mu_s
        ax.plot(t, waiting_time, label=station_id, linewidth=2, marker='s', markersize=2)
    ax.set_title('Waiting Times at Charging Stations')
    ax.set_xlabel('Time')
    ax.set_ylabel('Waiting Time')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # 3. Utilization rates
    ax = axs[1, 0]
    for station_id in station_ids:
        link_id = charging_stations[station_id]
        mu_s = station_params[station_id]['mu_s']
        arrival_rate = np.minimum(x_traj[link_id], 0.5)  # Outflow = arrival
        utilization = np.minimum(arrival_rate / mu_s, 1.0)
        ax.plot(t, utilization * 100, label=station_id, linewidth=2)
    ax.set_title('Station Utilization Rates')
    ax.set_xlabel('Time')
    ax.set_ylabel('Utilization (%)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_ylim([0, 105])
    
    # 4. Market share (final time snapshot)
    ax = axs[1, 1]
    market_share = []
    for station_id in station_ids:
        link_id = charging_stations[station_id]
        avg_flow = np.mean(x_traj[link_id, -100:])  # Average over last 100 time points
        market_share.append(avg_flow)
    
    total_flow = sum(market_share)
    if total_flow > 0:
        market_share = [ms / total_flow * 100 for ms in market_share]
    else:
        market_share = [0] * len(station_ids)
    
    colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24']
    ax.bar(station_ids, market_share, color=colors[:len(station_ids)])
    ax.set_title('Market Share (Average Flow)')
    ax.set_ylabel('Market Share (%)')
    ax.grid(True, alpha=0.3, axis='y')
    
    for i, (sid, ms) in enumerate(zip(station_ids, market_share)):
        ax.text(i, ms + 2, f'{ms:.1f}%', ha='center', fontweight='bold')
    
    plt.tight_layout()
    plt.show()


def animate_network(G, x_traj, y_NEV_traj, y_EV_traj, q_s_traj, t,
                   paths_EV, paths_NEV, od_pairs, edge_to_idx, idx_to_edge,
                   charging_stations, lambda_total):
    """
    Draw final network state as a static visualization.
    Shows the equilibrium network with final densities.
    """
    import matplotlib.colors as mcolors
    
    # Use final time step
    frame = -1
    
    norm = mcolors.Normalize(vmin=0, vmax=max(np.max(x_traj), 0.5))
    cmap = plt.cm.YlOrRd  # Yellow to Red for density
    cmap2 = plt.cm.magma
    pos = nx.get_node_attributes(G, 'pos')
    edges = list(G.edges(keys=True))
    n_links = len(edges)
    
    fig, ax = plt.subplots(figsize=(14, 10))
    
    ax.set_title(f"Network State at Equilibrium (t={t[frame]:.2f}s)", 
                fontsize=16, fontweight='bold', pad=25, color='#2c3e50')
    
    # Draw NODES only (no virtual nodes)
    node_colors = ['#ffeaa7'] * len(G.nodes())
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors,
                          node_size=1800, edgecolors='black', linewidths=2)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=11, font_weight='bold')
    
    # Draw EDGES with proper handling
    for i, (u, v, k) in enumerate(edges):
        edge_data = G.edges[(u, v, k)]
        link_type = edge_data.get('link_type', 'mixed')
        x_val = x_traj[i, frame]
        link_id_actual = edge_data.get('link_id')
        dens = max(0, x_traj[i, frame])  # Clamp to non-negative
        
        # Skip drawing self-loop origin/destination links
        if u == v:
            # Just show label near node
            label_text = ""
            if link_type == 'origin':
                lam_val = lambda_total.get(link_id_actual, 0)
                label_text = f"O: λ={lam_val:.2f}"
                ax.text(pos[u][0] - 0.7, pos[u][1] + 0.4, label_text,
                       fontsize=10, ha='center', fontweight='bold',
                       bbox=dict(facecolor='red', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.3'))
            elif link_type == 'destination':
                label_text = f"D: x={dens:.2f}"
                ax.text(pos[u][0] + 0.7, pos[u][1] - 0.4, label_text,
                       fontsize=10, ha='center', fontweight='bold',
                       bbox=dict(facecolor='cyan', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.3'))
            continue
        
        # Style based on link type
        if link_type == 'EV-only':
            color = cmap2(norm(x_val))
            style = (0, (5, 2))
            width = 2 + (x_val * 5)
            connection = "arc3,rad=0.3"
        else:
            color = cmap(norm(x_val))
            style = '-'
            width = 2 + (x_val * 5)
            connection = "arc3,rad=0.0"
        
        # Handle parallel edges
        if (u, v, 0) in edges and (u, v, 1) in edges:
            if k == 0:
                connection = "arc3,rad=-0.25"
            else:
                connection = "arc3,rad=0.25"
        
        # Draw edge
        ax.annotate("",
                   xy=pos[v], xycoords='data',
                   xytext=pos[u], textcoords='data',
                   arrowprops=dict(arrowstyle="->,head_length=0.6,head_width=0.4", 
                                 color=color, lw=width,
                                 linestyle=style, connectionstyle=connection,
                                 shrinkA=15, shrinkB=15, alpha=0.9))
        
        # Label
        mid_x = (pos[u][0] + pos[v][0]) / 2
        mid_y = (pos[u][1] + pos[v][1]) / 2
        dx = pos[v][0] - pos[u][0]
        dy = pos[v][1] - pos[u][1]
        length = np.sqrt(dx**2 + dy**2)
        
        dist = 0.5
        if 'rad=0.3' in connection or 'rad=0.25' in connection:
            off_x, off_y = (-dy/length) * dist, (dx/length) * dist
        elif 'rad=-0.3' in connection or 'rad=-0.25' in connection:
            off_x, off_y = (dy/length) * dist, (-dx/length) * dist
        else:
            off_x, off_y = 0, 0.25
        
        if link_type == 'EV-only':
            station_id = edge_data.get('station_id', '')
            queue = q_s_traj[station_id][frame]
            label_text = f"{station_id}\nq={queue:.2f}"
            bgcolor = '#d4edda'
        else:
            label_text = f"x={dens:.2f}"
            bgcolor = 'white'
        
        ax.text(mid_x + off_x, mid_y + off_y, label_text, fontsize=8, ha='center',
               bbox=dict(boxstyle='round,pad=0.3', facecolor=bgcolor, alpha=0.8, edgecolor='gray'))
    
    ax.set_xlim(-1.5, 9)
    ax.set_ylim(-2.5, 7)
    ax.axis('off')
    plt.tight_layout()
    plt.show()

# ============================================================================
# MAIN EXECUTION
# ============================================================================
if __name__ == "__main__":
    run_simulation()
    print("\n" + "="*70)
    print("SIMULATION COMPLETE")
    print("="*70)
